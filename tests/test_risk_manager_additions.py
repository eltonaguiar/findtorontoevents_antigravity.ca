"""Tests for the 2026-05-02 risk_manager additions:
strategy_drawdown, is_strategy_muted, rebalance_by_sharpe, per_class_risk.
"""
import unittest

from ml_battleground.shared.risk_manager import (
    CLASS_TARGET_BUDGET,
    MAX_CLASS_BUDGET,
    MIN_CLASS_BUDGET,
    PER_STRATEGY_DD_HALT,
    is_strategy_muted,
    per_class_risk,
    rebalance_by_sharpe,
    strategy_drawdown,
)


def _trade(strategy: str, pnl_pct: float, ts: str = "2026-04-01T00:00:00Z"):
    return {"strategy": strategy, "pnl_pct": pnl_pct, "resolved_at": ts}


class StrategyDrawdownTests(unittest.TestCase):
    def test_no_trades(self):
        self.assertEqual(strategy_drawdown([], "s1"), 0.0)

    def test_below_min_trades(self):
        # < 5 trades returns 0
        trades = [_trade("s1", -10.0) for _ in range(4)]
        self.assertEqual(strategy_drawdown(trades, "s1"), 0.0)

    def test_filters_other_strategies(self):
        trades = [_trade("s2", -50.0) for _ in range(10)]
        self.assertEqual(strategy_drawdown(trades, "s1"), 0.0)

    def test_drawdown_compounds(self):
        # 10 sequential -2% trades → ~18% drawdown
        trades = [_trade("s1", -2.0, f"2026-04-{i:02d}T00:00:00Z")
                  for i in range(1, 11)]
        dd = strategy_drawdown(trades, "s1")
        self.assertGreater(dd, 0.15)
        self.assertLess(dd, 0.25)

    def test_drawdown_recovers_off_peak(self):
        # gain to peak then 5% drop
        trades = (
            [_trade("s1", 5.0, f"2026-04-0{i}T00:00:00Z") for i in range(1, 6)]
            + [_trade("s1", -5.0, f"2026-04-1{i}T00:00:00Z") for i in range(1, 6)]
        )
        dd = strategy_drawdown(trades, "s1")
        # 5 consecutive -5% → ~22% peak-to-trough
        self.assertGreater(dd, 0.18)


class IsStrategyMutedTests(unittest.TestCase):
    def test_low_dd_not_muted(self):
        trades = [_trade("s1", 1.0) for _ in range(10)]
        muted, _ = is_strategy_muted("s1", trades)
        self.assertFalse(muted)

    def test_high_dd_muted(self):
        trades = [_trade("s1", -3.0, f"2026-04-{i:02d}T00:00:00Z")
                  for i in range(1, 11)]
        muted, reason = is_strategy_muted("s1", trades)
        self.assertTrue(muted)
        self.assertIn("dd=", reason)

    def test_threshold_at_default(self):
        # Sanity: threshold default is the module constant
        self.assertEqual(PER_STRATEGY_DD_HALT, 0.15)


class RebalanceBySharpeTests(unittest.TestCase):
    def test_empty_falls_back_to_target_budget(self):
        self.assertEqual(rebalance_by_sharpe({}), CLASS_TARGET_BUDGET)
        self.assertEqual(rebalance_by_sharpe(None), CLASS_TARGET_BUDGET)

    def test_all_negative_falls_back(self):
        self.assertEqual(
            rebalance_by_sharpe({"CRYPTO": -1.0, "EQUITY": -0.5}),
            CLASS_TARGET_BUDGET,
        )

    def test_weights_sum_to_one(self):
        out = rebalance_by_sharpe({"CRYPTO": 1.5, "EQUITY": 0.5, "FOREX": 0.2})
        self.assertAlmostEqual(sum(out.values()), 1.0, places=5)

    def test_clipping(self):
        # 3 classes so cap=0.45 is mathematically feasible.
        # CRYPTO has runaway Sharpe; EQUITY/FOREX get the floor.
        out = rebalance_by_sharpe({"CRYPTO": 100.0, "EQUITY": 0.01, "FOREX": 0.01})
        self.assertLessEqual(out["CRYPTO"], MAX_CLASS_BUDGET + 1e-9)
        self.assertGreaterEqual(out["EQUITY"], MIN_CLASS_BUDGET - 1e-9)
        self.assertGreaterEqual(out["FOREX"], MIN_CLASS_BUDGET - 1e-9)
        self.assertAlmostEqual(sum(out.values()), 1.0, places=5)

    def test_clipping_infeasible_returns_capped(self):
        # 2 classes can't both stay below MAX=0.45 and sum to 1.
        # Implementation must honour the cap even if sum < 1.
        out = rebalance_by_sharpe({"CRYPTO": 100.0, "EQUITY": 0.01})
        self.assertLessEqual(out["CRYPTO"], MAX_CLASS_BUDGET + 1e-9)
        self.assertGreaterEqual(out["EQUITY"], MIN_CLASS_BUDGET - 1e-9)

    def test_higher_sharpe_gets_higher_weight(self):
        out = rebalance_by_sharpe({"CRYPTO": 2.0, "EQUITY": 0.5, "FOREX": 0.5})
        self.assertGreater(out["CRYPTO"], out["EQUITY"])


class PerClassRiskTests(unittest.TestCase):
    def test_empty_weights_returns_base(self):
        self.assertEqual(per_class_risk(0.02, "CRYPTO", {}), 0.02)

    def test_overweight_class_gets_more_risk(self):
        weights = {"CRYPTO": 0.40, "EQUITY": 0.10, "FOREX": 0.10,
                   "COMMODITY": 0.10, "ETF": 0.10, "FUTURES": 0.20}
        crypto_risk = per_class_risk(0.02, "CRYPTO", weights)
        equity_risk = per_class_risk(0.02, "EQUITY", weights)
        self.assertGreater(crypto_risk, equity_risk)

    def test_clipped_to_max_2x(self):
        weights = {"CRYPTO": 0.99, "EQUITY": 0.01}
        risk = per_class_risk(0.02, "CRYPTO", weights)
        self.assertLessEqual(risk, 0.02 * 2.0 + 1e-9)

    def test_clipped_to_min_quarter(self):
        weights = {"CRYPTO": 0.99, "EQUITY": 0.01}
        risk = per_class_risk(0.02, "EQUITY", weights)
        self.assertGreaterEqual(risk, 0.02 * 0.25 - 1e-9)

    def test_unknown_class_uses_equal_weight(self):
        weights = {"CRYPTO": 0.5, "EQUITY": 0.5}
        risk = per_class_risk(0.02, "UNKNOWN", weights)
        # eq=0.5 → scalar=1 → base risk
        self.assertAlmostEqual(risk, 0.02, places=6)


if __name__ == "__main__":
    unittest.main()
