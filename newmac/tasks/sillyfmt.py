"""sillyfmt, built from source. ~/.emacs runs it from ~/proj/sillyfmt (the `sf` command).

https://github.com/thomask-m/sillyfmt
"""
from pathlib import Path

from ..core import Task, register
from .rust import cargo_bin

REPO = "https://github.com/thomask-m/sillyfmt.git"


@register
class Sillyfmt(Task):
    name = "sillyfmt"
    description = "sillyfmt formatter, built into ~/proj/sillyfmt"
    requires = ("rust",)

    @property
    def src(self) -> Path:
        return self.ctx.home / "proj" / "sillyfmt"

    def is_done(self) -> bool:
        return (self.src / "target" / "release" / "sillyfmt").exists()

    def apply(self) -> None:
        if not (self.src / "Cargo.toml").exists():
            self.ctx.run(["git", "clone", REPO, str(self.src)])
        self.ctx.run([
            str(cargo_bin(self.ctx.home)), "build", "--release",
            "-p", "sillyfmt-cli", "--manifest-path", str(self.src / "Cargo.toml"),
        ])
