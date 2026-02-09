# Homebrew formula for iMessages AI
# Install: brew tap maxawad/imessages-ai && brew install imessages-ai
# Or:      brew install maxawad/imessages-ai/imessages-ai

class ImessagesAi < Formula
  desc "ChatGPT-powered auto-responder for iMessage"
  homepage "https://github.com/maxawad/imessages-ai"
  url "https://github.com/maxawad/imessages-ai/archive/refs/tags/v1.0.0.tar.gz"
  sha256 "" # TODO: fill after first release
  license "MIT"
  head "https://github.com/maxawad/imessages-ai.git", branch: "main"

  depends_on :macos
  depends_on "python@3"

  resource "openai" do
    url "https://files.pythonhosted.org/packages/openai/openai-2.17.0.tar.gz"
    sha256 "" # TODO: fill after pinning
  end

  def install
    # Install Python library into libexec virtualenv
    venv = virtualenv_create(libexec, "python3")
    venv.pip_install resources

    # Install the main Python module
    (libexec/"lib").install "lib/imessages_ai.py"

    # Install the CLI wrapper, rewriting LIB_DIR to point at libexec
    inreplace "bin/imessages-ai" do |s|
      s.gsub! 'LIB_DIR="$(cd "$SCRIPT_DIR/../lib" && pwd)"',
              "LIB_DIR=\"#{libexec}/lib\""
      # Use the venv python
      s.gsub! 'PYTHON3="$(which python3)"',
              "PYTHON3=\"#{libexec}/bin/python3\""
      s.gsub! 'exec python3 "$LIB_DIR/imessages_ai.py"',
              "exec \"#{libexec}/bin/python3\" \"$LIB_DIR/imessages_ai.py\""
    end
    bin.install "bin/imessages-ai"
  end

  def caveats
    <<~EOS
      To get started:

        imessages-ai setup

      This will walk you through entering your OpenAI API key and preferences.

      Then start the listener:

        imessages-ai start        # background service (auto-starts on login)
        imessages-ai run          # foreground mode

      IMPORTANT: Your terminal needs Full Disk Access to read Messages.
        System Settings → Privacy & Security → Full Disk Access → enable Terminal/iTerm

      Config: ~/.config/imessages-ai/config
      Logs:   ~/Library/Logs/imessages-ai/
    EOS
  end

  service do
    run [opt_bin/"imessages-ai", "run"]
    keep_alive true
    log_path var/"log/imessages-ai/output.log"
    error_log_path var/"log/imessages-ai/error.log"
    working_dir Dir.home
  end

  test do
    assert_match "imessages-ai", shell_output("#{bin}/imessages-ai --version")
  end
end
