"""The compiled exe must give the same answers as the Brainfuck it came from.

Builds the exe into a temporary directory with ``buildexe.py`` and runs it as
a real process. Skipped, with the reason shown, when gcc is not on PATH.
Every supported date is checked only by ``python buildexe.py --all``, since
one process per date takes minutes; this test checks a sample.
"""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

import buildexe
from tests.support import line, source
from tests.test_examples import BOUNDARIES, SPECIFIED
from tests.test_invalid_dates import IMPOSSIBLE, MALFORMED, OUT_OF_RANGE
from tools import bf2c, reference

SAMPLE_STRIDE = 211


@unittest.skipUnless(shutil.which("gcc"), "gcc is not on PATH")
class ExeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._temp = tempfile.TemporaryDirectory()
        work = Path(cls._temp.name)
        cls.exe = buildexe.build(
            work / "dist", work / "build", icon=shutil.which("windres") is not None
        )

    @classmethod
    def tearDownClass(cls):
        cls._temp.cleanup()

    def assert_matches_oracle(self, inputs):
        self.assertEqual(buildexe.verify(self.exe, inputs), [])

    def test_named_dates(self):
        texts = [text for text, _ in SPECIFIED + BOUNDARIES]
        self.assert_matches_oracle([line(text) for text in texts])

    def test_invalid_and_malformed_input(self):
        texts = IMPOSSIBLE + OUT_OF_RANGE
        self.assert_matches_oracle([line(text) for text in texts] + list(MALFORMED))

    def test_sampled_supported_dates(self):
        dates = list(reference.supported_dates())[::SAMPLE_STRIDE]
        self.assert_matches_oracle([reference.encode(date) for date in dates])

    def test_smoke_inputs_used_by_the_build(self):
        self.assert_matches_oracle(buildexe.SMOKE_INPUTS)


class TranslationTests(unittest.TestCase):
    def test_translation_is_deterministic(self):
        self.assertEqual(bf2c.translate(source()), bf2c.translate(source()))

    def test_every_instruction_is_translated(self):
        text = bf2c.translate("+-<>.,[]")
        for statement in ("*p += 1;", "*p -= 1;", "p -= 1;", "p += 1;"):
            self.assertIn(statement, text)
        self.assertIn("putchar(*p);", text)
        self.assertIn("getchar()", text)
        self.assertIn("while (*p) {", text)

    def test_runs_are_folded(self):
        self.assertIn("*p += 3;", bf2c.translate("+++"))

    def test_loop_count_is_preserved(self):
        text = bf2c.translate(source())
        self.assertEqual(text.count("while (*p) {"), source().count("["))


if __name__ == "__main__":
    unittest.main()
