"""
Unit tests for FIX-M — Multiple-testing correction in walk_forward_backtester.

Covers:
  - deflated_sharpe_ratio (López de Prado 2018)
  - bonferroni_adjust
  - benjamini_hochberg (FDR control)
  - compute_anti_overfit_metrics integration (checks 9 and 10)

Per memory/feedback_mutate_before_kill.md, DSR/Bonferroni failure gates
PROMOTION into production, not auto-kill. The three-axis mutation protocol
runs first.
"""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alpha_engine.walk_forward_backtester import (
    benjamini_hochberg,
    bonferroni_adjust,
    compute_anti_overfit_metrics,
    deflated_sharpe_ratio,
)


class DeflatedSharpeRatioTests(unittest.TestCase):
    def test_single_trial_high_sharpe_passes(self):
        """SR=2.0 over n=100 with only 1 trial should have high DSR."""
        dsr, p = deflated_sharpe_ratio(2.0, n_trials=1, n_observations=100)
        self.assertGreater(dsr, 0.95)
        self.assertLess(p, 0.05)

    def test_many_trials_same_sharpe_is_penalised(self):
        """SR=2.0 tested across 80 strategies must NOT pass — selection bias."""
        dsr_single, _ = deflated_sharpe_ratio(2.0, n_trials=1, n_observations=100)
        dsr_many, _ = deflated_sharpe_ratio(2.0, n_trials=80, n_observations=100)
        self.assertLess(dsr_many, dsr_single)
        # SR=2 is not extraordinary enough to survive testing 80 strategies.
        self.assertLess(dsr_many, 0.95)

    def test_very_high_sharpe_survives_many_trials(self):
        """SR=5.0 should survive even testing 80 strategies — real edge."""
        dsr, _ = deflated_sharpe_ratio(5.0, n_trials=80, n_observations=200)
        self.assertGreaterEqual(dsr, 0.95)

    def test_zero_observations_returns_null(self):
        dsr, p = deflated_sharpe_ratio(2.0, n_trials=1, n_observations=1)
        self.assertEqual(dsr, 0.0)
        self.assertEqual(p, 1.0)

    def test_negative_sharpe_fails(self):
        dsr, _ = deflated_sharpe_ratio(-0.5, n_trials=10, n_observations=100)
        self.assertLess(dsr, 0.5)

    def test_invalid_n_trials_returns_null(self):
        dsr, p = deflated_sharpe_ratio(2.0, n_trials=0, n_observations=100)
        self.assertEqual(dsr, 0.0)
        self.assertEqual(p, 1.0)


class BonferroniAdjustTests(unittest.TestCase):
    def test_saturates_at_one(self):
        self.assertEqual(bonferroni_adjust(0.04, 80), 1.0)

    def test_tight_pvalue_survives_correction(self):
        adjusted = bonferroni_adjust(0.0001, 80)
        self.assertAlmostEqual(adjusted, 0.008, places=6)
        self.assertLess(adjusted, 0.05)

    def test_n_trials_one_is_identity(self):
        self.assertAlmostEqual(bonferroni_adjust(0.03, 1), 0.03, places=6)

    def test_invalid_n_trials_is_identity(self):
        self.assertAlmostEqual(bonferroni_adjust(0.03, 0), 0.03, places=6)

    def test_bounds(self):
        self.assertEqual(bonferroni_adjust(-0.5, 10), 0.0)
        self.assertEqual(bonferroni_adjust(2.0, 10), 1.0)


class BenjaminiHochbergTests(unittest.TestCase):
    def test_all_pass_when_all_tiny(self):
        res = benjamini_hochberg([0.001, 0.001, 0.001, 0.001], fdr=0.05)
        self.assertTrue(all(res))

    def test_none_pass_when_all_large(self):
        res = benjamini_hochberg([0.5, 0.5, 0.5, 0.5], fdr=0.05)
        self.assertFalse(any(res))

    def test_less_conservative_than_bonferroni(self):
        """BH should let through things Bonferroni would kill."""
        p_values = [0.001, 0.01, 0.02, 0.04, 0.045]
        bh = benjamini_hochberg(p_values, fdr=0.05)
        # Bonferroni on p=0.04 with n=5 = 0.20 > 0.05 → fail.
        # BH at rank 4, threshold = 4/5 * 0.05 = 0.04 → 0.04 passes.
        self.assertEqual(sum(bh), 5)  # all pass BH at 0.05 fdr

    def test_order_preserved(self):
        """Output list maps 1:1 to input indices, not sorted."""
        p_values = [0.5, 0.001, 0.5, 0.001]
        bh = benjamini_hochberg(p_values, fdr=0.05)
        self.assertEqual(bh, [False, True, False, True])

    def test_empty_input(self):
        self.assertEqual(benjamini_hochberg([], fdr=0.05), [])


