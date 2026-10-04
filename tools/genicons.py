"""Generate the committed icons from the master PNG.

Run only when ``assets/app-icon.png`` changes::

    python -m tools.genicons

Writes ``assets/fuckwhatday.ico`` for the exe and the web sizes the
GitHub Pages site under ``docs/img`` uses. All are committed, so neither
building the exe nor publishing the site needs an image library. This is
the only tool that uses a package outside the standard library (Pillow).
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
MASTER = ROOT / "assets" / "app-icon.png"
ICON = ROOT / "assets" / "fuckwhatday.ico"
SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)

WEB = ROOT / "docs" / "img"
# Hero shown at 160 CSS pixels, so 320 keeps it sharp on 2x screens.
WEB_SIZES = {"icon-320.png": 320, "apple-touch-icon.png": 180, "favicon-32.png": 32}


def main() -> int:
    with Image.open(MASTER) as image:
        rgba = image.convert("RGBA")
    rgba.save(ICON, sizes=[(s, s) for s in SIZES])
    print(f"wrote {ICON.relative_to(ROOT)}")
    WEB.mkdir(parents=True, exist_ok=True)
    for name, size in WEB_SIZES.items():
        path = WEB / name
        rgba.resize((size, size), Image.Resampling.LANCZOS).save(path, optimize=True)
        print(f"wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
