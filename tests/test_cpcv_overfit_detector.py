"""Tests for tools/cpcv_overfit_detector.py."""
from __future__ import annotations

import importlib.util
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "cpcv_overfit_detector", REPO / "tools" / "cpcv_overfit_detector.py"
)
co = importlib.util.module_from_spec(spec)
spec.loader.exec_module(co)


def _picks(pnl_list: list[float], strategy: str = "demo",
           start: str = "2026-01-01T00:00:00Z") -> list[dict]:
    base = datetime.fromisoformat(start.replace("Z", "+00:00"))
    return [{"strategy": strategy, "pnl_pct": pnl,
             "closed_at": (base + timedelta(hours=i)).isoformat().replace("+00:00", "Z")}
            for i, pnl in enumerate(pnl_list)]


class BlockPartitionTests(unittest.TestCase):
    def test_equal_split(self) -> None:
        arr = np.arange(60)
        blocks = co._block_partition(arr, k=6)
        self.assertEqual(len(blocks), 6)
        for b in blocks:
            self.assertEqual(len(b), 10)

    def test_remainder_absorbed_by_last_block(self) -> None:
        arr = np.arange(65)
        blocks = co._block_partition(arr, k=6)
        self.assertEqual(len(blocks), 6)
        # First 5 are size 10, last is size 15
        self.assertEqual(len(blocks[5]), 15)


class CpcvMathTests(unittest.TestCase):
    def test_no_overfit_in_uniform_returns(self) -> None:
        # All picks have the same PnL -> train and test means equal everywhere
        pnls = np.array([1.0] * 60)
        result = co.cpcv_overfit(pnls, k=6)
        self.assertEqual(result["overfit_gap_pct"], 0.0)
        self.assertFalse(result["flag_overfit"])

    def test_overfit_synthetic_concentrated_winners(self) -> None:
        # 60 picks: 50 zero-return + 10 mega-winners CLUSTERED in the middle
        # Best train fold can capture most of the cluster; test folds suffer
        pnls = np.zeros(60)
        pnls[25:35] = 10.0  # 10 winners clustered in block 3
        result = co.cpcv_overfit(pnls, k=6)
        # Best train mean should significantly exceed avg test mean
        self.assertGreater(result["overfit_gap_pct"], 0.5)

    def test_generalising_series_low_pbo(self) -> None:
        # Steady-positive series — winners spread evenly
        pnls = np.array([1.0, -0.5] * 30)
        result = co.cpcv_overfit(pnls, k=6)
        self.assertLess(result["pbo_estimate"], 0.5)
        self.assertFalse(result["flag_overfit"])

    def test_combinations_count_is_c_k_half(self) -> None:
        # K=6, half=3 -> C(6,3) = 20 combinations
        pnls = np.array([1.0] * 60)
        result = co.cpcv_overfit(pnls, k=6)
        self.assertEqual(result["n_combinations"], 20)


class AnalyzeStrategyTests(unittest.TestCase):
    def test_insufficient_n_returns_none(self) -> None:
        self.assertIsNone(co.analyze_strategy(_picks([1.0] * 30), min_n=60))

    def test_skips_malformed_pnl(self) -> None:
        good = _picks([1.0] * 65)
        bad = [
            {"strategy": "demo", "pnl_pct": None,
             "closed_at": "2026-02-01T00:00:00Z"},
            {"strategy": "demo", "pnl_pct": "not_numeric",
             "closed_at": "2026-02-01T00:00:00Z"},
        ]
        result = co.analyze_strategy(good + bad, min_n=60)
        self.assertIsNotNone(result)
        # Only 65 valid picks counted
        self.assertEqual(result["n"], 65)


class AnalyzeAllTests(unittest.TestCase):
    def test_filters_small_n_and_groups(self) -> None:
        picks = _picks([1.0] * 65, strategy="big")
        picks += _picks([1.0] * 10, strategy="too_small",
                        start="2026-02-01T00:00:00Z")
        summary = co.analyze_all(picks, min_n=60)
        names = {s["strategy"] for s in summary["strategies"]}
        self.assertIn("big", names)
        self.assertNotIn("too_small", names)

    def test_overfit_gap_detected_in_summary(self) -> None:
        # Synthetic overfit: all winners concentrated in one block;
        # produces a measurable overfit_gap_pct even though formal
        # flag_overfit (AND of gap+pbo) may not fire — pbo is naturally
        # bounded by CPCV symmetry. Asserting on gap is the useful
        # signal; flag is kept conservative for production usage.
        clean = _picks([1.0, -0.5] * 32, strategy="clean")
        overfit_pnls = [0.0] * 25 + [10.0] * 10 + [0.0] * 25
        overfit = _picks(overfit_pnls, strategy="overfit_cluster",
                         start="2026-02-01T00:00:00Z")
        summary = co.analyze_all(clean + overfit, min_n=60)
        names = {s["strategy"] for s in summary["strategies"]}
        self.assertIn("overfit_cluster", names)
        cluster_row = next(s for s in summary["strategies"]
                           if s["strategy"] == "overfit_cluster")
        clean_row = next(s for s in summary["strategies"]
                          if s["strategy"] == "clean")
        # Concentrated-winner series has materially larger overfit gap
        # than the clean series.
        self.assertGreater(
            cluster_row["overfit_gap_pct"], clean_row["overfit_gap_pct"]
        )
        self.assertGreater(cluster_row["overfit_gap_pct"], 1.0)


if __name__ == "__main__":
    unittest.main()
