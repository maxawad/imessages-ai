#!/usr/bin/env python3
"""
iMessages AI — ChatGPT-powered auto-responder for Apple Messages.

Monitors ~/Library/Messages/chat.db for outgoing messages that start with
a trigger prefix (default: @). Sends the prompt to OpenAI and replies in
the same conversation via AppleScript.

Config is read from ~/.config/imessages-ai/config (shell-style KEY=VALUE).
"""

from __future__ import annotations

import os
import re
import sqlite3
import subprocess
import sys
import time
import logging
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

CONFIG_DIR = Path.home() / ".config" / "imessages-ai"
CONFIG_FILE = CONFIG_DIR / "config"
LOG_DIR = Path.home() / "Library" / "Logs" / "imessages-ai"
MESSAGES_DB = Path.home() / "Library" / "Messages" / "chat.db"

# ---------------------------------------------------------------------------
# Defaults (overridable in config file)
# ---------------------------------------------------------------------------

DEFAULTS = {
    "OPENAI_API_KEY": "",
    "MODEL": "gpt-4o",
    "MAX_TOKENS": "1024",
    "TRIGGER_PREFIX": "@",
    "POLL_INTERVAL": "2",
    "ITALIC": "true",
}

# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------


def load_config() -> dict[str, str]:
    """Load config from ~/.config/imessages-ai/config and environment."""
    cfg = dict(DEFAULTS)

    # Read config file
    if CONFIG_FILE.exists():
        for line in CONFIG_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                cfg[key.strip()] = value.strip().strip('"').strip("'")

    # Environment variables always win
    for key in cfg:
        env_val = os.environ.get(key)
        if env_val:
            cfg[key] = env_val

    return cfg


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


def setup_logging():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stderr),
            logging.FileHandler(LOG_DIR / "imessages-ai.log"),
        ],
    )
    return logging.getLogger("imessages-ai")


log = setup_logging()

# ---------------------------------------------------------------------------
# OpenAI client (lazy init)
# ---------------------------------------------------------------------------

_client = None


def get_openai_client(api_key: str):
    global _client
    if _client is None:
        try:
            from openai import OpenAI
        except ImportError:
            log.error("openai package not installed. Run: pip3 install openai")
            raise SystemExit(1)
        _client = OpenAI(api_key=api_key)
    return _client


# ---------------------------------------------------------------------------
# Text extraction from Messages database
# ---------------------------------------------------------------------------


def extract_text_from_attributed_body(blob: bytes) -> Optional[str]:
    """Extract plain text from the attributedBody NSArchiver blob.

    Binary layout::

        NSString <ctrl> + <length-prefix> <UTF-8 text> \\x86\\x84 <attrs…>

    Length prefix after ``+``:
      - 0x00–0x7F → single-byte length; text at +1
      - 0x81      → 2-byte LE length; text at +3
      - 0x82      → 3-byte LE length; text at +4
    """
    if not blob:
        return None
    try:
        for marker in [b"NSString", b"NSMutableString"]:
            idx = blob.find(marker)
            if idx != -1:
                remaining = blob[idx + len(marker) :]
                break
        else:
            return None

        plus_idx = remaining.find(b"\x2b")
        if plus_idx == -1:
            return None
        remaining = remaining[plus_idx + 1 :]

        if not remaining:
            return None
        first = remaining[0]
        if first < 0x80:
            remaining = remaining[1:]
        elif first == 0x81:
            remaining = remaining[3:]
        elif first == 0x82:
            remaining = remaining[4:]
        else:
            remaining = remaining[1:]

        end_idx = remaining.find(b"\x86\x84")
        if end_idx != -1:
            remaining = remaining[:end_idx]

        text = remaining.decode("utf-8", errors="ignore").strip()
        return text if text else None
    except Exception:
        return None


