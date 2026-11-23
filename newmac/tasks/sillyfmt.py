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

    def uninstall_blockers(self) -> list[str]:
        if not self.src.exists():
            return []
        if not (self.src / ".git").exists():
            return [f"{self.src} isn't a git checkout, so it may hold work that exists nowhere else"]
        git = ["git", "-C", str(self.src)]
        checks = {
            "has uncommitted changes": [*git, "status", "--porcelain"],
            "has commits that aren't pushed": [*git, "log", "--branches", "--not", "--remotes", "--oneline"],
            "has stashed changes": [*git, "stash", "list"],
        }
        problems = []
        for problem, cmd in checks.items():
            out = self.ctx.output(cmd)
            if out is None:
                problems.append(f"couldn't check whether {self.src} {problem.removeprefix('has ')}")
            elif out:
                problems.append(f"{self.src} {problem}")
        return problems

    def uninstall(self) -> None:
        self.ctx.stash(self.src)

    def apply(self) -> None:
        if not (self.src / "Cargo.toml").exists():
            self.ctx.run(["git", "clone", REPO, str(self.src)])
        self.ctx.run([
            str(cargo_bin(self.ctx.home)), "build", "--release",
            "-p", "sillyfmt-cli", "--manifest-path", str(self.src / "Cargo.toml"),
        ])
