#!/bin/bash
# One-line setup for a brand-new Mac. No git or Command Line Tools needed:
#
#   curl -fsSL https://raw.githubusercontent.com/thomask-m/tools/main/install.sh | bash
#
# Downloads this repo to ~/proj/tools (or $TOOLS_DIR) and runs bootstrap.sh,
# which installs the Command Line Tools without a dialog. Pass bootstrap
# arguments after `bash -s --`, e.g. `... | bash -s -- --dry-run`.
set -euo pipefail

DEST="${TOOLS_DIR:-$HOME/proj/tools}"
TARBALL="https://github.com/thomask-m/tools/archive/refs/heads/main.tar.gz"

if [[ -e "$DEST/bootstrap.sh" ]]; then
    # Never overwrite an existing copy: it may have local changes.
    echo "==> $DEST already exists; running its bootstrap.sh"
else
    echo "==> Downloading the tools repo to $DEST"
    mkdir -p "$DEST"
    curl -fsSL "$TARBALL" | tar -xz -C "$DEST" --strip-components=1
fi

# When piped from curl, stdin is this script, not the keyboard. Hand the
# terminal to bootstrap.sh so sudo and installer prompts can be answered.
if [[ ! -t 0 ]] && { : </dev/tty; } 2>/dev/null; then
    exec "$DEST/bootstrap.sh" "$@" </dev/tty
fi
exec "$DEST/bootstrap.sh" "$@"
