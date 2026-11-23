"""Homebrew. bootstrap.sh installs it; this task puts it on PATH for new shells."""
import platform
from pathlib import Path

from ..core import Task, register

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
