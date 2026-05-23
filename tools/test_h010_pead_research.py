#!/usr/bin/env python3
"""Network-free unit tests for tools/h010_pead_research.py.

Covers the SUE math, slippage, the synthetic-record builder, the no-look-ahead
property, and the edge_stability_harness wiring. Run:

    python tools/test_h010_pead_research.py
"""
from __future__ import annotations

import statistics
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import h010_pead_research as h010  # noqa: E402
import edge_stability_harness as harness  # noqa: E402


class TestSUE(unittest.TestCase):
    def test_sue_basic(self):
        # prior raw surprises: pstdev known
        prior = [0.10, -0.05, 0.20, 0.05]
        sd = statistics.pstdev(prior)
        sue = h010.compute_sue(actual=1.20, estimate=1.00, prior_surprises=prior)
        self.assertIsNotNone(sue)
        self.assertAlmostEqual(sue, (1.20 - 1.00) / sd, places=9)

    def test_sue_positive_beat(self):
        prior = [0.01, 0.02, -0.01, 0.03, 0.0]
        sue = h010.compute_sue(2.00, 1.50, prior)
        self.assertGreater(sue, 0)  # beat -> positive SUE

    def test_sue_negative_miss(self):
        prior = [0.01, 0.02, -0.01, 0.03, 0.0]
        sue = h010.compute_sue(1.00, 1.50, prior)
        self.assertLess(sue, 0)  # miss -> negative SUE

    def test_sue_insufficient_history(self):
        # fewer than MIN_PRIOR_SURPRISES priors -> None (no look-ahead guard)
        prior = [0.1] * (h010.MIN_PRIOR_SURPRISES - 1)
        self.assertIsNone(h010.compute_sue(1.2, 1.0, prior))

    def test_sue_zero_dispersion(self):
        # all priors identical -> std 0 -> None (cannot standardize)
        prior = [0.05] * 6
        self.assertIsNone(h010.compute_sue(1.2, 1.0, prior))

    def test_sue_none_inputs(self):
        prior = [0.1, 0.2, -0.1, 0.05]
        self.assertIsNone(h010.compute_sue(None, 1.0, prior))
        self.assertIsNone(h010.compute_sue(1.0, None, prior))


class TestSlippage(unittest.TestCase):
    def test_slippage_100bps(self):
        # 100 bps round-trip = 0.01 deduction
        self.assertAlmostEqual(h010.apply_slippage(0.05, 100), 0.04, places=9)

    def test_slippage_flips_marginal_winner(self):
        # a +0.5% raw gain becomes a net loss after 100bps
        self.assertLess(h010.apply_slippage(0.005, 100), 0)

    def test_slippage_default(self):
        self.assertAlmostEqual(h010.apply_slippage(0.10),
                               0.10 - h010.SLIPPAGE_BPS / 10_000.0, places=9)


class TestRecord(unittest.TestCase):
    def test_long_winner(self):
        # positive SUE, LONG, positive net return -> WON
        r = h010.make_record("2024-01-10", "2024-02-10", sue=2.0,
                             net_ret=0.03, direction=1)
        self.assertEqual(r["status"], "WON")
        self.assertEqual(r[h010.ZED_HARNESS_FIELD], 2.0)
        self.assertEqual(r["direction"], 1)

    def test_short_winner(self):
        # negative SUE, SHORT (-1), negative net return -> signed positive -> WON
        r = h010.make_record("2024-01-10", "2024-02-10", sue=-1.8,
                             net_ret=-0.04, direction=-1)
        self.assertEqual(r["status"], "WON")
        self.assertEqual(r[h010.ZED_HARNESS_FIELD], 1.8)  # abs(SUE)

    def test_long_loser(self):
        r = h010.make_record("2024-01-10", "2024-02-10", sue=1.5,
                             net_ret=-0.02, direction=1)
        self.assertEqual(r["status"], "LOST")

    def test_record_has_harness_fields(self):
        r = h010.make_record("2024-01-10", "2024-02-10", 1.0, 0.01, 1)
        # the harness reads these
        for key in ("status", "resolved_at", "timestamp", h010.ZED_HARNESS_FIELD):
            self.assertIn(key, r)


