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
# NOTE (2026-11-20): a module-level `pytest.importorskip("arch")` used to sit
# here, before these tests. `reality_check_pvalue` DOES require `arch` (it
# imports `arch.bootstrap.SPA` lazily inside the function), so the skip was
# well-intentioned -- but placing it at module level aborted collection of the
# ENTIRE file, including every DSR and PBO test above it, none of which touch
# `arch`. Result: the whole suite never ran without `arch`, which is how a test
# that ASSERTED the annualized-Sharpe bug survived unnoticed. The skip is now
# scoped to the two tests that actually need the dependency.
import pytest  # noqa: E402  (already imported above; kept explicit for clarity)


def test_reality_check_high_pvalue_on_noise():
    """Pure-noise returns vs zero benchmark -> p-value not significant."""
    pytest.importorskip("arch", reason="arch.bootstrap.SPA required")
    rng = np.random.default_rng(RNG_SEED + 2)
    r = rng.normal(0.0, 0.01, size=400)
    p = reality_check_pvalue(r, benchmark=0.0, B=500, block_size=10)
    assert 0.0 <= p <= 1.0
    assert p > 0.10, f"expected non-significant p > 0.10 on noise, got {p:.3f}"


def test_reality_check_low_pvalue_on_real_edge():
    """Returns with material positive drift -> p-value below 0.05."""
    pytest.importorskip("arch", reason="arch.bootstrap.SPA required")
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
    """A clearly-significant Sharpe on a long history passes DSR even at n=200.

    NOTE: ``deflated_sharpe`` requires a PER-PERIOD Sharpe. This test used to
    pass an annualized value (``* sqrt(252)``), which silently returned
    DSR ~= 1.0 for *any* input including pure noise -- it was asserting the
    bug (see reports/VALIDATION_LAYER_AUDIT_2026-11-20.md Defect A).
    """
    rng = np.random.default_rng(RNG_SEED + 5)
    # Daily mean 0.002, vol 0.01 -> per-period SR ~= 0.2 -> annualized ~3.2
    r = rng.normal(0.002, 0.01, size=750)
    sr_pp = float(r.mean() / r.std(ddof=1))
    dsr = deflated_sharpe(sr_pp, n_trials=200, returns_array=r)
    assert dsr > 0.95, f"expected DSR > 0.95 on genuine edge, got {dsr:.3f}"


def test_deflated_sharpe_rejects_annualized_input():
    """An annualized Sharpe must raise, not silently pass.

    Regression guard for Defect A: passing annualized SR on a zero-edge series
    used to return DSR 1.0000 (a PASS), where the correct per-period answer is
    ~0.03 (reject).
    """
    rng = np.random.default_rng(RNG_SEED + 6)
    # Give the series real per-period drift so the ANNUALIZED value clears the
    # 1.0 guard (a near-zero-mean series produces a tiny annualized SR that the
    # guard would correctly accept).
    r = rng.normal(0.0012, 0.01, size=500)
    sr_pp = float(r.mean() / r.std(ddof=1))
    sr_ann = sr_pp * math.sqrt(252)  # ~1.9 -> must be rejected
    assert abs(sr_ann) > 1.0, f"fixture must exceed the guard, got {sr_ann:.3f}"

    with pytest.raises(ValueError, match="annualized|PER-PERIOD"):
        deflated_sharpe(sr_ann, n_trials=100, returns_array=r)

    # ...but the explicit annualised=True path must convert, not raise.
    dsr_converted = deflated_sharpe(
        sr_ann, n_trials=100, returns_array=r,
        annualised=True, periods_per_year=252,
    )
    dsr_direct = deflated_sharpe(sr_pp, n_trials=100, returns_array=r)
    assert abs(dsr_converted - dsr_direct) < 1e-9, (
        f"annualised=True must reproduce the per-period path: "
        f"{dsr_converted:.6f} vs {dsr_direct:.6f}"
    )
    # No edge -> must not pass the gate.
    assert dsr_direct < 0.95, (
        f"zero-edge series must not pass DSR, got {dsr_direct:.4f}"
    )


