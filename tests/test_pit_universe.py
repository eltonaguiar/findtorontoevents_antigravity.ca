"""Unit tests for tools/pit_universe.build_pit_universe (first-observation universe)."""
import os
import sys
import tempfile
import unittest
from datetime import date, timedelta

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from tools.pit_universe import build_pit_universe  # noqa: E402

D0 = date(2024, 1, 1)


def _write(cache, sym, start, end, step=1):
    """Write a Date,Close CSV from start..end inclusive (business-agnostic daily)."""
    d, i = start, 0
    with open(os.path.join(cache, f"{sym}_5y.csv"), "w") as f:
        f.write("Date,Open,High,Low,Close,Volume\n")
        while d <= end:
            px = 100.0 + i
            f.write(f"{d.isoformat()},{px},{px},{px},{px},1000\n")
            d += timedelta(days=step)
            i += 1


class TestPitUniverse(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cache = self.tmp.name
        # full-range series: present throughout
        _write(self.cache, "FULL", D0, D0 + timedelta(days=99))
        # starts late: first close 30 days in
        _write(self.cache, "LATE", D0 + timedelta(days=30), D0 + timedelta(days=99))
        # stops early: last close 60 days in
        _write(self.cache, "EARLY", D0, D0 + timedelta(days=60))
        # both-ends series: present at both ends of the window
        _write(self.cache, "BOTH", D0, D0 + timedelta(days=99))

    def tearDown(self):
        self.tmp.cleanup()

    def test_series_starting_late_excluded_before_start(self):
        u = build_pit_universe(D0 + timedelta(days=10), self.cache)
        self.assertNotIn("LATE", u)
        self.assertIn("LATE", build_pit_universe(D0 + timedelta(days=40), self.cache))

    def test_series_stopping_early_excluded_after_end(self):
        u = build_pit_universe(D0 + timedelta(days=80), self.cache)
        self.assertNotIn("EARLY", u)
        self.assertIn("EARLY", build_pit_universe(D0 + timedelta(days=50), self.cache))

    def test_full_range_series_included_throughout(self):
        for off in (0, 50, 99):
            self.assertIn("FULL", build_pit_universe(D0 + timedelta(days=off), self.cache))

    def test_symbol_present_at_both_ends_never_excluded(self):
        for off in (0, 1, 33, 70, 99):
            self.assertIn("BOTH", build_pit_universe(D0 + timedelta(days=off), self.cache))


if __name__ == "__main__":
    unittest.main()
