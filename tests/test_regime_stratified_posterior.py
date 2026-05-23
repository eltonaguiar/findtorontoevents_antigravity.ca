"""Tests for tools/regime_stratified_posterior.py."""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "regime_stratified_posterior",
    REPO / "tools" / "regime_stratified_posterior.py"
)
rsp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rsp)


def _fake_stats(wins: int, n: int, **kwargs):
    """Deterministic test stats — avoids importlib of wr_posterior."""
    if n <= 0:
        return {"posterior_mean": 0.5, "p_wr_above_50": 0.5,
                "ci_low_95": 0.0, "ci_high_95": 1.0}
    p = wins / n
    return {"posterior_mean": float(p),
            "p_wr_above_50": float(p),
            "ci_low_95": max(0.0, p - 0.1),
            "ci_high_95": min(1.0, p + 0.1)}


def _picks(spec: list[tuple[int, str]], strategy: str = "demo") -> list[dict]:
    """Build picks. spec is list of (win_flag, regime_label)."""
    return [{"strategy": strategy, "pnl_pct": 1.0 if w else -1.0,
             "regime": regime} for w, regime in spec]


class RegimeExtractionTests(unittest.TestCase):
    def test_explicit_regime_label_used(self) -> None:
        self.assertEqual(rsp.extract_regime({"regime": "BULL"}), "BULL")
        self.assertEqual(rsp.extract_regime({"regime": "bear"}), "BEAR")
        self.assertEqual(rsp.extract_regime({"regime": "  bull  "}), "BULL")

    def test_btc_direction_fallback(self) -> None:
        self.assertEqual(rsp.extract_regime({"btc_4h_direction": 1}), "BULL")
        self.assertEqual(rsp.extract_regime({"btc_4h_direction": -1}), "BEAR")
        self.assertEqual(rsp.extract_regime({"btc_4h_direction": 0}), "SIDEWAYS")
        self.assertEqual(rsp.extract_regime({"btc_4h_direction": 0.5}), "BULL")

    def test_unknown_fallback(self) -> None:
        self.assertEqual(rsp.extract_regime({}), "UNKNOWN")
        self.assertEqual(rsp.extract_regime({"regime": ""}), "UNKNOWN")
        self.assertEqual(rsp.extract_regime({"regime": None}), "UNKNOWN")
        self.assertEqual(rsp.extract_regime({"btc_4h_direction": "bad"}),
                         "UNKNOWN")


class StratifyTests(unittest.TestCase):
    def test_single_regime_only(self) -> None:
        # 12 BULL picks, 8 wins -> P(>50%) ≈ 0.667 (with fake stats)
        picks = _picks([(1, "BULL")] * 8 + [(0, "BULL")] * 4)
        result = rsp.stratify_strategy(picks, min_n=10,
                                        posterior_stats=_fake_stats)
        self.assertIsNotNone(result)
        self.assertEqual(result["regime_count"], 1)
        self.assertIn("BULL", result["regimes"])
        self.assertEqual(result["regimes"]["BULL"]["n"], 12)
        self.assertFalse(result["regime_dependent_flag"])  # only 1 regime

    def test_two_regime_dependence_detected(self) -> None:
        # BULL: 10 wins / 12 picks (P ~0.83); BEAR: 1 win / 12 picks (P ~0.08)
        picks = (_picks([(1, "BULL")] * 10 + [(0, "BULL")] * 2)
                 + _picks([(1, "BEAR")] * 1 + [(0, "BEAR")] * 11))
        result = rsp.stratify_strategy(picks, min_n=10,
                                        regime_dep_threshold=0.50,
                                        posterior_stats=_fake_stats)
        self.assertEqual(result["regime_count"], 2)
        self.assertTrue(result["regime_dependent_flag"])
        self.assertGreater(
            result["weighted_aggregate"]["p_above_50_max_regime"]
            - result["weighted_aggregate"]["p_above_50_min_regime"],
            0.50
        )

    def test_below_min_n_per_regime_skipped(self) -> None:
        # BULL has 12 picks (passes min_n=10); BEAR has 5 (below)
        picks = (_picks([(1, "BULL")] * 6 + [(0, "BULL")] * 6)
                 + _picks([(1, "BEAR")] * 5))
        result = rsp.stratify_strategy(picks, min_n=10,
                                        posterior_stats=_fake_stats)
        self.assertEqual(result["regime_count"], 1)  # only BULL counted
        self.assertTrue(result["regimes"]["BEAR"]["skipped"])
        self.assertFalse(result["regimes"]["BULL"]["skipped"])

    def test_unknown_regime_when_label_missing(self) -> None:
        # 12 picks with no regime label -> all UNKNOWN
        picks = [{"strategy": "demo", "pnl_pct": 1.0 if i < 8 else -1.0}
                 for i in range(12)]
        result = rsp.stratify_strategy(picks, min_n=10,
                                        posterior_stats=_fake_stats)
        self.assertEqual(result["regime_count"], 1)
        self.assertIn("UNKNOWN", result["regimes"])

    def test_malformed_picks_skipped(self) -> None:
        good = _picks([(1, "BULL")] * 8 + [(0, "BULL")] * 4)
        bad = [
            {"strategy": "demo", "pnl_pct": None, "regime": "BULL"},
            {"strategy": "demo", "pnl_pct": "not_a_number", "regime": "BULL"},
        ]
        result = rsp.stratify_strategy(good + bad, min_n=10,
                                        posterior_stats=_fake_stats)
        # Only the 12 good picks counted
        self.assertEqual(result["regimes"]["BULL"]["n"], 12)


