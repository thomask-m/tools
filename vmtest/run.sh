#!/bin/bash
# Test the whole install on a fresh macOS VM, then delete the VM.
#
#   vmtest/run.sh               # install this working tree (uncommitted changes too)
#   vmtest/run.sh --github      # install with the real curl one-liner (what's pushed)
#   vmtest/run.sh --keep-vm     # leave the VM running afterwards, to poke around
#   vmtest/run.sh --keep-image  # keep the ~24 GB macOS image for faster reruns
#   vmtest/run.sh --clean       # delete leftover test VMs and the cached image
#
# Uses Tart (https://tart.run) and Cirrus Labs' "vanilla" macOS image: a clean
# macOS with no Command Line Tools and no Homebrew, like a new Mac. Each run
# clones a fresh VM, installs, runs vmtest/verify.sh inside it, then deletes
# the VM, and the image too unless you pass --keep-image. Logs go to vmtest/logs/.
#
# Needs an Apple silicon Mac, Tart (`brew install openai/tools/tart`), and
# about 60 GB of free disk while it runs.
set -euo pipefail

TART="${TART:-tart}"  # or point TART at a downloaded tart.app/Contents/MacOS/tart
IMAGE="ghcr.io/cirruslabs/macos-tahoe-vanilla:latest"
VM_PREFIX="newmac-test"
INSTALL_URL="https://raw.githubusercontent.com/thomask-m/tools/main/install.sh"
NEEDED_GB=60

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$REPO_DIR/vmtest/logs"

FROM_GITHUB=0 KEEP_VM=0 KEEP_IMAGE=0 CLEAN=0
for arg in "$@"; do
    case "$arg" in
        --github) FROM_GITHUB=1 ;;
        --keep-vm) KEEP_VM=1 ;;
        --keep-image) KEEP_IMAGE=1 ;;
        --clean) CLEAN=1 ;;
        -h | --help) sed -n '2,17p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) echo "unknown option: $arg (see --help)" >&2; exit 2 ;;
    esac
done

say() { printf '\033[34m==>\033[0m %s\n' "$*"; }
die() { printf '\033[31merror:\033[0m %s\n' "$*" >&2; exit 1; }

command -v "$TART" >/dev/null || die "Tart isn't installed. Install it with: brew install openai/tools/tart (or set TART=/path/to/tart)"
[[ "$(uname -m)" == arm64 ]] || die "Tart needs an Apple silicon Mac."

# Deletes the cached macOS image (the big one) and any newmac-test VMs.
delete_image() {
    if "$TART" list --source oci --quiet 2>/dev/null | grep -qxF "$IMAGE"; then
        say "Deleting the cached macOS image ($IMAGE)"
        "$TART" delete "$IMAGE" || true
    fi
}

if ((CLEAN)); then
    for vm in $("$TART" list --source local --quiet | grep "^$VM_PREFIX-" || true); do
        say "Deleting VM $vm"
        "$TART" stop "$vm" >/dev/null 2>&1 || true
        "$TART" delete "$vm"
    done
    delete_image
    say "Clean. Tart is using $(du -sh ~/.tart 2>/dev/null | cut -f1 || echo nothing) in ~/.tart"
    exit 0
fi

# --- Disk space (only matters if the image still has to be downloaded) ---- #
if ! "$TART" list --source oci --quiet 2>/dev/null | grep -qxF "$IMAGE"; then
    free_gb="$(df -g "$HOME" | awk 'NR == 2 {print $4}')"
    ((free_gb >= NEEDED_GB)) || die "Need about ${NEEDED_GB} GB free for the VM, have ${free_gb} GB."
fi

VM="$VM_PREFIX-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/$VM.log"
TART_PID=""
IP=""

# The vanilla image's login is admin/admin (and it has passwordless sudo).
# ssh reads the password from this helper instead of a prompt.
ASKPASS="$(mktemp -t newmac-askpass)"
printf '#!/bin/sh\necho admin\n' >"$ASKPASS"
chmod 700 "$ASKPASS"

vm_ssh() {
    SSH_ASKPASS="$ASKPASS" SSH_ASKPASS_REQUIRE=force ssh \
        -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR \
        -o PreferredAuthentications=password -o PubkeyAuthentication=no \
        -o ConnectTimeout=5 -o ServerAliveInterval=30 \
        "admin@$IP" "$@"
}

cleanup() {
    local status=$?
    rm -f "$ASKPASS"
    if ((KEEP_VM)) && [[ -n "$IP" ]]; then
        say "VM left running: ssh admin@$IP (password: admin)"
        say "Delete it when you're done with: vmtest/run.sh --clean"
    else
        if [[ -n "$TART_PID" ]]; then
            say "Stopping and deleting VM $VM"
            "$TART" stop "$VM" >/dev/null 2>&1 || kill "$TART_PID" 2>/dev/null || true
            wait "$TART_PID" 2>/dev/null || true
        fi
        "$TART" delete "$VM" >/dev/null 2>&1 || true
        ((KEEP_IMAGE)) || delete_image
    fi
    exit "$status"
}
trap cleanup EXIT
trap 'exit 130' INT TERM

# --- Create and boot the VM ----------------------------------------------- #
say "Cloning a fresh VM from $IMAGE (the first time downloads ~24 GB)"
"$TART" clone "$IMAGE" "$VM"

say "Booting $VM (no window)"
"$TART" run --no-graphics "$VM" >"$LOG_DIR/$VM.tart.log" 2>&1 &
TART_PID=$!

IP="$("$TART" ip --wait 180 "$VM")" || die "VM didn't get an IP address"
say "Waiting for SSH at $IP"
for _ in $(seq 60); do
    vm_ssh true 2>/dev/null && break
    sleep 5
done
vm_ssh true || die "Couldn't SSH into the VM"

# --- Install -------------------------------------------------------------- #
SECONDS=0
if ((FROM_GITHUB)); then
    say "Running the curl one-liner from GitHub (logging to vmtest/logs/$VM.log)"
    install_cmd="curl -fsSL $INSTALL_URL | bash -s -- -y"
else
    say "Copying this working tree into the VM's ~/proj/tools"
    COPYFILE_DISABLE=1 tar -C "$REPO_DIR" --exclude .git --exclude vmtest/logs \
        --exclude __pycache__ -czf - . | vm_ssh 'mkdir -p ~/proj/tools && tar -xzf - -C ~/proj/tools'
    say "Running install.sh (logging to vmtest/logs/$VM.log)"
    install_cmd="~/proj/tools/install.sh -y"
fi

install_ok=1
vm_ssh "$install_cmd" 2>&1 | tee "$LOG" || install_ok=0
say "Install $( ((install_ok)) && echo finished || echo FAILED ) after $((SECONDS / 60)) min"

# --- Verify --------------------------------------------------------------- #
say "Checking that everything is installed and works"
verify_ok=1
vm_ssh 'bash -s' <"$REPO_DIR/vmtest/verify.sh" 2>&1 | tee -a "$LOG" || verify_ok=0

if ((install_ok && verify_ok)); then
    say "PASSED: a fresh Mac ends up fully set up. Log: vmtest/logs/$VM.log"
    exit 0
fi
say "FAILED: see vmtest/logs/$VM.log (rerun with --keep-vm to look around inside the VM)"
exit 1
