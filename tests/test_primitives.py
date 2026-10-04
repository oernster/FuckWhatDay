"""The assembler's routines, each run as its own small program.

FuckWhatDay is built entirely from these routines, so each is checked over
its whole input domain (every byte value where that is cheap) on the boring
interpreter, including the promise that scratch cells come back zero.
"""

from __future__ import annotations

import unittest

from tools import interpreter as bf
from tools.bfasm import Assembler, AssemblyError, Cell

A = Cell(0, "a", "operand")
B = Cell(1, "b", "operand")
C = Cell(2, "c", "operand")
D = Cell(3, "d", "result")
POOL_SIZE = 8
SCRATCH = tuple(Cell(4 + i, f"s{i}", "scratch") for i in range(POOL_SIZE))
SCRATCH_SLICE = slice(SCRATCH[0].address, SCRATCH[-1].address + 1)
EVERY_BYTE = range(bf.CELL_MODULUS)
DIVISORS = (4, 7)


def execute(build, *initial: int) -> bf.Result:
    """Assemble ``build`` after loading ``initial`` into a, b, c; run it."""
    asm = Assembler(SCRATCH)
    for cell, value in zip((A, B, C), initial):
        asm.add(cell, value)
    build(asm)
    return bf.run(asm.text())


class RoutineTests(unittest.TestCase):
    def assert_scratch_clean(self, result):
        self.assertEqual(result.tape[SCRATCH_SLICE], bytes(POOL_SIZE))

    def test_copy_preserves_the_source(self):
        for value in EVERY_BYTE:
            result = execute(lambda asm: asm.copy(A, B), value)
            self.assertEqual(result.tape[:2], bytes([value, value]))
            self.assert_scratch_clean(result)

    def test_move_scales_and_empties_the_source(self):
        result = execute(lambda asm: asm.move(A, B, C, factor=3), 5)
        self.assertEqual(result.tape[:3], bytes([0, 15, 15]))

    def test_set_replaces_the_value(self):
        result = execute(lambda asm: asm.set(A, 9), 200)
        self.assertEqual(result.tape[0], 9)

    def test_if_zero_and_if_nonzero(self):
        for value in (0, 1, 2, bf.CELL_MODULUS - 1):

            def build(asm):
                with asm.if_zero(A):
                    asm.add(B, 1)
                with asm.if_nonzero(A):
                    asm.add(C, 1)

            result = execute(build, value)
            with self.subTest(value=value):
                self.assertEqual(
                    result.tape[:3], bytes([value, value == 0, value != 0])
                )
                self.assert_scratch_clean(result)

    def test_if_else_takes_exactly_one_branch(self):
        for value in (0, 1, bf.CELL_MODULUS - 1):

            def build(asm):
                asm.if_else(A, lambda: asm.add(B, 1), lambda: asm.add(C, 1))

            result = execute(build, value)
            with self.subTest(value=value):
                self.assertEqual(result.tape[1:3], bytes([value != 0, value == 0]))
                self.assert_scratch_clean(result)

    def test_flag_member_over_every_byte(self):
        constants = (10, 13, 19, 20)
        for value in EVERY_BYTE:
            result = execute(lambda asm: asm.flag_member(A, constants, D), value)
            self.assertEqual(result.tape[D.address], value in constants, value)
            self.assertEqual(result.tape[A.address], value)
            self.assert_scratch_clean(result)

    def test_divmod_over_every_byte(self):
        for divisor in DIVISORS:
            for value in EVERY_BYTE:
                result = execute(lambda asm, d=divisor: asm.divmod(A, d, B, C), value)
                with self.subTest(value=value, divisor=divisor):
                    quotient, remainder = divmod(value, divisor)
                    self.assertEqual(result.tape[:3], bytes([0, quotient, remainder]))
                    self.assert_scratch_clean(result)

    def test_divmod_adds_to_an_existing_quotient(self):
        result = execute(lambda asm: asm.divmod(A, 4, B, C), 9, 100)
        self.assertEqual(result.tape[1:3], bytes([102, 1]))

    def test_print_text_writes_and_leaves_the_cell_zero(self):
        result = execute(lambda asm: asm.print_text(D, "SUNDAY\n"))
        self.assertEqual(result.output, b"SUNDAY\n")
        self.assertEqual(result.tape[D.address], 0)

    def test_read_and_write(self):
        def build(asm):
            asm.read(A)
            asm.write(A)

        self.assertEqual(bf.run(_text(build), b"q").output, b"q")


class ContractTests(unittest.TestCase):
    def test_loop_returns_the_pointer_to_its_cell(self):
        asm = Assembler(SCRATCH)
        with asm.loop(A):
            asm.add(A, -1)
            asm.add(C, 1)
        self.assertEqual(asm.pointer, A.address)

    def test_comments_may_not_contain_commands(self):
        for text in ("day + 1", "a, b", "x < y", "end.", "[note]"):
            with self.subTest(text=text), self.assertRaises(AssemblyError):
                Assembler(SCRATCH).note(text)

    def test_scratch_pool_exhaustion_is_refused(self):
        asm = Assembler(SCRATCH)
        with self.assertRaises(AssemblyError), asm.scratch(POOL_SIZE + 1):
            pass

    def test_scratch_is_returned_after_use(self):
        asm = Assembler(SCRATCH)
        with asm.scratch(POOL_SIZE):
            pass
        with asm.scratch(POOL_SIZE):
            pass
        self.assertEqual(asm.scratch_high_water, POOL_SIZE)


def _text(build) -> str:
    asm = Assembler(SCRATCH)
    build(asm)
    return asm.text()


if __name__ == "__main__":
    unittest.main()
