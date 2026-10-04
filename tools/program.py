"""The FuckWhatDay program, written as assembler calls.

Running this module writes ``src/fuckwhatday.annotated.bf``. ``strip.py``
then produces ``src/fuckwhatday.bf``. The calendar arithmetic itself happens
only when that Brainfuck runs; this module chooses instructions, never
answers. ARCHITECTURE.md explains every stage in pseudocode.

Constants are defined once here with their derivation. Each becomes a run of
``+`` or ``-`` in the emitted program.
"""

from __future__ import annotations

import sys
from pathlib import Path

from tools.bfasm import Assembler, Cell

# Calendar facts --------------------------------------------------------

WEEKDAY_NAMES = (
    "MONDAY",
    "TUESDAY",
    "WEDNESDAY",
    "THURSDAY",
    "FRIDAY",
    "SATURDAY",
    "SUNDAY",
)
DAYS_PER_WEEK = len(WEEKDAY_NAMES)
INVALID_TEXT = "INVALID"
NEWLINE = "\n"

MONTH_LENGTHS = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
FEBRUARY = 2

YEARS_PER_CENTURY = 100
LEAP_EVERY = 4  # years
CENTURIES_PER_CYCLE = 4  # a century year is leap every 400 years
DAYS_PER_COMMON_YEAR = 365

# Days from 1 January of a century year to 1 January a century later, for a
# century whose own first year is not leap: 100 years of 365 days plus one
# leap day for every fourth year except the century year itself.
DAYS_PER_CENTURY = (
    YEARS_PER_CENTURY * DAYS_PER_COMMON_YEAR + YEARS_PER_CENTURY // LEAP_EVERY - 1
)
CENTURY_SHIFT = DAYS_PER_CENTURY % DAYS_PER_WEEK

# Weekday (Monday is 0) of 1 January of year 0 of the proleptic Gregorian
# calendar. A 400 year cycle is exactly 146097 days, 20871 weeks, so this is
# also the weekday of 1 January 2000, a Saturday. ARCHITECTURE.md derives it.
EPOCH_WEEKDAY = WEEKDAY_NAMES.index("SATURDAY")

# Subtracting one day without risking an underflow: add one less than a week.
MINUS_ONE_DAY = DAYS_PER_WEEK - 1

