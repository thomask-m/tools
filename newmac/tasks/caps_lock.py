"""Caps Lock acts as Control, on every keyboard (built-in and external).

Uses Apple's `hidutil` to remap the key. A remap made with `hidutil` is lost
on restart, so a LaunchAgent runs the same command at every login. It takes
effect right away, with no logout, and doesn't need per-keyboard IDs like the
System Settings > Keyboard > Modifier Keys setting does.
"""
import plistlib
import tempfile
from pathlib import Path

from ..core import Task, register

# HID usage codes: 0x7_0000_0039 is Caps Lock, 0x7_0000_00E0 is Left Control.
MAPPING = '{"UserKeyMapping":[{"HIDKeyboardModifierMappingSrc":0x700000039,"HIDKeyboardModifierMappingDst":0x7000000E0}]}'
NO_MAPPING = '{"UserKeyMapping":[]}'
LABEL = "com.newmac.caps-lock-control"
AGENT = plistlib.dumps({
    "Label": LABEL,
    "ProgramArguments": ["/usr/bin/hidutil", "property", "--set", MAPPING],
    "RunAtLoad": True,
})


@register
class CapsLockControl(Task):
    name = "caps-lock-control"
    description = "Caps Lock acts as Control (all keyboards, via hidutil at login)"

    @property
    def agent(self) -> Path:
        return self.ctx.home / "Library" / "LaunchAgents" / f"{LABEL}.plist"

    def is_done(self) -> bool:
        return self.agent.exists() and self.agent.read_bytes() == AGENT

    def apply(self) -> None:
        src = Path(tempfile.mkdtemp(prefix="newmac-")) / self.agent.name
        src.write_bytes(AGENT)
        self.ctx.install_file(src, self.agent)  # runs at every login from now on
        self.ctx.run(["/usr/bin/hidutil", "property", "--set", MAPPING])  # and right now

    def uninstall(self) -> None:
        if not self.agent.exists():
            return  # never installed by us; leave any other remapping alone
        self.ctx.stash(self.agent)
        self.ctx.run(["/usr/bin/hidutil", "property", "--set", NO_MAPPING])
        self.ctx.note_restore(f"/usr/bin/hidutil property --set '{MAPPING}'")
