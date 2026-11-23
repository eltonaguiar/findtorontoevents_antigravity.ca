"""Tests for tools/effective_trials.py.

The finding this tool produces is a NEAR-ZERO effect: at mean pairwise correlation 0.19,
correlation narrows the max-statistic null by only ~1.5%, so the effective trial count for
a maximum is ~34 rather than ~5. A near-zero result is only believable if the measurement
can detect a large effect, so the central test here is a POWER test: on a synthetic family
with correlation 0.9 the same code must show a large narrowing. Without that, "correlation
barely matters" is indistinguishable from "the comparison is broken".

Also covered: the correlation estimators agree with known closed forms on equicorrelated
data (where the answer can be computed by hand), and the order-statistic solver inverts its
own generator.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from effective_trials import (  # noqa: E402
    c95_max_of_n, max_t_independent, max_t_joint, neff_correlation,
    solve_neff_max,
)


def _equicorr_matrix(T: int, N: int, rho: float, mu: float = 0.0,
                     seed: int = 0) -> np.ndarray:
    """Zero-(or mu-)mean returns with exactly the requested equicorrelation."""
    rng = np.random.default_rng(seed)
    common = rng.standard_normal((T, 1))
    idio = rng.standard_normal((T, N))
    return mu + np.sqrt(rho) * common + np.sqrt(1.0 - rho) * idio


# ---------------------------------------------------------- power of the measurement
def test_high_correlation_visibly_narrows_the_max_tail():
    """Power test: at rho=0.9 the max null MUST narrow a lot, or the tool measures nothing."""
    M = _equicorr_matrix(1200, 20, 0.9)
    M = M - M.mean(axis=0, keepdims=True)
    joint = max_t_joint(M, B=400, seed=3)
    indep = max_t_independent(M, B=400, seed=3)
    h_j = float(np.percentile(joint, 95))
    h_i = float(np.percentile(indep, 95))
    narrowing = 1.0 - h_j / h_i
    assert narrowing > 0.15, (
        f"rho=0.9 narrowed the max tail by only {narrowing:.1%} "
        f"({h_i:.3f} -> {h_j:.3f}); the measurement cannot see correlation")


def test_mild_correlation_barely_narrows_the_max_tail():
    """The actual finding: at rho=0.19 the effect is small. Pinned so it cannot drift."""
    M = _equicorr_matrix(2000, 20, 0.19)
    M = M - M.mean(axis=0, keepdims=True)
    joint = max_t_joint(M, B=400, seed=3)
    indep = max_t_independent(M, B=400, seed=3)
    narrowing = 1.0 - float(np.percentile(joint, 95)) / float(np.percentile(indep, 95))
    assert abs(narrowing) < 0.12, f"rho=0.19 narrowed by {narrowing:.1%}, expected small"


def test_independent_bootstrap_matches_the_order_statistic():
    """The sanity anchor: independent null p95 must look like max of N standard normals."""
    M = _equicorr_matrix(1500, 15, 0.0)
    M = M - M.mean(axis=0, keepdims=True)
    h_i = float(np.percentile(max_t_independent(M, B=400, seed=5), 95))
    assert abs(h_i - c95_max_of_n(15)) < 0.25, (h_i, c95_max_of_n(15))


# ---------------------------------------------------------- estimators and solver
def test_estimators_recover_the_planted_equicorrelation():
    N, rho = 12, 0.5
    M = _equicorr_matrix(4000, N, rho, seed=11)
    est = neff_correlation(np.corrcoef(M, rowvar=False))
    assert abs(est["mean_pairwise_corr"] - rho) < 0.05
    # closed form for equicorrelation: N / (1 + (N-1) rho)
    expected = N / (1 + (N - 1) * rho)
    assert abs(est["neff_equicorrelation"] - expected) < 0.6
    assert abs(est["neff_variance_of_sum"] - expected) < 0.6


def test_independent_columns_give_neff_equal_to_n():
    rng = np.random.default_rng(2)
    M = rng.standard_normal((3000, 10))
    est = neff_correlation(np.corrcoef(M, rowvar=False))
    assert abs(est["neff_equicorrelation"] - 10) < 1.0
    assert abs(est["mean_pairwise_corr"]) < 0.05


def test_solve_neff_max_inverts_the_order_statistic():
    for N in (2, 5, 12, 30):
        solved = solve_neff_max(c95_max_of_n(N))
        assert solved == N, f"target from N={N} solved to {solved}"


def test_c95_increases_with_n():
    vals = [c95_max_of_n(n) for n in (1, 5, 20, 50)]
    assert all(b > a for a, b in zip(vals, vals[1:])), vals
