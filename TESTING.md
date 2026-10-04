# Testing FuckWhatDay

## The gate

From the repository root:

```powershell
python -m unittest discover -s tests -t .
$LASTEXITCODE
```

`0` means every test passed. Read the exit code, not the last line of the
output. The suite uses only the standard library's `unittest`; it also runs
under pytest if you prefer, though nothing requires it.

The whole suite (89 tests) took 92 seconds when measured on a desktop
machine. Most of that is the exhaustive calendar test and the 3,000 random
programs run on the boring interpreter.

## The layers

Each layer states what it proves. Just as importantly, it states what it
does not.

### 1. The boring interpreter (`test_interpreter.py`)

**Proves:** `tools/interpreter.py` implements the execution model in
ARCHITECTURE.md: each instruction, byte wrapping both ways, bracket
validation, input order, the three end of input conventions, the
instruction limit, tape bounds and the instruction count.

**Does not prove:** that the interpreter is correct for every program. It
is checked against hand written programs whose behaviour is known without
running anything. Passing the calendar tests does not substitute for this
layer; a wrong interpreter could agree with a wrong program.

### 1b. The fast interpreter (`test_fast_interpreter.py`)

**Proves:** `tools/fastbf.py` agrees with the boring interpreter on output,
final tape, pointer, instruction count and bytes consumed. Checked over
hand written programs and 3,000 seeded random programs under random end of
input conventions. Where the boring interpreter fails on tape bounds, the
fast one must fail the same way; where it hits the instruction limit, the
fast one must fail too.

This layer earned its place on day one. The random corpus found a real
divergence: a transfer loop such as `[<>-]` steps onto cell -1 without
changing it; the first version of the fast interpreter only checked
bounds on cells a loop changed. It is now a named regression case.

**Does not prove:** agreement on every possible program. It is a sampled
equivalence, backed by the exact agreement checks in layer 6.

### 2. The oracle (`test_reference.py`)

**Proves:** `tools/reference.py` agrees with seven well documented
historical weekdays (1945-05-08, 1969-07-20, 2001-09-11 and others), that
the supported range holds exactly 73,049 dates and that its parsing
rejects what the input contract rejects.

**Does not prove:** that Python's `datetime` is right everywhere. It is a
widely used independent implementation; these facts guard against misusing
it.

### 3. Assembler routines (`test_primitives.py`)

**Proves:** each routine the program is built from does what
ARCHITECTURE.md says, over its input domain: `copy` and `flag_member` for
every byte value, `divmod` for every byte value with divisors 4 and 7, both
conditionals at 0, 1, 2 and 255. Each run also checks that every scratch
cell is back to zero. Contract tests check that loops return the pointer to
their cell, that a comment containing a command is refused and that the
scratch pool refuses to overdraw.

**Does not prove:** that the routines are composed correctly. Layers 4 to 6
do that.

### 4. Parser and tape map (`test_tape.py`)

**Proves:** after a run, the cells named in the ARCHITECTURE.md tape map
hold what it says they hold: century, year, month, day, both mod 4 values,
both ceilings, the leap flag, month length, month offset and the
weekday. Expected values come from Python's `calendar` module, not from the
program's formulas. Checked on every 97th supported date plus invalid and
malformed inputs. The workspace (input digits, `char`, `out`, scratch) must
end at zero. A further test reads the tape map table out of ARCHITECTURE.md
and compares it with the generator's layout, so the document cannot drift.

**Does not prove:** anything about dates it does not sample. Layer 6 covers
the full range for the final answer.

### 5. Named dates (`test_examples.py`)

**Proves:** the dates in the specification plus 30 boundary dates (month
ends of every length, February to March in common, leap, non leap century
and leap century years, December to January inside and across a century,
first and last supported dates) print the right weekday. These run on the
**boring** interpreter, so they do not depend on the fast one. Each expected
value is also checked against the oracle, so a typo in the table fails
rather than agreeing with a bug.

While writing this table every weekday was worked out by hand from 1
January of the year, then confirmed by the oracle. The specification's
expected values were all correct; none needed amending.

### 6. Invalid input (`test_invalid_dates.py`)

