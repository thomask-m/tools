"""Shared building blocks: the Task base class, a registry, and helpers.

Stdlib only. Targets Python 3.14; on a fresh Mac, bootstrap.sh installs it
with Homebrew before running these scripts.
"""

import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Sequence
from pathlib import Path

# --------------------------------------------------------------------------- #
# Output
# --------------------------------------------------------------------------- #

_COLOR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _COLOR else text


def info(msg: str) -> None:
    print(_c("34", "==> ") + msg)


def ok(msg: str) -> None:
    print(_c("32", " ✓  ") + msg)


def warn(msg: str) -> None:
    print(_c("33", " !  ") + msg)


def error(msg: str) -> None:
    print(_c("31", " ✗  ") + msg, file=sys.stderr)


def _detail(msg: str) -> None:
    """Dimmed, indented line for the individual actions a task takes."""
    print(_c("90", f"    {msg}"))


# --------------------------------------------------------------------------- #
# Context passed to every task
# --------------------------------------------------------------------------- #


class Context:
    """Run-wide settings shared by all tasks."""

    def __init__(self, dry_run: bool = False, assume_yes: bool = False) -> None:
        self.dry_run = dry_run
        self.assume_yes = assume_yes
        self.home = Path.home()

    def run(
        self,
        cmd: Sequence[str],
        check: bool = True,
        capture: bool = False,
        env: dict[str, str] | None = None,
        mutating: bool = True,
    ) -> subprocess.CompletedProcess:
        """Run a command. Mutating commands are only printed in dry-run mode.

        Pass mutating=False for read-only probes (e.g. `defaults read`) so they
        still execute during a dry run.
        """
        if mutating:
            _detail(f"{'[dry-run]' if self.dry_run else '$'} {shlex.join(cmd)}")
            if self.dry_run:
                return subprocess.CompletedProcess(cmd, 0, "", "")
        return subprocess.run(
            list(cmd),
            check=check,
            text=True,
            capture_output=capture,
            env={**os.environ, **(env or {})},
        )

    def output(self, cmd: Sequence[str]) -> str | None:
        """Run a read-only command and return stripped stdout, or None on failure."""
        try:
            res = self.run(cmd, check=True, capture=True, mutating=False)
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None
        return res.stdout.strip()

    def download(self, url: str) -> Path:
        """Download `url` into a fresh temp dir and return the file's path.

        Uses macOS's /usr/bin/curl rather than urllib: it ships with every Mac
        and connects to servers whose TLS setup Python's OpenSSL rejects.
        """
        name = url.rstrip("/").rsplit("/", 1)[-1] or "download"
        folder = Path(tempfile.gettempdir() if self.dry_run else tempfile.mkdtemp(prefix="newmac-"))
        dest = folder / name
        self.run(["/usr/bin/curl", "-fsSL", "--retry", "3", "-o", str(dest), url])
        return dest

    def install_file(self, src: Path, dest: Path) -> None:
        """Copy `src` to `dest`. A different existing `dest` is backed up first."""
        if dest.exists() and dest.read_bytes() == src.read_bytes():
            return
        prefix = "[dry-run] " if self.dry_run else ""
        if dest.exists():
            backup = dest.with_name(f"{dest.name}.bak-{time.strftime('%Y%m%d-%H%M%S')}")
            _detail(f"{prefix}back up {dest} -> {backup}")
            if not self.dry_run:
                dest.rename(backup)
        _detail(f"{prefix}copy {src} -> {dest}")
        if not self.dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)

    def ensure_line_in_file(self, path: Path, line: str) -> None:
        """Append `line` to `path` if it isn't already there."""
        existing = path.read_text() if path.exists() else ""
        if line in existing.splitlines():
            return
        _detail(f"{'[dry-run] ' if self.dry_run else ''}append to {path}: {line}")
        if self.dry_run:
            return
        with open(path, "a") as fh:
            if existing and not existing.endswith("\n"):
                fh.write("\n")
            fh.write(line + "\n")


# --------------------------------------------------------------------------- #
# Tasks and registry
# --------------------------------------------------------------------------- #


class Task:
    """One installable/configurable thing.

    Subclasses set `name`/`description`, optionally `requires`, and implement
    `is_done` (cheap, read-only check) and `apply` (do the work). Tasks should be
    idempotent: running `apply` twice must be safe.
    """

    name: str = ""
    description: str = ""
    requires: tuple[str, ...] = ()  # names of tasks that must run first

    def __init__(self, ctx: Context) -> None:
        self.ctx = ctx

    def is_done(self) -> bool:
        return False

    def apply(self) -> None:
        raise NotImplementedError


_REGISTRY: dict[str, type[Task]] = {}


def register(cls: type[Task]) -> type[Task]:
    """Class decorator that adds a Task to the registry (in definition order)."""
    if not cls.name:
        raise ValueError(f"{cls.__name__} must set a name")
    if cls.name in _REGISTRY:
        raise ValueError(f"duplicate task name: {cls.name}")
    _REGISTRY[cls.name] = cls
    return cls


def all_tasks() -> dict[str, type[Task]]:
    return dict(_REGISTRY)


def resolve_order(selected: Sequence[str]) -> list[str]:
    """Return `selected` plus their dependencies, topologically sorted."""
    order: list[str] = []
    visiting: set[str] = set()

    def visit(name: str) -> None:
        if name in order:
            return
        if name not in _REGISTRY:
            raise KeyError(f"unknown task: {name}")
        if name in visiting:
            raise ValueError(f"dependency cycle at {name}")
        visiting.add(name)
        for dep in _REGISTRY[name].requires:
            visit(dep)
        visiting.discard(name)
        order.append(name)

    for name in selected:
        visit(name)
    return order
