"""Tests for tools/holding_period_histogram.py."""
from __future__ import annotations

import importlib.util
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "holding_period_histogram",
    REPO / "tools" / "holding_period_histogram.py"
)
hp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hp)


def _pick(opened_at: str | None, closed_at: str, pnl_pct: float = 1.0,
          strategy: str = "demo") -> dict:
    return {"strategy": strategy, "opened_at": opened_at,
            "closed_at": closed_at, "pnl_pct": pnl_pct}


def _fmt(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


class PercentileTests(unittest.TestCase):
    def test_empty_returns_zero(self) -> None:
        self.assertEqual(hp._percentile([], 50), 0.0)

    def test_single_value(self) -> None:
        self.assertEqual(hp._percentile([42.0], 50), 42.0)

    def test_matches_numpy_linear(self) -> None:
        self.assertAlmostEqual(hp._percentile([1, 2, 3, 4, 5], 50), 3.0)
        self.assertAlmostEqual(hp._percentile([1, 2, 3, 4], 50), 2.5)


class BucketLabelTests(unittest.TestCase):
    def test_bucket_boundaries(self) -> None:
        self.assertEqual(hp._bucket_label(0.5), "1m_or_less")
        self.assertEqual(hp._bucket_label(3.0), "1m_to_5m")
        self.assertEqual(hp._bucket_label(60.0), "30m_to_1h")
        self.assertEqual(hp._bucket_label(120.0), "1h_to_4h")
        self.assertEqual(hp._bucket_label(60 * 24 * 8), "1w_to_1mo")
        self.assertEqual(hp._bucket_label(60 * 24 * 60), "over_1mo")


class HoldingPeriodTests(unittest.TestCase):
    def test_long_hold_strategy_median_above_1d(self) -> None:
        # 25 picks each held 7 days
        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        picks = [
            _pick(_fmt(base + timedelta(days=i)),
                  _fmt(base + timedelta(days=i + 7))) for i in range(25)
        ]
        result = hp.analyze_strategy(picks, min_n=20)
        self.assertIsNotNone(result)
        # Median ~ 7 days = 10080 minutes
        self.assertAlmostEqual(result["median_minutes"], 10080.0, places=2)
        self.assertFalse(result["flag_high_freq_low_conviction"])

    def test_short_hold_scalper_median_under_1h(self) -> None:
        # 60 picks each held 5 minutes, all on same day -> picks/day = 60
        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        picks = [
            _pick(_fmt(base + timedelta(minutes=10 * i)),
                  _fmt(base + timedelta(minutes=10 * i + 5))) for i in range(60)
        ]
        result = hp.analyze_strategy(picks, min_n=20)
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result["median_minutes"], 5.0, places=2)
        # Most picks span 60*10min = 600m = 10 hours -> picks/day from
        # picks_per_day = n / span_days = 60 / (10/24) = 144
        self.assertGreater(result["picks_per_day"], 50.0)
        self.assertTrue(result["flag_high_freq_low_conviction"])

    def test_missing_opened_at_falls_back(self) -> None:
        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        picks = [
            _pick(None, _fmt(base + timedelta(hours=i))) for i in range(25)
        ]
        result = hp.analyze_strategy(picks, min_n=20)
        self.assertIsNotNone(result)
        self.assertEqual(result["n"], 25)
        self.assertEqual(result["duration_unavailable"], 25)
        self.assertEqual(result["n_with_duration"], 0)
        # median_minutes is 0 when no durations
        self.assertEqual(result["median_minutes"], 0.0)

    def test_insufficient_n_returns_none(self) -> None:
        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        picks = [
            _pick(_fmt(base + timedelta(hours=i)),
                  _fmt(base + timedelta(hours=i + 1))) for i in range(10)
        ]
        self.assertIsNone(hp.analyze_strategy(picks, min_n=20))

    def test_skips_malformed(self) -> None:
        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        good = [
            _pick(_fmt(base + timedelta(hours=i)),
                  _fmt(base + timedelta(hours=i + 1))) for i in range(22)
        ]
        bad = [
            {"strategy": "demo", "pnl_pct": None,
             "closed_at": _fmt(base), "opened_at": _fmt(base)},
            {"strategy": "demo", "pnl_pct": "x",
             "closed_at": _fmt(base), "opened_at": _fmt(base)},
        ]
        result = hp.analyze_strategy(good + bad, min_n=20)
        self.assertEqual(result["n"], 22)

    def test_closed_before_opened_treated_as_unavailable(self) -> None:
        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        # Reversed: closed_at before opened_at -> duration_unavailable
        picks = [
            _pick(_fmt(base + timedelta(hours=2)),
                  _fmt(base + timedelta(hours=1))) for _ in range(22)
        ]
        result = hp.analyze_strategy(picks, min_n=20)
        self.assertEqual(result["duration_unavailable"], 22)
        self.assertEqual(result["n_with_duration"], 0)


class AnalyzeAllTests(unittest.TestCase):
    def test_groups_and_filters(self) -> None:
        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        long_picks = [
            _pick(_fmt(base + timedelta(days=i)),
                  _fmt(base + timedelta(days=i + 7)),
                  strategy="long_hold") for i in range(25)
        ]
        scalper_picks = [
            _pick(_fmt(base + timedelta(minutes=10 * i)),
                  _fmt(base + timedelta(minutes=10 * i + 5)),
                  strategy="scalper") for i in range(60)
        ]
        too_small = [
            _pick(_fmt(base + timedelta(hours=i)),
                  _fmt(base + timedelta(hours=i + 1)),
                  strategy="too_small") for i in range(10)
        ]
        summary = hp.analyze_all(long_picks + scalper_picks + too_small,
                                  min_n=20)
        names = [s["strategy"] for s in summary["strategies"]]
        self.assertIn("long_hold", names)
        self.assertIn("scalper", names)
        self.assertNotIn("too_small", names)
        # Sort: scalper (median 5m) first, long_hold (median 10080m) second
        self.assertEqual(names[0], "scalper")
        self.assertEqual(names[-1], "long_hold")
        self.assertEqual(summary["n_high_freq_flagged"], 1)


if __name__ == "__main__":
    unittest.main()
