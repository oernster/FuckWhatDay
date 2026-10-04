# Developing FuckWhatDay

## Tools

| Tool | What for | Where |
|---|---|---|
| Python 3 (developed and tested on 3.13) | the generator, both interpreters and the tests | python.org |
| MinGW-w64 gcc and windres (tested with WinLibs, gcc on PATH) | building the Windows exe | `winget install BrechtSanders.WinLibs.POSIX.UCRT` |
| Pillow | regenerating the icon, only when `assets/app-icon.png` changes | `python -m pip install pillow` |

The generator, interpreters and tests use only the standard library. The
exe test skips itself when gcc is not on PATH.

Every command below is PowerShell, run from the repository root.

## Layout

```
src/fuckwhatday.annotated.bf   the program, annotated (generated, committed)
src/fuckwhatday.bf             the program, stripped (generated, committed)
tools/bfasm.py                 macro assembler: cells, pointer tracking, routines
tools/program.py               the program as assembler calls, plus the tape layout
tools/strip.py                 annotated to stripped
tools/build.py                 runs program then strip
tools/interpreter.py           the boring reference interpreter
tools/fastbf.py                the fast compiling interpreter
tools/reference.py             the test oracle
tools/bf2c.py                  Brainfuck to C, one statement per instruction run
tools/genicons.py              master PNG to the committed .ico
buildexe.py                    builds and checks dist/fuckwhatday.exe
assets/fuckwhatday.ico         the exe icon (generated, committed)
tests/                         see TESTING.md
```

## Building the exe

```powershell
python buildexe.py
```

In order, it:

1. translates `src/fuckwhatday.bf` to `build/fuckwhatday.c` with
   `tools/bf2c.py`
2. compiles `assets/fuckwhatday.ico` into a resource with windres
3. compiles and statically links `dist/fuckwhatday.exe` with gcc (`-O2
   -static -s`), so it runs on Windows with nothing else installed
4. runs the exe on 13 smoke inputs (specified dates, invalid dates,
   malformed input, a CRLF line) and compares each answer with the oracle;
   any mismatch fails the build with a non zero exit code

`python buildexe.py --all` adds every supported date to step 4. One process
per date makes that take several minutes; run it before a release.

`build/` and `dist/` are ignored by git. To regenerate the icon after
changing the master PNG:

```powershell
python -m tools.genicons
```

## Running the program

```powershell
"20261004" | python tools/interpreter.py src/fuckwhatday.bf
```

Any Brainfuck interpreter with 8 bit wrapping cells works the same way.
Either source file can be given to it.

## Changing the program

1. Edit `tools/program.py` (the program) or `tools/bfasm.py` (the routines).
   A new cell goes in `PERSISTENT` and in the ARCHITECTURE.md tape map.
2. Regenerate both Brainfuck files:

   ```powershell
   python -m tools.build
   ```

   This writes `src/fuckwhatday.annotated.bf`, then strips it to
   `src/fuckwhatday.bf`.
3. Run the gate:

   ```powershell
   python -m unittest discover -s tests -t .
   $LASTEXITCODE
   ```

Never edit either `.bf` file by hand. `tests/test_source.py` fails if they
differ from what the generator produces.

Comments passed to `Assembler.note` may not contain any of `+ - < > . , [ ]`.
The assembler refuses them at build time, so write "minus one" rather than
"-1" and leave out full stops.

## Standing rules

- No date, clock, randomness or network in the generator; a structural test
  enforces it.
- No interpreter knows anything about FuckWhatDay; a structural test
  enforces it.
- Constants live in `tools/program.py` with their derivation, never as bare
  numbers in a routine.
- A claim in README.md, ARCHITECTURE.md or TESTING.md needs a test behind
  it. If the test does not exist, the claim does not go in.

## Releases

There is no release process and no version number yet. The program is the
two committed `.bf` files; a clean checkout plus the gate is the whole
verification.

See also [ARCHITECTURE.md](ARCHITECTURE.md), [TESTING.md](TESTING.md) and
[DECISIONS.md](DECISIONS.md).
