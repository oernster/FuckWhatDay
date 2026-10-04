# FuckWhatDay architecture

Brainfuck is hard to inspect, so this document is part of what makes the
implementation auditable. It explains why the program works without anyone
having to execute 17,534 instructions by hand. Every invariant below names
the test that enforces it.

## Invariants

| Invariant | Enforced by |
|---|---|
| The executable holds only the eight commands plus line feeds | `tests/test_source.py::PurityTests` |
| The executable is exactly the stripped annotated source, which is exactly what the generator produces | `tests/test_source.py::ReproducibilityTests` |
| Every supported date gives the same answer as an independent oracle | `tests/test_calendar.py` |
| The program reads at most nine bytes and never reads past the terminator | `test_source.py::test_at_most_nine_reads`, `test_invalid_dates.py::test_nothing_after_the_terminator_is_read` |
| End of input behaviour cannot change any answer | `test_invalid_dates.py` (malformed input under all three conventions), `test_calendar.py::test_valid_dates_ignore_the_end_of_input_convention` |
| Every scratch cell is zero when lent and when returned | `test_primitives.py::assert_scratch_clean`, `test_tape.py::assert_workspace_clean` |
| The tape map below is the layout the generator used; the cells hold what it says | `tests/test_tape.py` |
| No comment in the annotated source contains a command character | `Assembler.note` refuses one; `test_source.py` rechecks the file |
| Nothing in the toolchain can reach a network, spawn a process or (in the generator) know about dates | `test_source.py::ToolingBoundaryTests` |

## Execution assumptions

FuckWhatDay targets a conventional interpreter:

- the eight instructions `> < + - . , [ ]`; every other byte is ignored
- byte cells, wrapping 0 to 255 in both directions
- the pointer starts at cell 0; every cell starts at zero
- at least 31 cells to the right of cell 0 (cells 0 to 30 are used); no
  negative positions
- no particular behaviour of `,` at end of input (see below)

It depends on no interpreter extension, no cell larger than a byte and no
preprocessing. `tools/interpreter.py` defines exactly this model and is
tested on its own.

**End of input.** The program clears the cell it reads into, so the three
common conventions leave 0 (unchanged or zero) or 255 (minus one) there.
Neither is a digit or a terminator. A read that hits end of input therefore
always rejects the input, whichever convention the interpreter uses. On a
valid line the program stops after the terminator, so it never reaches end
of input at all.

## The pipeline

```
 input bytes
     |
 1 READ AND CHECK INPUT     8 digits then LF or CR; stop at the first bad byte
 2 ASSEMBLE NUMBERS         century, year, month, day; century must be 19 or 20
 3 LEAP YEAR                Gregorian rule from century and year
 4 MONTH LENGTH AND OFFSET  one countdown walk through the twelve months
 5 DAY CHECK                1 <= day <= month length
 6 WEEKDAY                  only when still valid; arithmetic mod 7
 7 OUTPUT                   weekday name or INVALID, then a line feed
```

Each stage is a section of `src/fuckwhatday.annotated.bf` with a heading in
capitals, the pointer position on entry and a one line contract. Every stage
runs on every input. `valid` decides what is printed; no stage skips
another. The only conditional stages are the reads (which stop at the first
rejection) and the weekday arithmetic (which runs only for valid input,
where its value bounds hold).

## Tape map

Cells are byte values. "Zero" means the cell is zero whenever no routine is
using it.