FIRST_YEAR = 1900
LAST_YEAR = 2099
SUPPORTED_CENTURIES = tuple(
    range(FIRST_YEAR // YEARS_PER_CENTURY, LAST_YEAR // YEARS_PER_CENTURY + 1)
)

# Input contract ----------------------------------------------------------

ZERO = ord("0")
DIGIT_CODES = tuple(range(ZERO, ZERO + 10))
TERMINATOR_CODES = (ord("\n"), ord("\r"))
DECIMAL = 10

# Tape layout -------------------------------------------------------------

PERSISTENT = (
    Cell(0, "valid", "1 while the input is still acceptable; 0 once rejected"),
    Cell(1, "char", "the byte just read; zero between reads"),
    Cell(2, "digit0", "first year digit; moved into century then zero"),
    Cell(3, "digit1", "second year digit; moved into century then zero"),
    Cell(4, "digit2", "third year digit; moved into year then zero"),
    Cell(5, "digit3", "fourth year digit; moved into year then zero"),
    Cell(6, "digit4", "first month digit; moved into month then zero"),
    Cell(7, "digit5", "second month digit; moved into month then zero"),
    Cell(8, "digit6", "first day digit; moved into day then zero"),
    Cell(9, "digit7", "second day digit; moved into day then zero"),
    Cell(10, "century", "year div 100"),
    Cell(11, "year", "year mod 100"),
    Cell(12, "month", "month as entered"),
    Cell(13, "day", "day as entered"),
    Cell(14, "century_mod4", "century mod 4"),
    Cell(15, "century_leaps", "ceil of century over 4"),
    Cell(16, "year_mod4", "year mod 4"),
    Cell(17, "year_leaps", "ceil of year over 4"),
    Cell(18, "leap", "1 if the full year is a Gregorian leap year"),
    Cell(19, "month_length", "days in the entered month; 0 if no such month"),
    Cell(20, "month_offset", "sum of earlier month lengths each taken mod 7"),
    Cell(21, "sum", "weekday accumulator; zero after the final reduction"),
    Cell(22, "weekday", "0 is Monday through 6 Sunday; valid input only"),
    Cell(23, "out", "output workspace; zero between characters"),
)
SCRATCH_FIRST = len(PERSISTENT)
SCRATCH_SIZE = 7  # the measured high water mark; test_tape holds it there
SCRATCH = tuple(
    Cell(SCRATCH_FIRST + i, f"scratch{i}", "scratch; zero on loan and on return")
    for i in range(SCRATCH_SIZE)
)
LAYOUT = PERSISTENT + SCRATCH
CELLS = {cell.name: cell for cell in PERSISTENT}

DIGITS = tuple(CELLS[f"digit{i}"] for i in range(8))


def _read_input(asm: Assembler) -> None:
    c = CELLS
    asm.section(
        "READ AND CHECK INPUT",
        "reads eight digits then one terminator; stops reading at the first bad byte",
    )
    asm.add(c["valid"], 1)
    for digit in DIGITS:
        asm.note(f"read {digit.name} only while still valid")
        with asm.if_nonzero(c["valid"]):
            asm.read(c["char"])
            with asm.scratch(1) as ok:
                asm.flag_member(c["char"], DIGIT_CODES, ok)

                def accept(digit=digit):
                    asm.move(c["char"], digit)
                    asm.add(digit, -ZERO)

                def reject():
                    asm.clear(c["valid"])

                asm.if_else(ok, accept, reject)
                asm.clear(ok)
            asm.clear(c["char"])
    asm.note("read the terminator only while still valid; it must be LF or CR")
    with asm.if_nonzero(c["valid"]):
        asm.read(c["char"])
        _require_member(asm, c["char"], TERMINATOR_CODES)
        asm.clear(c["char"])


def _require_member(asm: Assembler, value: Cell, constants: tuple[int, ...]) -> None:
    with asm.scratch(1) as ok:
        asm.flag_member(value, constants, ok)
        with asm.if_zero(ok):
            asm.clear(CELLS["valid"])
        asm.clear(ok)


def _assemble_numbers(asm: Assembler) -> None:
    c = CELLS
    asm.section(
        "ASSEMBLE NUMBERS",
        "digits are destroyed; century year month day are built",
    )
    pairs = (
        ("century", 0),
        ("year", 2),
        ("month", 4),
        ("day", 6),
    )
    for name, first in pairs:
        asm.move(DIGITS[first], c[name], factor=DECIMAL)
        asm.move(DIGITS[first + 1], c[name])
    asm.note("the century must be one the supported range covers")
    _require_member(asm, c["century"], SUPPORTED_CENTURIES)


def _divide(
    asm: Assembler,
    source: Cell,
    bias: int,
    quotient: Cell | None,
    remainder: Cell | None,
) -> None:
    """Divide a copy of ``source`` plus ``bias`` by LEAP_EVERY."""
    with asm.scratch(3) as (work, q, r):
        asm.copy(source, work)
        asm.add(work, bias)
        asm.divmod(work, LEAP_EVERY, quotient or q, remainder or r)
        asm.clear(q)
        asm.clear(r)


def _leap_year(asm: Assembler) -> None:
    c = CELLS
    asm.section(
        "LEAP YEAR",
        "century and year preserved; sets the mod4 and leaps cells and leap",
    )
    ceiling = LEAP_EVERY - 1
    _divide(asm, c["century"], 0, None, c["century_mod4"])
    _divide(asm, c["century"], ceiling, c["century_leaps"], None)
    _divide(asm, c["year"], 0, None, c["year_mod4"])
    _divide(asm, c["year"], ceiling, c["year_leaps"], None)
    asm.note("leap when year mod 4 is 0 and either year is not 0")
    asm.note("or the century is a multiple of 4")
    with asm.if_zero(c["year_mod4"]), asm.scratch(1) as either:
        with asm.if_nonzero(c["year"]):
            asm.add(either, 1)
        with asm.if_zero(c["century_mod4"]):
            asm.add(either, 1)
        with asm.once(either):
            asm.add(c["leap"], 1)


def _months(asm: Assembler) -> None:
    c = CELLS
    asm.section(
        "MONTH LENGTH AND OFFSET",
        "month preserved; walks a countdown through the twelve months",
    )
    asm.note("an out of range month never reaches zero so month length stays 0")
    with asm.scratch(2) as (countdown, earlier):
        asm.copy(c["month"], countdown)
        asm.add(earlier, 1)
        for number, length in enumerate(MONTH_LENGTHS, start=1):
            asm.note(f"month {number} has {length} days")
            asm.add(countdown, -1)
            with asm.if_zero(countdown):
                asm.clear(earlier)
                asm.add(c["month_length"], length)
                if number == FEBRUARY:
                    asm.copy(c["leap"], c["month_length"])
            with asm.if_nonzero(earlier):
                asm.add(c["month_offset"], length % DAYS_PER_WEEK)
                if number == FEBRUARY:
                    asm.copy(c["leap"], c["month_offset"])
        asm.clear(countdown)
        asm.clear(earlier)


def _check_day(asm: Assembler) -> None:
    c = CELLS
    asm.section(
        "DAY CHECK",
        "day and month length preserved; clears valid unless day is in range",
    )
    with asm.if_zero(c["day"]):
        asm.clear(c["valid"])
    asm.note("count day down against month length; reaching zero first means too big")
    with asm.scratch(3) as (count, room, over):
        asm.copy(c["day"], count)
        asm.copy(c["month_length"], room)
        with asm.loop(count):
            asm.add(count, -1)
            with asm.if_zero(room):
                asm.set(over, 1)
            asm.add(room, -1)
        asm.clear(room)
        with asm.once(over):
            asm.clear(c["valid"])


def _reduce(asm: Assembler, value: Cell, target: Cell) -> None:
    """Replace ``value`` by itself mod 7, written to ``target``."""
    with asm.scratch(2) as (quotient, remainder):
        asm.divmod(value, DAYS_PER_WEEK, quotient, remainder)
        asm.clear(quotient)
        asm.move(remainder, target)


def _weekday(asm: Assembler) -> None:
    c = CELLS
    s = c["sum"]
    asm.section(
        "WEEKDAY",
        "runs only for valid input; inputs preserved; sets weekday",
    )
    with asm.if_nonzero(c["valid"]):
        asm.note("weekday of 1 January of year 0")
        asm.add(s, EPOCH_WEEKDAY)
        asm.note("each whole century shifts the weekday by 36524 mod 7")
        with asm.scratch(1) as work:
            asm.copy(c["century"], work)
            asm.move(work, s, factor=CENTURY_SHIFT)
        _reduce(asm, s, s)
        asm.note("plus one day for each 400 year leap century before this one")
        asm.copy(c["century_leaps"], s)
        asm.note("plus one day per year since the century began")
        asm.copy(c["year"], s)
        asm.note("plus one day per leap year since the century began")
        asm.copy(c["year_leaps"], s)
        asm.note("less one day if that count included a non leap century year")
        with asm.if_nonzero(c["year"]), asm.if_nonzero(c["century_mod4"]):
            asm.add(s, MINUS_ONE_DAY)
        asm.note("plus the days in earlier months of this year")
        asm.copy(c["month_offset"], s)
        asm.note("plus the day of the month less one")
        asm.copy(c["day"], s)
        asm.add(s, MINUS_ONE_DAY)
        _reduce(asm, s, c["weekday"])


def _output(asm: Assembler) -> None:
    c = CELLS
    asm.section("OUTPUT", "prints a weekday name or INVALID then a line feed")

    def name() -> None:
        with asm.scratch(1) as countdown:
            asm.copy(c["weekday"], countdown)
            asm.add(countdown, 1)
            for text in WEEKDAY_NAMES:
                asm.add(countdown, -1)
                with asm.if_zero(countdown):
                    asm.note(text)
                    asm.print_text(c["out"], text)
            asm.clear(countdown)

    def invalid() -> None:
        asm.note(INVALID_TEXT)
        asm.print_text(c["out"], INVALID_TEXT)

    asm.if_else(c["valid"], name, invalid)
    asm.note("line feed")
    asm.print_text(c["out"], NEWLINE)


HEADER = (
    "FUCKWHATDAY",
    "A Gregorian day of week calculator written in Brainfuck",
    "",
    "Input  eight ASCII digits YYYYMMDD then a line feed or carriage return",
    "Output MONDAY to SUNDAY or INVALID then a line feed",
    "Range  1900 01 01 to 2099 12 31",
    "",
    "This annotated file is generated by the program module in tools",
    "Every comment is free of the eight command characters so stripping",
    "comments cannot change behaviour; the stripped copy is fuckwhatday bf",
    "Tape map and algorithm are in ARCHITECTURE md",
)


def build() -> tuple[str, Assembler]:
    """Return the annotated source and the assembler that produced it."""
    asm = Assembler(SCRATCH)
    for line in HEADER:
        asm.note(line)
    _read_input(asm)
    _assemble_numbers(asm)
    _leap_year(asm)
    _months(asm)
    _check_day(asm)
    _weekday(asm)
    _output(asm)
    asm.section("END", "every scratch cell is zero")
    return asm.text(), asm


ROOT = Path(__file__).resolve().parent.parent
ANNOTATED_PATH = ROOT / "src" / "fuckwhatday.annotated.bf"


def main() -> int:
    text, _ = build()
    ANNOTATED_PATH.parent.mkdir(exist_ok=True)
    ANNOTATED_PATH.write_text(text, encoding="ascii", newline="\n")
    print(f"wrote {ANNOTATED_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
