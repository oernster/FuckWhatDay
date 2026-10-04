"""Shared helpers: load the committed program and run it.

Every application test runs the committed ``src/fuckwhatday.bf``, never a
freshly generated copy, so what is tested is exactly what ships.
``test_source.py`` separately proves the committed file is what the
generator produces.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from tools import fastbf
from tools import interpreter as bf

ROOT = Path(__file__).resolve().parent.parent
PROGRAM_PATH = ROOT / "src" / "fuckwhatday.bf"
ANNOTATED_PATH = ROOT / "src" / "fuckwhatday.annotated.bf"


@lru_cache(maxsize=1)
def source() -> str:
    return PROGRAM_PATH.read_text(encoding="ascii")


@lru_cache(maxsize=1)
def compiled() -> fastbf.Program:
    return fastbf.Program(source())


def run_fast(data: bytes, **options) -> bf.Result:
    return compiled().run(data, **options)


def run_boring(data: bytes, **options) -> bf.Result:
    return bf.run(source(), data, **options)


def line(text: str) -> bytes:
    """Return ``text`` as an input line ending in a line feed."""
    return text.encode("ascii") + b"\n"
