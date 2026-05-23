"""Tests for tools/wr_posterior_timeseries.py."""
from __future__ import annotations

import importlib.util
import unittest
from datetime import timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "wr_posterior_timeseries", REPO / "tools" / "wr_posterior_timeseries.py"
)
ts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ts)


def _picks(outcomes: list[int], start_iso: str = "2026-04-01T00:00:00Z",
           strategy: str = "demo") -> list[dict]:
    base = ts._parse_iso(start_iso)
    out = []
    for i, w in enumerate(outcomes):
        new_ts = (base + timedelta(hours=i)).isoformat().replace("+00:00", "Z")
        out.append({
            "strategy": strategy,
            "asset_class": "CRYPTO",
            "pnl_pct": 1.0 if w else -1.0,
            "closed_at": new_ts,
        })
    return out


class TimeSeriesShapeTests(unittest.TestCase):
    def test_insufficient_n_returns_none(self) -> None:
        self.assertIsNone(ts.compute_strategy_timeseries(_picks([1] * 19)))

    def test_step_emits_every_nth_plus_final(self) -> None:
        result = ts.compute_strategy_timeseries(_picks([1] * 25), step=10, min_n=20)
        self.assertIsNotNone(result)
        ns = [s["n"] for s in result["series"]]
        self.assertEqual(ns, [10, 20, 25])


class DecayDetectionTests(unittest.TestCase):
    def test_monotone_improving_no_decay(self) -> None:
        result = ts.compute_strategy_timeseries(_picks([1] * 30),
                                                step=10, min_n=20)
        self.assertIsNotNone(result)
        self.assertFalse(result["decay_flag"])
        self.assertGreater(result["latest_p_above_50"], 0.95)

    def test_decaying_series_flagged(self) -> None:
        outcomes = [1] * 20 + [0] * 30
        result = ts.compute_strategy_timeseries(_picks(outcomes),
                                                step=10, min_n=20,
                                                decay_drop=0.30)
        self.assertIsNotNone(result)
        self.assertTrue(result["decay_flag"])
        self.assertGreater(result["decay_amount"], 0.30)

    def test_stable_below_50_no_flag(self) -> None:
        outcomes = ([1] * 4 + [0] * 6) * 3
        result = ts.compute_strategy_timeseries(_picks(outcomes),
                                                step=10, min_n=20,
                                                decay_drop=0.30)
        self.assertIsNotNone(result)
        self.assertFalse(result["decay_flag"])

    def test_stable_high_no_flag(self) -> None:
        outcomes = ([1] * 7 + [0] * 3) * 3
        result = ts.compute_strategy_timeseries(_picks(outcomes),
                                                step=10, min_n=20,
                                                decay_drop=0.30)
        self.assertIsNotNone(result)
        self.assertFalse(result["decay_flag"])
        self.assertGreater(result["latest_p_above_50"], 0.9)


class MalformedPickTests(unittest.TestCase):
    def test_skips_malformed_picks(self) -> None:
        picks = _picks([1] * 25)
        picks.append({"strategy": "demo", "asset_class": "CRYPTO",
                      "pnl_pct": None, "closed_at": "2026-04-15T00:00:00Z"})
        picks.append({"strategy": "demo", "asset_class": "CRYPTO",
                      "pnl_pct": "not_a_number",
                      "closed_at": "2026-04-15T00:00:00Z"})
        picks.append({"strategy": "demo", "asset_class": "CRYPTO",
                      "pnl_pct": 1.0, "closed_at": None})
        picks.append({"strategy": "demo", "asset_class": "CRYPTO",
                      "pnl_pct": 1.0, "closed_at": "not-a-timestamp"})
        result = ts.compute_strategy_timeseries(picks, step=10, min_n=20)
        self.assertIsNotNone(result)
        self.assertEqual(result["n_total"], 25)
        self.assertEqual(result["n_skipped"], 4)


class AnalyzeAllTests(unittest.TestCase):
    def test_groups_by_strategy(self) -> None:
        picks = _picks([1] * 25, strategy="winner")
        picks += _picks([0] * 25, strategy="loser",
                        start_iso="2026-04-02T00:00:00Z")
        picks += _picks([1] * 5, strategy="too_small",
                        start_iso="2026-04-03T00:00:00Z")
        summary = ts.analyze_all(picks, step=10, min_n=20)
        names = {s["strategy"] for s in summary["strategies"]}
        self.assertIn("winner", names)
        self.assertIn("loser", names)
        self.assertNotIn("too_small", names)
        winner = next(s for s in summary["strategies"] if s["strategy"] == "winner")
        loser = next(s for s in summary["strategies"] if s["strategy"] == "loser")
        self.assertGreater(winner["latest_p_above_50"], 0.95)
        self.assertLess(loser["latest_p_above_50"], 0.05)


if __name__ == "__main__":
    unittest.main()