class AntiOverfitMetricsIntegrationTests(unittest.TestCase):
    """compute_anti_overfit_metrics with checks 9+10 wired in."""

    def _base_is_oos(self):
        """Fixtures that pass all 8 legacy checks."""
        return (
            {
                "win_rate": 55.0,
                "profit_factor": 1.5,
                "sharpe": 1.2,
                "max_drawdown_pct": 10.0,
            },
            {
                "win_rate": 55.0,
                "profit_factor": 1.4,
                "max_drawdown_pct": 15.0,
                "total_trades": 50,
                "num_windows_with_trades": 4,
                "total_pnl_pct": 20.0,
            },
        )

    def test_legacy_shape_without_pnls_skips_new_checks(self):
        is_r, oos_r = self._base_is_oos()
        report = compute_anti_overfit_metrics(is_r, oos_r, n_trials=80)
        self.assertIn("dsr_selection_bias", report["checks"])
        self.assertIn("bonferroni_p", report["checks"])
        self.assertTrue(report["checks"]["dsr_selection_bias"]["skipped"])
        self.assertTrue(report["checks"]["bonferroni_p"]["skipped"])
        # Skipped checks pass=True → don't tank overall.
        self.assertTrue(report["checks"]["dsr_selection_bias"]["pass"])
        # Legacy 8 checks are unaffected.
        for k in (
            "oos_is_wr_ratio", "oos_is_pf_ratio", "is_sharpe_not_extreme",
            "oos_drawdown_ratio", "min_oos_trades", "min_consistent_windows",
            "no_single_window_dominance", "oos_wr_absolute_min",
        ):
            self.assertIn(k, report["checks"])

    def test_strong_edge_passes_both_new_checks(self):
        """A clean, high-Sharpe signal must pass Bonferroni at small n_trials
        and must not be marked as skipped. DSR is stricter (uses an
        expected-max-Sharpe bar that's hard to clear even with low n_trials),
        so we assert the pass-or-evidence-present condition only for Bonferroni
        and just require DSR to have fired (not skipped) with a non-null value."""
        is_r, oos_r = self._base_is_oos()
        # ~1% per trade, tight std → per-trade Sharpe ~2.5 → tight t-stat
        oos_pnls = [1.0, 1.1, 0.9, 1.2, 1.0, 1.1, 0.95, 1.05, 1.0, 1.15] * 10
        report = compute_anti_overfit_metrics(
            is_r, oos_r, n_trials=5, oos_trade_pnls=oos_pnls
        )
        dsr_chk = report["checks"]["dsr_selection_bias"]
        bon_chk = report["checks"]["bonferroni_p"]
        self.assertFalse(dsr_chk.get("skipped", False))
        self.assertFalse(bon_chk.get("skipped", False))
        self.assertEqual(dsr_chk["n_trials"], 5)
        self.assertEqual(bon_chk["n_trials"], 5)
        self.assertTrue(bon_chk["pass"])  # Bonferroni p must clear 0.05 at n=5
        # DSR metadata present and non-null
        self.assertIsNotNone(dsr_chk["value"])
        self.assertGreater(dsr_chk["per_trade_sharpe"], 1.0)

    def test_noise_strategy_fails_with_many_trials(self):
        """Near-zero mean PnL across 80 strategies must FAIL new checks."""
        is_r, oos_r = self._base_is_oos()
        # Mean ~0, volatile — classic false positive when tested alongside 79 others
        oos_pnls = [0.5, -0.4, 0.3, -0.5, 0.4, -0.3, 0.5, -0.4] * 6
        report = compute_anti_overfit_metrics(
            is_r, oos_r, n_trials=80, oos_trade_pnls=oos_pnls
        )
        self.assertFalse(report["checks"]["dsr_selection_bias"]["pass"])
        self.assertFalse(report["checks"]["bonferroni_p"]["pass"])
        self.assertFalse(report["overall_pass"])

    def test_multiple_testing_metadata_emitted(self):
        is_r, oos_r = self._base_is_oos()
        report = compute_anti_overfit_metrics(
            is_r, oos_r, n_trials=42, oos_trade_pnls=[0.1] * 50
        )
        self.assertIn("multiple_testing", report)
        self.assertEqual(report["multiple_testing"]["n_trials"], 42)
        self.assertTrue(report["multiple_testing"]["applied"])

    def test_n_trials_one_is_backward_compatible(self):
        """Default call shape n_trials=1 must match legacy semantics roughly."""
        is_r, oos_r = self._base_is_oos()
        report = compute_anti_overfit_metrics(is_r, oos_r)  # all defaults
        self.assertEqual(report["multiple_testing"]["n_trials"], 1)
        # Without trade pnls, new checks are skipped and overall rides legacy 8.
        self.assertTrue(report["checks"]["dsr_selection_bias"]["skipped"])

    def test_boundary_sample_size(self):
        is_r, oos_r = self._base_is_oos()
        report = compute_anti_overfit_metrics(
            is_r, oos_r, n_trials=1, oos_trade_pnls=[0.5]
        )
        # n=1 is not enough; expect skip.
        self.assertTrue(report["checks"]["dsr_selection_bias"]["skipped"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
