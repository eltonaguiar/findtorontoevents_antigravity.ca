"""Tests for alpha_engine.anti_overfit_validator.

Covers all three public functions with synthetic non-overfit and overfit
fixtures, plus the multiple-testing penalty for DSR. Designed to be cheap
(seconds, not minutes) so the suite can run on every CI cycle.
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from alpha_engine.anti_overfit_validator import (
    cpcv_pbo,
    deflated_sharpe,
    reality_check_pvalue,
)

RNG_SEED = 7


# ---------------------------------------------------------------------------
# CPCV / PBO
# ---------------------------------------------------------------------------
def test_cpcv_pbo_low_on_consistent_oos_edge():
    """One strategy with persistent positive drift -> PBO well below 0.5.

    The IS-best is always strategy 0 because it has a stable mean; OOS rank
    of strategy 0 stays near the top, so the logit fraction below zero is
    small.
    """
    rng = np.random.default_rng(RNG_SEED)
    T, S = 600, 10
    M = rng.normal(0.0, 0.01, size=(T, S))
    # Strategy 0 has true positive Sharpe; rest are noise
    M[:, 0] += 0.0025
    pbo = cpcv_pbo(M, n_folds=8, n_test_groups=2)
    assert 0.0 <= pbo <= 1.0
    assert pbo < 0.5, f"expected PBO < 0.5 on real-edge fixture, got {pbo:.3f}"


def test_cpcv_pbo_higher_on_noise_than_on_real_edge():
    """Pure-noise PBO must exceed real-edge PBO at the same fold count.

    Absolute thresholds depend on (T, S, n_folds) and are noisy at small
    sample sizes; the load-bearing assertion is the *relative* gap. The
    real-edge fixture (one strategy with persistent positive drift) should
    push PBO toward zero while pure noise lingers near 0.5.
    """
    n_folds = 8
    rng = np.random.default_rng(RNG_SEED + 1)
    T, S = 400, 20
    M_noise = rng.normal(0.0, 0.01, size=(T, S))
    pbo_noise = cpcv_pbo(M_noise, n_folds=n_folds, n_test_groups=2)
    assert 0.0 <= pbo_noise <= 1.0

    rng2 = np.random.default_rng(RNG_SEED + 100)
    M_edge = rng2.normal(0.0, 0.01, size=(T, S))
    M_edge[:, 0] += 0.0025
    pbo_edge = cpcv_pbo(M_edge, n_folds=n_folds, n_test_groups=2)
    assert pbo_edge < pbo_noise, (
        f"expected PBO_noise > PBO_edge, got noise={pbo_noise:.3f} "
        f"edge={pbo_edge:.3f}"
    )
    # Sanity floor: noise PBO must not collapse to zero (would imply our
    # logic is identical to real-edge case).
    assert pbo_noise > 0.20, f"noise PBO suspiciously low: {pbo_noise:.3f}"


# ---------------------------------------------------------------------------
# Reality Check / SPA
# ---------------------------------------------------------------------------
arch = pytest.importorskip("arch", reason="arch package not installed; pip install arch")


def test_reality_check_high_pvalue_on_noise():
    """Pure-noise returns vs zero benchmark -> p-value not significant."""
    rng = np.random.default_rng(RNG_SEED + 2)
    r = rng.normal(0.0, 0.01, size=400)
    p = reality_check_pvalue(r, benchmark=0.0, B=500, block_size=10)
    assert 0.0 <= p <= 1.0
    assert p > 0.10, f"expected non-significant p > 0.10 on noise, got {p:.3f}"


def test_reality_check_low_pvalue_on_real_edge():
    """Returns with material positive drift -> p-value below 0.05."""
    rng = np.random.default_rng(RNG_SEED + 3)
    # Strong daily drift relative to vol so SPA can detect it with B=500
    r = rng.normal(0.003, 0.01, size=400)
    p = reality_check_pvalue(r, benchmark=0.0, B=500, block_size=10)
    assert p < 0.05, f"expected p < 0.05 on real-edge fixture, got {p:.3f}"


# ---------------------------------------------------------------------------
# Deflated Sharpe
# ---------------------------------------------------------------------------
def test_deflated_sharpe_decreases_with_n_trials():
    """DSR strictly decreases as n_trials grows for the same headline SR."""
    rng = np.random.default_rng(RNG_SEED + 4)
    r = rng.normal(0.001, 0.01, size=300)
    sr = float(r.mean() / r.std(ddof=1))
    dsr_1 = deflated_sharpe(sr, n_trials=1, returns_array=r)
    dsr_100 = deflated_sharpe(sr, n_trials=100, returns_array=r)
    dsr_10000 = deflated_sharpe(sr, n_trials=10_000, returns_array=r)
    assert dsr_1 >= dsr_100 >= dsr_10000
    assert dsr_10000 < dsr_1, (
        f"DSR penalty should bite at large n_trials: "
        f"dsr_1={dsr_1:.3f} dsr_10000={dsr_10000:.3f}"
    )


def test_deflated_sharpe_genuine_edge_passes():
    """A clearly-significant Sharpe on a long history passes DSR even at n=200."""
    rng = np.random.default_rng(RNG_SEED + 5)
    # Daily mean 0.002, vol 0.01 -> per-period SR ~= 0.2 -> annualized ~3.2
    r = rng.normal(0.002, 0.01, size=750)
    sr = float(r.mean() / r.std(ddof=1) * math.sqrt(252))
    dsr = deflated_sharpe(sr, n_trials=200, returns_array=r)
    assert dsr > 0.95, f"expected DSR > 0.95 on genuine edge, got {dsr:.3f}"


def test_deflated_sharpe_input_validation():
    with pytest.raises(ValueError):
        deflated_sharpe(1.0, n_trials=0, returns_array=np.zeros(10))
    with pytest.raises(ValueError):
        deflated_sharpe(1.0, n_trials=10, returns_array=np.zeros(3))


def test_cpcv_pbo_input_validation():
    rng = np.random.default_rng(0)
    with pytest.raises(ValueError):
        cpcv_pbo(rng.normal(size=100), n_folds=5)  # 1-D
    with pytest.raises(ValueError):
        cpcv_pbo(rng.normal(size=(100, 1)), n_folds=5)  # only 1 strategy
