"""A fast Brainfuck interpreter that compiles a program to Python once.

Same execution model as ``tools/interpreter.py`` (byte cells, fixed tape,
selectable end of input behaviour, an instruction limit) and contains no
FuckWhatDay specific logic. It exists only so the exhaustive calendar test
can execute the program about 73,000 times in reasonable time.

Speed comes from three standard techniques:

- runs of ``+ - < >`` fold into one addition per cell and one pointer move
- a loop whose body only adds and moves, returns to its start and changes
  its own cell by exactly one per pass (``[-]``, ``[->+<]`` and the like)
  becomes a multiplication instead of a loop
- the whole program becomes one Python function, compiled once and reused

The instruction count it reports is exact: every folded operation adds the
number of raw instructions it stands for, so ``steps`` agrees with the
boring interpreter on every program that finishes.
``tests/test_fast_interpreter.py`` holds it to that.
"""

from __future__ import annotations

from dataclasses import dataclass

from tools.interpreter import (
    CELL_MODULUS,
    DEFAULT_STEP_LIMIT,
    DEFAULT_TAPE_LENGTH,
    EOF_MINUS_ONE,
    EOF_MODES,
    EOF_UNCHANGED,
    EOF_ZERO,
    Result,
    StepLimitExceeded,
    TapeBoundsError,
    instructions,
    match_brackets,
)

_MASK = CELL_MODULUS - 1
_UNCHANGED_SENTINEL = -1
_INDENT = "    "


@dataclass(frozen=True, slots=True)
class _Loop:
    body: tuple


def _parse(code: str) -> tuple:
    """Turn an instruction stream into a tree: characters and loops."""
    match_brackets(code)
    stack: list[list] = [[]]
    for ch in code:
        if ch == "[":
            stack.append([])
        elif ch == "]":
            body = stack.pop()
            stack[-1].append(_Loop(tuple(body)))
        else:
            stack[-1].append(ch)
    return tuple(stack[0])


@dataclass(frozen=True, slots=True)
class _Transfer:
    own: int
    deltas: tuple[tuple[int, int], ...]
    low: int
    high: int


def _transfer_shape(loop: _Loop) -> _Transfer | None:
    """Describe a pure add and move loop; None for any other loop.

    ``low`` and ``high`` are the furthest cells the body visits, not merely
    the cells it changes: ``[<>-]`` never changes cell -1 but still steps
    onto it, which is a tape error at cell 0.
    """
    offset = low = high = 0
    deltas: dict[int, int] = {}
    for item in loop.body:
        if isinstance(item, _Loop) or item in ".,":
            return None
        if item == ">":
            offset += 1
        elif item == "<":
            offset -= 1
        else:
            step = 1 if item == "+" else -1
            deltas[offset] = deltas.get(offset, 0) + step
        low, high = min(low, offset), max(high, offset)
    if offset != 0:
        return None
    own = deltas.pop(0, 0) % CELL_MODULUS
    if own not in (1, _MASK):
        return None
    kept = tuple(sorted((k, v) for k, v in deltas.items() if v % CELL_MODULUS))
    return _Transfer(own, kept, low, high)


