"""Identical input gives identical output, every time.

The program has no clock, randomness, environment or files to read: a
Brainfuck program sees only its input bytes. These tests check that the
toolchain adds no such dependency either.
"""

from __future__ import annotations

import unittest

from tests.support import line, run_boring, source
from tools import fastbf
from tools import interpreter as bf

REPEATS = 5
INPUTS = (line("20261004"), line("19000229"), b"", b"2026-10-04\n")


class DeterminismTests(unittest.TestCase):
    def test_repeated_runs_are_identical(self):
        for data in INPUTS:
            with self.subTest(data=data):
                results = {run_boring(data) for _ in range(REPEATS)}
                self.assertEqual(len(results), 1)

    def test_independent_compilations_are_identical(self):
        first = fastbf.Program(source())
        second = fastbf.Program(source())
        self.assertEqual(first.python_source, second.python_source)
        for data in INPUTS:
            with self.subTest(data=data):
                self.assertEqual(first.run(data), second.run(data))

    def test_the_two_interpreters_agree_on_every_input_here(self):
        program = fastbf.Program(source())
        for data in INPUTS:
            for eof in bf.EOF_MODES:
                with self.subTest(data=data, eof=eof):
                    self.assertEqual(
                        program.run(data, eof=eof), run_boring(data, eof=eof)
                    )


if __name__ == "__main__":
    unittest.main()
