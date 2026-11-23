"""Homebrew. bootstrap.sh installs it; this task puts it on PATH for new shells."""
import platform
from pathlib import Path

from ..core import Task, register, warn

UNINSTALL_URL = "https://raw.githubusercontent.com/Homebrew/install/HEAD/uninstall.sh"
# Installed by this repo, so they come back with ./bootstrap.sh.
OURS = {"python@3.14"}

PREFIX = Path("/opt/homebrew" if platform.machine() == "arm64" else "/usr/local")
BREW = PREFIX / "bin" / "brew"
SHELLENV_LINE = f'eval "$({BREW} shellenv)"'


@register
class Homebrew(Task):
    name = "homebrew"
    description = "Homebrew package manager, on PATH via ~/.zprofile"
    requires = ("xcode-clt",)

    @property
    def zprofile(self) -> Path:
        return self.ctx.home / ".zprofile"

    def is_done(self) -> bool:
        if not BREW.exists() or not self.zprofile.exists():
            return False
        return SHELLENV_LINE in self.zprofile.read_text().splitlines()

    def apply(self) -> None:
        if not BREW.exists():
            raise RuntimeError("Homebrew is missing; run ./bootstrap.sh to install it")
        self.ctx.ensure_line_in_file(self.zprofile, SHELLENV_LINE)

    def uninstall(self) -> None:
        self.ctx.remove_line_from_file(self.zprofile, SHELLENV_LINE)
        if not self.ctx.everything:
            warn("kept Homebrew itself (pass --everything to remove it)")
            return
        if not BREW.exists():
            return
        from .brew_packages import FORMULAE
        from .emacs import CASK
        others = [
            *(f for f in (self.ctx.output([str(BREW), "leaves"]) or "").split() if f not in {*FORMULAE, *OURS}),
            *(c for c in (self.ctx.output([str(BREW), "list", "--cask"]) or "").split() if c != CASK),
        ]
        if others:
            warn("this also removes everything else you installed with Homebrew, which")
            warn("bootstrap won't reinstall unless you add it first: " + " ".join(others))
        installer = self.ctx.download(UNINSTALL_URL)
        self.ctx.run(["/bin/bash", str(installer), "--force"], env={"NONINTERACTIVE": "1"})