def test_deflated_sharpe_rejects_low_annualized_input():
    """The subtler leak: a zero-edge series annualises to only ~0.5.

    An absolute ``|SR| > 1.0`` guard misses this entirely, yet the annualized
    value still pushes DSR to 1.0000. Detection must compare against the
    per-period Sharpe *implied by returns_array*, not a fixed magnitude.
    """
    rng = np.random.default_rng(RNG_SEED + 7)
    # Deterministic construction: force mu=0.0001, sd=0.01 so the per-period
    # Sharpe is exactly 0.01 and the annualized value is exactly 0.1587 -- far
    # below any absolute magnitude guard, yet still a unit error.
    base = rng.normal(0.0, 1.0, size=500)
    r = (base - base.mean()) / base.std(ddof=1) * 0.01 + 0.0001
    sr_pp = float(r.mean() / r.std(ddof=1))
    sr_ann = sr_pp * math.sqrt(252)
    assert abs(sr_pp - 0.01) < 1e-9, f"fixture drift, sr_pp={sr_pp}"
    assert abs(sr_ann) < 0.5, (
        f"fixture must stay well under any absolute guard to test the ratio "
        f"path, got annualised SR {sr_ann:.4f}"
    )

    with pytest.raises(ValueError, match="ANNUALIZED|annualized|per-period"):
        deflated_sharpe(sr_ann, n_trials=100, returns_array=r)

    # The correct per-period input must be accepted and must reject.
    dsr = deflated_sharpe(sr_pp, n_trials=100, returns_array=r)
    assert dsr < 0.95, f"zero-edge series must not pass DSR, got {dsr:.4f}"


def test_deflated_sharpe_accepts_legitimate_per_period_input():
    """No false positives: genuine per-period callers must not raise."""
    for offset in range(5):
        rng = np.random.default_rng(RNG_SEED + 20 + offset)
        r = rng.normal(0.0015, 0.01, size=600)
        sr_pp = float(r.mean() / r.std(ddof=1))
        dsr = deflated_sharpe(sr_pp, n_trials=50, returns_array=r)
        assert 0.0 <= dsr <= 1.0, f"DSR out of range: {dsr}"


def test_deflated_sharpe_accepts_large_per_period_sharpe():
    """A per-period Sharpe is NOT bounded by 1.0 -- do not reject on magnitude.

    Regression: the guard's absolute backstop fired on any ``|SR| > 1.0``,
    which misreported genuine per-period values as unit errors. On the live
    closed-pick ledger the worst source systems have per-period Sharpes of
    -1.20 to -3.68, so DSR came back nan for exactly the systems that most
    needed to fail visibly.

    The distinguishing property is not magnitude but *agreement with the value
    implied by returns_array*. Here the supplied value IS ``mu/sd``, so it must
    be accepted no matter how large.
    """
    rng = np.random.default_rng(RNG_SEED + 40)
    # Two-point distribution: 90% small win, 10% exact scratch. That shape
    # gives mu/sd = 3.0, which no absolute magnitude guard should reject.
    r = np.where(rng.random(400) < 0.9, 0.001, 0.0)
    sr_pp = float(r.mean() / r.std(ddof=1))
    assert abs(sr_pp) > 1.0, f"fixture must be large-magnitude, got {sr_pp}"

    dsr = deflated_sharpe(sr_pp, n_trials=50, returns_array=r)
    assert 0.0 <= dsr <= 1.0, f"DSR out of range: {dsr}"


def test_deflated_sharpe_still_rejects_annualized_even_when_large():
    """The ratio probe must keep working for high-magnitude annualized inputs.

    Guards against over-relaxing: a value that is sqrt(252)x the implied Sharpe
    is still a unit error even though it is also > 1.0.
    """
    rng = np.random.default_rng(RNG_SEED + 41)
    base = rng.normal(0.0, 1.0, size=400)
    base[:40] -= 12.0
    r = base * 0.001
    sr_pp = float(r.mean() / r.std(ddof=1))
    sr_ann = sr_pp * math.sqrt(252)

    with pytest.raises(ValueError, match="ANNUALIZED|annualized"):
        deflated_sharpe(sr_ann, n_trials=50, returns_array=r)


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
