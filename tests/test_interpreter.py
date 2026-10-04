"""The boring interpreter, tested on its own.

Every later layer uses this interpreter as evidence, so it is checked first
against programs whose behaviour is known without running FuckWhatDay.
"""

from __future__ import annotations

import unittest

from tools import interpreter as bf

CODE_H = ord("H")
CODE_I = ord("i")


class InstructionTests(unittest.TestCase):
    def test_plus_and_minus_change_the_current_cell(self):
        result = bf.run("+++--")
        self.assertEqual(result.tape[0], 1)

    def test_moves_change_the_current_cell(self):
        result = bf.run(">+>++<")
        self.assertEqual(result.tape[:3], bytes([0, 1, 2]))
        self.assertEqual(result.pointer, 1)

    def test_output_writes_the_current_cell(self):
        result = bf.run("+" * CODE_H + "." + "+" * (CODE_I - CODE_H) + ".")
        self.assertEqual(result.output, b"Hi")

    def test_input_reads_bytes_in_order(self):
        result = bf.run(",>,>,", b"abc")
        self.assertEqual(result.tape[:3], b"abc")

    def test_consumed_counts_bytes_read_but_not_end_of_input(self):
        self.assertEqual(bf.run(",,", b"abc").consumed, 2)
        self.assertEqual(bf.run(",,,,", b"ab").consumed, 2)

    def test_loop_multiplies(self):
        result = bf.run("++++++[>+++++++<-]>")
        self.assertEqual(result.tape[1], 42)
        self.assertEqual(result.tape[0], 0)

    def test_nested_loops(self):
        result = bf.run("+++[>++[>+++<-]<-]")
        self.assertEqual(result.tape[2], 18)

    def test_loop_with_zero_cell_is_skipped(self):
        result = bf.run("[+++]>+")
        self.assertEqual(result.tape[:2], bytes([0, 1]))

    def test_non_command_characters_are_ignored(self):
        result = bf.run("add one + then move > and add two ++ done")
        self.assertEqual(result.tape[:2], bytes([1, 2]))


class WrappingTests(unittest.TestCase):
    def test_decrement_below_zero_wraps_to_255(self):
        self.assertEqual(bf.run("-").tape[0], bf.CELL_MODULUS - 1)

    def test_increment_past_255_wraps_to_zero(self):
        self.assertEqual(bf.run("+" * bf.CELL_MODULUS).tape[0], 0)


class BracketTests(unittest.TestCase):
    def test_unmatched_open_is_rejected(self):
        with self.assertRaises(bf.BracketError):
            bf.run("+[")

    def test_unmatched_close_is_rejected(self):
        with self.assertRaises(bf.BracketError):
            bf.run("+]")

    def test_jump_table_pairs_partners(self):
        self.assertEqual(bf.match_brackets("[[]]"), (3, 2, 1, 0))


class EndOfInputTests(unittest.TestCase):
    def test_unchanged_leaves_the_cell_alone(self):
        result = bf.run("+++,", eof=bf.EOF_UNCHANGED)
        self.assertEqual(result.tape[0], 3)

    def test_zero_writes_zero(self):
        result = bf.run("+++,", eof=bf.EOF_ZERO)
        self.assertEqual(result.tape[0], 0)

    def test_minus_one_writes_255(self):
        result = bf.run("+++,", eof=bf.EOF_MINUS_ONE)
        self.assertEqual(result.tape[0], bf.CELL_MODULUS - 1)

    def test_unknown_mode_is_rejected(self):
        with self.assertRaises(ValueError):
            bf.run("", eof="sideways")


class LimitTests(unittest.TestCase):
    def test_infinite_loop_hits_the_step_limit(self):
        with self.assertRaises(bf.StepLimitExceeded):
            bf.run("+[]", step_limit=1000)

    def test_program_within_the_limit_finishes(self):
        self.assertEqual(bf.run("++", step_limit=2).steps, 2)

    def test_one_instruction_over_the_limit_fails(self):
        with self.assertRaises(bf.StepLimitExceeded):
            bf.run("+++", step_limit=2)

    def test_steps_count_every_executed_instruction(self):
        # '+' '[' then one pass of '-' ']' : four instructions
        self.assertEqual(bf.run("+[-]").steps, 4)

    def test_moving_left_of_cell_zero_is_an_error(self):
        with self.assertRaises(bf.TapeBoundsError):
            bf.run("<")

    def test_moving_past_the_last_cell_is_an_error(self):
        with self.assertRaises(bf.TapeBoundsError):
            bf.run(">>>", tape_length=3)


class InstructionStreamTests(unittest.TestCase):
    def test_instructions_keeps_only_the_eight_commands(self):
        self.assertEqual(bf.instructions("a+b-c<d>e.f,g[h]i"), "+-<>.,[]")


if __name__ == "__main__":
    unittest.main()
