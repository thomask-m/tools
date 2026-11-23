"""Command-line tools from Homebrew. Add a formula to FORMULAE to install it."""
from ..core import Task, register, warn
from .homebrew import BREW, PREFIX

FORMULAE = {  # formula -> why it's here
    "clang-format": "Emacs `cf` command (C-c C-f) formats C/C++ with it",
    "cmake": "Emacs vterm builds its native module with it",
    "libtool": "Emacs vterm builds its native module with it",
    "libvterm": "the terminal library Emacs vterm links against",
}


@register
class BrewPackages(Task):
    name = "brew-packages"
    description = "Homebrew command-line tools: " + ", ".join(FORMULAE)
    requires = ("homebrew",)

    def _missing(self) -> list[str]:
        # Every installed formula has a link at <prefix>/opt/<name>; no need to start brew.
        return [f for f in FORMULAE if not (PREFIX / "opt" / f).exists()]

    def is_done(self) -> bool:
        return not self._missing()

    def apply(self) -> None:
        if missing := self._missing():
            self.ctx.run([str(BREW), "install", *missing])

    def uninstall(self) -> None:
        if not BREW.exists():
            return
        remove = []
        for f in (f for f in FORMULAE if (PREFIX / "opt" / f).exists()):
            users = self.ctx.output([str(BREW), "uses", "--installed", f]) or ""
            if others := [u for u in users.split() if u not in FORMULAE]:
                warn(f"kept {f}: other Homebrew packages need it ({' '.join(others)})")
            else:
                remove.append(f)
        if remove:
            self.ctx.run([str(BREW), "uninstall", *remove])
            self.ctx.note_restore(" ".join([str(BREW), "install", *remove]))
