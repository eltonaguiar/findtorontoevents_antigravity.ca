"""Tests for tools/sharpe_lower_bound.py."""
from __future__ import annotations

import importlib.util
import math
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "sharpe_lower_bound", REPO / "tools" / "sharpe_lower_bound.py"
)
slb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(slb)

ds_spec = importlib.util.spec_from_file_location(
    "deflated_sharpe", REPO / "tools" / "deflated_sharpe.py"
)
ds = importlib.util.module_from_spec(ds_spec)
ds_spec.loader.exec_module(ds)


class ReuseLo2002SETests(unittest.TestCase):
    """The whole point of using importlib is that the SE math is shared.
    Verify our helpers ARE the deflated_sharpe ones."""

    def test_sharpe_se_behavior_matches(self) -> None:
        """Importlib loads create distinct module objects, so symbol
        identity (`is`) won't match. Behavioural identity is what
        actually matters: same inputs must give same SE output."""
        sharpe_se, _, _ = slb._load_deflated_sharpe_helpers()
        for sr_ann, skew, kurt, T in [
            (1.5, 0.1, 3.5, 100),
            (-0.5, -0.3, 4.0, 50),
            (3.0, 1.2, 6.0, 200),
        ]:
            self.assertAlmostEqual(
                sharpe_se(sr_ann, skew, kurt, T),
                ds._sharpe_se(sr_ann, skew, kurt, T),
                places=10,
                msg=f"SE mismatch at SR={sr_ann}, skew={skew}, kurt={kurt}, T={T}"
            )

    def test_annual_trades_constant_matches(self) -> None:
        _, _, annual_trades = slb._load_deflated_sharpe_helpers()
        self.assertEqual(annual_trades, ds.ANNUAL_TRADES)


class ComputeSharpeLBTests(unittest.TestCase):
    def test_insufficient_n_returns_none(self) -> None:
        result = slb.compute_sharpe_lb([1.0] * 19)
        self.assertIsNone(result)

    def test_tight_high_sharpe_high_lb(self) -> None:
        # 50 picks of consistent positive PnL with low variance
        # mu = 1.0, std small → Sharpe huge → LB also huge positive
        rets = [1.0 + (0.01 if i % 2 == 0 else -0.01) for i in range(50)]
        result = slb.compute_sharpe_lb(rets)
        self.assertIsNotNone(result)
        self.assertGreater(result["sharpe_obs_annual"], 0)
        self.assertGreater(result["sharpe_lb_95_one_sided"], 0)
        self.assertTrue(result["classifies_as_significant_at_95"])

    def test_noisy_high_mean_low_lb(self) -> None:
        # 25 picks: small positive mean swamped by big variance
        # Specifically alternate between +5 and -4.5: mean ~+0.25 but std ~5
        # Sharpe small, SE large → LB plausibly negative
        rets = []
        for i in range(25):
            rets.append(5.0 if i % 2 == 0 else -4.5)
        result = slb.compute_sharpe_lb(rets)
        self.assertIsNotNone(result)
        # The 95% LB should be lower than the point estimate
        self.assertLess(
            result["sharpe_lb_95_one_sided"], result["sharpe_obs_annual"]
        )

    def test_clearly_negative_returns_negative_lb(self) -> None:
        # 30 consistent losses → negative Sharpe → negative LB (more
        # negative than the point estimate due to LB subtracting SE)
        rets = [-1.0 + (0.01 if i % 2 == 0 else -0.01) for i in range(30)]
        result = slb.compute_sharpe_lb(rets)
        self.assertIsNotNone(result)
        self.assertLess(result["sharpe_obs_annual"], 0)
        self.assertLess(result["sharpe_lb_95_one_sided"], 0)
        self.assertFalse(result["classifies_as_significant_at_95"])

    def test_lb_below_point_estimate(self) -> None:
        # Invariant: 95% one-sided LB must always be <= point estimate
        rets = [0.5, -0.3, 0.8, -0.1, 0.4, 0.2, -0.5, 0.1, 0.3, -0.2,
                0.6, -0.4, 0.7, -0.1, 0.2, 0.5, -0.3, 0.1, 0.4, -0.2,
                0.3, 0.5, -0.1, 0.2]
        result = slb.compute_sharpe_lb(rets)
        self.assertIsNotNone(result)
        self.assertLessEqual(
            result["sharpe_lb_95_one_sided"], result["sharpe_obs_annual"]
        )


class AnalyzeAllTests(unittest.TestCase):
    def _picks(self, pnls: list[float], strategy: str = "demo") -> list[dict]:
        return [{"strategy": strategy, "pnl_pct": p} for p in pnls]

    def test_groups_by_strategy_and_filters_small_n(self) -> None:
        # n=25 winning + n=10 small + n=20 noisy
        winners = self._picks([1.0] * 25, strategy="winner")
        small = self._picks([1.0] * 10, strategy="too_small")
        noisy = self._picks(
            [5.0, -4.5] * 10, strategy="noisy"
        )
        summary = slb.analyze_all(winners + small + noisy, min_n=20)
        names = {s["strategy"] for s in summary["strategies"]}
        self.assertIn("winner", names)
        self.assertIn("noisy", names)
        self.assertNotIn("too_small", names)

    def test_skips_malformed_pnls(self) -> None:
        good = self._picks([1.0] * 25, strategy="x")
        bad = [{"strategy": "x", "pnl_pct": None},
               {"strategy": "x", "pnl_pct": "not_a_number"},
               {"strategy": "x", "pnl_pct": float("inf")},
               {"strategy": "x", "pnl_pct": float("nan")}]
        summary = slb.analyze_all(good + bad, min_n=20)
        x_row = next(s for s in summary["strategies"]
                     if s["strategy"] == "x")
        self.assertEqual(x_row["n"], 25)


if __name__ == "__main__":
    unittest.main()
