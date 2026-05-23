"""Tests for tools/slippage_realism_check.py."""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "slippage_realism_check", REPO / "tools" / "slippage_realism_check.py"
)
src = importlib.util.module_from_spec(spec)
spec.loader.exec_module(src)


def _picks(rows: list[tuple[str, float]], strategy: str = "demo",
           asset_class: str = "CRYPTO") -> list[dict]:
    """Each row is (pnl_label, pnl_value). pnl_label is unused here, just
    a description for clarity. Returns picks list."""
    return [{"strategy": strategy, "asset_class": asset_class,
             "pnl_pct": p} for _, p in rows]


class LoadTcTests(unittest.TestCase):
    def test_missing_file_returns_empty(self) -> None:
        self.assertEqual(src.load_declared_tc(Path("/nonexistent")), {})

    def test_loads_cost_pct(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                         encoding="utf-8") as f:
            json.dump({"costs": {"CRYPTO": {"cost_pct": 0.30},
                                 "EQUITY": {"cost_pct": 0.10}}}, f)
            path = Path(f.name)
        try:
            tc = src.load_declared_tc(path)
            self.assertEqual(tc["CRYPTO"], 0.30)
            self.assertEqual(tc["EQUITY"], 0.10)
        finally:
            path.unlink()

    def test_falls_back_to_cost_bps(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                         encoding="utf-8") as f:
            json.dump({"costs": {"FOREX": {"cost_bps": 5}}}, f)
            path = Path(f.name)
        try:
            tc = src.load_declared_tc(path)
            self.assertAlmostEqual(tc["FOREX"], 0.05)
        finally:
            path.unlink()

    def test_skips_malformed_entries(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                         encoding="utf-8") as f:
            json.dump({"costs": {"CRYPTO": {"cost_pct": 0.30},
                                 "BAD": {"cost_pct": "not_numeric"},
                                 "EMPTY": {}, "STR": "not_a_dict"}}, f)
            path = Path(f.name)
        try:
            tc = src.load_declared_tc(path)
            self.assertIn("CRYPTO", tc)
            self.assertNotIn("BAD", tc)
            self.assertNotIn("EMPTY", tc)
        finally:
            path.unlink()


class AnalyzeStrategyTests(unittest.TestCase):
    def test_zero_cost_synthetic_no_flag(self) -> None:
        # All winners at +1.0, no losers. WR=1, mean=+1, winners_mean=1,
        # losers_mean=0. cost_free = (1 - 0)*1 = 1.0. implied_tc = max(0, 1-1) = 0.
        rows = [("w", 1.0)] * 25
        declared = {"CRYPTO": 0.30}
        result = src.analyze_strategy(_picks(rows), declared, min_n=20)
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result["implied_tc_pct"], 0.0)
        self.assertFalse(result["flag_under_reported_friction"])

    def test_high_friction_synthetic_flagged(self) -> None:
        # WR=0.5, winners_mean=0.1, losers_mean=-1.0
        # mean_pnl = (0.1 - 1.0)/2 = -0.45
        # cost_free = (0.1 - (-1.0)) * 0.5 = 0.55
        # implied_tc = 0.55 - (-0.45) = 1.0% (100 bps)
        # declared CRYPTO = 0.30% -> ratio = 1.0/0.30 = 3.33 > 1.5 -> flag
        rows = [("w", 0.1), ("l", -1.0)] * 12
        declared = {"CRYPTO": 0.30}
        result = src.analyze_strategy(_picks(rows), declared, min_n=20)
        self.assertIsNotNone(result)
        self.assertGreater(result["implied_tc_pct"], 0.5)
        self.assertGreater(result["ratio_implied_to_declared"], 1.5)
        self.assertTrue(result["flag_under_reported_friction"])

    def test_missing_declared_tc_no_ratio(self) -> None:
        # Asset class not in declared dict -> ratio is None, no flag
        rows = [("w", 0.1), ("l", -1.0)] * 12
        result = src.analyze_strategy(_picks(rows, asset_class="UNICORN"),
                                       {}, min_n=20)
        self.assertIsNotNone(result)
        self.assertIsNone(result["ratio_implied_to_declared"])
        self.assertFalse(result["flag_under_reported_friction"])

    def test_insufficient_n_returns_none(self) -> None:
        rows = [("w", 1.0)] * 10
        self.assertIsNone(src.analyze_strategy(_picks(rows), {"CRYPTO": 0.30},
                                                min_n=20))

    def test_skips_malformed_pnls(self) -> None:
        good = _picks([("w", 1.0), ("l", -1.0)] * 11)  # 22 picks
        bad = [{"strategy": "demo", "asset_class": "CRYPTO", "pnl_pct": None},
               {"strategy": "demo", "asset_class": "CRYPTO",
                "pnl_pct": "not_a_number"},
               {"strategy": "demo", "asset_class": "CRYPTO",
                "pnl_pct": float("inf")}]
        result = src.analyze_strategy(good + bad, {"CRYPTO": 0.30}, min_n=20)
        self.assertEqual(result["n"], 22)


class AnalyzeAllTests(unittest.TestCase):
    def test_groups_and_sorts(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                         encoding="utf-8") as f:
            json.dump({"costs": {"CRYPTO": {"cost_pct": 0.30}}}, f)
            tc_path = Path(f.name)
        try:
            picks = (_picks([("w", 0.1), ("l", -1.0)] * 12, strategy="hi_fric")
                     + _picks([("w", 1.0)] * 25, strategy="zero_fric"))
            summary = src.analyze_all(picks, min_n=20, tc_path=tc_path)
            names = {s["strategy"] for s in summary["strategies"]}
            self.assertEqual(names, {"hi_fric", "zero_fric"})
            self.assertEqual(summary["n_under_reported_friction"], 1)
            self.assertEqual(summary["strategies"][0]["strategy"], "hi_fric")
        finally:
            tc_path.unlink()


if __name__ == "__main__":
    unittest.main()