**Proves:** 15 impossible dates (including 1900-02-29 and 30 February in a
leap year), 6 out of range years and 17 malformed inputs (empty, too few or
too many digits, missing terminator, separators, letters, spaces, tabs, NUL,
0xFF, the bytes either side of the digits) all print `INVALID`. Every
malformed case runs under all three end of input conventions. Two further
tests prove reading stops at the first bad byte and that nothing after the
terminator is read. Every one of the 256 byte values is substituted into
each of the nine input positions of a valid line (2,304 inputs) and the
output compared with the oracle. A seeded fuzz of 1,500 near valid inputs is
compared byte for byte with the oracle.

### 7. Every supported date (`test_calendar.py`)

**Proves:** for every one of the 73,049 dates from 1900-01-01 to
2099-12-31, the committed `src/fuckwhatday.bf` prints the same weekday as
the oracle. Passing it establishes agreement with an independent reference
across the entire declared domain. It also runs every 211th date on both
interpreters and requires identical results (output, tape, pointer,
instruction count); it also checks those dates give identical results under all
three end of input conventions.

**Does not prove:** that the interpreter is universally correct (layers 1
and 1b) nor anything about dates outside the supported range beyond the
fact that they are rejected (layer 6).

### 8. Source and structure (`test_source.py`)

**Proves:**

- the executable holds only the eight commands plus line feeds; its
  brackets balance
- every comment line in the annotated source is free of command characters
- the annotated source is byte for byte what `tools/program.py` generates,
  the executable is byte for byte the stripped annotated source and the
  generator is deterministic
- the program contains exactly nine `,` instructions and exactly 58 `.`
  instructions, the number needed to spell the seven names, `INVALID` and
  one line feed once each
- no module under `tools/` imports anything that could reach a network or
  spawn a process; the generator imports nothing that knows about dates or
  time; the interpreters import only `sys`, `dataclasses` and each other and
  their code mentions no weekday, leap year or program file

**A weak bound, stated as weak:** the program is also checked to hold fewer
instructions than there are supported dates. That rules out a naive per
date table, not a compressed one. The real evidence that the program
computes rather than looks up is the algorithm in ARCHITECTURE.md, the
generator's inability to see a date and the tape map tests showing the
intermediate values being computed.

### 9. Determinism (`test_determinism.py`)

**Proves:** repeated runs on the same input give identical results; two
independent compilations by the fast interpreter generate identical Python
and identical results; both interpreters agree on every input there under
every end of input convention.

A Brainfuck program has no clock, randomness, environment or file access;
its only input is the byte stream. The structural tests in layer 8 check
that the toolchain adds none.

## Guards proven by planting a violation

A test that has never been seen to fail is not yet a guard. Each of these
was planted, observed to fail, then restored:

| Planted defect | Caught by |
|---|---|
| A stray `x` at the start of `src/fuckwhatday.bf` | purity and reproducibility tests |
| One `+` changed to `-` in the executable | reproducibility test |
| `import socket` in `tools/strip.py` | network boundary and generator boundary tests |
| `import datetime` in `tools/program.py` | generator boundary test |
| The epoch weekday off by one | exhaustive test: all 73,049 dates wrong |
| The "minus one day" constant set to zero | exhaustive test: all 73,049 dates wrong |
| The leap rule replaced by "every fourth year" | exhaustive test: 307 answers wrong (1900-02-29 accepted, March to December 1900 shifted) |

## What the tests never do

No network access, no clock reads, no randomness without a fixed seed, no
files written. Every application test runs the committed
`src/fuckwhatday.bf`, never a freshly generated copy, so what is tested is
what ships.

## Coverage

There is no line coverage gate: the suite uses only the standard library;
`coverage.py` is not part of it. The gate that matters here is domain
coverage. Every supported date is executed, every byte value is fed to the
character classifier and to `divmod`; every malformed input class runs
under every end of input convention.

## Running part of the suite

```powershell
python -m unittest tests.test_examples
python -m unittest tests.test_calendar
python -m unittest tests.test_source.PurityTests
```

See also [ARCHITECTURE.md](ARCHITECTURE.md), [DECISIONS.md](DECISIONS.md)
and [DEVELOPMENT.md](DEVELOPMENT.md).
