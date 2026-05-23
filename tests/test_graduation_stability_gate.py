"""Tests for the walk-forward stability gate added to graduation criteria
(2026-05-18) — a strategy must be net-positive in a majority of forward-test
sub-windows, not merely net-positive overall. Stops single-window luck from
graduating a no-edge strategy to live (reports/EDGE_VERDICT_2026-05-18.md).
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "incubator", "testing"))

from forward_test_tracker import StrategyGraduationCriteria  # noqa: E402

_BASE = dict(days_in_test=50, trades_count=60, win_rate=0.55,
             sharpe=1.4, max_drawdown=0.12, pnl_pct=8.0)


class StabilityGateTests(unittest.TestCase):
    def setUp(self):
        self.c = StrategyGraduationCriteria()

    def test_no_window_pnls_is_backward_compatible(self):
        # callers that do not supply window_pnls must still pass on good metrics
        passed, reasons = self.c.check(dict(_BASE))
        self.assertTrue(passed, reasons)

    def test_lucky_single_window_is_blocked(self):
        # +12% all from window 1, negative in the other 3 -> not durable
        passed, reasons = self.c.check({**_BASE, "window_pnls": [12.0, -1.5, -2.0, -0.5]})
        self.assertFalse(passed)
        self.assertTrue(any("unstable" in r for r in reasons))

    def test_stable_strategy_passes(self):
        # net-positive in 3 of 4 windows -> durable
        passed, reasons = self.c.check({**_BASE, "window_pnls": [3.0, 2.0, -0.5, 3.5]})
        self.assertTrue(passed, reasons)

    def test_all_windows_positive_passes(self):
        passed, reasons = self.c.check({**_BASE, "window_pnls": [1.0, 2.0, 1.5, 0.8]})
        self.assertTrue(passed, reasons)

    def test_too_few_windows_skips_gate(self):
        # fewer than n_stability_windows -> gate is skipped, not failed
        passed, reasons = self.c.check({**_BASE, "window_pnls": [5.0, -1.0]})
        self.assertTrue(passed, reasons)

    def test_exactly_at_threshold_passes(self):
        # 60% threshold: 3/5 windows positive == 0.60 -> passes (>=)
        passed, reasons = self.c.check({**_BASE, "window_pnls": [1.0, 1.0, 1.0, -1.0, -1.0]})
        self.assertTrue(passed, reasons)

    def test_just_below_threshold_blocked(self):
        # 2/5 = 0.40 < 0.60 -> blocked
        passed, reasons = self.c.check({**_BASE, "window_pnls": [1.0, 1.0, -1.0, -1.0, -1.0]})
        self.assertFalse(passed)


if __name__ == "__main__":
    unittest.main()
