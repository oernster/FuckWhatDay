"""A deliberately boring Brainfuck interpreter.

This module defines the execution model FuckWhatDay is written against and
contains no FuckWhatDay specific logic. It executes any valid Brainfuck
program:

- the eight instructions ``> < + - . , [ ]``; every other byte is ignored
- byte cells wrapping modulo 256
- a fixed length tape starting at cell 0, every cell initially zero
- moving left of cell 0 or right of the last cell is an error, not a wrap
- input supplied up front as bytes; the behaviour of ``,`` at end of input
  is selectable so tests can prove a program does not depend on it
- an instruction limit so a broken program fails instead of hanging

It is slow on purpose: one instruction per loop iteration, no folding.
``tools/fastbf.py`` is the fast one and is tested against this one.

Command line use::

    python tools/interpreter.py src/fuckwhatday.bf < input.txt
"""

from __future__ import annotations

import sys
from dataclasses import dataclass

COMMANDS = "><+-.,[]"
CELL_MODULUS = 256
DEFAULT_TAPE_LENGTH = 30000
DEFAULT_STEP_LIMIT = 50_000_000

EOF_UNCHANGED = "unchanged"
EOF_ZERO = "zero"
EOF_MINUS_ONE = "minus_one"
EOF_MODES = (EOF_UNCHANGED, EOF_ZERO, EOF_MINUS_ONE)


class BrainfuckError(Exception):
    """Base class for every failure this interpreter reports."""


class BracketError(BrainfuckError):
    """The program's brackets do not match."""


class TapeBoundsError(BrainfuckError):
    """The data pointer left the tape."""


class StepLimitExceeded(BrainfuckError):
    """The program executed more instructions than allowed."""


@dataclass(frozen=True, slots=True)
class Result:
    """What a finished run leaves behind."""

    output: bytes
    tape: bytes
    pointer: int
    steps: int
    consumed: int  # input bytes actually read, excluding reads at end of input


def instructions(source: str) -> str:
    """Return the executable instruction stream of ``source``."""
    return "".join(ch for ch in source if ch in COMMANDS)


def match_brackets(code: str) -> tuple[int, ...]:
    """Return a jump table: for each bracket, the index of its partner."""
    jumps = [0] * len(code)
    stack: list[int] = []
    for index, ch in enumerate(code):
        if ch == "[":
            stack.append(index)
        elif ch == "]":
            if not stack:
                raise BracketError(f"unmatched ']' at instruction {index}")
            opening = stack.pop()
            jumps[opening] = index
            jumps[index] = opening
    if stack:
        raise BracketError(f"unmatched '[' at instruction {stack[-1]}")
    return tuple(jumps)


def _eof_value(mode: str, current: int) -> int:
    if mode == EOF_UNCHANGED:
        return current
    if mode == EOF_ZERO:
        return 0
    if mode == EOF_MINUS_ONE:
        return CELL_MODULUS - 1
    raise ValueError(f"unknown EOF mode {mode!r}; expected one of {EOF_MODES}")


def run(
    source: str,
    data: bytes = b"",
    *,
    step_limit: int = DEFAULT_STEP_LIMIT,
    tape_length: int = DEFAULT_TAPE_LENGTH,
    eof: str = EOF_UNCHANGED,
) -> Result:
    """Execute ``source`` with ``data`` as its input."""
    _eof_value(eof, 0)
    code = instructions(source)
    jumps = match_brackets(code)
    tape = bytearray(tape_length)
    output = bytearray()
    pointer = 0
    pc = 0
    read_at = 0
    steps = 0
    while pc < len(code):
        if steps >= step_limit:
            raise StepLimitExceeded(f"exceeded {step_limit} instructions")
        steps += 1
        op = code[pc]
        if op == ">":
            pointer += 1
            if pointer >= tape_length:
                raise TapeBoundsError(f"pointer moved past cell {tape_length - 1}")
        elif op == "<":
            pointer -= 1
            if pointer < 0:
                raise TapeBoundsError("pointer moved left of cell 0")
        elif op == "+":
            tape[pointer] = (tape[pointer] + 1) % CELL_MODULUS
        elif op == "-":
            tape[pointer] = (tape[pointer] - 1) % CELL_MODULUS
        elif op == ".":
            output.append(tape[pointer])
        elif op == ",":
            if read_at < len(data):
                tape[pointer] = data[read_at]
                read_at += 1
            else:
                tape[pointer] = _eof_value(eof, tape[pointer])
        elif op == "[":
            if tape[pointer] == 0:
                pc = jumps[pc]
        elif op == "]":
            if tape[pointer] != 0:
                pc = jumps[pc]
        pc += 1
    return Result(bytes(output), bytes(tape), pointer, steps, read_at)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: python tools/interpreter.py PROGRAM.bf < input", file=sys.stderr)
        return 2
    with open(argv[1], encoding="ascii") as handle:
        source = handle.read()
    result = run(source, sys.stdin.buffer.read())
    sys.stdout.buffer.write(result.output)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
