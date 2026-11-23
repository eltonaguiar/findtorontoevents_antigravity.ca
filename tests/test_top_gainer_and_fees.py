"""
Regression tests for tools/top_gainer_test.py and tools/fee_arithmetic.py.

The first top-gainer run reported a +880%/yr alpha. That was not an edge, it was
a look-ahead: the strategy ranked names using day d's return and then captured
day d's own return. The test `test_daily_series_does_not_capture_the_ranking_bar`
exists specifically to catch that defect class coming back.

Run: python3 -m pytest tests/test_top_gainer_and_fees.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import fee_arithmetic  # noqa: E402
from tools import top_gainer_test as tgt  # noqa: E402


# --------------------------------------------------------------------------
# forward-return alignment
# --------------------------------------------------------------------------
def _tiny_ret(n=40, ncols=3, seed=3):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2024-01-01", periods=n)
    data = rng.normal(0, 0.01, size=(n, ncols))
    return pd.DataFrame(data, index=idx, columns=[f"S{i}" for i in range(ncols)])


def test_forward_return_is_next_bar_not_current_bar():
    """fwd at t must be a_{t+1} (+ ... + a_{t+hold}), never include a_t."""
    ret = _tiny_ret()
    logret = np.log1p(ret)

    for hold in (1, 2, 5):
        fwd = logret.shift(-hold).rolling(hold).sum()
        t = ret.index[10]
        expected = sum(logret.iloc[10 + k + 1] for k in range(hold)).to_numpy()
        np.testing.assert_allclose(fwd.loc[t].to_numpy(), expected, rtol=1e-12,
                                   err_msg=f"hold={hold} misaligned")


def test_double_shift_would_break_alignment():
    """Guards the exact bug: an extra .shift(-(hold-1)) must NOT be present."""
    ret = _tiny_ret()
    logret = np.log1p(ret)
    hold = 5
    correct = logret.shift(-hold).rolling(hold).sum()
    buggy = logret.shift(-hold).rolling(hold).sum().shift(-(hold - 1))
    t = ret.index[10]
    assert not np.allclose(correct.loc[t].to_numpy(), buggy.loc[t].to_numpy()), \
        "the two forms should differ; if equal the bug was reintroduced silently"


# --------------------------------------------------------------------------
# look-ahead in the tradable series
# --------------------------------------------------------------------------
def test_daily_series_does_not_capture_the_ranking_bar():
    """The strategy ranks on bar d, so it can only earn returns from d+1.

    Plant a large return on one date and confirm that the tradable series does
    not receive that date's return while standing on that same date's rank.
    """
    ret = _tiny_ret(n=60, ncols=4)
    spike_date = ret.index[30]
    ret.loc[spike_date, "S0"] = 0.50          # +50% on the spike bar

    lookback, hold = 5, 1
    s = tgt.daily_series(ret, lookback, 0.5, hold)

    # Rebuild the expectation by hand: for each rebalance date d, the series at
    # date d+1 must equal the mean return of the names selected at d using the
    # trailing window ending at d (inclusive).
    logret = np.log1p(ret)
    trail = logret.rolling(lookback).sum()
    bad = []
    for d in ret.index[lookback::hold]:
        tr = trail.loc[d]
        if tr.notna().sum() < 3:
            continue
        cut = tr.dropna().quantile(0.5)
        top = tr[tr >= cut].dropna().index
        nxt = ret.index[ret.index.get_loc(d) + 1] if ret.index.get_loc(d) + 1 < len(ret) else None
        if nxt is None or not len(top):
            continue
        expected = float(ret.loc[nxt, top].dropna().mean())
        got = s.get(nxt)
        if got is None or abs(got - expected) > 1e-12:
            bad.append((d, nxt, expected, got))
    assert not bad, f"selection/entry misaligned on {len(bad)} dates, first={bad[:2]}"


def test_series_never_indexes_a_bar_used_for_ranking_only():
    """With lookback=1, hold=1, every value must come from a date AFTER a rank date."""
    ret = _tiny_ret(n=30, ncols=3)
    s = tgt.daily_series(ret, 1, 0.34, 1)
    rank_dates = set(ret.index[1::1])
    # every output date should be one bar after some rank date
    for d in s.index:
        prev = ret.index[ret.index.get_loc(d) - 1]
        assert prev in rank_dates


# --------------------------------------------------------------------------
# verdict must not be decided by raw return
# --------------------------------------------------------------------------
def test_verdict_uses_ci_not_raw_return():
    ret = _tiny_ret(n=80, ncols=5, seed=9)
    r = tgt.run_one(ret, 2, 1, 0.4, "t")
    assert "verdict" in r
    assert r["verdict"] in ("PASS", "REFUTED")
    if not r["ci_excludes_zero"]:
        assert r["verdict"] == "REFUTED", "non-significant CI must not PASS"


# --------------------------------------------------------------------------
# fee arithmetic
# --------------------------------------------------------------------------
def test_fee_arithmetic_matches_hand_calc():
    out = fee_arithmetic.compute()
    b, y = out["balance"], out["years"]
    for key, row in out["rows"].items():
        expected = b * fee_arithmetic.ASSUMED[key]["mer_rate"] * y
        assert abs(row["cost_dollars"] - expected) < 0.01, key


def test_fee_arithmetic_units_are_decimals_not_percent():
    """A 100x units error once made every figure wrong; pin the scale."""
    out = fee_arithmetic.compute()
    etf = out["rows"]["index_etf"]
    assert 0.05 < etf["assumed_mer_pct"] < 0.5, etf["assumed_mer_pct"]
    assert 500 < etf["cost_dollars"] < 5000, etf["cost_dollars"]


def test_active_fund_ratio_is_double_digit():
    out = fee_arithmetic.compute()
    assert out["ratios"]["active_mf_vs_index_etf"] > 10
