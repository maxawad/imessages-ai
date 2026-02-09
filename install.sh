#!/bin/bash
# iMessages AI — one-line installer
# Usage: curl -fsSL https://raw.githubusercontent.com/maxawad/imessages-ai/main/install.sh | bash
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

echo ""
echo -e "${BOLD}╔══════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║        iMessages AI — Installer          ║${NC}"
echo -e "${BOLD}║  ChatGPT auto-responder for iMessage     ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════╝${NC}"
echo ""

# ---- macOS check ----
if [[ "$(uname)" != "Darwin" ]]; then
    echo -e "${RED}Error: iMessages AI requires macOS.${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} macOS detected"

# ---- Homebrew ----
if command -v brew &>/dev/null; then
    echo -e "${GREEN}✓${NC} Homebrew found"
else
    echo -e "${YELLOW}Homebrew not found. Installing...${NC}"
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

    # Add brew to PATH for Apple Silicon
    if [ -f "/opt/homebrew/bin/brew" ]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi
    echo -e "${GREEN}✓${NC} Homebrew installed"
fi

# ---- Python 3 ----
if command -v python3 &>/dev/null; then
    PY_VER=$(python3 --version 2>&1 | awk '{print $2}')
    echo -e "${GREEN}✓${NC} Python ${PY_VER} found"
else
    echo -e "${YELLOW}Installing Python 3 via Homebrew...${NC}"
    brew install python@3
    echo -e "${GREEN}✓${NC} Python installed"
fi

# ---- Install via Homebrew tap ----
echo ""
echo -e "${BLUE}Installing iMessages AI...${NC}"

if brew list imessages-ai &>/dev/null 2>&1; then
    echo -e "${YELLOW}Upgrading existing installation...${NC}"
    brew upgrade maxawad/imessages-ai/imessages-ai || true
else
    brew tap maxawad/imessages-ai 2>/dev/null || true
    brew install maxawad/imessages-ai/imessages-ai
fi

echo ""
echo -e "${GREEN}✓ iMessages AI installed!${NC}"
echo ""

# ---- Run setup ----
echo -e "${BOLD}Let's configure it now...${NC}"
echo ""
imessages-ai setup

# ---- Offer to start ----
echo ""
read -rp "$(echo -e "${BOLD}Start iMessages AI now? [Y/n]${NC} ")" start_now
if [[ ! "$start_now" =~ ^[Nn] ]]; then
    imessages-ai start
fi

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║          Installation complete!          ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
echo ""
echo "  Send a message starting with @ in iMessage to use ChatGPT!"
echo ""
echo "  Commands:"
echo "    imessages-ai status    Check if it's running"
echo "    imessages-ai logs      View live logs"
echo "    imessages-ai stop      Stop the service"
echo "    imessages-ai setup     Reconfigure"
echo ""
