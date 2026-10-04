"""Named regression dates, on the boring interpreter.

These run on the boring interpreter on purpose: they are the cases a reader
checks first, so they do not depend on the fast interpreter being right.
Each expected weekday is also asserted against the oracle, so a typo here
cannot quietly agree with a bug in the program.
"""

from __future__ import annotations

import unittest

from tests.support import line, run_boring
from tools import reference

SPECIFIED = (
    ("19000101", "MONDAY"),
    ("19000228", "WEDNESDAY"),
    ("19000229", "INVALID"),
    ("20000229", "TUESDAY"),
    ("20240229", "THURSDAY"),
    ("20261004", "SUNDAY"),
    ("20991231", "THURSDAY"),
)

BOUNDARIES = (
    # first and last supported dates
    ("19000101", "MONDAY"),
    ("20991231", "THURSDAY"),
    # January to February
    ("20260131", "SATURDAY"),
    ("20260201", "SUNDAY"),
    # February to March, common year
    ("20260228", "SATURDAY"),
    ("20260301", "SUNDAY"),
    # February to March, leap year
    ("20240228", "WEDNESDAY"),
    ("20240229", "THURSDAY"),
    ("20240301", "FRIDAY"),
    # February to March, the non leap century year
    ("19000228", "WEDNESDAY"),
    ("19000301", "THURSDAY"),
    # February to March, the leap century year
    ("20000228", "MONDAY"),
    ("20000229", "TUESDAY"),
    ("20000301", "WEDNESDAY"),
    # December to January, across the century
    ("19991231", "FRIDAY"),
    ("20000101", "SATURDAY"),
    # December to January, inside a century
    ("20251231", "WEDNESDAY"),
    ("20260101", "THURSDAY"),
    # 30 day month boundaries
    ("20260430", "THURSDAY"),
    ("20260501", "FRIDAY"),
    ("20261130", "MONDAY"),
    ("20261201", "TUESDAY"),
    # 31 day month boundaries
    ("20260731", "FRIDAY"),
    ("20260801", "SATURDAY"),
    ("20261031", "SATURDAY"),
    ("20261101", "SUNDAY"),
    # century behaviour away from February
    ("19001231", "MONDAY"),
    ("19010101", "TUESDAY"),
    ("20001231", "SUNDAY"),
    ("20010101", "MONDAY"),
)


class ExampleTests(unittest.TestCase):
    def check(self, cases):
        for text, expected in cases:
            with self.subTest(date=text):
                data = line(text)
                self.assertEqual(
                    reference.expected_output(data), line(expected), "table typo"
                )
                self.assertEqual(run_boring(data).output, line(expected))

    def test_dates_named_in_the_specification(self):
        self.check(SPECIFIED)

    def test_boundary_dates(self):
        self.check(BOUNDARIES)

    def test_1900_is_not_a_leap_year(self):
        self.assertEqual(run_boring(line("19000229")).output, line("INVALID"))

    def test_2000_is_a_leap_year(self):
        self.assertEqual(run_boring(line("20000229")).output, line("TUESDAY"))

    def test_carriage_return_terminator_is_accepted(self):
        self.assertEqual(run_boring(b"20261004\r\n").output, line("SUNDAY"))


if __name__ == "__main__":
    unittest.main()
