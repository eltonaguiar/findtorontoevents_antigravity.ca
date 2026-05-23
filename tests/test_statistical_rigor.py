"""Smoke tests for alpha_engine.statistical_rigor."""
from __future__ import annotations

import math

import pytest

from alpha_engine.statistical_rigor import (
    audit_metrics_block,
    benjamini_hochberg,
    bootstrap_ci,
    probabilistic_sharpe_ratio,
    profit_factor,
    sharpe,
    win_rate,
)


def test_profit_factor_basic():
    assert profit_factor([0.02, -0.01, 0.03, -0.02]) == pytest.approx(5 / 3)
    assert profit_factor([]) == 0.0
    assert profit_factor([0.01, 0.02]) == float("inf")
    assert profit_factor([-0.01, -0.02]) == 0.0


def test_win_rate():
    assert win_rate([0.1, -0.1, 0.1, -0.1]) == 0.5
    assert win_rate([]) == 0.0
    assert win_rate([0.0, 0.0]) == 0.0  # zero is not a "win"


def test_sharpe_zero_variance():
    assert sharpe([0.01, 0.01, 0.01]) == 0.0
    assert sharpe([0.01]) == 0.0  # singleton


def test_bootstrap_ci_reproducible():
    rng = [0.01, -0.005, 0.02, -0.01, 0.015, -0.008, 0.012, -0.004]
    a = bootstrap_ci(rng, profit_factor, n_resamples=200, seed=7)
    b = bootstrap_ci(rng, profit_factor, n_resamples=200, seed=7)
    assert a == b
    point, lo, hi = a
    assert math.isfinite(lo)
    assert math.isfinite(hi)
    assert lo <= point <= hi or math.isclose(lo, point) or math.isclose(hi, point)


def test_bootstrap_ci_thin_input_returns_nan():
    point, lo, hi = bootstrap_ci([0.01], profit_factor)
    assert math.isnan(lo)
    assert math.isnan(hi)


def test_benjamini_hochberg_no_rejections():
    # Uniform high p-values — none should pass at 5% FDR
    assert benjamini_hochberg([0.9, 0.8, 0.7], fdr=0.05) == [False, False, False]


def test_benjamini_hochberg_all_significant():
    assert benjamini_hochberg([0.001, 0.002, 0.003], fdr=0.05) == [True, True, True]


def test_benjamini_hochberg_partial():
    # p-values where the smallest pass, the largest don't
    pvals = [0.001, 0.04, 0.5]
    out = benjamini_hochberg(pvals, fdr=0.05)
    assert out[0] is True
    assert out[2] is False


def test_psr_returns_probability():
    # Positive-mean series should give PSR > 0.5 vs benchmark 0
    rng = [0.01, 0.012, -0.005, 0.015, 0.008, -0.003, 0.011, 0.009, -0.004, 0.013]
    p = probabilistic_sharpe_ratio(rng, sharpe_benchmark=0.0)
    assert 0.0 <= p <= 1.0
    assert p > 0.5
    # Thin input returns 0.5 (no info)
    assert probabilistic_sharpe_ratio([0.01], 0.0) == 0.5


def test_audit_metrics_block_shape():
    rng = [0.01, -0.005, 0.02, -0.01, 0.015, -0.008, 0.012, -0.004] * 5
    block = audit_metrics_block(rng, n_resamples=100, seed=11)
    assert block["n"] == len(rng)
    for k in ("profit_factor", "win_rate", "sharpe"):
        assert {"point", "lo", "hi"} <= block[k].keys()
    assert 0.0 <= block["psr_vs_zero"] <= 1.0
