#!/usr/bin/env python3.14
"""Bootstrap a new Mac: install the tools and settings I always want.

Examples:
    ./bootstrap.sh                       # brand-new Mac: installs Python 3.14, then runs this
    python3.14 bootstrap.py --list       # show available tasks
    python3.14 bootstrap.py --dry-run    # show what would happen
    python3.14 bootstrap.py              # run everything
    python3.14 bootstrap.py emacs        # run one task (plus its dependencies)
    ./cleanup.sh                         # show what --uninstall would remove (see cleanup.sh)
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
    p.add_argument("-f", "--force", action="store_true",
                   help="run tasks even if they look done (with --uninstall: ignore safety checks)")
    p.add_argument("-u", "--uninstall", action="store_true",
                   help="undo the tasks so the install can be tested from scratch; only shows "
                        "what it would do unless --yes is given")
    p.add_argument("--everything", action="store_true",
                   help="with --uninstall: also remove Homebrew and the Command Line Tools")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)

    if platform.system() != "Darwin":
        core.error("These scripts are for macOS only.")
        return 1

    if args.everything and not args.uninstall:
        core.error("--everything only works with --uninstall")
        return 2
    # Uninstalling is a dry run unless --yes says otherwise.
    dry_run = args.dry_run or (args.uninstall and not args.yes)
    ctx = core.Context(dry_run=dry_run, assume_yes=args.yes, everything=args.everything)
    registry = core.all_tasks()

    if args.list:
        width = max(len(n) for n in registry)
        for name, cls in registry.items():
            status = "done" if cls(ctx).is_done() else "todo"
            deps = f"  (needs: {', '.join(cls.requires)})" if cls.requires else ""
            print(f"  {name:<{width}}  [{status}]  {cls.description}{deps}")
        return 0

    if args.uninstall:
        return uninstall(ctx, registry, args.tasks, ignore_blockers=args.force)

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


def uninstall(ctx: core.Context, registry: dict, names: list[str], ignore_blockers: bool) -> int:
    """Undo tasks in reverse install order. Only the named ones, if any are named."""
    if unknown := [n for n in names if n not in registry]:
        core.error(f"unknown task: {', '.join(unknown)}")
        core.error(f"available: {', '.join(registry)}")
        return 2
    order = [n for n in reversed(core.resolve_order(list(registry))) if not names or n in names]
    tasks = [registry[n](ctx) for n in order]

    blockers = [(t.name, reason) for t in tasks for reason in t.uninstall_blockers()]
    for name, reason in blockers:
        core.error(f"{name}: {reason}")
    if blockers and not ignore_blockers:
        core.error("Nothing was removed. Fix the above first, or pass --force to remove anyway.")
        return 1

    for task in tasks:
        core.info(f"{task.name}: remove {task.description}")
        try:
            task.uninstall()
        except (subprocess.CalledProcessError, OSError, RuntimeError) as exc:
            core.error(f"{task.name} failed: {exc}")
            if ctx.backed_up:
                core.error(f"What was removed so far is in {ctx.backup_dir} (restore.sh puts it back).")
            return 1

    if ctx.dry_run:
        core.info("Nothing changed (dry run). Rerun with --yes to remove the above.")
    elif not ctx.backed_up:
        core.info("Nothing left to remove.")
    else:
        core.info(f"Removed. Everything moved aside is in {ctx.backup_dir}")
        core.info(f"  put it back: {ctx.backup_dir / 'restore.sh'}")
        core.info("  or reinstall from scratch: ./bootstrap.sh")
    return 0


if __name__ == "__main__":
    sys.exit(main())
