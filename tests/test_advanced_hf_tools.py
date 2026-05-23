"""Unit tests for 5 advanced hedge-fund tools:
    tools/hurst_regime.py
    tools/cusum_filter.py
    tools/hyrotrader_risk_sizer.py
    tools/hrp_allocator.py
    tools/mtf_ensemble.py
"""
import math
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.hurst_regime import hurst_exponent, classify_regime, strategy_regime_match  # noqa
from tools.cusum_filter import log_returns, cusum_events, suggest_threshold, sampling_reduction_rate  # noqa
from tools.hyrotrader_risk_sizer import kelly_fraction, size_pick  # noqa
from tools.hrp_allocator import (  # noqa
    correlation_matrix, compute_hrp_weights, compare_to_naive_inverse_vol,
)
from tools.mtf_ensemble import (  # noqa
    signal_from_fields, equal_weight_ensemble, performance_weighted_ensemble,
    inverse_noise_weights, passes_mtf_threshold,
)


# ============ HURST REGIME ============
# Note: Hurst R/S analysis is defined on returns/increments, not price levels.
# A price series is non-stationary and always produces H near 1.0.

def _trending_returns(n=512, drift=0.05, noise=0.3, seed=1):
    """Strong autocorrelated positive drift in returns => H > 0.55."""
    rng = random.Random(seed)
    out = []
    prev = 0.0
    for _ in range(n):
        # AR(1) process with positive autocorr + drift
        prev = 0.6 * prev + drift + rng.gauss(0, noise)
        out.append(prev)
    return out


def _iid_returns(n=512, sigma=1.0, seed=2):
    """I.I.D. Gaussian returns => H ~= 0.5."""
    rng = random.Random(seed)
    return [rng.gauss(0, sigma) for _ in range(n)]


def _mean_reverting_returns(n=512, seed=3):
    """Anti-persistent / oscillating returns => H < 0.45."""
    rng = random.Random(seed)
    out = []
    prev = 0.0
    for _ in range(n):
        # Negative autocorr: each return tends to oppose prior
        prev = -0.6 * prev + rng.gauss(0, 1.0)
        out.append(prev)
    return out


class HurstRegimeTests(unittest.TestCase):
    def test_trending_detected(self):
        H = hurst_exponent(_trending_returns())
        self.assertGreater(H, 0.55)

    def test_mean_reverting_detected(self):
        H = hurst_exponent(_mean_reverting_returns())
        self.assertLess(H, 0.45)

    def test_random_walk_near_half(self):
        H = hurst_exponent(_iid_returns())
        self.assertGreater(H, 0.35)
        self.assertLess(H, 0.65)

    def test_classify_regime_shape(self):
        r = classify_regime(_trending_returns())
        self.assertEqual(r["regime"], "TRENDING")
        self.assertIn("hurst", r)
        self.assertIn("confidence", r)

    def test_mean_rev_strategy_blocked_in_trending(self):
        self.assertFalse(strategy_regime_match("rsi2_mean_reversion", "TRENDING"))

    def test_trend_strategy_blocked_in_mean_reverting(self):
        self.assertFalse(strategy_regime_match("futures_momentum", "MEAN_REVERTING"))

    def test_random_walk_allows_both(self):
        self.assertTrue(strategy_regime_match("rsi2_mean_reversion", "RANDOM_WALK"))
        self.assertTrue(strategy_regime_match("futures_momentum", "RANDOM_WALK"))


# ============ CUSUM FILTER ============

class CUSUMFilterTests(unittest.TestCase):
    def test_no_events_on_tiny_threshold(self):
        rets = [0.001, 0.001, 0.001]
        events = cusum_events(rets, threshold=100.0)
        self.assertEqual(events, [])

    def test_up_events_on_positive_drift(self):
        rets = [0.02, 0.02, 0.02, 0.02, 0.02]
        events = cusum_events(rets, threshold=0.04)
        self.assertTrue(any(e["direction"] == "UP" for e in events))

    def test_down_events_on_negative_drift(self):
        rets = [-0.02, -0.02, -0.02, -0.02]
        events = cusum_events(rets, threshold=0.04)
        self.assertTrue(any(e["direction"] == "DOWN" for e in events))

    def test_log_returns_basic(self):
        rets = log_returns([100.0, 110.0, 110.0, 99.0])
        self.assertAlmostEqual(rets[0], math.log(1.1), places=4)

    def test_suggest_threshold(self):
        rets = [0.01, -0.01, 0.02, -0.02, 0.005]
        t = suggest_threshold(rets, k=2.0)
        self.assertGreater(t, 0)

    def test_reduction_rate(self):
        self.assertAlmostEqual(sampling_reduction_rate(100, 5), 0.95)


# ============ HYROTRADER RISK-SIZER ============

