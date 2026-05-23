"""Tests for tools/factor_attribution.py."""
from __future__ import annotations

import importlib.util
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "factor_attribution", REPO / "tools" / "factor_attribution.py"
)
fa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fa)


def _picks(daily_pnl_by_strategy: dict[str, list[float]],
           start: str = "2026-01-01") -> list[dict]:
    """Build a picks list with one pick per strategy per day."""
    base = datetime.fromisoformat(start).replace(tzinfo=timezone.utc)
    out: list[dict] = []
    for strat, daily_pnls in daily_pnl_by_strategy.items():
        for i, pnl in enumerate(daily_pnls):
            ts = (base + timedelta(days=i)).isoformat().replace("+00:00", "Z")
            out.append({"strategy": strat, "asset_class": "CRYPTO",
                        "pnl_pct": pnl, "closed_at": ts})
    return out


class FactorBuilderTests(unittest.TestCase):
    def test_factors_have_nan_padding_for_initial_window(self) -> None:
        # Benchmark with 10 days; mom_window=5 → first 4 days have NaN F_mom
        bench = {f"2026-01-{i+1:02d}": float(i) for i in range(10)}
        factors = fa.build_factors(bench, mom_window=5, qual_window=5)
        days = sorted(factors.keys())
        self.assertTrue(np.isnan(factors[days[0]]["mom"]))
        self.assertTrue(np.isnan(factors[days[3]]["mom"]))  # i=3 < window=5 - 1
        self.assertFalse(np.isnan(factors[days[4]]["mom"]))  # i=4 → has 5 vals

    def test_factor_vol_sign(self) -> None:
        bench = {"2026-01-01": 1.0, "2026-01-02": -0.5, "2026-01-03": 0.0}
        factors = fa.build_factors(bench)
        self.assertEqual(factors["2026-01-01"]["vol"], 1.0)
        self.assertEqual(factors["2026-01-02"]["vol"], -1.0)
        self.assertEqual(factors["2026-01-03"]["vol"], 0.0)


class AttributionTests(unittest.TestCase):
    def setUp(self) -> None:
        # Build a benchmark with 30 days of varying daily returns
        rng = np.random.default_rng(42)
        days = [f"2026-01-{i+1:02d}" if i < 9 else f"2026-01-{i+1}"
                for i in range(30)]
        self.bench_daily = {d: float(rng.normal(0.1, 1.0)) for d in days}
        self.factors = fa.build_factors(self.bench_daily,
                                        mom_window=5, qual_window=5)

    def test_pure_alpha_strategy_high_alpha_share(self) -> None:
        # Strategy with constant 1.0% return — orthogonal to all factors
        days = sorted(self.bench_daily.keys())
        strat_daily = {d: 1.0 for d in days}
        result = fa.attribute_strategy(strat_daily, self.factors, min_n=20)
        self.assertIsNotNone(result)
        # Constant returns → alpha ≈ 1.0, betas ≈ 0 → alpha_share near 100%
        self.assertGreater(result["alpha_share_pct"], 90.0)
        self.assertAlmostEqual(result["alpha_pct"], 1.0, places=2)

    def test_pure_beta_strategy_low_alpha_share(self) -> None:
        # Strategy that exactly mimics the benchmark's daily returns
        days = sorted(self.bench_daily.keys())
        strat_daily = {d: self.bench_daily[d] * 2.0 for d in days}
        result = fa.attribute_strategy(strat_daily, self.factors, min_n=20)
        self.assertIsNotNone(result)
        # Strategy is 2× the benchmark — should have low alpha, high beta
        self.assertLess(abs(result["alpha_pct"]), 0.5)
        # Sum of beta contributions should dominate
        self.assertGreater(result["beta_contrib_abs"], abs(result["alpha_pct"]))

    def test_insufficient_n_returns_none(self) -> None:
        days = sorted(self.bench_daily.keys())[:10]
        strat_daily = {d: 1.0 for d in days}
        self.assertIsNone(
            fa.attribute_strategy(strat_daily, self.factors, min_n=20))

    def test_nan_factor_dates_skipped(self) -> None:
        # First 4 days have NaN F_mom → should be skipped
        days = sorted(self.bench_daily.keys())
        strat_daily = {d: 1.0 for d in days}
        result = fa.attribute_strategy(strat_daily, self.factors, min_n=20)
        self.assertIsNotNone(result)
        # 30 days total, but first 4 dropped due to NaN F_mom → n=26
        self.assertEqual(result["n"], 26)


class AnalyzeAllTests(unittest.TestCase):
    def test_groups_by_strategy_filters_small_n(self) -> None:
        rng = np.random.default_rng(7)
        days = [f"2026-01-{i+1:02d}" if i < 9 else f"2026-01-{i+1}"
                for i in range(30)]
        bench_pnls = [float(rng.normal(0.1, 1.0)) for _ in range(30)]
        # Three strategies: pure-alpha winner, beta-mimicker, too-small
        picks = []
        for i, d in enumerate(days):
            picks.append({"strategy": "alpha_strategy", "asset_class": "CRYPTO",
                          "pnl_pct": 1.0, "closed_at": f"{d}T00:00:00Z"})
            picks.append({"strategy": "beta_strategy", "asset_class": "CRYPTO",
                          "pnl_pct": bench_pnls[i] * 2.0,
                          "closed_at": f"{d}T00:00:00Z"})
            if i < 5:
                picks.append({"strategy": "small_strategy",
                              "asset_class": "CRYPTO",
                              "pnl_pct": 0.5,
                              "closed_at": f"{d}T00:00:00Z"})
        summary = fa.analyze_all(picks, min_n=20)
        names = {s["strategy"] for s in summary["strategies"]}
        self.assertIn("alpha_strategy", names)
        self.assertIn("beta_strategy", names)
        self.assertNotIn("small_strategy", names)
        alpha_row = next(s for s in summary["strategies"]
                         if s["strategy"] == "alpha_strategy")
        beta_row = next(s for s in summary["strategies"]
                        if s["strategy"] == "beta_strategy")
        self.assertGreater(alpha_row["alpha_share_pct"],
                           beta_row["alpha_share_pct"])


class DailyAggregationTests(unittest.TestCase):
    def test_multiple_picks_same_day_averaged(self) -> None:
        picks = [
            {"strategy": "x", "pnl_pct": 1.0, "closed_at": "2026-01-01T00:00:00Z"},
            {"strategy": "x", "pnl_pct": -1.0, "closed_at": "2026-01-01T12:00:00Z"},
            {"strategy": "x", "pnl_pct": 2.0, "closed_at": "2026-01-02T00:00:00Z"},
        ]
        daily = fa._aggregate_daily(picks)
        self.assertAlmostEqual(daily["2026-01-01"], 0.0)
        self.assertAlmostEqual(daily["2026-01-02"], 2.0)

    def test_skips_missing_pnl_or_ts(self) -> None:
        picks = [
            {"strategy": "x", "pnl_pct": None, "closed_at": "2026-01-01T00:00:00Z"},
            {"strategy": "x", "pnl_pct": 1.0, "closed_at": None},
            {"strategy": "x", "pnl_pct": "not_a_number",
             "closed_at": "2026-01-01T00:00:00Z"},
            {"strategy": "x", "pnl_pct": 1.0, "closed_at": "2026-01-02T00:00:00Z"},
        ]
        daily = fa._aggregate_daily(picks)
        self.assertEqual(set(daily.keys()), {"2026-01-02"})


if __name__ == "__main__":
    unittest.main()
