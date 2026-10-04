"""Regenerate both Brainfuck sources: annotated first, then stripped.

Run from the repository root::

    python -m tools.build

``tests/test_source.py`` fails if the committed files differ from what this
produces, so the two cannot drift apart from their generator.
"""

from __future__ import annotations

import sys

from tools import program, strip


def main() -> int:
    program.main()
    return strip.main()


if __name__ == "__main__":
    sys.exit(main())
