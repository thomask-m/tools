"""Fonts, downloaded into ~/Library/Fonts. Add a file name and URL to FONTS."""
from ..core import Task, register

FONTS = {  # file name in ~/Library/Fonts -> download URL
    # Used by ~/.emacs: (font . "FixederSys 2x 16"). https://tom7.org/fixedersys/
    "FixederSys2x.ttf": "https://tom7.org/fixedersys/FixederSys2x.ttf",
}


@register
class Fonts(Task):
    name = "fonts"
    description = "Fonts: " + ", ".join(FONTS)

    def _missing(self) -> dict[str, str]:
        fonts_dir = self.ctx.home / "Library" / "Fonts"
        return {name: url for name, url in FONTS.items() if not (fonts_dir / name).exists()}

    def is_done(self) -> bool:
        return not self._missing()

    def apply(self) -> None:
        fonts_dir = self.ctx.home / "Library" / "Fonts"
        for name, url in self._missing().items():
            self.ctx.install_file(self.ctx.download(url), fonts_dir / name)

    def uninstall(self) -> None:
        for name in FONTS:
            self.ctx.stash(self.ctx.home / "Library" / "Fonts" / name)
