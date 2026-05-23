"""Tests for tools/symbol_concentration_index.py."""
from __future__ import annotations

import importlib.util
import unittest
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "symbol_concentration_index",
    REPO / "tools" / "symbol_concentration_index.py"
)
sci = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sci)


class HHIComputationTests(unittest.TestCase):
    def test_single_symbol_hhi_10000(self) -> None:
        # All picks on one symbol -> HHI = 1 * 10000
        counts = Counter({"BTCUSDT": 50})
        result = sci.compute_concentration(counts)
        self.assertEqual(result["hhi"], 10000.0)
        self.assertEqual(result["effective_n_symbols"], 1.0)
        self.assertEqual(result["top1_share_pct"], 100.0)
        self.assertTrue(result["flag_single_symbol_dominated"])

    def test_evenly_spread_hhi_inverse_n(self) -> None:
        # 5 symbols, 10 picks each -> share=0.2 each -> HHI = 5 * 0.04 * 10000 = 2000
        counts = Counter({"A": 10, "B": 10, "C": 10, "D": 10, "E": 10})
        result = sci.compute_concentration(counts)
        self.assertAlmostEqual(result["hhi"], 2000.0, places=4)
        self.assertAlmostEqual(result["effective_n_symbols"], 5.0, places=4)
        self.assertFalse(result["flag_single_symbol_dominated"])

    def test_three_evenly_spread_hhi(self) -> None:
        # 3 symbols evenly: HHI = 3 * (1/3)^2 * 10000 ≈ 3333.33
        counts = Counter({"A": 10, "B": 10, "C": 10})
        result = sci.compute_concentration(counts)
        self.assertAlmostEqual(result["hhi"], 10000.0 / 3, places=2)
        self.assertAlmostEqual(result["effective_n_symbols"], 3.0, places=4)

    def test_top3_share_caps_at_100(self) -> None:
        # Only 2 symbols -> top3_share = 100%
        counts = Counter({"A": 5, "B": 5})
        result = sci.compute_concentration(counts)
        self.assertEqual(result["top3_share_pct"], 100.0)

    def test_dominated_below_threshold(self) -> None:
        # 80% on one symbol, 5% each on 4 others
        # HHI = 0.64 * 10000 + 4 * 0.0025 * 10000 = 6400 + 100 = 6500
        counts = Counter({"BTC": 80, "A": 5, "B": 5, "C": 5, "D": 5})
        result = sci.compute_concentration(counts)
        self.assertAlmostEqual(result["hhi"], 6500.0, places=4)
        self.assertTrue(result["flag_single_symbol_dominated"])

    def test_empty_counter_zeroes(self) -> None:
        result = sci.compute_concentration(Counter())
        self.assertEqual(result["n_picks"], 0)
        self.assertEqual(result["hhi"], 0.0)
        self.assertEqual(result["effective_n_symbols"], 0.0)


class AnalyzeStrategyTests(unittest.TestCase):
    def _picks(self, symbols: list[str]) -> list[dict]:
        return [{"strategy": "x", "symbol": s} for s in symbols]

    def test_insufficient_n_returns_none(self) -> None:
        # min_n=20 default, only 10 picks
        self.assertIsNone(sci.analyze_strategy(self._picks(["BTC"] * 10)))

    def test_skips_missing_or_empty_symbol(self) -> None:
        good = self._picks(["BTC"] * 25)
        bad = [
            {"strategy": "x", "symbol": None},
            {"strategy": "x", "symbol": ""},
            {"strategy": "x"},  # missing field
            {"strategy": "x", "symbol": 123},  # non-string
        ]
        result = sci.analyze_strategy(good + bad)
        self.assertIsNotNone(result)
        # Only 25 valid picks counted
        self.assertEqual(result["n_picks"], 25)


class AnalyzeAllTests(unittest.TestCase):
    def _picks(self, strategy: str, symbols: list[str]) -> list[dict]:
        return [{"strategy": strategy, "symbol": s} for s in symbols]

    def test_groups_by_strategy_and_filters_small_n(self) -> None:
        picks = (self._picks("dominated", ["BTC"] * 24)
                 + self._picks("diversified", ["A", "B", "C", "D", "E"] * 5)
                 + self._picks("too_small", ["X"] * 10))
        summary = sci.analyze_all(picks)
        names = {s["strategy"] for s in summary["strategies"]}
        self.assertIn("dominated", names)
        self.assertIn("diversified", names)
        self.assertNotIn("too_small", names)

    def test_dominated_count_in_summary(self) -> None:
        picks = (self._picks("a_dominated", ["BTC"] * 25)
                 + self._picks("b_diversified", ["A", "B", "C", "D"] * 6))
        summary = sci.analyze_all(picks)
        self.assertEqual(summary["n_single_symbol_dominated"], 1)

    def test_sorts_by_hhi_descending(self) -> None:
        picks = (self._picks("low_conc", ["A", "B", "C"] * 10)
                 + self._picks("high_conc", ["BTC"] * 30))
        summary = sci.analyze_all(picks)
        # high_conc should be first (HHI 10000) over low_conc (HHI 3333)
        self.assertEqual(summary["strategies"][0]["strategy"], "high_conc")


if __name__ == "__main__":
    unittest.main()
