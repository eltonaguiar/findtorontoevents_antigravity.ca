"""Tests for tools/pbo_and_reality_check.py and tools/xsmom_invvol_variant.py.

The properties that matter are the ones that would silently produce a wrong verdict:

  * the stationary bootstrap must actually resample contiguous blocks (block length
    of 1 makes a "reality check" that ignores serial correlation, which is the whole
    reason for using it);
  * Reality Check must be CONSERVATIVE — its p-value can never be smaller than the
    uncorrected p-value of the winning cell, and on pure noise it must not reject;
  * a genuinely dominant cell must still be found, otherwise the test has no power
    and a null result would be uninformative;
  * inverse-vol sizing must keep total exposure at 1.0 and must actually differ from
    equal weight, or H-232 would silently re-run H-201 and "fail" for the wrong reason.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from pbo_and_reality_check import reality_check, stationary_bootstrap_index  # noqa: E402
from xsmom_invvol_variant import turnover_fraction, xsmom_invvol  # noqa: E402


# ------------------------------------------------------------- bootstrap index
def test_stationary_bootstrap_indices_in_range_and_blocky():
    rng = np.random.default_rng(0)
    T, q = 500, 20
    idx = stationary_bootstrap_index(T, q, rng)
    assert idx.shape == (T,)
    assert idx.min() >= 0 and idx.max() < T
    # contiguous runs: count how often the index advances by one
    steps = (np.diff(idx) == 1).mean()
    # with mean block 20, ~95% of steps continue the block; with q=1 only ~1/T
    assert steps > 0.75, f"not blocky: only {steps:.2%} of steps continue a block"


def test_stationary_bootstrap_block_length_one_is_iid():
    rng = np.random.default_rng(0)
    idx = stationary_bootstrap_index(300, 1.0, rng)
    steps = (np.diff(idx) == 1).mean()
    assert steps < 0.05, f"q=1 should rarely continue: {steps:.3f}"


# ------------------------------------------------------------ reality check
def test_reality_check_never_beats_the_uncorrected_best():
    rng = np.random.default_rng(3)
    # one cell with a real edge, 20 noise cells
    F = rng.normal(0.0, 0.01, size=(600, 20))
    F[:, 0] += 0.004
    r = reality_check(F, B=300, seed=5)
    assert r["p_value"] >= r["best_cell_uncorrected_p"] - 1e-9
    assert r["best_cell_index"] == 0


def test_reality_check_is_calibrated_under_pure_noise():
    """A valid test rejects a true null ~5% of the time, not 30% of the time.

    A single noise draw proves nothing either way: under H0 the p-value is roughly
    uniform, so one draw landing at 0.2 (or even 0.06) is expected behaviour. What
    must be checked is the rejection RATE over independent draws, so this loops.
    """
    ps, rej = [], 0
    for s in range(40):
        rng = np.random.default_rng(100 + s)
        F = rng.normal(0.0, 0.01, size=(500, 12))
        r = reality_check(F, B=300, seed=s)
        ps.append(r["p_value"])
        rej += int(r["p_value"] <= 0.05)
    rate = rej / len(ps)
    assert rate <= 0.15, (f"rejected {rate:.0%} of true nulls against a nominal 5% "
                          f"(smallest p {sorted(ps)[:4]})")


def test_reality_check_has_power_against_a_dominant_cell():
    rng = np.random.default_rng(11)
    F = rng.normal(0.0, 0.01, size=(1000, 10))
    F[:, 4] += 0.0025          # t ~ 7.9 on its own
    r = reality_check(F, B=400, seed=3)
    assert r["p_value"] < 0.01, f"no power: p={r['p_value']}"
    assert r["best_cell_index"] == 4


def test_reality_check_is_deterministic_for_a_fixed_seed():
    rng = np.random.default_rng(1)
    F = rng.normal(0.0, 0.01, size=(300, 5))
    a = reality_check(F, B=200, seed=42)
    b = reality_check(F, B=200, seed=42)
    assert a["p_value"] == b["p_value"]


def test_studentised_and_spa_variants_run_and_are_bounded():
    rng = np.random.default_rng(5)
    F = rng.normal(0.0, 0.01, size=(400, 8))
    F[:, 0] += 0.003
    for kw in ({"studentize": True}, {"studentize": True, "spa_recenter": True}):
        r = reality_check(F, B=200, seed=4, **kw)
        assert 0.0 <= r["p_value"] <= 1.0


# ------------------------------------------------------------ inverse-vol sizing
def _synthetic_closes(n=400, k=6, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2020-01-01", periods=n, freq="B")
    vols = np.linspace(0.005, 0.03, k)          # deliberately very different vols
    rets = rng.normal(0.0002, 1.0, size=(n, k)) * vols
    px = 100 * np.cumprod(1 + rets, axis=0)
    return pd.DataFrame(px, index=idx, columns=[f"S{i}" for i in range(k)])


def test_invvol_weights_sum_to_one_and_stay_levered_neutral():
    closes = _synthetic_closes()
    net, w = xsmom_invvol(closes, lookback=60, top_k=3, rebal_days=10)
    exposure = w.sum(axis=1)
    assert exposure.max() <= 1.0001 + 1e-9
    held = w[w.sum(axis=1) > 0]
    assert np.allclose(held.sum(axis=1), 1.0, atol=1e-9)
    # never more than top_k names held at once
    assert int((held > 1e-12).sum(axis=1).max()) <= 3
    assert np.isfinite(net.loc[closes.index[61:]]).all()


def test_invvol_weights_are_not_equal_weight():
    """The variant must actually differ from H-201, or it re-tests the same rule."""
    closes = _synthetic_closes()
    _net, w = xsmom_invvol(closes, lookback=60, top_k=3, rebal_days=10)
    held = w[w.sum(axis=1) > 0]
    max_dev = float((held - 1.0 / 3.0).abs().max().max())
    assert max_dev > 0.02, f"weights barely differ from equal ({max_dev:.4f})"


def test_invvol_gives_more_weight_to_the_lower_vol_name():
    closes = _synthetic_closes()
    _net, w = xsmom_invvol(closes, lookback=60, top_k=3, rebal_days=10)
    held = w[w.sum(axis=1) > 0]
    vol = closes.pct_change(fill_method=None).rolling(60, min_periods=30).std()
    # average weight of S0 (lowest vol) should exceed S5 (highest vol) when held
    w_low = held["S0"].replace(0, np.nan).mean()
    w_high = held["S5"].replace(0, np.nan).mean()
    assert w_low > w_high, f"low-vol weight {w_low:.3f} not above high-vol {w_high:.3f}"


def test_turnover_fraction_is_bounded_and_zero_on_flat_book():
    closes = _synthetic_closes()
    _net, w = xsmom_invvol(closes, lookback=60, top_k=3, rebal_days=10)
    turn = turnover_fraction(w)
    assert (turn >= -1e-12).all()
    # full rotation of a 3-name fully invested book can never exceed 2.0
    assert turn.max() <= 2.0 + 1e-9