| Cell | Name | Holds |
|---|---|---|
| 0 | `valid` | 1 while the input is still acceptable; 0 once rejected |
| 1 | `char` | the byte just read; zero between reads |
| 2 | `digit0` | first year digit; moved into `century`, then zero |
| 3 | `digit1` | second year digit; moved into `century`, then zero |
| 4 | `digit2` | third year digit; moved into `year`, then zero |
| 5 | `digit3` | fourth year digit; moved into `year`, then zero |
| 6 | `digit4` | first month digit; moved into `month`, then zero |
| 7 | `digit5` | second month digit; moved into `month`, then zero |
| 8 | `digit6` | first day digit; moved into `day`, then zero |
| 9 | `digit7` | second day digit; moved into `day`, then zero |
| 10 | `century` | year div 100 (19 or 20 when valid) |
| 11 | `year` | year mod 100 |
| 12 | `month` | month as entered (0 to 99) |
| 13 | `day` | day as entered (0 to 99) |
| 14 | `century_mod4` | century mod 4 |
| 15 | `century_leaps` | ceil(century / 4) |
| 16 | `year_mod4` | year mod 4 |
| 17 | `year_leaps` | ceil(year / 4) |
| 18 | `leap` | 1 if the full year is a Gregorian leap year |
| 19 | `month_length` | days in the entered month; 0 if there is no such month |
| 20 | `month_offset` | sum of the earlier months' lengths, each taken mod 7 |
| 21 | `sum` | weekday accumulator; zero after the final reduction |
| 22 | `weekday` | 0 for Monday to 6 for Sunday; valid input only |
| 23 | `out` | output workspace; zero between characters |
| 24 to 30 | scratch | pool of seven temporaries, lent by the assembler |

Cells 10 to 22 keep their values when the program ends, which is what lets
`tests/test_tape.py` check them against values computed independently with
Python's `calendar` module. Cells 1 to 9, 23 and the scratch pool end at zero.

The scratch pool is sized to the measured high water mark of seven cells.
`test_tape.py` fails if the generator ever needs more or fewer.

## Representation

**Input.** Eight ASCII digits `YYYYMMDD`, then `\n` (10) or `\r` (13).
Nothing after the terminator is read. PowerShell pipes end lines with
`\r\n`; the `\r` terminates and the `\n` is never read.

**Parsed date.** A four digit year does not fit in a byte, so the year is
held as two numbers: `century = Y div 100` and `year = Y mod 100`, with
`Y = 100 * century + year`. Month and day are single bytes. Every value the
program builds from valid input stays below 256 (bounds below), so
wrapping never happens on a valid path. On invalid paths wrapping is
harmless: every loop is bounded by a byte value and the result is discarded.

**Booleans.** A flag is 0 or 1. Some intermediate counts (`either` in the
leap year stage) reach 2; they are only ever tested for zero.

## Routines and their contracts

All routines are emitted by `tools/bfasm.py`. Because every cell has a fixed
address, the generator always knows where the pointer is. "Pointer contract"
therefore has a precise meaning: a routine may be entered with the pointer
anywhere, because the assembler emits the moves to reach its cells. Where it
leaves the pointer is also known at generation time; every loop returns
the pointer to the cell it tests before its closing bracket. In Brainfuck,
being one cell to the left is a different program; here it cannot happen
silently, because no instruction is written by hand.

| Routine | Effect | Inputs | Scratch |
|---|---|---|---|
| `clear(a)` | `a = 0` | destroys `a` | none |
| `set(a, k)` | `a = k` | destroys `a` | none |
| `move(a, b...)` | `b += a` for each target (optionally times a factor); `a = 0` | **destroys** `a` | none |
| `copy(a, b)` | `b += a` | preserves `a` | 1 |
| `once(a)` | run the block once if `a != 0` | **destroys** `a` (cleared first) | none |
| `if_nonzero(a)` | run the block once if `a != 0` | preserves `a` | 2 |
| `if_zero(a)` | run the block once if `a == 0` | preserves `a` | 3 |
| `if_else(a, f, g)` | `f` if `a != 0`, else `g` | preserves `a` | 3 |
| `flag_member(v, K, r)` | `r = 1` if `v` is in the constant set `K` | preserves `v`; `r` must be 0 | 1 plus `if_zero` |
| `divmod(n, d, q, r)` | `q += n div d`, `r = n mod d` | **destroys** `n`; `r` must be 0 | 1 plus `if_zero` |
| `print_text(o, s)` | write the string `s` | `o` is 0 before and after | none |

`once` is the primitive conditional: `a[[-] body]`. Clearing `a` first
makes the loop run at most once. `if_zero` uses the standard flag idiom:
set a flag, clear it if a copy of `a` is non zero, then `once(flag)`.

`flag_member` never compares with `<` or `>`. It walks a copy of the value
down through the sorted constants, subtracting the gap to each; it tests
for zero at each stop. A value outside the set never reaches zero at a stop,
whatever wrapping does in between.

