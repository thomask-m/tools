"""Xcode Command Line Tools: git, clang, make, etc. Homebrew needs these.

bootstrap.sh installs them (headlessly, via softwareupdate) before Python 3.14
exists, so this task only checks; it's here for `--list` and as a dependency.
"""
from ..core import Task, register


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
