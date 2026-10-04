"""The test oracle: what FuckWhatDay should print for a given input.

This is NOT part of the application. It exists so tests can compare the
Brainfuck program's answer against an independent one.

It deliberately shares no algorithm with the Brainfuck program. The weekday
comes from Python's ``datetime`` (proleptic Gregorian ordinals) and validity
from ``datetime`` refusing to build an impossible date. The Brainfuck program
instead counts days from 1 January of the year using century arithmetic and
month lengths; see ARCHITECTURE.md.
"""

from __future__ import annotations

import datetime

FIRST_SUPPORTED = datetime.date(1900, 1, 1)
LAST_SUPPORTED = datetime.date(2099, 12, 31)

WEEKDAYS = (
    "MONDAY",
    "TUESDAY",
    "WEDNESDAY",
    "THURSDAY",
    "FRIDAY",
    "SATURDAY",
    "SUNDAY",
)
INVALID = "INVALID"

DIGITS = "0123456789"
INPUT_DIGITS = len("YYYYMMDD")
TERMINATORS = (b"\n", b"\r")


def parse(text: str) -> datetime.date | None:
    """Return the supported date ``text`` names; None for anything else."""
    if len(text) != INPUT_DIGITS or any(ch not in DIGITS for ch in text):
        return None
    try:
        date = datetime.date(int(text[:4]), int(text[4:6]), int(text[6:]))
    except ValueError:
        return None
    if not FIRST_SUPPORTED <= date <= LAST_SUPPORTED:
        return None
    return date


def weekday(date: datetime.date) -> str:
    """Return the English weekday name of ``date`` in capitals."""
    return WEEKDAYS[date.weekday()]


def expected_output(data: bytes) -> bytes:
    """Return the exact bytes FuckWhatDay must write for input ``data``.

    The contract: eight ASCII digits then a line feed or carriage return.
    Nothing after the terminator is read, so it cannot change the answer.
    """
    body = data[:INPUT_DIGITS]
    terminator = data[INPUT_DIGITS : INPUT_DIGITS + 1]
    date = None
    if terminator in TERMINATORS:
        date = parse(body.decode("latin-1"))
    answer = INVALID if date is None else weekday(date)
    return (answer + "\n").encode("ascii")


def supported_dates():
    """Yield every date in the supported range, in order."""
    date = FIRST_SUPPORTED
    one_day = datetime.timedelta(days=1)
    while date <= LAST_SUPPORTED:
        yield date
        date += one_day


def encode(date: datetime.date) -> bytes:
    """Return the input line for ``date``."""
    return date.strftime("%Y%m%d").encode("ascii") + b"\n"
