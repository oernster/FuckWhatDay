# Decisions

Each entry records what was decided, the alternatives and the trade-off.

## Why FuckWhatDay exists

WhatDay already tells you what day it is, sensibly. FuckWhatDay answers the
same question for any date in two centuries, using a language with eight
instructions and no numbers wider than a byte. The point is to show that a
small, verifiable application can be engineered properly whatever the
implementation language, by putting the rigour in the structure (tape map,
routine contracts, exhaustive comparison) rather than in the language.

There is overwhelming evidence that it should not exist. It does anyway.

## Bounded date range: 1900-01-01 to 2099-12-31

An unbounded year needs multi byte arithmetic, which multiplies the size of
every routine for no gain in what the program demonstrates. Two centuries
are enough to need the full Gregorian rule (1900 is not a leap year, 2000
is) and few enough dates, 73,049, to test every one. The range check is
also cheap: it is exactly "century is 19 or 20".

## Weekday algorithm: days from year 0, by century and year

The weekday of 1 January is computed arithmetically from the century and
the year within it (ARCHITECTURE.md, stage 6), then the lengths of the
earlier months and the day of the month are added, all mod 7.

Alternatives considered:

- **Zeller's congruence** treats January and February as months 13 and 14
  of the previous year. Borrowing a year across the century boundary
  (2000-01 belongs to 1999) means a borrow between the two bytes that hold
  the year. Avoidable complexity.
- **A four entry century anchor table (the Doomsday method)** is compact
  but hides the leap rule inside the table, which is harder to audit.
- **Counting days from a fixed epoch with a loop per day** is simple and
  far too slow: tens of thousands of iterations per date, each with
  Brainfuck overhead.

The chosen form keeps the leap rule explicit, needs no borrow across bytes
and reuses the month length walk that validation needs anyway, so one pass
over the months serves both.

The oracle uses Python's `datetime` instead, so the program and its oracle
do not share a formula (nor, therefore, a mistake in one).

## Numeric representation

A four digit year does not fit in a byte, so the year is stored as two
bytes, `century` (19 or 20) and `year` (0 to 99). Every leap year and
weekday term is expressed in those two numbers. The alternative, a 16 bit
year built from two cells with carry, would need multi byte division for
mod 4, mod 100 and mod 400. Splitting at the century boundary makes all of
those single byte operations.

The weekday accumulator is reduced mod 7 once part way through and once at
the end. The bound of 205 (ARCHITECTURE.md) shows that is enough.
Subtraction mod 7 is always done by adding 6, so no value ever goes below
zero on a valid path.

## Byte cells with wrapping

Byte cells that wrap are the most common interpreter convention, so the
program assumes them and depends on them. The values it computes (century,
year, month, day, the leap terms, the weekday accumulator) stay between 0
and 205 on every valid path, so no answer is produced by wrapping
arithmetic. The countdowns and walkers that do the comparisons are another
matter: the month countdown, the membership walker and the output countdown
routinely run past zero, wrap and are then cleared one unit at a time. On
an interpreter with wider cells each such clear would take up to one step
per value the cell can hold (over four billion for 32 bit cells), so
FuckWhatDay requires 8 bit wrapping cells. That requirement is stated
in the README rather than engineered away.

## Input format: `YYYYMMDD` then LF or CR

`YYYYMMDD` is one fixed width field with no separators to validate, which
keeps the reader a simple loop of eight identical steps. `YYYY-MM-DD` would
add two more checks for modest benefit.

The terminator is required, rather than optional, because Brainfuck has no
portable end of input: interpreters leave the cell unchanged, write zero or
write 255. Requiring a terminator means a valid line never reaches end of
input. A read that does reach it can only yield 0 or 255, neither of which is
a digit or a terminator, so it always rejects. That turns undefined
behaviour into a documented rejection under every convention.

CR is accepted as well as LF because PowerShell pipes send `\r\n`
(measured). The CR terminates; the LF is never read.

There is no prompt. The output is exactly one line, which keeps the program
usable in pipes and makes the test contract a byte comparison.

## Validation strategy: one flag, checked at the end

Every check clears one cell, `valid`. Nothing branches early except reading,
which stops at the first rejected byte so the program never waits for input
it is going to reject. An impossible month needs no check of its own: it
never matches in the month walk, so its length stays 0 and every day is
then out of range. The weekday arithmetic is skipped for invalid input,
because that is where the value bounds stop holding.

Full validation turned out to be proportionate. Nothing in the
specification's validation list was dropped.

## Tape layout: fixed addresses, a lent scratch pool

Every value has one fixed cell, named once in `tools/program.py` and
documented in ARCHITECTURE.md. Temporaries come from a pool of seven cells
lent and returned by the assembler. Fixed addresses make the pointer
position known at every instruction, which is what makes pointer contracts
mechanical rather than a matter of care. The cost is pointer travel: the
pool sits beyond the named cells, so many routines walk twenty or so cells
each way. That costs execution steps rather than correctness; it was accepted.

## Generated source, annotated and stripped

The program is written as calls to a small macro assembler
(`tools/bfasm.py`, `tools/program.py`). The assembler writes
`src/fuckwhatday.annotated.bf`; stripping writes `src/fuckwhatday.bf`.

The alternative was writing 17,534 instructions by hand. That would be
neither auditable nor testable stage by stage: an off by one pointer move
in the middle of a hand typed block has no name to find it by.

This does not move the calculation into Python. The generator never sees a
date, imports nothing that knows about dates or time (a structural test
checks) and emits the same fixed text on every run. It decides which
instructions to write, the way a C compiler does; the arithmetic happens
when those instructions run. Both Brainfuck files are committed, so the
program can be read, run and audited without Python; tests fail if
either file differs from what the generator produces.

## Why the test tooling is Python

Testing needs an interpreter, an oracle and a harness able to execute the
program 73,049 times. Python's standard library provides all three with no
dependencies. None of it performs the application's calculation: the
oracle exists to disagree with the program when the program is wrong.

## Two interpreters

The boring interpreter defines the execution model and is simple enough to
check by reading. At about 40 ms per date it would take most of an hour to
run every date. The fast interpreter compiles the program to Python once,
folds instruction runs and turns simple transfer loops into arithmetic; it
runs a date in well under a millisecond. It is trusted only because it is
tested against the boring one, on random programs and on sampled dates of
the real program, down to the instruction count.

## Why exhaustive verification

The domain is finite and small. Sampling would leave a question the
exhaustive run answers outright. Every supported date runs on every test
run, in about half a minute, so "every supported date has been tested" is a
claim the normal test command re-establishes.

## Optimisation: deferred

The program has not been optimised for size or speed. Pointer travel to the
scratch pool and clearing of wrapped countdowns dominate its cost. Placing
the scratch pool between the cells it serves would cut execution steps; so
would clearing countdowns by adding back a known amount. Neither is a
release requirement and both would make the layout harder to document.
