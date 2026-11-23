#!/usr/bin/env python3
"""Tests for the paired-bootstrap β-hurdle (backlog D2-D7).

The properties that must never regress:
  * identical strategy and benchmark  -> CI contains 0, hurdle 2 FAILS
  * pure beta (long the benchmark)    -> hurdle 2 FAILS even when hurdle 1 passes
  * genuinely superior strategy       -> CI strictly positive, both hurdles PASS
  * inverted strategy                 -> CI strictly negative
  * wrong pairing                     -> raises rather than silently comparing
"""
from __future__ import annotations

import importlib.util
import random
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "pbs", ROOT / "tools" / "paired_bootstrap_vs_benchmark.py")
pbs = importlib.util.module_from_spec(_spec)
sys.modules["pbs"] = pbs
_spec.loader.exec_module(pbs)


def _series(n=500, mu=0.0, sd=0.01, seed=7):
    rng = random.Random(seed)
    return [rng.gauss(mu, sd) for _ in range(n)]


# ------------------------------------------------------------ D3: identical
def test_identical_series_ci_contains_zero():
    """A strategy that IS the benchmark has no signal. CI must contain 0."""
    b = _series()
    r = pbs.block_bootstrap_ci([x - x for x in b], n_boot=2000)
    assert r["mean_diff"] == 0.0
    assert r["ci_low"] <= 0.0 <= r["ci_high"]
    assert r["excludes_zero"] is False


def test_identical_series_fails_hurdle2():
    b = _series()
    g = pbs.two_hurdle_gate(b, b, n_boot=2000)
    assert g["hurdle2_signal_pass"] is False


# ------------------------------------------------------- D7: pure-beta trap
def test_pure_beta_passes_cash_hurdle_but_fails_signal_hurdle():
    """The exact failure mode freebuff's C-016 identified.

    Benchmark with a fat positive drift so hurdle 1 clears easily. A strategy
    that is nothing but the benchmark must still FAIL hurdle 2.
    """
    b = _series(mu=0.0010, sd=0.008, seed=11)   # ~ +25%/yr drift
    g = pbs.two_hurdle_gate(b, b, n_boot=2000)
    assert g["hurdle1_cash_pass"] is True, "fixture should clear the cash hurdle"
    assert g["hurdle2_signal_pass"] is False
    assert g["verdict"] == "BETA_ONLY_FAIL_HURDLE_2"


def test_scaled_beta_also_fails_signal_hurdle():
    """1.5x beta is still beta. No new information.

    THIS TEST FOUND A REAL DEFECT. With a raw paired difference, `s = 1.5*b`
    PASSED hurdle 2, because a leveraged index fund genuinely differs from the
    index. That is the beta trap in a new costume. The fix was to make hurdle 2 a
    BETA-ADJUSTED alpha (Jensen), which gives alpha = 0 for any pure scaling.
    """
    b = _series(mu=0.0010, sd=0.008, seed=12)
    s = [1.5 * x for x in b]
    g = pbs.two_hurdle_gate(s, b, n_boot=2000)
    assert abs(g["beta"] - 1.5) < 1e-9
    assert g["hurdle2_signal_pass"] is False, "scaled beta must not pass"
    # and the raw difference WOULD have passed -- this is why beta-adjustment exists
    assert g["raw_difference_ci"]["excludes_zero"] is True


def test_leverage_alpha_is_zero():
    b = _series(mu=0.0, sd=0.01, seed=13)
    for mult in (0.5, 1.0, 2.0, 3.0):
        s = [mult * x for x in b]
        a = pbs.beta_adjusted_alpha_ci(s, b, n_boot=1000)
        assert abs(a["beta"] - mult) < 1e-9
        assert abs(a["mean_diff"]) < 1e-12, f"{mult}x beta must have zero alpha"


# ------------------------------------------------------------ genuine alpha
def test_genuine_edge_passes_both_hurdles():
    b = _series(mu=0.0005, sd=0.010, seed=21)
    rng = random.Random(99)
    s = [x + 0.0012 + rng.gauss(0, 0.002) for x in b]  # +12bp/period alpha
    g = pbs.two_hurdle_gate(s, b, n_boot=2000)
    assert g["hurdle1_cash_pass"] is True
    assert g["hurdle2_signal_pass"] is True
    assert g["paired"]["ci_low"] > 0
    assert g["verdict"] == "PASS"


# -------------------------------------------------------------- D4: inverted
def test_inverted_strategy_ci_strictly_negative():
    """Inverting the benchmark is beta = -1 with ZERO alpha.

    Two distinct claims, and they must not be confused:
      * the RAW difference is strictly negative (you made less than the benchmark)
      * the BETA-ADJUSTED alpha is zero (you added no information)
    """
    # benchmark MUST have positive drift: inverting a zero-mean series leaves a
    # zero mean difference (-2b has mean -2*0 = 0), so the raw-difference
    # assertion would be vacuous. Drift must also be large enough that the CI
    # actually resolves: -2*0.0005 with sd 0.01 over 500 obs is only ~1.1 SE from
    # zero, so the CI straddles it and the assertion would be wrong, not the code.
    b = _series(mu=0.0020, sd=0.01, seed=31)
    s = [-x for x in b]
    g = pbs.two_hurdle_gate(s, b, n_boot=2000)
    assert g["raw_difference_ci"]["mean_diff"] < 0
    assert g["raw_difference_ci"]["ci_high"] < 0
    assert abs(g["beta"] + 1.0) < 1e-9, "inversion is beta = -1"
    assert abs(g["paired"]["mean_diff"]) < 1e-12, "and zero alpha"
    assert g["hurdle2_signal_pass"] is False


def test_detected_underperformance_is_one_sided():
    b = _series(mu=0.0, sd=0.01, seed=41)
    rng = random.Random(42)
    s = [x - 0.0010 + rng.gauss(0, 0.001) for x in b]
    r = pbs.block_bootstrap_ci([a - c for a, c in zip(s, b)], n_boot=2000)
    assert r["p_le_zero"] > 0.95, "clear underperformance should be near-certain"


# ------------------------------------------------------------- pairing guard
def test_unpaired_raises():
    with pytest.raises(ValueError):
        pbs.two_hurdle_gate(_series(100), _series(101))


def test_empty_raises():
    with pytest.raises(ValueError):
        pbs.block_bootstrap_ci([])


# --------------------------------------------------------------- determinism
def test_same_seed_same_ci():
    b = _series(seed=51)
    s = [x + 0.0005 for x in b]
    d = [a - c for a, c in zip(s, b)]
    r1 = pbs.block_bootstrap_ci(d, n_boot=1000, seed=5)
    r2 = pbs.block_bootstrap_ci(d, n_boot=1000, seed=5)
    assert r1 == r2


def test_block_size_bounded_by_series_length():
    r = pbs.block_bootstrap_ci([0.001, 0.002, 0.003], n_boot=100, block=50)
    assert r["block"] == 3


# ---------------------------------------------------------------- hurdle value
def test_hurdle_is_432bp_not_rounded():
    """4.32% exactly — a 4.31% result must not pass."""
    assert pbs.HURDLE_TBILL_APR == 0.0432