`divmod` counts one unit at a time against a countdown that starts at `d`.
When the countdown reaches zero it is reset to `d`, the remainder is
cleared and the quotient goes up by one. No intermediate value exceeds `n`.

## Stage 1: reading and checking input

```
valid = 1
for each of the eight digit cells:
    if valid:
        char = read()
        if char is one of '0'..'9': digit = char - '0'
        else: valid = 0
        char = 0
if valid:
    char = read()
    if char is not LF and not CR: valid = 0
    char = 0
```

The program contains exactly nine `,` instructions, none inside a loop that
could repeat it. Too few digits fails at the first non digit (often the
terminator). Too many digits fails at the terminator check, which sees a
digit. An empty input fails at the first read, under any end of input
convention.

## Stage 2: assembling numbers

```
century = 10 * digit0 + digit1      (move with factor 10, then move)
year    = 10 * digit2 + digit3
month   = 10 * digit4 + digit5
day     = 10 * digit6 + digit7
if century is not one of 19, 20: valid = 0
```

The century check is the whole range check: 1900 to 2099 is exactly
centuries 19 and 20 with any `year` from 00 to 99.

## Stage 3: the Gregorian leap year rule

The rule is leap if divisible by 4, except divisible by 100, unless
divisible by 400. With `Y = 100c + y`:

- `Y mod 4 = y mod 4`, because 100 is a multiple of 4
- `Y mod 100 = y`
- `Y mod 400 = 0` exactly when `y = 0` and `c mod 4 = 0`

So:

```
leap = (y mod 4 == 0) and (y != 0 or c mod 4 == 0)
```

That is the complete rule, evaluated for whatever century was entered. It
is not the "every fourth year" shortcut. A planted shortcut (see
TESTING.md) changes 307 answers: 1900-02-29 accepted, plus every day from
March to December 1900 shifted by one.

In tape operations: `divmod` on copies gives `century_mod4` and
`year_mod4`; then `if_zero(year_mod4)` holds a counter `either`, increased by
`if_nonzero(year)` and by `if_zero(century_mod4)`; `once(either)` sets `leap`.

The same stage computes `century_leaps = ceil(c / 4)` and
`year_leaps = ceil(y / 4)` as `(x + 3) div 4`, which stage 6 needs.

## Stage 4: month length and month offset

One walk through the twelve months produces both the length of the entered
month and the days in the months before it:

```
countdown = month; earlier = 1
for k = 1 to 12:
    countdown = countdown - 1
    if countdown == 0:
        earlier = 0
        month_length = length(k) + (leap if k == 2)
    if earlier:
        month_offset += (length(k) mod 7) + (leap if k == 2)
```

`length(k)` is the twelve entry table 31, 28, 31, 30, 31, 30, 31, 31, 30,
31, 30, 31, emitted as constants. February's leap day is added by copying
`leap`. This is the only table in the program apart from the seven names;
it maps months to lengths, not dates to weekdays.

An impossible month needs no separate check. Month 0 starts the countdown
at 0, which wraps to 255 on the first step and never returns to zero in 12
steps. Months 13 to 99 stay above zero for all 12 steps. Either way
`month_length` stays 0 and stage 5 rejects every day.

## Stage 5: day check

```
if day == 0: valid = 0
count = day; room = month_length; over = 0
repeat count times:
    if room == 0: over = 1
    room = room - 1
if over: valid = 0
```

`over` is set exactly when the walk finds `room` at zero before `count` runs
out, that is when `day > month_length`. Together with the century check this
covers every rejection the specification lists: month outside 1 to 12, day
0, day past the end of the month, 29 February in a common year and years
outside 1900 to 2099.

## Stage 6: the weekday

Number weekdays Monday 0 to Sunday 6. Let `E` be the weekday of 1 January
of year 0 in the proleptic Gregorian calendar.

**Days before 1 January of year Y = 100c + y.** From year 0 there are
`365 Y` days plus one per leap year in years `0` to `Y - 1`:

- leap years in `0` to `100c - 1`: `25c` multiples of 4, less `c` century
  years, plus `ceil(c/4)` multiples of 400; that is `24c + ceil(c/4)`
