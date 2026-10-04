"""Invalid dates and malformed input must print INVALID.

Malformed cases run under all three end of input conventions, because a
program that answered correctly under only one would be depending on
undocumented interpreter behaviour.
"""

from __future__ import annotations

import random
import unittest

from tests.support import line, run_boring, run_fast
from tools import interpreter as bf
from tools import reference

INVALID = line("INVALID")
TERMINATED_LENGTH = len("YYYYMMDD\n")

IMPOSSIBLE = (
    "19000229",  # 1900 is not a leap year
    "20260229",
    "21000229",
    "20260431",
    "20260631",
    "20260931",
    "20261131",
    "20260230",
    "20240230",  # not even in a leap year
    "20260132",
    "20260001",
    "20261301",
    "20269901",
    "20260100",
    "20260000",
)

OUT_OF_RANGE = (
    "18991231",
    "21000101",
    "00000101",
    "10000101",
    "99991231",
    "30000101",
)

MALFORMED = (
    b"",
    b"\n",
    b"2026100\n",  # too few digits
    b"202610044\n",  # too many digits
    b"20261004",  # no terminator at all
    b"2026-10-04\n",
    b"2026/10/04\n",
    b"YYYYMMDD\n",
    b"2026O104\n",  # letter O
    b"20261004 \n",  # trailing space
    b" 20261004\n",  # leading space
    b"2026 1004\n",
    b"20261004\t\n",
    b"\x0020261004\n",
    b"2026\xff1004\n",
    b"/0261004\n",  # the byte before 0
    b":0261004\n",  # the byte after 9
)

FUZZ_SEED = 1004
FUZZ_CASES = 1500
FUZZ_TERMINATED_SHARE = 0.5  # half the cases get a terminator in the right place
FUZZ_ALPHABET = b"0123456789" * 3 + b"\n\r -/:aZ\x00\xff"


class ImpossibleDateTests(unittest.TestCase):
    def test_impossible_dates(self):
        for text in IMPOSSIBLE:
            with self.subTest(date=text):
                self.assertEqual(reference.expected_output(line(text)), INVALID)
                self.assertEqual(run_boring(line(text)).output, INVALID)

    def test_dates_outside_the_supported_range(self):
        for text in OUT_OF_RANGE:
            with self.subTest(date=text):
                self.assertEqual(run_boring(line(text)).output, INVALID)


class MalformedInputTests(unittest.TestCase):
    def test_malformed_input_under_every_end_of_input_convention(self):
        for data in MALFORMED:
            for eof in bf.EOF_MODES:
                with self.subTest(data=data, eof=eof):
                    self.assertEqual(reference.expected_output(data), INVALID)
                    self.assertEqual(run_boring(data, eof=eof).output, INVALID)

    def test_reading_stops_at_the_first_bad_byte(self):
        result = run_boring(b"20x61004\n")
        self.assertEqual(result.consumed, len(b"20x"))

    def test_nothing_after_the_terminator_is_read(self):
        result = run_boring(b"20261004\nthis is never read")
        self.assertEqual(result.output, line("SUNDAY"))
        self.assertEqual(result.consumed, TERMINATED_LENGTH)


class EveryByteTests(unittest.TestCase):
    def test_every_byte_value_in_every_position(self):
        base = bytearray(line("20240229"))
        for position in range(TERMINATED_LENGTH):
            for value in range(bf.CELL_MODULUS):
                data = bytes(base[:position] + bytes([value]) + base[position + 1 :])
                expected = reference.expected_output(data)
                self.assertEqual(run_fast(data).output, expected, (position, value))


class FuzzTests(unittest.TestCase):
    def test_near_valid_inputs_agree_with_the_oracle(self):
        rng = random.Random(FUZZ_SEED)
        for _ in range(FUZZ_CASES):
            length = rng.randint(0, TERMINATED_LENGTH + 2)
            data = bytes(rng.choice(FUZZ_ALPHABET) for _ in range(length))
            if rng.random() < FUZZ_TERMINATED_SHARE:
                data = data[: TERMINATED_LENGTH - 1] + b"\n"
            eof = rng.choice(bf.EOF_MODES)
            with self.subTest(data=data, eof=eof):
                expected = reference.expected_output(data)
                self.assertEqual(run_fast(data, eof=eof).output, expected)


if __name__ == "__main__":
    unittest.main()
