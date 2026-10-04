"""Parser and tape map tests: the documented layout is what the program does.

ARCHITECTURE.md publishes a tape map. These tests make it a checked claim:
after a run, every named cell holds the value the map says it holds,
computed here from Python's ``calendar`` module rather than from the
program's own formulas. The map in the document must also match the layout
the generator used.
"""

from __future__ import annotations

import calendar
import re
import unittest

from tests.support import ROOT, run_boring, run_fast
from tools import program, reference

CELLS = program.CELLS
SAMPLE_STRIDE = 97
CENTURY = 100
CYCLE = 4
SCRATCH_SLICE = slice(program.SCRATCH[0].address, program.SCRATCH[-1].address + 1)
ARCHITECTURE = ROOT / "ARCHITECTURE.md"


def expected_cells(date) -> dict[str, int]:
    century, year = divmod(date.year, CENTURY)
    lengths = [calendar.monthrange(date.year, m)[1] for m in range(1, 13)]
    return {
        "valid": 1,
        "century": century,
        "year": year,
        "month": date.month,
        "day": date.day,
        "century_mod4": century % CYCLE,
        "century_leaps": -(-century // CYCLE),
        "year_mod4": year % CYCLE,
        "year_leaps": -(-year // CYCLE),
        "leap": int(calendar.isleap(date.year)),
        "month_length": lengths[date.month - 1],
        "month_offset": sum(
            n % len(reference.WEEKDAYS) for n in lengths[: date.month - 1]
        ),
        "sum": 0,
        "weekday": date.weekday(),
    }


class TapeMapTests(unittest.TestCase):
    def assert_workspace_clean(self, tape):
        self.assertEqual(tape[SCRATCH_SLICE], bytes(program.SCRATCH_SIZE))
        for name in ("char", "out", *(d.name for d in program.DIGITS)):
            self.assertEqual(tape[CELLS[name].address], 0, name)

    def test_named_cells_after_valid_dates(self):
        for date in list(reference.supported_dates())[::SAMPLE_STRIDE]:
            tape = run_fast(reference.encode(date)).tape
            with self.subTest(date=date.isoformat()):
                for name, value in expected_cells(date).items():
                    self.assertEqual(tape[CELLS[name].address], value, name)
                self.assert_workspace_clean(tape)

    def test_parsed_fields_of_an_invalid_date_are_kept(self):
        tape = run_boring(b"20260431\n").tape
        self.assertEqual(tape[CELLS["valid"].address], 0)
        self.assertEqual(tape[CELLS["month"].address], 4)
        self.assertEqual(tape[CELLS["day"].address], 31)
        self.assertEqual(tape[CELLS["month_length"].address], 30)
        self.assert_workspace_clean(tape)

    def test_impossible_month_has_no_length(self):
        tape = run_boring(b"20261301\n").tape
        self.assertEqual(tape[CELLS["month_length"].address], 0)
        self.assert_workspace_clean(tape)

    def test_workspace_is_clean_after_malformed_input(self):
        for data in (b"", b"2026x", b"20261004", b"2026100410\n"):
            with self.subTest(data=data):
                self.assert_workspace_clean(run_boring(data).tape)

    def test_scratch_pool_is_exactly_the_high_water_mark(self):
        _, asm = program.build()
        self.assertEqual(asm.scratch_high_water, program.SCRATCH_SIZE)

    def test_layout_addresses_are_contiguous_and_unique(self):
        addresses = [cell.address for cell in program.LAYOUT]
        self.assertEqual(addresses, list(range(len(addresses))))


class DocumentedMapTests(unittest.TestCase):
    def test_architecture_tape_map_matches_the_layout(self):
        text = ARCHITECTURE.read_text(encoding="utf-8")
        pattern = r"^\| (\d+) \| `(\w+)` \|"
        rows = {
            int(addr): name for addr, name in re.findall(pattern, text, re.MULTILINE)
        }
        expected = {cell.address: cell.name for cell in program.PERSISTENT}
        self.assertEqual(rows, expected)
        first, last = program.SCRATCH[0].address, program.SCRATCH[-1].address
        self.assertIn(f"| {first} to {last} | scratch |", text)


if __name__ == "__main__":
    unittest.main()
