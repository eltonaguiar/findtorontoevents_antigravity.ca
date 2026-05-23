"""Tests for tools/wr_baseline_differential.py."""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "wr_baseline_differential", REPO / "tools" / "wr_baseline_differential.py"
)
wbd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wbd)


def _picks(wins: int, losses: int, asset_class: str = "CRYPTO",
           strategy: str = "demo") -> list[dict]:
    out = []
    for _ in range(wins):
        out.append({"strategy": strategy, "asset_class": asset_class,
                    "pnl_pct": 1.0})
    for _ in range(losses):
        out.append({"strategy": strategy, "asset_class": asset_class,
                    "pnl_pct": -1.0})
    return out


class WilsonLBTests(unittest.TestCase):
    def test_zero_n_returns_zero(self) -> None:
        self.assertEqual(wbd._wilson_lb_pct(0, 0), 0.0)

    def test_lb_below_point_estimate(self) -> None:
        # 70 wins / 100 -> point 70%, LB < 70
        lb = wbd._wilson_lb_pct(70, 100)
        self.assertLess(lb, 70.0)

    def test_lb_increases_with_n(self) -> None:
        lb_small = wbd._wilson_lb_pct(7, 10)
        lb_large = wbd._wilson_lb_pct(70, 100)
        # Larger n -> tighter LB closer to point estimate
        self.assertGreater(lb_large, lb_small)


class ClassBaselineTests(unittest.TestCase):
    def test_below_min_n_class_excluded(self) -> None:
        picks = _picks(40, 60, asset_class="CRYPTO")  # 100 picks, baseline 40%
        picks += _picks(5, 5, asset_class="FOREX")   # 10 picks, below min_n
        baselines = wbd.compute_class_baselines(picks, min_n_class=100)
        self.assertIn("CRYPTO", baselines)
        self.assertNotIn("FOREX", baselines)
        self.assertAlmostEqual(baselines["CRYPTO"]["wr_pct"], 40.0)

    def test_baseline_correct_proportion(self) -> None:
        picks = _picks(38, 62, asset_class="CRYPTO")
        picks += _picks(55, 45, asset_class="FOREX")
        baselines = wbd.compute_class_baselines(picks, min_n_class=100)
        self.assertAlmostEqual(baselines["CRYPTO"]["wr_pct"], 38.0)
        self.assertAlmostEqual(baselines["FOREX"]["wr_pct"], 55.0)


class StrategyAnalysisTests(unittest.TestCase):
    def setUp(self) -> None:
        # CRYPTO baseline ~38%, FOREX baseline ~55%
        self.picks = (_picks(38, 62, asset_class="CRYPTO",
                              strategy="class_filler_crypto")
                      + _picks(55, 45, asset_class="FOREX",
                               strategy="class_filler_forex"))
        self.baselines = wbd.compute_class_baselines(self.picks, min_n_class=100)

    def test_in_line_strategy_zero_differential(self) -> None:
        # Strategy at exactly the CRYPTO baseline
        s_picks = _picks(38, 62, asset_class="CRYPTO",
                         strategy="in_line")[:100]
        s_picks_subset = s_picks[:25]  # 25 picks, ratio close to baseline
        # Hand-pick 9 wins / 16 losses for ~36% (close to 38% baseline)
        s_picks_subset = (_picks(9, 16, asset_class="CRYPTO",
                                  strategy="in_line"))
        result = wbd.analyze_strategy(s_picks_subset, self.baselines)
        self.assertIsNotNone(result)
        # 36% - 38% = -2pp differential, near zero
        self.assertLess(abs(result["differential_pp"]), 5.0)
        self.assertFalse(result["flag_above_baseline"])

    def test_above_baseline_positive_differential(self) -> None:
        # Strategy at 80% WR vs 38% CRYPTO baseline -> differential +42pp
        s_picks = _picks(40, 10, asset_class="CRYPTO",
                         strategy="hot")  # 80% WR n=50
        result = wbd.analyze_strategy(s_picks, self.baselines)
        self.assertIsNotNone(result)
        self.assertGreater(result["differential_pp"], 30)
        self.assertGreater(result["differential_wilson_lb_95_pp"], 5)
        self.assertTrue(result["flag_above_baseline"])

    def test_below_baseline_negative_differential(self) -> None:
        s_picks = _picks(2, 23, asset_class="CRYPTO",
                         strategy="cold")  # 8% WR n=25
        result = wbd.analyze_strategy(s_picks, self.baselines)
        self.assertIsNotNone(result)
        self.assertLess(result["differential_pp"], -20)
        self.assertFalse(result["flag_above_baseline"])

    def test_insufficient_class_baseline_skipped(self) -> None:
        # Strategy in BOND class which has no baseline (no class data)
        s_picks = _picks(20, 5, asset_class="BOND",
                         strategy="rare")
        result = wbd.analyze_strategy(s_picks, self.baselines)
        self.assertIsNotNone(result)
        self.assertIsNone(result["class_baseline_wr_pct"])
        self.assertIsNone(result["differential_pp"])
        self.assertFalse(result["flag_above_baseline"])

    def test_insufficient_strategy_n_returns_none(self) -> None:
        s_picks = _picks(8, 2, asset_class="CRYPTO")  # n=10 < min_n=20
        self.assertIsNone(wbd.analyze_strategy(s_picks, self.baselines))


class AnalyzeAllTests(unittest.TestCase):
    def test_groups_and_baselines_in_summary(self) -> None:
        # Class fillers (>=100 each) + 2 strategies
        picks = _picks(38, 62, asset_class="CRYPTO",
                       strategy="class_filler_crypto")
        picks += _picks(55, 45, asset_class="FOREX",
                        strategy="class_filler_forex")
        # Hot CRYPTO strategy
        picks += _picks(40, 10, asset_class="CRYPTO", strategy="hot_crypto")
        # In-line FOREX strategy (n=25)
        picks += _picks(14, 11, asset_class="FOREX",
                        strategy="in_line_forex")  # 56% WR ~ baseline

        summary = wbd.analyze_all(picks, min_n_strategy=20)
        self.assertIn("CRYPTO", summary["class_baselines"])
        self.assertIn("FOREX", summary["class_baselines"])
        names = {s["strategy"] for s in summary["strategies"]}
        self.assertIn("hot_crypto", names)
        self.assertIn("in_line_forex", names)
        self.assertGreaterEqual(summary["n_above_baseline"], 1)


if __name__ == "__main__":
    unittest.main()
