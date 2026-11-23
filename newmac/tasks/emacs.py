"""GNU Emacs, GUI build (emacsformacosx.com) via the Homebrew cask.

The config is installed by the emacs-config task (see emacs_config.py).
"""
from pathlib import Path

from ..core import Task, register
from .homebrew import BREW, PREFIX

CASK = "emacs-app"
APP = Path("/Applications/Emacs.app")
EMACS = APP / "Contents" / "MacOS" / "Emacs"  # the binary, for --batch runs


@register
class Emacs(Task):
    name = "emacs"
    description = "GNU Emacs (GUI app)"
    requires = ("homebrew",)

    def is_done(self) -> bool:
        return APP.exists() or (PREFIX / "Caskroom" / CASK).exists()

    def apply(self) -> None:
        self.ctx.run([str(BREW), "install", "--cask", CASK])
