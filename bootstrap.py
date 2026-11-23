#!/usr/bin/env python3.14
"""Bootstrap a new Mac: install the tools and settings I always want.

Examples:
    ./bootstrap.sh                       # brand-new Mac: installs Python 3.14, then runs this
    python3.14 bootstrap.py --list       # show available tasks
    python3.14 bootstrap.py --dry-run    # show what would happen
    python3.14 bootstrap.py              # run everything
    python3.14 bootstrap.py emacs        # run one task (plus its dependencies)
"""
# Everything above the newmac imports must stay parseable by old Pythons (the
# 3.9 from the Command Line Tools), so the wrong interpreter gets a clear
# message instead of a SyntaxError.
import sys

if sys.version_info < (3, 14):
    sys.stderr.write(
        "bootstrap.py needs Python 3.14 or newer (this is Python %d.%d).\n"
        "Run ./bootstrap.sh instead: it installs Python 3.14 with Homebrew,\n"
        "then runs this script with the same arguments.\n" % sys.version_info[:2]
    )
    sys.exit(1)

import argparse  # noqa: E402
import platform  # noqa: E402
import subprocess  # noqa: E402

from newmac import core  # noqa: E402
from newmac import tasks  # noqa: E402,F401  (importing registers all tasks)


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("tasks", nargs="*", help="task names to run (default: all)")
    p.add_argument("-l", "--list", action="store_true", help="list tasks and their status")
    p.add_argument("-n", "--dry-run", action="store_true", help="print actions without doing them")
    p.add_argument("-y", "--yes", action="store_true", help="don't prompt for confirmation")
    p.add_argument("-f", "--force", action="store_true", help="run tasks even if they look done")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)

    if platform.system() != "Darwin":
        core.error("These scripts are for macOS only.")
        return 1

    ctx = core.Context(dry_run=args.dry_run, assume_yes=args.yes)
    registry = core.all_tasks()

    if args.list:
        width = max(len(n) for n in registry)
        for name, cls in registry.items():
            status = "done" if cls(ctx).is_done() else "todo"
            deps = f"  (needs: {', '.join(cls.requires)})" if cls.requires else ""
            print(f"  {name:<{width}}  [{status}]  {cls.description}{deps}")
        return 0

    try:
        order = core.resolve_order(args.tasks or list(registry))
    except (KeyError, ValueError) as exc:
        core.error(exc.args[0])
        core.error(f"available: {', '.join(registry)}")
        return 2

    for name in order:
        task = registry[name](ctx)
        core.info(f"{name}: {task.description}")
        if not args.force and task.is_done():
            core.ok("already done")
            continue
        try:
            task.apply()
        except (subprocess.CalledProcessError, OSError, RuntimeError) as exc:
            # Later tasks may depend on this one; stop rather than cascade errors.
            core.error(f"{name} failed: {exc}")
            return 1
        core.ok("done")

    core.info("All done." + (" (dry run, nothing changed)" if ctx.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
