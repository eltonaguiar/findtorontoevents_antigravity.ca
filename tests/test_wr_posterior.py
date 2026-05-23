"""Tests for tools/wr_posterior.py.

Verifies Beta-Bernoulli posterior math + edge cases.
"""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "wr_posterior", REPO / "tools" / "wr_posterior.py"
)
wp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wp)


class PosteriorMathTests(unittest.TestCase):
    def test_jeffreys_uniform_data(self) -> None:
        # 5 wins / 10 trials with Jeffreys prior: posterior Beta(5.5, 5.5)
        # mean = 0.5, P(WR > 0.5) ≈ 0.5
        s = wp.posterior_stats(wins=5, n=10)
        self.assertAlmostEqual(s["posterior_mean"], 0.5, places=3)
        self.assertAlmostEqual(s["p_wr_above_50"], 0.5, places=2)
        self.assertLess(s["ci_low_95"], 0.5)
        self.assertGreater(s["ci_high_95"], 0.5)

    def test_high_wr_large_n_decisive(self) -> None:
        s = wp.posterior_stats(wins=80, n=100)
        self.assertGreater(s["p_wr_above_50"], 0.999)
        self.assertGreater(s["posterior_mean"], 0.78)
        self.assertLess(s["posterior_mean"], 0.81)

    def test_zero_wr_decisive_loser(self) -> None:
        s = wp.posterior_stats(wins=0, n=20)
        self.assertLess(s["p_wr_above_50"], 0.001)
        self.assertLess(s["posterior_mean"], 0.05)

    def test_small_n_wide_interval(self) -> None:
        small = wp.posterior_stats(wins=4, n=5)
        large = wp.posterior_stats(wins=80, n=100)
        self.assertGreater(small["ci_width"], large["ci_width"])

    def test_ci_contains_mean(self) -> None:
        for w, n in [(1, 2), (5, 10), (50, 100), (0, 50), (50, 50)]:
            s = wp.posterior_stats(wins=w, n=n)
            self.assertLessEqual(s["ci_low_95"], s["posterior_mean"])
            self.assertGreaterEqual(s["ci_high_95"], s["posterior_mean"])

    def test_uniform_prior_extreme_data(self) -> None:
        # Uniform Beta(1,1), 0 wins / 1 trial → posterior Beta(1, 2)
        # mean = 1/3
        s = wp.posterior_stats(wins=0, n=1, alpha0=1.0, beta0=1.0)
        self.assertAlmostEqual(s["posterior_mean"], 1.0 / 3.0, places=4)


class StrategyAnalysisTests(unittest.TestCase):
    def _picks(self) -> list[dict]:
        # 12 BTCUSDT picks: 9 wins, 3 losses → WR=0.75
        out = []
        for i in range(9):
            out.append({"strategy": "alpha", "asset_class": "CRYPTO",
                        "pnl_pct": 1.0})
        for i in range(3):
            out.append({"strategy": "alpha", "asset_class": "CRYPTO",
                        "pnl_pct": -1.0})
        # 5 zero-win picks for 'beta' — below MIN_N=10, must be excluded
        for i in range(5):
            out.append({"strategy": "beta", "asset_class": "CRYPTO",
                        "pnl_pct": -1.0})
        return out

    def test_min_n_filter(self) -> None:
        rows, _ = wp.analyze_strategies(self._picks(), min_n=10)
        names = [r["strategy"] for r in rows]
        self.assertIn("alpha", names)
        self.assertNotIn("beta", names)  # n=5 < min_n=10

    def test_winner_at_top(self) -> None:
        rows, _ = wp.analyze_strategies(self._picks(), min_n=10)
        # 'alpha' should be top by P(WR>50%)
        self.assertEqual(rows[0]["strategy"], "alpha")
        self.assertGreater(rows[0]["p_wr_above_50"], 0.9)

    def test_skips_missing_pnl(self) -> None:
        bad = [{"strategy": "x", "pnl_pct": None} for _ in range(20)]
        good = [{"strategy": "x", "pnl_pct": 1.0} for _ in range(15)]
        rows, _ = wp.analyze_strategies(bad + good, min_n=10)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["n"], 15)


if __name__ == "__main__":
    unittest.main()
