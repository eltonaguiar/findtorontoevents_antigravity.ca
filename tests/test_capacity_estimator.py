"""Tests for tools/capacity_estimator.py."""
from __future__ import annotations

import importlib.util
import math
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "capacity_estimator", REPO / "tools" / "capacity_estimator.py"
)
ce = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ce)


class CapacityFormulaTests(unittest.TestCase):
    def test_zero_edge_zero_capacity(self) -> None:
        self.assertEqual(ce.capacity_usd(0.0, 0.02, 1e9), 0.0)

    def test_negative_edge_zero_capacity(self) -> None:
        self.assertEqual(ce.capacity_usd(-50.0, 0.02, 1e9), 0.0)

    def test_high_edge_low_vol_high_capacity(self) -> None:
        # 100bps edge, 1% vol, $1B ADV, lambda=0.5
        # Q = (100 / (0.5 * 0.01 * 10000))^2 * 1e9 = (100/50)^2 * 1e9 = 4e9
        cap = ce.capacity_usd(100.0, 0.01, 1_000_000_000, lambda_const=0.5)
        self.assertAlmostEqual(cap, 4_000_000_000, delta=1.0)

    def test_low_edge_high_vol_low_capacity(self) -> None:
        # 5bps edge, 5% vol, $1B ADV, lambda=0.5
        # Q = (5 / (0.5 * 0.05 * 10000))^2 * 1e9 = (5/250)^2 * 1e9 = 4e5
        cap = ce.capacity_usd(5.0, 0.05, 1_000_000_000, lambda_const=0.5)
        self.assertAlmostEqual(cap, 400_000.0, delta=10.0)


class SigmaEstimationTests(unittest.TestCase):
    def test_atr_path_used_when_present(self) -> None:
        picks = [
            {"atr": 0.5, "entry_price": 100.0, "asset_class": "EQUITY"}
            for _ in range(10)
        ]
        # sigma = 0.5/100 * sqrt(252) ≈ 0.0794
        fallback = {"EQUITY": 0.99}
        sigma = ce.estimate_strategy_sigma(picks, fallback)
        self.assertAlmostEqual(sigma, 0.5 / 100.0 * math.sqrt(252), places=4)

    def test_class_fallback_when_atr_missing(self) -> None:
        picks = [{"asset_class": "FOREX"} for _ in range(10)]
        fallback = {"FOREX": 0.0123}
        sigma = ce.estimate_strategy_sigma(picks, fallback)
        self.assertAlmostEqual(sigma, 0.0123, places=6)

    def test_class_fallback_when_few_atr_samples(self) -> None:
        picks = (
            [{"atr": 0.5, "entry_price": 100.0, "asset_class": "EQUITY"}
             for _ in range(4)]
            + [{"asset_class": "EQUITY"} for _ in range(10)]
        )
        fallback = {"EQUITY": 0.0234}
        sigma = ce.estimate_strategy_sigma(picks, fallback)
        # Less than 5 ATR samples -> fallback
        self.assertAlmostEqual(sigma, 0.0234, places=6)


class ADVLookupTests(unittest.TestCase):
    def test_override_takes_precedence(self) -> None:
        adv, src = ce.lookup_adv_usd("BTCUSDT", "CRYPTO",
                                     adv_overrides={"BTCUSDT": 999_999.0})
        self.assertEqual(adv, 999_999.0)
        self.assertEqual(src, "override:BTCUSDT")

    def test_fallback_when_unknown(self) -> None:
        # Use a clearly nonexistent symbol; should hit fallback
        adv, src = ce.lookup_adv_usd("NOT_A_REAL_SYMBOL_ZZZ_999", "EQUITY",
                                     adv_overrides={"force_fallback": 0.0})
        self.assertEqual(src, "fallback:EQUITY")
        self.assertEqual(adv, ce.FALLBACK_ADV_USD["EQUITY"])

    def test_fallback_class_unknown(self) -> None:
        adv, src = ce.lookup_adv_usd("???", "QUANTUM_DERIVATIVES")
        self.assertEqual(src, "fallback:QUANTUM_DERIVATIVES")
        self.assertEqual(adv, ce.FALLBACK_ADV_USD["UNKNOWN"])


