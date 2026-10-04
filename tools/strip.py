"""Produce the executable ``fuckwhatday.bf`` from the annotated source.

Stripping keeps the eight command characters in order and drops everything
else, then wraps the result into lines of a fixed width so the file diffs
sensibly. Line feeds are the only non command bytes in the output; every
conforming interpreter ignores them.
"""

from __future__ import annotations

import sys
from pathlib import Path

from tools.interpreter import instructions

LINE_WIDTH = 80

ROOT = Path(__file__).resolve().parent.parent
ANNOTATED_PATH = ROOT / "src" / "fuckwhatday.annotated.bf"
STRIPPED_PATH = ROOT / "src" / "fuckwhatday.bf"


def strip(annotated: str) -> str:
    """Return the stripped, wrapped executable form of ``annotated``."""
    code = instructions(annotated)
    lines = [code[i : i + LINE_WIDTH] for i in range(0, len(code), LINE_WIDTH)]
    return "\n".join(lines) + "\n"


def main() -> int:
    annotated = ANNOTATED_PATH.read_text(encoding="ascii")
    STRIPPED_PATH.write_text(strip(annotated), encoding="ascii", newline="\n")
    print(f"wrote {STRIPPED_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