class HyroSizerTests(unittest.TestCase):
    def test_kelly_basic(self):
        # WR 60%, avg_win 2, avg_loss 1 → strongly positive edge
        k = kelly_fraction(0.60, 2.0, 1.0)
        self.assertGreater(k, 0.0)

    def test_kelly_negative_edge_zero(self):
        # WR 40%, avg_win 1, avg_loss 1 → negative edge
        k = kelly_fraction(0.40, 1.0, 1.0)
        self.assertEqual(k, 0.0)

    def test_daily_soft_stop_rejects(self):
        p = dict(entry_price=100, stop_loss=99, risk_reward=2.5, direction="LONG",
                 asset_class="CRYPTO")
        out = size_pick(p, account_balance=5000, todays_realized_pnl_pct=-3.0)
        self.assertFalse(out["passed"])
        self.assertTrue(any("daily_soft_stop" in r for r in out["reject_reasons"]))

    def test_rr_below_floor_rejects(self):
        p = dict(entry_price=100, stop_loss=99, risk_reward=1.5, direction="LONG",
                 asset_class="CRYPTO")
        out = size_pick(p, account_balance=5000)
        self.assertFalse(out["passed"])

    def test_crypto_cap_applied(self):
        # Strong edge with tight stop should hit crypto cap 0.75%
        p = dict(entry_price=100, stop_loss=99.5, risk_reward=3.0, direction="LONG",
                 asset_class="CRYPTO")
        out = size_pick(p, account_balance=5000, target_risk_pct=5.0)
        # Class cap for CRYPTO is 0.75%
        self.assertLessEqual(out["risk_actual_pct"], 0.76)

    def test_hard_3pct_cap_never_exceeded(self):
        p = dict(entry_price=100, stop_loss=95, risk_reward=3.0, direction="LONG",
                 asset_class="BOND")
        out = size_pick(p, account_balance=5000, target_risk_pct=10.0)
        # Even with 10% target, should cap at 3%
        self.assertLessEqual(out["risk_actual_pct"], 3.01)


# ============ HRP ALLOCATOR ============

class HRPAllocatorTests(unittest.TestCase):
    def test_correlation_matrix_self_is_one(self):
        data = {"A": [1.0, 2.0, 3.0], "B": [3.0, 2.0, 1.0]}
        assets, m = correlation_matrix(data)
        self.assertEqual(m[0][0], 1.0)
        self.assertEqual(m[1][1], 1.0)

    def test_hrp_weights_sum_to_one(self):
        data = {
            "A": [1.0, -0.5, 2.0, 0.3, -0.1] * 4,
            "B": [0.1, 0.1, -0.05, 0.2, 0.0] * 4,
            "C": [2.0, -1.0, 3.0, 1.0, -0.5] * 4,
        }
        w = compute_hrp_weights(data)
        self.assertAlmostEqual(sum(w.values()), 1.0, places=3)
        for weight in w.values():
            self.assertGreaterEqual(weight, 0.0)
            self.assertLessEqual(weight, 1.0)

    def test_hrp_single_asset(self):
        data = {"A": [1.0, 2.0, 3.0]}
        w = compute_hrp_weights(data)
        self.assertEqual(w, {"A": 1.0})

    def test_compare_shape(self):
        data = {
            "A": [1.0, -0.5, 2.0] * 4,
            "B": [0.1, 0.1, -0.05] * 4,
        }
        out = compare_to_naive_inverse_vol(data)
        self.assertIn("naive_inverse_vol", out)
        self.assertIn("hrp", out)
        self.assertIn("delta", out)


# ============ MTF ENSEMBLE ============

class MTFEnsembleTests(unittest.TestCase):
    def test_signal_normalization_buy_to_long(self):
        s = signal_from_fields("BUY", 75, 0.8)
        self.assertEqual(s["direction"], "LONG")
        self.assertGreater(s["strength"], 0)

    def test_signal_normalization_sell_to_short(self):
        s = signal_from_fields("SELL", 75, 0.8)
        self.assertEqual(s["direction"], "SHORT")
        self.assertLess(s["strength"], 0)

    def test_equal_weight_all_long(self):
        signals = {
            "5m":  signal_from_fields("LONG", 70, 0.7),
            "1h":  signal_from_fields("LONG", 75, 0.8),
            "4h":  signal_from_fields("LONG", 80, 0.85),
        }
        e = equal_weight_ensemble(signals)
        self.assertEqual(e["direction"], "LONG")
        self.assertGreater(e["strength"], 0.3)
        self.assertAlmostEqual(e["agreement_pct"], 100.0)

    def test_equal_weight_mixed(self):
        signals = {
            "5m":  signal_from_fields("LONG", 70, 0.7),
            "1h":  signal_from_fields("SHORT", 75, 0.7),
            "4h":  signal_from_fields("LONG", 80, 0.85),
        }
        e = equal_weight_ensemble(signals)
        # 2 long, 1 short => agreement 2/3 = 66.7%
        self.assertAlmostEqual(e["agreement_pct"], 66.67, places=1)

    def test_performance_weighted_respects_weights(self):
        signals = {
            "5m":  signal_from_fields("LONG", 70, 0.7),    # will be downweighted
            "4h":  signal_from_fields("SHORT", 80, 0.9),   # heavy weight
        }
        weights = {"5m": 0.1, "4h": 0.9}
        e = performance_weighted_ensemble(signals, weights)
        self.assertEqual(e["direction"], "SHORT")

    def test_inverse_noise_weights(self):
        vols = {"5m": 0.02, "1h": 0.01, "4h": 0.005}
        w = inverse_noise_weights(vols)
        # Lower vol => higher weight
        self.assertGreater(w["4h"], w["1h"])
        self.assertGreater(w["1h"], w["5m"])
        self.assertAlmostEqual(sum(w.values()), 1.0, places=3)

    def test_gate_rejects_few_timeframes(self):
        e = {"direction": "LONG", "strength": 0.5, "agreement_pct": 100.0, "n_timeframes": 2}
        gate = passes_mtf_threshold(e, min_n_tf=3)
        self.assertFalse(gate["passed"])

    def test_gate_passes_strong_aligned(self):
        e = {"direction": "LONG", "strength": 0.5, "agreement_pct": 80.0, "n_timeframes": 4}
        gate = passes_mtf_threshold(e, min_strength=0.3, min_n_tf=3)
        self.assertTrue(gate["passed"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
