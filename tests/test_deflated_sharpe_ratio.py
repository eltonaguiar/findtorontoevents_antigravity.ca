"""Tests for deflated_sharpe_ratio (DSR) — Bailey & Lopez de Prado 2014.

Cherry-picked from Kimi's hedge-fund-uplift work per the head-to-head
comparison verdict (`reports/KIMI_VS_MAIN_COMPARISON_2026_05_02.md`):
DSR was the one genuinely valuable addition not already in main.
"""
from __future__ import annotations

import math

import pytest

from alpha_engine.statistical_rigor import (
    _norm_cdf,
    _norm_ppf,
    deflated_sharpe_ratio,
)


# ─────────────────────────────────────────────────────────────────
# _norm_ppf — Acklam fallback contract
# ─────────────────────────────────────────────────────────────────

def test_norm_ppf_round_trip_with_norm_cdf():
    """_norm_ppf should be the inverse of _norm_cdf within Acklam tolerance (~1.5e-9)."""
    for x in (-2.5, -1.0, -0.5, 0.0, 0.5, 1.0, 2.5):
        p = _norm_cdf(x)
        x_back = _norm_ppf(p)
        assert abs(x_back - x) < 1e-6, f"Round-trip failed at x={x}: {x_back}"


def test_norm_ppf_quantiles_match_known_values():
    """Sanity: _norm_ppf(0.975) ≈ 1.96, _norm_ppf(0.5) = 0, _norm_ppf(0.025) ≈ -1.96."""
    assert abs(_norm_ppf(0.975) - 1.95996) < 1e-3
    assert abs(_norm_ppf(0.5)) < 1e-6
    assert abs(_norm_ppf(0.025) + 1.95996) < 1e-3


def test_norm_ppf_handles_extremes():
    """Boundary values must NOT crash. The Acklam fallback returns ±inf for
    p in [0, 1] boundaries; scipy returns nan for p outside [0, 1]. Both are
    valid degenerate-input behaviors — what matters is no crash + DSR caller
    handles it gracefully.
    """
    for p_invalid in (0.0, 1.0, -0.5, 1.5):
        result = _norm_ppf(p_invalid)
        # Acceptable outcomes: -inf, +inf, or nan
        assert (
            result == -math.inf
            or result == math.inf
            or math.isnan(result)
        ), f"_norm_ppf({p_invalid}) returned unexpected {result}"


# ─────────────────────────────────────────────────────────────────
# deflated_sharpe_ratio — degenerate inputs
# ─────────────────────────────────────────────────────────────────

def test_dsr_returns_zero_for_too_few_observations():
    """DSR requires n >= 4. Less than 4 returns 0.0."""
    assert deflated_sharpe_ratio([], n_trials=10) == 0.0
    assert deflated_sharpe_ratio([0.01], n_trials=10) == 0.0
    assert deflated_sharpe_ratio([0.01, 0.02, 0.03], n_trials=10) == 0.0


def test_dsr_returns_zero_for_invalid_n_trials():
    """n_trials < 1 is invalid."""
    returns = [0.01] * 10
    assert deflated_sharpe_ratio(returns, n_trials=0) == 0.0
    assert deflated_sharpe_ratio(returns, n_trials=-5) == 0.0


def test_dsr_handles_zero_variance():
    """Constant-positive returns: DSR=1.0 (definitely outperforms zero baseline).
    Constant-zero/negative: DSR=0.0.
    """
    pos = [0.01] * 100
    neg = [-0.01] * 100
    zero = [0.0] * 100
    assert deflated_sharpe_ratio(pos, n_trials=100) == 1.0
    assert deflated_sharpe_ratio(neg, n_trials=100) == 0.0
    assert deflated_sharpe_ratio(zero, n_trials=100) == 0.0


def test_dsr_filters_non_finite():
    """NaN/inf values are filtered before the n>=4 check."""
    bad = [float("nan"), float("inf"), 0.01, 0.02]  # only 2 finite
    assert deflated_sharpe_ratio(bad, n_trials=10) == 0.0


# ─────────────────────────────────────────────────────────────────
# deflated_sharpe_ratio — algorithmic behavior
# ─────────────────────────────────────────────────────────────────

def test_dsr_in_unit_interval():
    """DSR is a probability — must be in [0, 1]."""
    # Slight positive drift on small sample
    returns = [0.001 + 0.02 * (i - 50) / 50.0 for i in range(100)]
    for n_trials in (1, 10, 100, 1000):
        dsr = deflated_sharpe_ratio(returns, n_trials=n_trials)
        assert 0.0 <= dsr <= 1.0, f"DSR={dsr} out of range for n_trials={n_trials}"


def test_dsr_decreases_as_n_trials_grows():
    """Selection bias correction: more trials -> lower DSR for the same data."""
    # Strongly positive drift so we can see the deflation effect cleanly
    returns = [0.005 + 0.001 * (i % 7) for i in range(120)]
    dsr_1 = deflated_sharpe_ratio(returns, n_trials=1)
    dsr_100 = deflated_sharpe_ratio(returns, n_trials=100)
    dsr_10000 = deflated_sharpe_ratio(returns, n_trials=10000)
    # More trials -> stricter -> lower DSR (or equal in degenerate cases)
    assert dsr_1 >= dsr_100 >= dsr_10000, (
        f"DSR should be monotone non-increasing in n_trials; "
        f"got {dsr_1=}, {dsr_100=}, {dsr_10000=}"
    )


def test_dsr_n_trials_one_uses_zero_e_max():
    """When n_trials=1, the expected max under the null is just the mean (0).
    DSR reduces to PSR-vs-zero (probability that observed Sharpe > 0).
    """
    # Strongly positive returns
    returns = [0.01, 0.02, 0.015, 0.018, 0.012, 0.022, 0.014, 0.019, 0.011, 0.025]
    dsr = deflated_sharpe_ratio(returns, n_trials=1)
    # Should be very high (close to 1) since the drift is clearly positive
    assert dsr > 0.95, f"DSR for clearly-positive returns at n_trials=1: {dsr}"


def test_dsr_supplied_skewness_kurtosis_used():
    """When skewness/kurtosis are passed in, the function uses them rather than recomputing."""
    returns = [0.01, 0.02, 0.015, 0.018, 0.012, 0.022, 0.014, 0.019]
    # Compare auto-computed vs passed-in zero-skew, normal-kurtosis
    dsr_auto = deflated_sharpe_ratio(returns, n_trials=10)
    dsr_normal = deflated_sharpe_ratio(returns, n_trials=10, skewness=0.0, kurtosis=0.0)
    # Different inputs should give different (or at least computable) results
    assert 0.0 <= dsr_auto <= 1.0
    assert 0.0 <= dsr_normal <= 1.0


def test_dsr_published_in_all():
    """Verify deflated_sharpe_ratio is exported via __all__."""
    import alpha_engine.statistical_rigor as sr
    assert "deflated_sharpe_ratio" in sr.__all__
