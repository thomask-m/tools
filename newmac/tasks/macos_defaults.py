"""macOS settings for development, applied with `defaults write`.

Edit SETTINGS to taste. Each entry: (domain, key, type, value, note).
Types are the `defaults` type flags: bool, int, float, string.
"""
import plistlib

from ..core import Task, register

type Setting = tuple[str, str, str, object, str]

G = "NSGlobalDomain"

SETTINGS: list[Setting] = [
    # Keyboard: fast key repeat, and holding a key repeats instead of showing accents.
    (G, "ApplePressAndHoldEnabled", "bool", False, "key repeat instead of accent popup"),
    (G, "KeyRepeat", "int", 2, "fast key repeat"),
    (G, "InitialKeyRepeat", "int", 15, "short delay before repeat"),
    # Text: stop macOS from "fixing" code and shell commands as you type.
    (G, "NSAutomaticQuoteSubstitutionEnabled", "bool", False, "no smart quotes"),
    (G, "NSAutomaticDashSubstitutionEnabled", "bool", False, "no smart dashes"),
    (G, "NSAutomaticSpellingCorrectionEnabled", "bool", False, "no autocorrect"),
    (G, "NSAutomaticCapitalizationEnabled", "bool", False, "no auto-capitalization"),
    (G, "NSAutomaticPeriodSubstitutionEnabled", "bool", False, "no double-space period"),
    # Finder: show everything.
    (G, "AppleShowAllExtensions", "bool", True, "show all file extensions"),
    ("com.apple.finder", "AppleShowAllFiles", "bool", True, "show hidden files"),
    ("com.apple.finder", "ShowPathbar", "bool", True, "show path bar"),
    ("com.apple.finder", "ShowStatusBar", "bool", True, "show status bar"),
    ("com.apple.finder", "FXPreferredViewStyle", "string", "Nlsv", "list view by default"),
    ("com.apple.finder", "_FXSortFoldersFirst", "bool", True, "folders first"),
    # Don't litter network and USB drives with .DS_Store files.
    ("com.apple.desktopservices", "DSDontWriteNetworkStores", "bool", True, "no .DS_Store on network"),
    ("com.apple.desktopservices", "DSDontWriteUSBStores", "bool", True, "no .DS_Store on USB"),
]

# Apps to restart so changes take effect.
RESTART = ["Finder", "SystemUIServer"]


@register
class MacOSDefaults(Task):
    name = "macos-defaults"
    description = "macOS settings for development (keyboard, Finder, text input)"

    def _read_domain(self, domain: str) -> dict:
        """All of a domain's current values (one `defaults` call, not one per key)."""
        xml = self.ctx.output(["defaults", "export", domain, "-"])
        return plistlib.loads(xml.encode()) if xml else {}

    def _pending(self) -> list[Setting]:
        current = {d: self._read_domain(d) for d in {s[0] for s in SETTINGS}}
        return [s for s in SETTINGS if current[s[0]].get(s[1]) != s[3]]

    def is_done(self) -> bool:
        return not self._pending()

    def apply(self) -> None:
        for domain, key, type_, value, _note in self._pending():
            val = str(value).lower() if type_ == "bool" else str(value)
            self.ctx.run(["defaults", "write", domain, key, f"-{type_}", val])
        for app in RESTART:
            self.ctx.run(["killall", app], check=False)
        # Keyboard settings only apply after logging out and back in.
