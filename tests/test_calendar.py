"""Every supported date, compared against the oracle.

All 73,049 dates from 1900-01-01 to 2099-12-31 run through the committed
program on the fast interpreter. A sample also runs on the boring
interpreter and must match the fast result exactly (output, tape, pointer,
instruction count), which ties the exhaustive result back to the execution
model the boring interpreter defines.
"""

from __future__ import annotations

import re
import unittest

from tests.support import ROOT, run_boring, run_fast
from tools import interpreter as bf
from tools import reference

SUPPORTED_DATE_COUNT = 73049  # 200 * 365 plus 49 leap days (1904 to 2096)
BORING_SAMPLE_STRIDE = 211  # a prime, so the sample drifts through weekdays

ARCHITECTURE = ROOT / "ARCHITECTURE.md"
STEP_RANGE = re.compile(r"between ([\d,]+) and ([\d,]+) executed instructions")
MAX_STEPS_CLAIM = re.compile(r'data-claim="max-steps">([\d,]+)<')
SITE_SOURCES = (ROOT / "site" / "pages", ROOT / "docs")


def _number(text: str) -> int:
    return int(text.replace(",", ""))


class ExhaustiveCalendarTests(unittest.TestCase):
    def test_every_supported_date_matches_the_oracle(self):
        checked = 0
        mismatches = []
        steps = []
        for date in reference.supported_dates():
            data = reference.encode(date)
            result = run_fast(data)
            expected = reference.expected_output(data)
            if result.output != expected:
                mismatches.append((date.isoformat(), result.output, expected))
            steps.append(result.steps)
            checked += 1
        self.assertEqual(mismatches[:10], [])
        self.assertEqual(checked, SUPPORTED_DATE_COUNT)
        self.assert_documented_step_counts(min(steps), max(steps))

    def assert_documented_step_counts(self, fewest: int, most: int):
        """The step counts quoted in the docs and on the site are measured."""
        low, high = STEP_RANGE.search(ARCHITECTURE.read_text("utf-8")).groups()
        self.assertEqual((_number(low), _number(high)), (fewest, most))
        claims = [
            (path.name, _number(found))
            for folder in SITE_SOURCES
            for path in sorted(folder.glob("*.html"))
            for found in MAX_STEPS_CLAIM.findall(path.read_text("utf-8"))
        ]
        self.assertTrue(claims, "the site no longer quotes the maximum")
        for name, claimed in claims:
            self.assertEqual(claimed, most, name)

    def test_sample_agrees_exactly_with_the_boring_interpreter(self):
        dates = list(reference.supported_dates())[::BORING_SAMPLE_STRIDE]
        for date in dates:
            data = reference.encode(date)
            with self.subTest(date=date.isoformat()):
                self.assertEqual(run_fast(data), run_boring(data))

    def test_valid_dates_ignore_the_end_of_input_convention(self):
        dates = list(reference.supported_dates())[::BORING_SAMPLE_STRIDE]
        for date in dates:
            data = reference.encode(date)
            results = {run_fast(data, eof=eof) for eof in bf.EOF_MODES}
            with self.subTest(date=date.isoformat()):
                self.assertEqual(len(results), 1)


if __name__ == "__main__":
    unittest.main()
