"""Tests for drift-aware multiplier wiring on calculate_smart_score.

Strategy: install a synthetic per-source factor map via the test hook, then
verify that two otherwise-identical picks get scored proportionally to their
source's drift factor.
"""
from __future__ import annotations

import os
import sys
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from alpha_engine import drift_aware_scoring as das  # noqa: E402
from audit_trail.quality_gates import calculate_smart_score  # noqa: E402


def _base_pick(source_system: str, **overrides):
    """Return a pick with valid trade geometry. Mirrors test_calculate_smart_score_recalibration._base_pick."""
    pick = {
        "symbol": "XYZUSDT",
        "direction": "LONG",
        "entry_price": 100.0,
        "take_profit": 105.0,
        "stop_loss": 95.0,
        "score": 85,  # in the top piecewise band -> base = 25.5
        "strategy": "non_copy_strategy",
        "asset_class": "CRYPTO",
        "confidence": 0.5,
        "source_system": source_system,
    }
    pick.update(overrides)
    return pick


class TestDetectSimpleDrift(unittest.TestCase):
    """The pure WR-vs-WR helper drives the multiplier."""

    def setUp(self):
        self.now = datetime(2026, 4, 28, tzinfo=timezone.utc)

    def _make_history(self, baseline_n, baseline_wins, recent_n, recent_wins):
        hist = []
        baseline_day = self.now - timedelta(days=60)
        recent_day = self.now - timedelta(days=5)
        for i in range(baseline_n):
            hist.append({
                "status": "WON" if i < baseline_wins else "LOST",
                "closed_at": baseline_day.isoformat(),
                "pnl_pct": 1.0 if i < baseline_wins else -1.0,
            })
        for i in range(recent_n):
            hist.append({
                "status": "WON" if i < recent_wins else "LOST",
                "closed_at": recent_day.isoformat(),
                "pnl_pct": 1.0 if i < recent_wins else -1.0,
            })
        return hist

    def test_no_drift_when_recent_wr_matches_baseline(self):
        # baseline 60% (60/100), recent 60% (12/20) -> drop_pp = 0 -> severity 0
        hist = self._make_history(100, 60, 20, 12)
        snap = das.detect_simple_drift(hist, now=self.now)
        self.assertEqual(snap["severity"], 0.0)

    def test_drift_below_threshold_keeps_factor_one(self):
        # baseline 55% -> recent 45% (drop=10pp) is below DRIFT_THRESHOLD_PP=15
        hist = self._make_history(100, 55, 20, 9)
        snap = das.detect_simple_drift(hist, now=self.now)
        self.assertEqual(snap["severity"], 0.0)
        self.assertAlmostEqual(das._severity_to_factor(snap["severity"]), 1.0, places=6)

    def test_hard_drift_collapses_to_min_factor(self):
        # baseline 60% -> recent 25% (drop=35pp) >= HARD_DRIFT_THRESHOLD_PP=30
        hist = self._make_history(100, 60, 20, 5)
        snap = das.detect_simple_drift(hist, now=self.now)
        self.assertEqual(snap["severity"], 1.0)
        self.assertAlmostEqual(das._severity_to_factor(snap["severity"]), das.MIN_FACTOR, places=6)

    def test_too_few_recent_trades_returns_neutral(self):
        # Only 5 recent picks: below MIN_RECENT_TRADES=10
        hist = self._make_history(100, 60, 5, 1)
        snap = das.detect_simple_drift(hist, now=self.now)
        self.assertEqual(snap["severity"], 0.0)


class TestWiringOnCalculateSmartScore(unittest.TestCase):
    """Verify the post-hoc wrapper actually scales the returned smart score."""

    def setUp(self):
        # Install synthetic per-source drift factors. Reset on tearDown.
        das.set_cache_for_testing({
            "drifting_source": 0.5,   # max drift
            "stable_source": 1.0,     # no drift -> default anyway, kept explicit
        })

    def tearDown(self):
        das.reset_cache()

    def test_stable_source_score_unchanged(self):
        # A source not in the cache (or factor==1.0) should produce the original score.
        baseline = calculate_smart_score(_base_pick("stable_source"))
        # Cold-start guarantee: an unknown source also gets factor 1.0.
        unknown = calculate_smart_score(_base_pick("never_seen_source"))
        self.assertEqual(baseline, unknown)
        self.assertGreater(baseline, 0)

    def test_drifting_source_is_halved(self):
        stable = calculate_smart_score(_base_pick("stable_source"))
        drifted = calculate_smart_score(_base_pick("drifting_source"))
        # 0.5x then re-rounded to 1 decimal place -> within 0.1 of stable * 0.5
        self.assertAlmostEqual(drifted, round(stable * 0.5, 1), delta=0.1)
        self.assertLess(drifted, stable)

    def test_score_floor_is_preserved(self):
        # Drift haircut should never push the score below 0.
        zero_pick = _base_pick("drifting_source", score=0, take_profit=100.0, stop_loss=100.0)
        # Invalid geometry -> early return 0 inside calculate_smart_score; haircut still safe.
        self.assertEqual(calculate_smart_score(zero_pick), 0.0)

    def test_apply_drift_aware_multiplier_handles_none_source(self):
        # Edge case: pick missing source_system -> factor 1.0, score unchanged.
        self.assertAlmostEqual(das.apply_drift_aware_multiplier(50.0, None), 50.0, places=6)
        self.assertAlmostEqual(das.apply_drift_aware_multiplier(50.0, ""), 50.0, places=6)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
