"""The oracle is tested too, against facts that do not come from Python.

If ``tools/reference.py`` were wrong, the exhaustive test would faithfully
compare the program against a wrong answer. These dates are well documented
historical weekdays, not values computed by ``datetime``.
"""

from __future__ import annotations

import datetime
import unittest

from tools import reference

HISTORICAL = (
    (datetime.date(1900, 1, 1), "MONDAY"),
    (datetime.date(1945, 5, 8), "TUESDAY"),  # VE Day
    (datetime.date(1963, 11, 22), "FRIDAY"),  # Kennedy assassination
    (datetime.date(1969, 7, 20), "SUNDAY"),  # Apollo 11 landing
    (datetime.date(1989, 11, 9), "THURSDAY"),  # Berlin Wall opened
    (datetime.date(2000, 1, 1), "SATURDAY"),
    (datetime.date(2001, 9, 11), "TUESDAY"),
)
SUPPORTED_DATE_COUNT = 73049


class ReferenceTests(unittest.TestCase):
    def test_historical_weekdays(self):
        for date, name in HISTORICAL:
            with self.subTest(date=date):
                self.assertEqual(reference.weekday(date), name)

    def test_supported_range_has_the_expected_number_of_dates(self):
        self.assertEqual(
            sum(1 for _ in reference.supported_dates()), SUPPORTED_DATE_COUNT
        )

    def test_parse_rejects_what_the_contract_rejects(self):
        for text in (
            "19000229",
            "20261301",
            "18991231",
            "21000101",
            "2026100",
            "2026-1-4",
        ):
            with self.subTest(text=text):
                self.assertIsNone(reference.parse(text))

    def test_parse_accepts_the_leap_century(self):
        self.assertEqual(reference.parse("20000229"), datetime.date(2000, 2, 29))

    def test_expected_output_requires_a_terminator(self):
        self.assertEqual(reference.expected_output(b"20261004"), b"INVALID\n")
        self.assertEqual(reference.expected_output(b"20261004\r"), b"SUNDAY\n")


if __name__ == "__main__":
    unittest.main()