def get_message_text(text_col: Optional[str], body: Optional[bytes]) -> Optional[str]:
    if text_col and text_col.strip():
        return text_col.strip()
    return extract_text_from_attributed_body(body)


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{MESSAGES_DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def get_latest_rowid(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT MAX(ROWID) FROM message").fetchone()
    return row[0] or 0


def get_new_messages(conn: sqlite3.Connection, after_rowid: int) -> list[dict]:
    cursor = conn.execute(
        """
        SELECT m.ROWID, m.text, m.attributedBody, m.is_from_me,
               c.guid AS chat_guid, c.chat_identifier
        FROM message m
        JOIN chat_message_join cmj ON m.ROWID = cmj.message_id
        JOIN chat c ON cmj.chat_id = c.ROWID
        WHERE m.ROWID > ? AND m.is_from_me = 1
        ORDER BY m.ROWID ASC
        """,
        (after_rowid,),
    )
    messages = []
    for row in cursor.fetchall():
        text = get_message_text(row["text"], row["attributedBody"])
        if text:
            messages.append(
                {
                    "rowid": row["ROWID"],
                    "text": text,
                    "chat_guid": row["chat_guid"],
                    "chat_identifier": row["chat_identifier"],
                }
            )
    return messages


# ---------------------------------------------------------------------------
# Unicode italic formatting
# ---------------------------------------------------------------------------

_ITALIC_MAP = {}
for _i, _ch in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
    _ITALIC_MAP[_ch] = chr(0x1D434 + _i)
for _i, _ch in enumerate("abcdefghijklmnopqrstuvwxyz"):
    _ITALIC_MAP[_ch] = chr(0x210E) if _ch == "h" else chr(0x1D44E + _i)


def to_italic(text: str) -> str:
    """Convert ASCII letters → Unicode Mathematical Italic glyphs."""
    return "".join(_ITALIC_MAP.get(ch, ch) for ch in text)


# ---------------------------------------------------------------------------
# Markdown stripper
# ---------------------------------------------------------------------------


def strip_markdown(text: str) -> str:
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"\1", text)
    text = re.sub(r"(?<!_)_(?!_)(.+?)(?<!_)_(?!_)", r"\1", text)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\[(.+?)\]\((.+?)\)", r"\1 (\2)", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    return text


# ---------------------------------------------------------------------------
# ChatGPT
# ---------------------------------------------------------------------------


def ask_chatgpt(prompt: str, cfg: dict) -> str:
    client = get_openai_client(cfg["OPENAI_API_KEY"])
    log.info("Sending to ChatGPT: %s...", prompt[:80])

    response = client.chat.completions.create(
        model=cfg["MODEL"],
        max_tokens=int(cfg["MAX_TOKENS"]),
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant responding via iMessage. "
                    "Keep responses concise and suitable for text messages. "
                    "Use plain text only. Use numbered lists, bullet points (•), "
                    "and short paragraphs for structure. "
                    "NEVER use markdown: no **, no __, no ##, no ` backticks, "
                    "no [links](url). Just plain text."
                ),
            },
            {"role": "user", "content": prompt},
        ],
    )
    return strip_markdown(response.choices[0].message.content.strip())


# ---------------------------------------------------------------------------
# Send via AppleScript
# ---------------------------------------------------------------------------


def send_imessage(chat_guid: str, text: str) -> bool:
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    script = (
        'tell application "Messages"\n'
        f'  set targetChat to a reference to chat id "{chat_guid}"\n'
        f'  send "{escaped}" to targetChat\n'
        "end tell"
    )
    try:
        r = subprocess.run(
            ["osascript", "-e", script], capture_output=True, text=True, timeout=30
        )
        if r.returncode == 0:
            log.info("Sent reply to %s", chat_guid)
            return True
        log.error("AppleScript error: %s", r.stderr.strip())
        return False
    except subprocess.TimeoutExpired:
        log.error("AppleScript timed out")
        return False
    except Exception as e:
        log.error("Failed to send message: %s", e)
        return False


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


def run():
    cfg = load_config()

    if not cfg["OPENAI_API_KEY"]:
        log.error(
            "OPENAI_API_KEY not set. Run: imessages-ai setup"
        )
        raise SystemExit(1)

    trigger = cfg["TRIGGER_PREFIX"]
    poll = int(cfg["POLL_INTERVAL"])
    italic = cfg["ITALIC"].lower() in ("true", "1", "yes")

    log.info("=" * 55)
    log.info("iMessages AI — listening for '%s' messages", trigger)
    log.info("  Model:   %s", cfg["MODEL"])
    log.info("  Italic:  %s", italic)
    log.info("  Config:  %s", CONFIG_FILE)
    log.info("  Logs:    %s", LOG_DIR / "imessages-ai.log")
    log.info("=" * 55)

    try:
        conn = get_db_connection()
        last_rowid = get_latest_rowid(conn)
        conn.close()
        log.info("Messages DB OK — starting from ROWID %d", last_rowid)
    except sqlite3.OperationalError as e:
        log.error("Cannot read Messages DB: %s", e)
        log.error(
            "Fix: System Settings → Privacy & Security → Full Disk Access → enable your terminal"
        )
        raise SystemExit(1)

    # Quick OpenAI smoke test
    get_openai_client(cfg["OPENAI_API_KEY"])
    log.info("OpenAI client ready")
    log.info("Listening...\n")

    processed: set[int] = set()

    while True:
        try:
            conn = get_db_connection()
            new = get_new_messages(conn, last_rowid)
            conn.close()

            for msg in new:
                rid = msg["rowid"]
                if rid > last_rowid:
                    last_rowid = rid
                if rid in processed:
                    continue

                text = msg["text"]
                if not text.startswith(trigger):
                    continue

                prompt = text[len(trigger) :].strip()
                if not prompt:
                    continue

                processed.add(rid)
                log.info("Triggered! Chat: %s", msg["chat_identifier"])
                log.info("  Prompt: %s", prompt)

                try:
                    reply = ask_chatgpt(prompt, cfg)
                    if italic:
                        reply = to_italic(reply)
                    log.info("  Reply: %s...", reply[:100])
                    time.sleep(1)
                    ok = send_imessage(msg["chat_guid"], reply)
                    if ok:
                        log.info("  Delivered ✓")
                    else:
                        log.warning("  Delivery failed")
                except Exception as e:
                    log.error("  Error: %s", e)

            if len(processed) > 1000:
                processed.clear()

        except sqlite3.OperationalError as e:
            log.warning("DB busy: %s (retrying…)", e)
        except KeyboardInterrupt:
            log.info("\nStopped.")
            break
        except Exception as e:
            log.error("Unexpected: %s", e)

        time.sleep(poll)


if __name__ == "__main__":
    run()
