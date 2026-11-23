"""Xcode Command Line Tools: git, clang, make, etc. Homebrew needs these.

bootstrap.sh installs them (headlessly, via softwareupdate) before Python 3.14
exists, so this task only checks; it's here for `--list` and as a dependency.
"""
from pathlib import Path

from ..core import Task, register, warn

CLT = Path("/Library/Developer/CommandLineTools")


@register
class XcodeCLT(Task):
    name = "xcode-clt"
    description = "Xcode Command Line Tools (git, clang, make)"

    def is_done(self) -> bool:
        return self.ctx.output(["xcode-select", "-p"]) is not None

    def apply(self) -> None:
        if self.is_done():  # reached with --force; nothing to do
            return
        raise RuntimeError("Command Line Tools are missing; run ./bootstrap.sh to install them")

    def uninstall(self) -> None:
        if not self.ctx.everything:
            warn("kept (pass --everything to remove the Command Line Tools)")
            return
        if (active := self.ctx.output(["xcode-select", "-p"])) and not active.startswith(str(CLT)):
            warn(f"git and clang come from {active} (Xcode), not the Command Line Tools")
        if CLT.exists():
            self.ctx.stash(CLT, sudo=True)
            self.ctx.note_restore(f"sudo xcode-select --switch {CLT}")
        # Forget the removed path, so `xcode-select -p` fails and bootstrap.sh reinstalls.
        self.ctx.run(["sudo", "xcode-select", "--reset"])
