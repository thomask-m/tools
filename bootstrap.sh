#!/bin/bash
# One command for a brand-new Mac: ./bootstrap.sh [bootstrap.py args...]
#
# A fresh Mac only has the Python 3.9 that comes with the Xcode Command Line
# Tools, and bootstrap.py needs Python 3.14. This launcher installs the Command
# Line Tools, Homebrew and python@3.14 (each only if missing), then hands off
# to bootstrap.py with the same arguments. Safe to rerun.
#
# With --dry-run / -n it only prints what it would install.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BOOTSTRAP_PY="$SCRIPT_DIR/bootstrap.py"
BREW_INSTALL_URL="https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh"

DRY_RUN=0
for arg in "$@"; do
    case "$arg" in
        --dry-run | -n) DRY_RUN=1 ;;
        # Same meaning as bootstrap.py's --yes: let Homebrew install without prompts.
        --yes | -y) export NONINTERACTIVE=1 ;;
    esac
done

say() { printf '==> %s\n' "$*"; }
would() { printf '    [dry-run] %s\n' "$*"; }

# --- Xcode Command Line Tools --------------------------------------------- #
# Installed headlessly with softwareupdate (the same trick Homebrew's installer
# uses), so it works over SSH, e.g. in a test VM. Creating the placeholder file
# makes softwareupdate offer the Command Line Tools as an available update.
CLT_PLACEHOLDER=/tmp/.com.apple.dt.CommandLineTools.installondemand.in-progress
CLT_TIMEOUT=$((45 * 60))

# Newest "Command Line Tools" label from `softwareupdate -l` output on stdin.
clt_label() {
    grep -B 1 -E 'Command Line Tools' |
        awk -F'*' '/^ *\*/ {print $2}' |
        sed -e 's/^ *Label: //' -e 's/^ *//' |
        sort -V |
        tail -n1
}

install_clt() {
    say "Installing the Xcode Command Line Tools (may ask for your password)."
    sudo /usr/bin/touch "$CLT_PLACEHOLDER"
    local label
    label="$(/usr/sbin/softwareupdate -l 2>/dev/null | clt_label || true)"
    if [[ -n "$label" ]]; then
        sudo /usr/sbin/softwareupdate -i "$label"
        sudo /usr/bin/xcode-select --switch /Library/Developer/CommandLineTools
    fi
    sudo /bin/rm -f "$CLT_PLACEHOLDER"
    xcode-select -p >/dev/null 2>&1 && return 0

    # Fallback: the GUI installer. It needs someone at the screen.
    if [[ -n "${SSH_CONNECTION:-}" ]]; then
        echo "error: softwareupdate didn't offer the Command Line Tools, and the" >&2
        echo "fallback installer needs a GUI session. Run this at the Mac itself." >&2
        exit 1
    fi
    say "Falling back to the installer dialog. Finish the install there."
    xcode-select --install || true
    local waited=0
    until xcode-select -p >/dev/null 2>&1; do
        if ((waited >= CLT_TIMEOUT)); then
            echo "error: timed out waiting for the Command Line Tools; rerun when installed" >&2
            exit 1
        fi
        sleep 10
        waited=$((waited + 10))
    done
}

if ! xcode-select -p >/dev/null 2>&1; then
    if ((DRY_RUN)); then
        would "sudo softwareupdate -i '<Command Line Tools label>' (dialog fallback if not offered)"
    else
        install_clt
        say "Command Line Tools installed."
    fi
fi

# --- Homebrew ------------------------------------------------------------- #
if [[ "$(uname -m)" == "arm64" ]]; then
    BREW=/opt/homebrew/bin/brew
else
    BREW=/usr/local/bin/brew
fi

if [[ ! -x "$BREW" ]]; then
    if ((DRY_RUN)); then
        would "/bin/bash -c \"\$(curl -fsSL $BREW_INSTALL_URL)\""
    else
        say "Installing Homebrew."
        /bin/bash -c "$(curl -fsSL "$BREW_INSTALL_URL")"
    fi
fi

[[ -x "$BREW" ]] && eval "$("$BREW" shellenv)"

# --- Python 3.14 ---------------------------------------------------------- #
PYTHON="${BREW%/bin/brew}/opt/python@3.14/bin/python3.14"
if [[ ! -x "$PYTHON" ]]; then
    if ((DRY_RUN)); then
        would "brew install python@3.14"
    else
        say "Installing Python 3.14."
        "$BREW" install python@3.14
    fi
fi

# --- Hand off to bootstrap.py --------------------------------------------- #
if [[ -x "$PYTHON" ]]; then
    exec "$PYTHON" "$BOOTSTRAP_PY" "$@"
fi

if ((DRY_RUN)); then
    would "python3.14 $BOOTSTRAP_PY $*"
    exit 0
fi

echo "error: python3.14 not found after installing it" >&2
exit 1