- leap years in `100c` to `100c + y - 1`: `ceil(y/4)` multiples of 4, less
  one if that range includes the century year `100c` (when `y >= 1`) and the
  century year is not leap (when `c mod 4 != 0`)

`365 Y = 36500c + 365y`, so the total is
`36524c + ceil(c/4) + 365y + ceil(y/4) - correction`.
Mod 7, `36524 = 5` and `365 = 1`, giving

```
jan1    = E + 5c + ceil(c/4) + y + ceil(y/4) - correction      (mod 7)
weekday = jan1 + month_offset + (day - 1)                      (mod 7)
```

**The epoch.** A 400 year Gregorian cycle is 146,097 days, exactly 20,871
weeks, so 1 January of year 0 falls on the same weekday as 1 January 2000,
which is a Saturday: `E = 5`. As a check, `c = 20, y = 0` gives
`5 + 100 + 5 + 0 + 0 - 0 = 110`; `110 mod 7 = 5`: Saturday, as it
should be. `c = 19, y = 0` gives `105 mod 7 = 0`: 1 January 1900 was a
Monday.

**On the tape.** Subtraction mod 7 is done by adding 6, so the accumulator
never goes below zero:

```
sum  = 5                                (E)
sum += 5 * century; sum = sum mod 7     (at most 105 before reducing)
sum += century_leaps + year + year_leaps
if year != 0 and century_mod4 != 0: sum += 6
sum += month_offset + day + 6           (day - 1)
weekday = sum mod 7
```

**Bounds.** This stage runs only when `valid` is still 1, so `century` is
19 or 20 and `day` is at most 31. The largest value `sum` can reach is
6 + 5 + 99 + 25 + 6 + 27 + 31 + 6 = 205, below 256. (27 is the largest
`month_offset`, reached in December of a leap year.)

The oracle in `tools/reference.py` does not use this formula. It asks
Python's `datetime`, which counts proleptic Gregorian ordinals, so the two
are independent computations of the same fact.

## Stage 7: output

```
if valid:
    countdown = weekday + 1
    for each of the seven names in order:
        countdown = countdown - 1
        if countdown == 0: print name
else:
    print "INVALID"
print line feed
```

`print_text` walks the `out` cell from one character code to the next,
adding the difference and writing with `.`, then returns it to zero. The
program holds exactly 58 `.` instructions: the seven names, `INVALID` and
one line feed, each written once. `test_source.py` counts them.

## Source and executable

```
tools/program.py   --build-->   src/fuckwhatday.annotated.bf   --strip-->   src/fuckwhatday.bf
```

- `tools/program.py` describes the program as assembler calls and owns
  every constant, each with its derivation.
- `src/fuckwhatday.annotated.bf` is real Brainfuck: comments are free of
  command characters, so any conforming interpreter runs it as is. Its
  instruction stream is exactly the stripped file's, which a test checks.
- `src/fuckwhatday.bf` is the instruction stream, wrapped at 80 columns.

Both files are committed, so the program can be read and run without
Python.

```
src/fuckwhatday.bf   --tools/bf2c.py-->   build/fuckwhatday.c   --gcc-->   dist/fuckwhatday.exe
```

The Windows exe is the same program again. `tools/bf2c.py` replaces each
run of identical instructions with the one C statement that does the same
thing to an `unsigned char` tape, so the exe executes the Brainfuck's own
steps rather than any calendar logic of its own. It does not check tape
bounds; the program never leaves cells 0 to 30, which the interpreters
(which do check) establish on every test run. `python -m tools.build` regenerates both; `tests/test_source.py`
fails if either differs from what the generator produces.

The generator never sees a date. It imports no `datetime`, `calendar`,
`time` or `random` (a structural test checks), takes no input and emits the
same text on every run.

## Execution cost

Measured on the committed program: 17,534 instructions, bracket nesting at
most 4 deep, between 326,622 and 567,392 executed instructions per valid
date. The cost is dominated by moving the pointer to and from the scratch
pool and by clearing wrapped countdowns one unit at a time. None of this has
been optimised; see DECISIONS.md.

See also [TESTING.md](TESTING.md), [DECISIONS.md](DECISIONS.md) and
[DEVELOPMENT.md](DEVELOPMENT.md).
