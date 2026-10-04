"""A small macro assembler that writes annotated Brainfuck.

This is development tooling, in the same sense as a C compiler is tooling
for a C program. It turns calls such as ``copy(day, x)`` into the fixed
Brainfuck instructions that perform them at run time. It never sees a date:
nothing here (nor in ``tools/program.py``) reads input, calls ``datetime`` or
emits a value that depends on a calendar date. The arithmetic happens when
the emitted Brainfuck runs.

Design rules, which ARCHITECTURE.md relies on:

- Every cell has one fixed address, named once in a layout. The pointer's
  position is therefore known at every point of generation, so the pointer
  contract of each routine is mechanical: a loop always returns the pointer
  to the cell it tests before its closing bracket.
- Scratch cells come from a pool. A scratch cell is zero when handed out and
  must be zero when handed back; ``tests/test_tape.py`` checks the whole
  pool is zero when the program ends.
- Comments may not contain any of the eight commands, so annotation can never
  change behaviour. ``note`` refuses such text.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass

from tools.interpreter import CELL_MODULUS, COMMANDS

INDENT = "  "
CODE_WIDTH = 72
HALF_CELL = CELL_MODULUS // 2


class AssemblyError(Exception):
    """The program description asked for something the assembler refuses."""


@dataclass(frozen=True, slots=True)
class Cell:
    """A named tape cell at a fixed address."""

    address: int
    name: str
    role: str


class Assembler:
    """Accumulates annotated Brainfuck while tracking the data pointer."""

    def __init__(self, scratch: tuple[Cell, ...]) -> None:
        self.pointer = 0
        self._lines: list[str] = []
        self._code = ""
        self._depth = 0
        self._free = list(scratch)
        self._in_use: list[Cell] = []
        self.scratch_high_water = 0

    # Text ---------------------------------------------------------------

    def text(self) -> str:
        """Return the annotated source produced so far."""
        self._flush()
        return "\n".join(self._lines) + "\n"

    def _flush(self) -> None:
        if self._code:
            self._lines.append(INDENT * self._depth + self._code)
            self._code = ""

    def _emit(self, code: str) -> None:
        self._code += code
        if len(self._code) >= CODE_WIDTH:
            self._flush()

    def note(self, text: str) -> None:
        """Add a comment line; refuses text holding a command character."""
        bad = sorted(set(text) & set(COMMANDS))
        if bad:
            raise AssemblyError(f"comment {text!r} contains commands {bad}")
        self._flush()
        self._lines.append(INDENT * self._depth + text if text else "")

    def section(self, title: str, contract: str) -> None:
        """Start a titled block and record where the pointer stands."""
        self.note("")
        self.note(title)
        self.note(f"  pointer at cell {self.pointer}")
        self.note(f"  {contract}")

    # Scratch ------------------------------------------------------------

    @contextmanager
    def scratch(self, count: int):
        """Lend ``count`` zeroed scratch cells for the duration of a block."""
        if count > len(self._free):
            raise AssemblyError("scratch pool exhausted; enlarge the layout")
        cells = [self._free.pop(0) for _ in range(count)]
        self._in_use.extend(cells)
        self.scratch_high_water = max(self.scratch_high_water, len(self._in_use))
        try:
            yield cells[0] if count == 1 else tuple(cells)
        finally:
            for cell in cells:
                self._in_use.remove(cell)
            self._free = sorted(self._free + cells, key=lambda c: c.address)

    # Primitive instructions ---------------------------------------------

    def goto(self, cell: Cell) -> None:
        """Move the pointer to ``cell``."""
        distance = cell.address - self.pointer
        self._emit(">" * distance if distance > 0 else "<" * -distance)
        self.pointer = cell.address

    def add(self, cell: Cell, amount: int) -> None:
        """Add ``amount`` (any integer) to ``cell`` modulo 256."""
        amount %= CELL_MODULUS
        if amount == 0:
            return
        self.goto(cell)
        self._emit(
            "+" * amount if amount <= HALF_CELL else "-" * (CELL_MODULUS - amount)
        )

    def read(self, cell: Cell) -> None:
        """Read one input byte into ``cell``."""
        self.goto(cell)
        self._emit(",")

    def write(self, cell: Cell) -> None:
        """Write ``cell`` as one output byte."""
        self.goto(cell)
        self._emit(".")

    @contextmanager
    def loop(self, cell: Cell):
        """Repeat the block while ``cell`` is non zero.

        Pointer contract: the block may move anywhere; the assembler returns
        the pointer to ``cell`` before the closing bracket.
        """
        self.goto(cell)
        self._emit("[")
        self._flush()
        self._depth += 1
        yield
        self.goto(cell)
        self._flush()
        self._depth -= 1
        self._emit("]")
        self._flush()

    # Routines built from the primitives ---------------------------------

    def clear(self, cell: Cell) -> None:
        """Set ``cell`` to zero."""
        self.goto(cell)
        self._emit("[-]")

    def set(self, cell: Cell, value: int) -> None:
        """Set ``cell`` to ``value``."""
        self.clear(cell)
        self.add(cell, value)

    def move(self, source: Cell, *targets: Cell, factor: int = 1) -> None:
        """Add ``factor`` times ``source`` to every target; ``source`` ends 0.

        Destructive on ``source``. One flat loop, no nested brackets.
        """
        self.goto(source)
        self._emit("[-")
        for target in targets:
            self.add(target, factor)
        self.goto(source)
        self._emit("]")

    def copy(self, source: Cell, target: Cell) -> None:
        """Add ``source`` to ``target``; ``source`` is preserved."""
        with self.scratch(1) as spare:
            self.note(f"add {source.name} to {target.name} via {spare.name}")
            self.move(source, target, spare)
            self.move(spare, source)

    @contextmanager
    def once(self, cond: Cell):
        """Run the block once if ``cond`` is non zero; ``cond`` ends zero.

        Destructive on ``cond``, which is cleared before the block runs.
        """
        with self.loop(cond):
            self.clear(cond)
            yield

    @contextmanager
    def if_nonzero(self, cell: Cell):
        """Run the block once if ``cell`` is non zero; ``cell`` preserved."""
        with self.scratch(1) as test:
            self.note(f"if {cell.name} is not zero")
            self.copy(cell, test)
            with self.once(test):
                yield

    @contextmanager
    def if_zero(self, cell: Cell):
        """Run the block once if ``cell`` is zero; ``cell`` preserved."""
        with self.scratch(2) as (flag, test):
            self.note(f"if {cell.name} is zero")
            self.add(flag, 1)
            self.copy(cell, test)
            with self.once(test):
                self.add(flag, -1)
            with self.once(flag):
                yield

    def if_else(self, cell: Cell, then, otherwise) -> None:
        """Call ``then`` if ``cell`` is non zero, else ``otherwise``."""
        with self.scratch(1) as pending:
            self.note(f"if {cell.name} then the first branch else the second")
            self.add(pending, 1)
            with self.if_nonzero(cell):
                self.add(pending, -1)
                then()
            self.note(f"else branch for {cell.name}")
            with self.once(pending):
                otherwise()

    def flag_member(
        self, value: Cell, constants: tuple[int, ...], result: Cell
    ) -> None:
        """Set ``result`` to 1 if ``value`` equals one of ``constants``.

        ``result`` must be zero on entry; ``value`` is preserved. The test
        walks a copy down through the sorted constants and checks for zero at
        each one, so no comparison relies on wrapping.
        """
        with self.scratch(1) as walker:
            listed = " ".join(str(constant) for constant in sorted(set(constants)))
            self.note(f"set {result.name} if {value.name} is one of {listed}")
            self.copy(value, walker)
            reached = 0
            for constant in sorted(set(constants)):
                self.add(walker, -(constant - reached))
                reached = constant
                with self.if_zero(walker):
                    self.set(result, 1)
            self.clear(walker)

    def divmod(
        self, number: Cell, divisor: int, quotient: Cell, remainder: Cell
    ) -> None:
        """Add ``number // divisor`` to ``quotient`` and set ``remainder``.

        Destructive on ``number``. ``quotient`` may already hold a value,
        which is added to; ``remainder`` must be zero on entry. One unit is
        counted at a time against a countdown from ``divisor``, so no
        intermediate value exceeds ``number``.
        """
        with self.scratch(1) as countdown:
            self.note(
                f"divide {number.name} by {divisor} into "
                f"{quotient.name} and {remainder.name}"
            )
            self.add(countdown, divisor)
            with self.loop(number):
                self.add(number, -1)
                self.add(remainder, 1)
                self.add(countdown, -1)
                with self.if_zero(countdown):
                    self.add(countdown, divisor)
                    self.clear(remainder)
                    self.add(quotient, 1)
            self.clear(countdown)

    def print_text(self, cell: Cell, text: str) -> None:
        """Write ``text`` through ``cell``, which is zero before and after."""
        current = 0
        for ch in text:
            self.add(cell, ord(ch) - current)
            current = ord(ch)
            self.write(cell)
        self.add(cell, -current)