class StrategyEstimateTests(unittest.TestCase):
    def _picks(self, n: int, mean_pnl: float, asset_class: str = "CRYPTO",
               symbol: str = "BTCUSDT") -> list[dict]:
        # Build n picks alternating around the mean to give a defined avg
        return [{"strategy": "x", "asset_class": asset_class,
                 "symbol": symbol, "pnl_pct": mean_pnl,
                 "atr": 1.0, "entry_price": 100.0} for _ in range(n)]

    def test_insufficient_n_returns_none(self) -> None:
        result = ce.estimate_strategy(self._picks(10, 1.0), {})
        self.assertIsNone(result)

    def test_pure_alpha_low_vol_high_capacity(self) -> None:
        # ATR/price = 1/100 -> sigma = 0.01 * sqrt(252) ≈ 0.1587
        # mean_pnl_pct = 1.0 -> edge_bps = 100
        # Override ADV to 1e9 for determinism
        picks = self._picks(30, 1.0, asset_class="CRYPTO", symbol="BTCUSDT")
        result = ce.estimate_strategy(picks, {"CRYPTO": 0.05},
                                      adv_overrides={"BTCUSDT": 1_000_000_000.0})
        self.assertIsNotNone(result)
        self.assertEqual(result["n"], 30)
        self.assertGreater(result["capacity_usd"], 100_000)
        self.assertEqual(result["adv_source"], "override:BTCUSDT")

    def test_high_vol_low_edge_low_capacity(self) -> None:
        # ATR=20 entry=100 -> sigma = 0.20 * sqrt(252) ≈ 3.17 (massive vol)
        picks = [{"strategy": "x", "asset_class": "CRYPTO",
                  "symbol": "FOO", "pnl_pct": 0.05,  # tiny edge
                  "atr": 20.0, "entry_price": 100.0} for _ in range(30)]
        result = ce.estimate_strategy(picks, {"CRYPTO": 0.05},
                                      adv_overrides={"FOO": 1_000_000_000.0})
        self.assertIsNotNone(result)
        self.assertLess(result["capacity_usd"],
                        # both lower than the high-edge case
                        100_000_000)


class AnalyzeAllTests(unittest.TestCase):
    def test_groups_by_strategy_filters_small_n(self) -> None:
        picks = []
        for _ in range(25):
            picks.append({"strategy": "winner", "asset_class": "CRYPTO",
                          "symbol": "BTCUSDT", "pnl_pct": 1.0,
                          "atr": 1.0, "entry_price": 100.0})
        for _ in range(25):
            picks.append({"strategy": "loser", "asset_class": "CRYPTO",
                          "symbol": "ETHUSDT", "pnl_pct": -0.5,
                          "atr": 2.0, "entry_price": 100.0})
        for _ in range(5):
            picks.append({"strategy": "small", "asset_class": "CRYPTO",
                          "symbol": "FOO", "pnl_pct": 1.0,
                          "atr": 1.0, "entry_price": 100.0})
        summary = ce.analyze_all(picks, min_n=20,
                                 adv_overrides={"BTCUSDT": 1_000_000_000.0,
                                                "ETHUSDT": 1_000_000_000.0})
        names = {s["strategy"] for s in summary["strategies"]}
        self.assertIn("winner", names)
        self.assertIn("loser", names)
        self.assertNotIn("small", names)
        winner = next(s for s in summary["strategies"]
                      if s["strategy"] == "winner")
        loser = next(s for s in summary["strategies"]
                     if s["strategy"] == "loser")
        self.assertGreater(winner["capacity_usd"], 0)
        self.assertEqual(loser["capacity_usd"], 0)


class CapacityBucketTests(unittest.TestCase):
    def test_bucket_thresholds(self) -> None:
        self.assertEqual(ce._capacity_bucket(0), "ZERO (negative-edge)")
        self.assertEqual(ce._capacity_bucket(50_000), "TOY (<$100k)")
        self.assertEqual(ce._capacity_bucket(500_000), "RETAIL ($100k-$1M)")
        self.assertEqual(ce._capacity_bucket(5_000_000), "PROP ($1M-$10M)")
        self.assertEqual(ce._capacity_bucket(50_000_000), "FUND ($10M-$100M)")
        self.assertEqual(ce._capacity_bucket(500_000_000),
                         "INSTITUTIONAL (>$100M)")


if __name__ == "__main__":
    unittest.main()
