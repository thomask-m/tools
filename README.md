# tools: new-Mac bootstrap

Scripts that set up a fresh Mac (work or personal) for development.

Uses only the Python standard library and needs Python 3.14.

## Quick start on a new Mac

```bash
./bootstrap.sh
```

A fresh Mac has no Python 3.14, only the Python 3.9 that comes with the Xcode
Command Line Tools. `bootstrap.sh` is a small launcher that installs whatever is
missing (the Command Line Tools, Homebrew, then `python@3.14`) and runs
`bootstrap.py` with Python 3.14, passing your arguments along. It is safe to
rerun. With `--dry-run` it only prints what it would install.

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
| `emacs`          | `brew install --cask emacs-app` (the GUI build from emacsformacosx.com) |
| `emacs-config`   | Copies `dotfiles/emacs` to `~/.emacs` and `dotfiles/emacs.custom.el` to `~/.emacs.custom.el` |
| `emacs-packages` | Installs the MELPA packages listed in `package-selected-packages` |

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
   ```

2. Import it in `newmac/tasks/__init__.py`. The import order there is the run order.

Use the `self.ctx` helpers (`run`, `output`, `download`,
`ensure_line_in_file`) instead of calling `subprocess` directly, so `--dry-run` works.
