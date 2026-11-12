# iMessages AI

A small macOS tool that lets you talk to ChatGPT from inside Messages. Type a message that starts with `@` in any conversation, and the answer appears in that same conversation a few seconds later.

## What it does

- Watches your local Messages database for new outgoing messages that start with a trigger prefix (default `@`).
- Sends the rest of the message to the OpenAI chat API.
- Replies in the same conversation using AppleScript.
- Only reacts to messages you send yourself, never to messages from other people.
- Strips markdown from answers and can format replies in Unicode italics so they stand out.
- Runs in the foreground or as a background service that starts at login (launchd).

Example:

```
@list countries in latin america
```

The reply arrives in the same chat:

> 𝐻𝑒𝑟𝑒 𝑎𝑟𝑒 𝑡ℎ𝑒 𝑐𝑜𝑢𝑛𝑡𝑟𝑖𝑒𝑠 𝑖𝑛 𝐿𝑎𝑡𝑖𝑛 𝐴𝑚𝑒𝑟𝑖𝑐𝑎:
>
> 1. 𝑀𝑒𝑥𝑖𝑐𝑜
> 2. 𝐺𝑢𝑎𝑡𝑒𝑚𝑎𝑙𝑎, 𝐵𝑒𝑙𝑖𝑧𝑒, 𝐻𝑜𝑛𝑑𝑢𝑟𝑎𝑠...

## Tech stack

- Python 3.9+ (standard library plus the `openai` package)
- Bash CLI wrapper (`bin/imessages-ai`)
- SQLite (reads `~/Library/Messages/chat.db` read-only)
- AppleScript via `osascript` to send replies
- launchd for the background service
- Homebrew formula (`Formula/imessages-ai.rb`)

## Status

Working prototype. It needs your own OpenAI API key and only runs on macOS. There is no web demo, because it depends on the local Messages app.

## Requirements

- macOS with Messages.app signed in to iMessage
- Python 3.9 or newer
- An OpenAI API key
- Full Disk Access for your terminal app (System Settings, Privacy and Security, Full Disk Access), so it can read the Messages database

## Install and run

### From source (works without Homebrew)

```bash
git clone https://github.com/maxawad/imessages-ai.git
cd imessages-ai
pip3 install -r requirements.txt
./bin/imessages-ai setup     # asks for your API key, model and prefix
./bin/imessages-ai run       # run in the foreground, Ctrl+C to stop
```

Then send yourself a message such as `@what is the capital of France` in Messages.

### One-line installer

```bash
curl -fsSL https://raw.githubusercontent.com/maxawad/imessages-ai/main/install.sh | bash
```

This uses Homebrew and the `maxawad/tap` tap, so it needs that tap to be published and working.

## Commands

```bash
imessages-ai setup      # Interactive configuration (API key, model, etc.)
imessages-ai start      # Run as background service (auto-starts on login)
imessages-ai stop       # Stop background service
imessages-ai restart    # Restart service
imessages-ai run        # Run in foreground (Ctrl+C to stop)
imessages-ai status     # Check config, service, and DB access
imessages-ai logs       # Tail the log file
imessages-ai uninstall  # Remove service and config
```

## Configuration

Settings live in `~/.config/imessages-ai/config`, outside the repository. Your API key is stored there and never committed. Each value can also be set as an environment variable of the same name.

```bash
OPENAI_API_KEY=your-key-here   # Required
MODEL=gpt-4o                   # OpenAI model
MAX_TOKENS=1024                # Max response length
TRIGGER_PREFIX=@               # Message prefix that triggers AI
POLL_INTERVAL=2                # Seconds between DB checks
ITALIC=true                    # Unicode italic formatting
```

## How it works

1. Polls `~/Library/Messages/chat.db` for new outgoing messages.
2. Detects messages starting with the trigger prefix.
3. Sends the prompt to the OpenAI chat completions API.
4. Replies in the same conversation via AppleScript.
5. Only responds to your own messages (`is_from_me = 1`).

Note that the text of your triggered messages is sent to OpenAI, so avoid using the prefix for anything private.

## Project layout

- `bin/imessages-ai`: command line wrapper (setup, service control, status)
- `lib/imessages_ai.py`: the message watcher and OpenAI client
- `install.sh`: one-line installer
- `Formula/imessages-ai.rb`: Homebrew formula

## License

MIT, see `LICENSE`.
