"""My Emacs config, and the packages it needs.

The config lives in this repo under dotfiles/ and is copied to:
  ~/.emacs            main config
  ~/.emacs.custom.el  Customize output (set via `custom-file` in ~/.emacs)

These are copies, not symlinks. After changing your config, copy it back into
dotfiles/ so the next machine gets it.
"""
from pathlib import Path

from ..core import Task, register, warn
from .emacs import EMACS

DOTFILES = Path(__file__).resolve().parents[2] / "dotfiles"
FILES = {  # repo file -> name in $HOME
    "emacs": ".emacs",
    "emacs.custom.el": ".emacs.custom.el",
}
PACKAGES_EL = Path(__file__).with_name("emacs_packages.el")
# Prints where package.el installs packages, as ~/.emacs's settings leave it.
PACKAGE_DIR_EL = """(progn
  (setq custom-file (expand-file-name "~/.emacs.custom.el"))
  (load custom-file t t)
  (require 'package)
  (princ (expand-file-name package-user-dir)))"""


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

    def uninstall_blockers(self) -> list[str]:
        return [
            f"{dest} differs from dotfiles/{src.name}; save your changes first: cp {dest} {src}"
            for src, dest in self._pairs()
            if dest.exists() and dest.read_bytes() != src.read_bytes()
        ]

    def uninstall(self) -> None:
        for _src, dest in self._pairs():
            self.ctx.stash(dest)


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

    def uninstall(self) -> None:
        if not EMACS.exists():
            warn("Emacs isn't installed, so can't tell where its packages are; left them")
            return
        found = self.ctx.output([str(EMACS), "--batch", "--eval", PACKAGE_DIR_EL])
        package_dir = Path(found) if found else None
        if not package_dir or not package_dir.is_relative_to(self.ctx.home) or package_dir == self.ctx.home:
            raise RuntimeError(f"unexpected Emacs package folder {found!r}; not touching it")
        self.ctx.stash(package_dir)