class TestHarnessWiring(unittest.TestCase):
    """The harness verdict is THE gate — verify the records feed it correctly."""

    def _records(self, n, winner_z, loser_z, start_day=1):
        """Build n records spanning enough days for several 14-day windows."""
        recs = []
        for i in range(n):
            day = start_day + i  # 1..n consecutive days
            won = i % 2 == 0
            z = winner_z if won else loser_z
            d = f"2024-{((day - 1)//28)+1:02d}-{((day-1)%28)+1:02d}"
            recs.append({
                "status": "WON" if won else "LOST",
                "resolved_at": d, "entry_date": d, "timestamp": d,
                h010.ZED_HARNESS_FIELD: z,
            })
        return recs

    def test_harness_verdict_callable(self):
        recs = self._records(40, winner_z=2.0, loser_z=1.0)
        v = h010.harness_verdict(recs)
        self.assertIn("admissible", v)
        self.assertIn("per_window_eff", v)

    def test_harness_loader_restored(self):
        # harness._load must be restored after harness_verdict (no global leak)
        orig = harness._load
        h010.harness_verdict(self._records(40, 2.0, 1.0))
        self.assertIs(harness._load, orig)

    def test_strong_separation_high_eff(self):
        # winners carry a much higher signal_z -> eff should be large positive
        # in a window that scores. Build a dense single-window sample.
        recs = []
        for i in range(80):
            won = i % 2 == 0
            recs.append({
                "status": "WON" if won else "LOST",
                "resolved_at": "2024-03-01", "entry_date": "2024-03-01",
                "timestamp": "2024-03-01",
                h010.ZED_HARNESS_FIELD: 3.0 if won else 0.5,
            })
        v = h010.harness_verdict(recs)
        scored = [e for e in v["per_window_eff"] if e["eff"] is not None]
        self.assertTrue(scored)
        self.assertGreater(scored[0]["eff"], 0.30)  # winners score higher

    def test_no_separation_low_eff(self):
        # winners and losers carry identical signal_z -> eff ~ 0 -> not admissible
        recs = []
        for i in range(80):
            won = i % 2 == 0
            recs.append({
                "status": "WON" if won else "LOST",
                "resolved_at": "2024-03-01", "entry_date": "2024-03-01",
                "timestamp": "2024-03-01",
                h010.ZED_HARNESS_FIELD: 1.5,
            })
        v = h010.harness_verdict(recs)
        self.assertFalse(v["admissible"])


class TestPurgeEmbargo(unittest.TestCase):
    def test_purge_embargo_blocks(self):
        recs = [
            {"status": "WON", "entry_date": "2024-01-01", "resolved_at": "2024-02-01"},
            {"status": "LOST", "entry_date": "2024-01-05", "resolved_at": "2024-02-05"},
            {"status": "WON", "entry_date": "2024-02-01", "resolved_at": "2024-03-01"},
        ]
        cv = h010.purge_embargo(recs)
        self.assertEqual(cv["oos_n"], 3)
        self.assertAlmostEqual(cv["oos_wr"], 2 / 3, places=3)
        self.assertTrue(cv["blocks"])

    def test_purge_embargo_empty(self):
        cv = h010.purge_embargo([])
        self.assertEqual(cv["oos_n"], 0)
        self.assertIsNone(cv["oos_wr"])


class TestNoLookAhead(unittest.TestCase):
    """SUE for event k must use ONLY surprises from events 0..k-1."""

    def test_standardizer_excludes_current_event(self):
        # Walk the same loop research_pead uses: append AFTER compute.
        events = [
            {"actual": 1.0, "estimate": 0.9},
            {"actual": 1.1, "estimate": 1.0},
            {"actual": 0.8, "estimate": 0.9},
            {"actual": 1.2, "estimate": 1.0},
            {"actual": 2.0, "estimate": 1.0},   # the event we score
        ]
        prior: list[float] = []
        sue_values = []
        for ev in events:
            raw = ev["actual"] - ev["estimate"]
            sue = h010.compute_sue(ev["actual"], ev["estimate"], prior)
            prior.append(raw)   # appended AFTER compute -> no look-ahead
            sue_values.append(sue)
        # first MIN_PRIOR_SURPRISES events cannot be scored
        self.assertIsNone(sue_values[0])
        # the last event IS scored, using exactly the 4 prior surprises
        prior_4 = [0.1, 0.1, -0.1, 0.2]
        sd = statistics.pstdev(prior_4)
        self.assertAlmostEqual(sue_values[-1], (2.0 - 1.0) / sd, places=6)


if __name__ == "__main__":
    unittest.main(verbosity=2)
