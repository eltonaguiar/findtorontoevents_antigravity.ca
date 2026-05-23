"""Tests for tools/pnl_weighted_concentration.py."""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "pnl_weighted_concentration",
    REPO / "tools" / "pnl_weighted_concentration.py"
)
pwc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pwc)


def _picks(rows: list[tuple[str, float]], strategy: str = "demo") -> list[dict]:
    """Build picks. rows is a list of (symbol, pnl_pct)."""
    return [{"strategy": strategy, "symbol": s, "pnl_pct": p}
            for s, p in rows]


class WeightCounterTests(unittest.TestCase):
    def test_abs_pnl_counter_uses_absolute_value(self) -> None:
        # Mix of wins and losses on same symbol — both contribute
        rows = [("BTC", 1.0), ("BTC", -1.0)]
        weights = pwc._abs_pnl_by_symbol_counter(rows := _picks(rows))
        self.assertEqual(weights["BTC"],
                         int(round(1.0 * 10000)) + int(round(1.0 * 10000)))

    def test_abs_pnl_counter_breakeven_picks_register(self) -> None:
        rows = [("BTC", 0.0), ("BTC", 0.0)]
        weights = pwc._abs_pnl_by_symbol_counter(_picks(rows))
        # Both should still count (scaled to min 1 each)
        self.assertEqual(weights["BTC"], 2)

    def test_abs_pnl_skips_missing_pnl(self) -> None:
        picks = [{"strategy": "x", "symbol": "BTC", "pnl_pct": 1.0},
                 {"strategy": "x", "symbol": "BTC", "pnl_pct": None},
                 {"strategy": "x", "symbol": "BTC", "pnl_pct": "not_numeric"}]
        weights = pwc._abs_pnl_by_symbol_counter(picks)
        # Only the valid pick counts
        self.assertEqual(weights["BTC"], int(round(1.0 * 10000)))

    def test_count_counter_skips_invalid_picks(self) -> None:
        picks = [{"strategy": "x", "symbol": "BTC", "pnl_pct": 1.0},
                 {"strategy": "x", "symbol": "", "pnl_pct": 1.0},
                 {"strategy": "x", "symbol": "ETH", "pnl_pct": None}]
        counts = pwc._count_by_symbol_counter(picks)
        self.assertEqual(counts["BTC"], 1)
        self.assertNotIn("ETH", counts)
        self.assertNotIn("", counts)


class HiddenConcentrationDetectionTests(unittest.TestCase):
    def test_even_counts_uneven_pnl_flagged(self) -> None:
        # 10 BTC picks at +99%, 10 ETH picks at -0.01%
        # Counts: 50/50. PnL absolute: BTC ≈ 990, ETH ≈ 0.1 -> PnL HHI near 10000.
        # count_hhi = 5000, pnl_hhi ≈ 9999 -> gap ≈ 4999 > 2000 -> flagged
        rows = ([("BTC", 99.0)] * 10 + [("ETH", 0.01)] * 10)
        result = pwc.analyze_strategy(_picks(rows), min_n=20)
        self.assertIsNotNone(result)
        self.assertTrue(result["flag_hidden_concentration"])
        self.assertGreater(result["pnl_minus_count_hhi"], 2000)

    def test_even_counts_even_pnl_not_flagged(self) -> None:
        # 50/50 counts AND 50/50 PnL -> count_hhi == pnl_hhi -> gap ≈ 0
        rows = ([("BTC", 1.0), ("ETH", 1.0)] * 12)
        result = pwc.analyze_strategy(_picks(rows), min_n=20)
        self.assertIsNotNone(result)
        self.assertFalse(result["flag_hidden_concentration"])
        self.assertAlmostEqual(result["pnl_minus_count_hhi"], 0, delta=10)

    def test_single_symbol_both_equal_10000(self) -> None:
        rows = [("BTC", 1.0)] * 25
        result = pwc.analyze_strategy(_picks(rows), min_n=20)
        self.assertIsNotNone(result)
        self.assertEqual(result["count_hhi"], 10000.0)
        self.assertEqual(result["pnl_hhi"], 10000.0)
        self.assertAlmostEqual(result["pnl_minus_count_hhi"], 0, delta=10)
        self.assertFalse(result["flag_hidden_concentration"])

    def test_pnl_diversified_count_concentrated(self) -> None:
        # 24 BTC picks at +0.1, 1 ETH pick at +99.0
        # Counts: 96%/4% -> count_hhi ≈ 9216 + 16 = 9232
        # PnL: BTC=2.4 (24*0.1), ETH=99 -> shares 0.024/0.976 -> pnl_hhi ≈ 9529
        # gap ≈ 297 — modest, NOT flagged at default 2000 threshold
        rows = [("BTC", 0.1)] * 24 + [("ETH", 99.0)]
        result = pwc.analyze_strategy(_picks(rows), min_n=20)
        self.assertIsNotNone(result)
        # Negative gap is also possible (count more concentrated than PnL);
        # this test pins the directional result, not magnitude.
        self.assertGreater(result["count_hhi"], 9000)


class AnalyzeStrategyEdgeTests(unittest.TestCase):
    def test_insufficient_n_returns_none(self) -> None:
        rows = [("BTC", 1.0)] * 10
        self.assertIsNone(pwc.analyze_strategy(_picks(rows), min_n=20))

    def test_skips_malformed_picks(self) -> None:
        good = _picks([("BTC", 1.0)] * 22)
        bad = [
            {"strategy": "demo", "symbol": "BTC", "pnl_pct": None},
            {"strategy": "demo", "symbol": "", "pnl_pct": 1.0},
            {"strategy": "demo"},  # no symbol no pnl
            {"strategy": "demo", "symbol": "ETH",
             "pnl_pct": "not_numeric"},
        ]
        result = pwc.analyze_strategy(good + bad, min_n=20)
        self.assertIsNotNone(result)
        # Only 22 valid picks counted
        self.assertEqual(result["n_picks"], 22)


class AnalyzeAllTests(unittest.TestCase):
    def test_groups_and_sorts_by_gap(self) -> None:
        # One hidden-concentration strategy + one balanced
        hidden_rows = ([("BTC", 99.0)] * 10 + [("ETH", 0.01)] * 10)
        balanced_rows = ([("A", 1.0), ("B", 1.0)] * 12)
        picks = (_picks(hidden_rows, strategy="hidden")
                 + _picks(balanced_rows, strategy="balanced"))
        summary = pwc.analyze_all(picks, min_n=20)
        names = [s["strategy"] for s in summary["strategies"]]
        # 'hidden' has positive gap and should sort first
        self.assertEqual(names[0], "hidden")
        self.assertGreaterEqual(summary["n_hidden_concentration"], 1)


if __name__ == "__main__":
    unittest.main()
