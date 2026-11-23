#!/bin/bash
# Runs INSIDE the test VM after the install, to check everything really works.
# vmtest/run.sh streams it in over SSH: `ssh admin@<vm> bash -s < verify.sh`.
#
# Two kinds of checks:
#   1. bootstrap.py's own view: every task reports done, and a second run
#      changes nothing.
#   2. Independent checks that each thing actually works (runs the tool,
#      loads the Emacs config, formats with sillyfmt...), not just that a
#      file exists.
set -uo pipefail

TOOLS="$HOME/proj/tools"
EMACS=/Applications/Emacs.app/Contents/MacOS/Emacs
PASS=0
FAIL=0

[[ -x /opt/homebrew/bin/brew ]] && eval "$(/opt/homebrew/bin/brew shellenv)"
export PATH="$HOME/.cargo/bin:$PATH"

check() {  # check "description" command...
    local desc="$1"
    shift
    local out
    if out="$("$@" 2>&1)"; then
        printf '  PASS  %s\n' "$desc"
        PASS=$((PASS + 1))
    else
        printf '  FAIL  %s\n' "$desc"
        printf '%s\n' "$out" | tail -5 | sed 's/^/          /'
        FAIL=$((FAIL + 1))
    fi
}

# --- 1. bootstrap.py's own checks ----------------------------------------- #
no_todo() { ! python3.14 "$TOOLS/bootstrap.py" --list | tee /dev/stderr | grep -q '\[todo\]'; }
second_run_is_noop() {
    local out
    out="$("$TOOLS/bootstrap.sh" -y 2>&1)" || { echo "$out"; return 1; }
    # Every task should say "already done"; a bare "done" means it did work again.
    if grep -E '✓  done$' <<<"$out"; then return 1; fi
    grep -q 'already done' <<<"$out"
}

echo "==> bootstrap.py's own view"
check "every task reports done (--list)" no_todo
check "second run changes nothing" second_run_is_noop

# --- 2. independent checks ------------------------------------------------ #
echo "==> Command Line Tools and Homebrew"
check "Command Line Tools installed" xcode-select -p
check "git works" git --version
check "brew works" brew --version
check "new zsh login shells find brew (~/.zprofile)" zsh -lc 'command -v brew'
check "Python 3.14 works" python3.14 --version

# Helpers so a check's command (and its error output) runs inside `check`.
setting_is() {  # setting_is domain key expected
    local value
    value="$(defaults read "$1" "$2" 2>&1)" || { echo "$value"; return 1; }
    [[ "$value" == "$3" ]] || { echo "$1 $2 is '$value', expected '$3'"; return 1; }
}
sillyfmt_formats() {
    local out
    out="$(echo '(a,(b,c))' | "$HOME/proj/sillyfmt/target/release/sillyfmt" 2>&1)" || { echo "$out"; return 1; }
    [[ "$out" == "( a, (b, c) )" ]] || { echo "got: $out"; return 1; }
}

echo "==> macOS settings"
check "fast key repeat (KeyRepeat = 2)" setting_is -g KeyRepeat 2
check "Finder shows hidden files" setting_is com.apple.finder AppleShowAllFiles 1
check "no smart quotes" setting_is -g NSAutomaticQuoteSubstitutionEnabled 0

echo "==> Tools"
check "clang-format runs" clang-format --version
check "cmake runs" cmake --version
check "cargo runs" cargo --version
check "sillyfmt formats" sillyfmt_formats
check "FixederSys font installed" sh -c 'file "$HOME/Library/Fonts/FixederSys2x.ttf" | grep -q TrueType'

echo "==> Emacs"
check "Emacs.app installed" test -x "$EMACS"
check "~/.emacs matches dotfiles/emacs" cmp "$HOME/.emacs" "$TOOLS/dotfiles/emacs"
check "~/.emacs.custom.el matches dotfiles" cmp "$HOME/.emacs.custom.el" "$TOOLS/dotfiles/emacs.custom.el"
check "no Emacs packages missing" test -z "$("$EMACS" --batch -l "$TOOLS/newmac/tasks/emacs_packages.el" 2>/dev/null)"
# The real test: the whole config loads, so every package it `require`s works.
check "Emacs loads ~/.emacs without errors" sh -c "\"$EMACS\" --batch -l \"$HOME/.emacs\" --eval '(message \"config-ok\")' 2>&1 | grep -q config-ok"

echo
echo "==> $PASS passed, $FAIL failed"
((FAIL == 0))