class AnalyzeAllTests(unittest.TestCase):
    def test_groups_by_strategy(self) -> None:
        picks = _picks([(1, "BULL")] * 10 + [(0, "BULL")] * 2,
                       strategy="winner")
        picks += _picks([(0, "BULL")] * 10 + [(1, "BULL")] * 2,
                        strategy="loser")
        summary = rsp.analyze_all(picks, min_n=10, posterior_stats=_fake_stats)
        names = {s["strategy"] for s in summary["strategies"]}
        self.assertIn("winner", names)
        self.assertIn("loser", names)

    def test_regime_dep_count_in_summary(self) -> None:
        picks = (_picks([(1, "BULL")] * 12 + [(0, "BEAR")] * 12,
                        strategy="regime_dependent_x")
                 + _picks([(1, "BULL")] * 6 + [(0, "BULL")] * 6,
                          strategy="balanced_y"))
        summary = rsp.analyze_all(picks, min_n=10,
                                   regime_dep_threshold=0.50,
                                   posterior_stats=_fake_stats)
        self.assertGreaterEqual(summary["n_regime_dependent"], 1)


class WeightedAggregateTests(unittest.TestCase):
    def test_single_bucket_aggregate_matches_baseline(self) -> None:
        # Single BULL regime: weighted aggregate should equal that regime's mean
        picks = _picks([(1, "BULL")] * 7 + [(0, "BULL")] * 3)
        result = rsp.stratify_strategy(picks, min_n=10,
                                        posterior_stats=_fake_stats)
        wa = result["weighted_aggregate"]
        bull = result["regimes"]["BULL"]
        self.assertAlmostEqual(wa["posterior_mean"], bull["posterior_mean"])

    def test_two_bucket_aggregate_is_frequency_weighted(self) -> None:
        # 10 BULL @ 0.7 mean + 10 BEAR @ 0.3 mean -> aggregate = 0.5
        picks = (_picks([(1, "BULL")] * 7 + [(0, "BULL")] * 3)
                 + _picks([(1, "BEAR")] * 3 + [(0, "BEAR")] * 7))
        result = rsp.stratify_strategy(picks, min_n=10,
                                        posterior_stats=_fake_stats)
        wa = result["weighted_aggregate"]
        # Each regime has n=10, equal weights -> aggregate ~= (0.7 + 0.3) / 2 = 0.5
        self.assertAlmostEqual(wa["posterior_mean"], 0.5, places=2)


if __name__ == "__main__":
    unittest.main()
