# tools: new-Mac bootstrap

Scripts that set up a fresh Mac (work or personal) for development.

Uses only the Python standard library and needs Python 3.14.

## Quick start on a new Mac

```bash
curl -fsSL https://raw.githubusercontent.com/thomask-m/tools/main/install.sh | bash
```

That's the whole setup. It needs nothing but `curl`, which every Mac has:

1. `install.sh` downloads this repo to `~/proj/tools` (set `TOOLS_DIR` to
   change that). If that folder already exists, it uses it as-is.
2. It runs `bootstrap.sh`, which installs the Xcode Command Line Tools
   (through `softwareupdate`, with no dialog), Homebrew, then `python@3.14`,
   each only if missing. It asks for your password for these installs.
3. `bootstrap.sh` then runs `bootstrap.py` with Python 3.14, which does the
   rest (see Tasks below).

To preview without changing anything:

```bash
curl -fsSL https://raw.githubusercontent.com/thomask-m/tools/main/install.sh | bash -s -- --dry-run
```

Everything is safe to rerun. Later you can run `~/proj/tools/bootstrap.sh`
directly.

The downloaded folder isn't a git repo. To push changes (like an updated Emacs
config) from that machine, turn it into one once git is installed:

```bash
cd ~/proj/tools && git init -b main && git remote add origin https://github.com/thomask-m/tools.git && git fetch origin && git reset origin/main && git branch -u origin/main
```

## Usage

Once Python 3.14 is installed, run `bootstrap.py` directly (or keep using
`./bootstrap.sh`, which takes the same arguments):

```bash
python3.14 bootstrap.py --list      # tasks and whether each is already done
python3.14 bootstrap.py --dry-run   # print what would happen, change nothing
python3.14 bootstrap.py             # run every task
python3.14 bootstrap.py emacs       # run one task (its dependencies run first)
```

Flags: `-y/--yes` skips prompts (Homebrew installs non-interactively),
`-f/--force` reruns tasks that look done.

Tasks skip themselves when already done, so rerunning is safe.

## Tasks

| Task             | What it does                                                     |
|------------------|------------------------------------------------------------------|
| `xcode-clt`      | Checks for the Xcode Command Line Tools (`bootstrap.sh` installs them) |
| `macos-defaults` | Keyboard repeat, no autocorrect or smart quotes, Finder shows hidden files and extensions, no `.DS_Store` on network or USB drives |
| `homebrew`       | Checks for Homebrew (`bootstrap.sh` installs it), adds `brew shellenv` to `~/.zprofile` |
| `brew-packages`  | Homebrew tools: `clang-format` (Emacs `cf`), `cmake`, `libtool`, `libvterm` (Emacs vterm). Edit `FORMULAE` in `brew_packages.py` to add more |
| `rust`           | Rust via the official rustup installer (stable, in `~/.cargo`) |
| `fonts`          | Downloads FixederSys 2x (the Emacs font) into `~/Library/Fonts`. Edit `FONTS` in `fonts.py` to add more |
| `emacs`          | `brew install --cask emacs-app` (the GUI build from emacsformacosx.com) |
| `emacs-config`   | Copies `dotfiles/emacs` to `~/.emacs` and `dotfiles/emacs.custom.el` to `~/.emacs.custom.el` |
| `emacs-packages` | Installs the MELPA packages listed in `package-selected-packages` |
| `sillyfmt`       | Clones and builds sillyfmt into `~/proj/sillyfmt` (the Emacs `sf` command) |

## Emacs config

Your config is kept in `dotfiles/`:

- `dotfiles/emacs` becomes `~/.emacs`
- `dotfiles/emacs.custom.el` becomes `~/.emacs.custom.el`

They're copied, not linked. If a different `~/.emacs` or `~/.emacs.custom.el`
is already there, it's renamed to `<name>.bak-<date>-<time>` first, so nothing
is lost.

When you change your config, copy it back so the next machine gets it:

```bash
cp ~/.emacs dotfiles/emacs && cp ~/.emacs.custom.el dotfiles/emacs.custom.el
```

`emacs-packages` installs every package in `package-selected-packages` (from
`~/.emacs.custom.el`). Install a package with `M-x package-install` and Emacs
adds it to that list for you, so remember to copy the file back afterwards.

## Starting over: `cleanup.sh`

To check that the install really works, undo it and run it again.
`cleanup.sh` (same as `python3.14 bootstrap.py --uninstall`) undoes every
task, in reverse order:

```bash
./cleanup.sh                  # show what would be removed (changes nothing)
./cleanup.sh --yes            # remove it
./cleanup.sh --yes emacs-config fonts   # only some tasks
./cleanup.sh --yes --everything         # also Homebrew and the Command Line Tools
./bootstrap.sh                # then install everything again
```

- **Nothing is deleted outright if it can be moved.** Files go to
  `~/newmac-backup-<date>-<time>/`, and its `restore.sh` puts them back,
  along with any macOS settings that were reset and any formulas or apps that
  were uninstalled. Delete that folder once you're happy with the reinstall.
- **It won't start if it would lose work.** It stops before removing anything if
  `~/proj/sillyfmt` has uncommitted, unpushed or stashed changes, or if
  `~/.emacs` or `~/.emacs.custom.el` differs from `dotfiles/` (copy it back
  first). `--force` skips these checks.
- **Homebrew and the Command Line Tools stay unless you pass `--everything`.**
  Removing Homebrew also removes everything else you installed with it, so
  the dry run lists those packages first: add the ones you want to
  `brew_packages.py` before you remove them. Homebrew is removed with its
  official uninstaller, so it isn't in the backup folder. The Command Line
  Tools are moved there.
- Without `--everything`, Python 3.14 stays too, since the cleanup runs on it.
- macOS settings are deleted rather than set to other values, which puts
  them back to Apple's defaults, as on a new Mac.
- If Xcode.app is installed, `xcode-select` falls back to it after the
  Command Line Tools are removed, so `bootstrap.sh` won't reinstall them.
  Move Xcode.app aside too if you want to test that step.

Back up first (Time Machine, or at least `tmutil localsnapshot`).

## Adding a task

1. Create `newmac/tasks/<thing>.py`:

   ```python
   from ..core import Task, register

   @register
   class Thing(Task):
       name = "thing"
       description = "What it installs"
       requires = ("homebrew",)         # optional

       def is_done(self) -> bool:       # cheap, read-only check
           ...

       def apply(self) -> None:         # do the work through self.ctx
           self.ctx.run(["brew", "install", "thing"])

       def uninstall(self) -> None:     # undo apply, for cleanup.sh
           self.ctx.run(["brew", "uninstall", "thing"])
           self.ctx.note_restore("brew install thing")
   ```

2. Import it in `newmac/tasks/__init__.py`. The import order there is the run order.

Use the `self.ctx` helpers (`run`, `output`, `download`,
`ensure_line_in_file`) instead of calling `subprocess` directly, so `--dry-run` works.
In `uninstall`, move files with `self.ctx.stash(path)` and undo edits with
`remove_line_from_file`, so `restore.sh` can put them back. Use
`note_restore` for anything else. If removing could lose work, return the
reason from `uninstall_blockers()`.
