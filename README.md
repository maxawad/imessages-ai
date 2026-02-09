# iMessages AI

ChatGPT-powered auto-responder for Apple iMessage. Send a message starting with `@` and get an AI response back in the same conversation.

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/maxawad/imessages-ai/main/install.sh | bash
```

Or with Homebrew:

```bash
brew install maxawad/imessages-ai/imessages-ai
imessages-ai setup
```

## Usage

Send any message starting with `@` in Messages.app:

```
@list countries in latin america
```

The AI responds in the same conversation:

> 𝐻𝑒𝑟𝑒 𝑎𝑟𝑒 𝑡ℎ𝑒 𝑐𝑜𝑢𝑛𝑡𝑟𝑖𝑒𝑠 𝑖𝑛 𝐿𝑎𝑡𝑖𝑛 𝐴𝑚𝑒𝑟𝑖𝑐𝑎:
>
> 1. 𝑀𝑒𝑥𝑖𝑐𝑜
> 2. 𝐺𝑢𝑎𝑡𝑒𝑚𝑎𝑙𝑎, 𝐵𝑒𝑙𝑖𝑧𝑒, 𝐻𝑜𝑛𝑑𝑢𝑟𝑎𝑠...

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

Config lives at `~/.config/imessages-ai/config`:

```bash
OPENAI_API_KEY=sk-...    # Required
MODEL=gpt-4o             # OpenAI model
MAX_TOKENS=1024          # Max response length
TRIGGER_PREFIX=@         # Message prefix that triggers AI
POLL_INTERVAL=2          # Seconds between DB checks
ITALIC=true              # Unicode italic formatting
```

## Requirements

- macOS with Messages.app
- Python 3.9+
- OpenAI API key
- **Full Disk Access** for your terminal (System Settings → Privacy & Security → Full Disk Access)

## How It Works

1. Polls `~/Library/Messages/chat.db` for new outgoing messages
2. Detects messages starting with the trigger prefix (`@`)
3. Sends the prompt to OpenAI's ChatGPT API
4. Replies in the same conversation via AppleScript
5. Only responds to **your** messages (`is_from_me = 1`)

## License

MIT
