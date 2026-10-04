"""Regenerate the Brainfuck sources and the copies the website serves.

Run from the repository root::

    python -m tools.build

In order: the annotated source, the stripped source, the two files the
GitHub Pages site loads (``docs/fuckwhatday.bf`` and ``docs/tape-map.json``),
then the site's pages (``tools/site.py``).
``tests/test_source.py`` and ``tests/test_site.py`` fail if any committed
file differs from what this produces, so none can drift from the generator.
"""

from __future__ import annotations

import json
import shutil
import sys

from tools import program, site, strip

SITE = program.ROOT / "docs"
SITE_PROGRAM = SITE / "fuckwhatday.bf"
SITE_TAPE_MAP = SITE / "tape-map.json"


def tape_map_json() -> str:
    """Return the persistent cells as JSON for the site's tape inspector."""
    cells = [
        {"address": cell.address, "name": cell.name, "role": cell.role}
        for cell in program.PERSISTENT
    ]
    return json.dumps(cells, indent=2) + "\n"


def publish() -> None:
    SITE.mkdir(exist_ok=True)
    shutil.copyfile(strip.STRIPPED_PATH, SITE_PROGRAM)
    print(f"wrote {SITE_PROGRAM.relative_to(program.ROOT)}")
    SITE_TAPE_MAP.write_text(tape_map_json(), encoding="ascii", newline="\n")
    print(f"wrote {SITE_TAPE_MAP.relative_to(program.ROOT)}")


def main() -> int:
    program.main()
    strip.main()
    publish()
    return site.main()


if __name__ == "__main__":
    sys.exit(main())
