"""Rust (stable), installed with the official rustup installer into ~/.cargo."""
from pathlib import Path

from ..core import Task, register

RUSTUP_URL = "https://sh.rustup.rs"
# The line `rustup-init -y` adds to these shell startup files.
ENV_LINE = '. "$HOME/.cargo/env"'
PROFILES = (".profile", ".bash_profile", ".bashrc", ".zshenv")


def cargo_bin(home: Path) -> Path:
    """Where rustup puts cargo. Works before ~/.cargo/bin is on PATH."""
    return home / ".cargo" / "bin" / "cargo"


@register
class Rust(Task):
    name = "rust"
    description = "Rust toolchain via rustup (~/.cargo)"
    requires = ("xcode-clt",)

    def is_done(self) -> bool:
        return cargo_bin(self.ctx.home).exists()

    def apply(self) -> None:
        installer = self.ctx.download(RUSTUP_URL)
        # -y: default (stable) toolchain, and rustup adds ~/.cargo/bin to your shell profiles.
        self.ctx.run(["/bin/sh", str(installer), "-y"])

    def uninstall(self) -> None:
        # Like `rustup self uninstall`, but moved aside instead of deleted.
        home = self.ctx.home
        for name in (".cargo", ".rustup", ".config/fish/conf.d/rustup.fish"):
            self.ctx.stash(home / name)
        for name in PROFILES:
            self.ctx.remove_line_from_file(home / name, ENV_LINE)
