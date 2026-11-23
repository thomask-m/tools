"""My Emacs config, and the packages it needs.

The config lives in this repo under dotfiles/ and is copied to:
  ~/.emacs            main config
  ~/.emacs.custom.el  Customize output (set via `custom-file` in ~/.emacs)

These are copies, not symlinks. After changing your config, copy it back into
dotfiles/ so the next machine gets it.
"""
from pathlib import Path

from ..core import Task, register
from .emacs import EMACS

DOTFILES = Path(__file__).resolve().parents[2] / "dotfiles"
FILES = {  # repo file -> name in $HOME
    "emacs": ".emacs",
    "emacs.custom.el": ".emacs.custom.el",
}
PACKAGES_EL = Path(__file__).with_name("emacs_packages.el")


@register
class EmacsConfig(Task):
    name = "emacs-config"
    description = "Emacs config (~/.emacs, ~/.emacs.custom.el) from dotfiles/"
    requires = ("emacs",)

    def _pairs(self) -> list[tuple[Path, Path]]:
        return [(DOTFILES / src, self.ctx.home / dest) for src, dest in FILES.items()]

    def is_done(self) -> bool:
        return all(d.exists() and d.read_bytes() == s.read_bytes() for s, d in self._pairs())

    def apply(self) -> None:
        for src, dest in self._pairs():
            self.ctx.install_file(src, dest)


@register
class EmacsPackages(Task):
    name = "emacs-packages"
    description = "Emacs packages from package-selected-packages (MELPA)"
    requires = ("emacs-config",)

    def is_done(self) -> bool:
        # Prints missing packages, one per line; empty output means all installed.
        missing = self.ctx.output([str(EMACS), "--batch", "-l", str(PACKAGES_EL)])
        return missing == ""

    def apply(self) -> None:
        self.ctx.run(
            [str(EMACS), "--batch", "--eval", "(setq newmac-install t)", "-l", str(PACKAGES_EL)]
        )
