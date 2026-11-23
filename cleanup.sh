#!/bin/bash
# Undo what bootstrap.sh installed, so the install can be tested from scratch.
#
#   ./cleanup.sh                  # show what would be removed (changes nothing)
#   ./cleanup.sh --yes            # remove it; files are moved to ~/newmac-backup-<time>/
#   ./cleanup.sh --everything     # also remove Homebrew (and all it installed) and
#                                 # the Command Line Tools, like a brand-new Mac
#   ./cleanup.sh emacs-config     # only some tasks
#
# It refuses to start if it would lose work (uncommitted sillyfmt changes, an
# ~/.emacs that differs from dotfiles/). The backup folder has a restore.sh
# that puts everything back. Same as `python3.14 bootstrap.py --uninstall`.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

for prefix in /opt/homebrew /usr/local; do
    PYTHON="$prefix/opt/python@3.14/bin/python3.14"
    [[ -x "$PYTHON" ]] && exec "$PYTHON" "$SCRIPT_DIR/bootstrap.py" --uninstall "$@"
done
echo "error: Python 3.14 isn't installed. Nothing to clean up: bootstrap.sh installs it first." >&2
exit 1
