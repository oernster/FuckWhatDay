"""Generate the committed Windows icon from the master PNG.

Run only when ``assets/app-icon.png`` changes::

    python -m tools.genicons

The result, ``assets/fuckwhatday.ico``, is committed, so building the exe
needs no image library. This is the only tool that uses a package outside
the standard library (Pillow).
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
MASTER = ROOT / "assets" / "app-icon.png"
ICON = ROOT / "assets" / "fuckwhatday.ico"
SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)


def main() -> int:
    with Image.open(MASTER) as image:
        image.convert("RGBA").save(ICON, sizes=[(s, s) for s in SIZES])
    print(f"wrote {ICON.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