class _Emitter:
    def __init__(self) -> None:
        self.lines: list[str] = []
        self.depth = 1
        self._reset()

    def _reset(self) -> None:
        self.ops: list[tuple] = []
        self.offset = 0
        self.low = 0
        self.high = 0
        self.count = 0

    def line(self, text: str) -> None:
        self.lines.append(_INDENT * self.depth + text)

    @staticmethod
    def cell(offset: int) -> str:
        return "t[p]" if offset == 0 else f"t[p + {offset}]"

    def char(self, ch: str) -> None:
        self.count += 1
        if ch in "<>":
            self.offset += 1 if ch == ">" else -1
            self.low = min(self.low, self.offset)
            self.high = max(self.high, self.offset)
            return
        if ch in "+-":
            step = 1 if ch == "+" else -1
            last = self.ops[-1] if self.ops else None
            if last and last[0] == "add" and last[1] == self.offset:
                self.ops[-1] = ("add", self.offset, last[2] + step)
            else:
                self.ops.append(("add", self.offset, step))
            return
        self.ops.append(("out" if ch == "." else "in", self.offset))

    def flush(self) -> None:
        if self.low < 0 or self.high > 0:
            self.line(f"if p + {self.low} < 0 or p + {self.high} >= L:")
            self.line(_INDENT + "raise TapeBoundsError('pointer left the tape')")
        for op in self.ops:
            cell = self.cell(op[1])
            if op[0] == "add":
                amount = op[2] % CELL_MODULUS
                if amount:
                    self.line(f"{cell} = ({cell} + {amount}) & {_MASK}")
            elif op[0] == "out":
                self.line(f"out.append({cell})")
            else:
                self.line("if r < n:")
                self.line(f"{_INDENT}{cell} = data[r]")
                self.line(f"{_INDENT}r += 1")
                self.line(f"elif eof != {_UNCHANGED_SENTINEL}:")
                self.line(f"{_INDENT}{cell} = eof")
        if self.offset:
            self.line(f"p += {self.offset}")
        if self.count:
            self.line(f"s += {self.count}")
        self._reset()

    def emit(self, nodes: tuple) -> None:
        for node in nodes:
            if isinstance(node, _Loop):
                self.loop(node)
            else:
                self.char(node)

    def loop(self, node: _Loop) -> None:
        self.flush()
        shape = _transfer_shape(node)
        if shape is not None:
            self.transfer(node, shape)
            return
        self.line("s += 1")
        self.line("while t[p]:")
        self.depth += 1
        self.line("if s > limit:")
        self.line(_INDENT + "raise StepLimitExceeded('instruction limit exceeded')")
        self.emit(node.body)
        self.count += 1
        self.flush()
        self.depth -= 1

    def transfer(self, node: _Loop, shape: _Transfer) -> None:
        per_pass = len(node.body) + 1
        self.line("v = t[p]")
        self.line("if v:")
        self.depth += 1
        if shape.own == 1:
            self.line(f"v = {CELL_MODULUS} - v")
        if shape.low < 0 or shape.high > 0:
            self.line(f"if p + {shape.low} < 0 or p + {shape.high} >= L:")
            self.line(_INDENT + "raise TapeBoundsError('pointer left the tape')")
        for offset, delta in shape.deltas:
            cell = self.cell(offset)
            self.line(f"{cell} = ({cell} + {delta % CELL_MODULUS} * v) & {_MASK}")
        self.line("t[p] = 0")
        self.line(f"s += v * {per_pass}")
        self.depth -= 1
        self.line("s += 1")


def _eof_code(mode: str) -> int:
    if mode == EOF_UNCHANGED:
        return _UNCHANGED_SENTINEL
    if mode == EOF_ZERO:
        return 0
    if mode == EOF_MINUS_ONE:
        return _MASK
    raise ValueError(f"unknown EOF mode {mode!r}; expected one of {EOF_MODES}")


class Program:
    """A Brainfuck program compiled once and runnable many times."""

    def __init__(self, source: str) -> None:
        emitter = _Emitter()
        emitter.emit(_parse(instructions(source)))
        emitter.flush()
        header = "def _execute(t, data, limit, L, eof):"
        prologue = ["p = 0", "s = 0", "r = 0", "n = len(data)", "out = bytearray()"]
        epilogue = [
            "if s > limit:",
            _INDENT + "raise StepLimitExceeded('instruction limit exceeded')",
            "return out, p, s, r",
        ]
        body = [_INDENT + text for text in prologue] + emitter.lines
        body += [_INDENT + text for text in epilogue]
        namespace = {
            "StepLimitExceeded": StepLimitExceeded,
            "TapeBoundsError": TapeBoundsError,
        }
        self.python_source = "\n".join([header, *body]) + "\n"
        # Compiling the translated program is this interpreter's whole method;
        # the source is generated above from the eight commands only.
        code = compile(self.python_source, "<brainfuck>", "exec")
        exec(code, namespace)  # noqa: S102
        self._execute = namespace["_execute"]

    def run(
        self,
        data: bytes = b"",
        *,
        step_limit: int = DEFAULT_STEP_LIMIT,
        tape_length: int = DEFAULT_TAPE_LENGTH,
        eof: str = EOF_UNCHANGED,
    ) -> Result:
        """Execute the program with ``data`` as its input."""
        tape = bytearray(tape_length)
        out, pointer, steps, consumed = self._execute(
            tape, data, step_limit, tape_length, _eof_code(eof)
        )
        return Result(bytes(out), bytes(tape), pointer, steps, consumed)


def run(source: str, data: bytes = b"", **options) -> Result:
    """Compile and execute ``source`` once; see ``Program.run``."""
    return Program(source).run(data, **options)
