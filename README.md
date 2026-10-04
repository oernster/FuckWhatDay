# <img width="128" height="128" alt="app-icon" src="https://github.com/user-attachments/assets/a8268d1e-684c-4b33-a35a-b5ecfba68ed0" /> FuckWhatDay

A Gregorian day-of-week calculator written in Brainfuck.

It accepts a date and tells you what day of the week it is.

No part of that calculation is delegated to a sensible programming language.

FuckWhatDay exists because WhatDay already solved this problem sensibly.

> **Commercial licences available.** FuckWhatDay is free software under the
> GPL-3.0. A separately sold commercial licence covering the author's own
> code is also offered; see
> [ernster.dev/commercial-licensing.html](https://ernster.dev/commercial-licensing.html).

## What it does

- accepts a Gregorian date
- validates it
- calculates its weekday
- prints the weekday

## What it does not do

- read the system clock
- access the network
- store personal data
- require an account
- require a database
- use Python to perform the actual calculation
- make sensible use of engineering time

## Who it is for

People who want to see a small, non trivial program built properly in a
language that does everything it can to prevent that: readers interested
in Brainfuck, in verification or in what "tested" can mean when the domain
is small enough to test completely.

It is not for finding out what day it is. Use WhatDay or a calendar.

## Supported range

1900-01-01 to 2099-12-31, proleptic Gregorian, with the full leap year rule:
divisible by 4, except divisible by 100, unless divisible by 400. 1900 is not
a leap year; 2000 is.

## Input and output

Input is eight ASCII digits, `YYYYMMDD`, followed by a line feed or a
carriage return. Nothing after the terminator is read.

Output is one line: the weekday in capitals or `INVALID`.

| Input | Output |
|---|---|
| `20261004` | `SUNDAY` |
| `20000229` | `TUESDAY` |
| `19000229` | `INVALID` (1900 is not a leap year) |
| `20260431` | `INVALID` (April has 30 days) |
| `20261301` | `INVALID` |
| `21000101` | `INVALID` (outside the supported range) |
| `2026-10-04` | `INVALID` (separators are not part of the format) |

Invalid dates, malformed input, missing terminators and empty input all
print `INVALID`. The program never guesses, normalises or wraps a bad date
into a good one.

## Running it

With the interpreter in this repository (Python 3, standard library only):

```powershell
"20261004" | python tools/interpreter.py src/fuckwhatday.bf
```

Or with any Brainfuck interpreter that meets the assumptions below.
`src/fuckwhatday.bf` is the program; `src/fuckwhatday.annotated.bf` is the
same program with comments; it runs too.

## Execution assumptions

- the eight standard instructions; everything else ignored
- 8 bit cells wrapping 0 to 255 (required, not merely preferred)
- at least 31 cells to the right of the start; no negative positions
- any end of input behaviour (unchanged, 0 or 255): the program never needs
  to read past the terminator; a read at end of input can only reject

## Running the tests

```powershell
python -m unittest discover -s tests -t .
$LASTEXITCODE
```

`0` means everything passed. The suite takes about a minute and a half.

## Verification

**Every supported date has been tested.** All 73,049 dates from 1900-01-01
to 2099-12-31 run through the committed program on every test run and must
match an independent reference built on Python's `datetime`, which shares no
algorithm with the program. The tests also cover:

- the Brainfuck interpreters themselves, before they are trusted as evidence
- every assembler routine over its input domain
- the documented tape map, cell by cell
- specified and boundary dates, including 1900 and 2000 in February
- impossible dates, every byte value in every input position and malformed
  input under all three end of input conventions
- source purity: the executable holds only Brainfuck, is exactly what the
  generator produces and holds exactly nine reads and enough output
  instructions to spell the eight possible answers once each
- determinism

[TESTING.md](TESTING.md) says what each layer proves and what it does not.

## How it works

The year is held as a century and a year within it, so every value fits in
a byte. The program reads and checks eight digits, applies the Gregorian
leap rule, walks the twelve months once to find both the month's length
and the days before it, then computes the weekday of 1 January from the
century and year with arithmetic mod 7. It adds the month offset and the
day, then prints one of seven names.

The Brainfuck is generated from a small macro assembler written in Python.
The generator never sees a date; it chooses instructions while the
calculation happens when they run. Both the annotated and the stripped
program are committed; a test fails if either differs from what the
generator produces.

- [ARCHITECTURE.md](ARCHITECTURE.md): tape map, algorithms, routine contracts
- [DECISIONS.md](DECISIONS.md): what was chosen and why
- [TESTING.md](TESTING.md): the test layers
- [DEVELOPMENT.md](DEVELOPMENT.md): changing and rebuilding the program

## Relationship to WhatDay

WhatDay is a desktop application that shows the current day of the week.
FuckWhatDay is not a port of it and shares no code with it. It takes the
same subject and makes almost every implementation decision unnecessarily
difficult. It has no clock, so it does not know what day it is today. You
tell it a date; it tells you the day.

## Stack

| Part | Technology |
|---|---|
| Application | Brainfuck |
| Generator, interpreters, oracle, tests | Python 3 standard library |

## Licence

GPL-3.0. See [LICENSE](LICENSE).

The joke is the implementation language. The engineering should not be a
joke.
