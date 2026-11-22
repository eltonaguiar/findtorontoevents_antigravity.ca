"""Unit tests for tools/bond_momentum.py (item 34).

Focus: the three things that could silently produce a flattering number --
lookahead in the yield decision, shorting when the rule says flat, and a
cross-sectional rule that ranks a missing ETF as worst.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.bond_momentum import (  # noqa: E402
    b1_time_series, b2_cross_sectional, b3_duration_timing, run_weights,
)
from tools.momentum_core import mom_12_1, month_end_index, monthly_returns  # noqa: E402


def _panel(n_months=40, symbols=("AAA", "BBB", "CCC", "DDD", "EEE", "FFF")):
    days = pd.bdate_range("2018-01-01", periods=n_months * 21)
    data = {s: 100.0 * np.cumprod(np.full(len(days), 1.0 + 0.0005 * (j - 2.5)))
            for j, s in enumerate(symbols)}
    return pd.DataFrame(data, index=days)


def _yields(n_years=6, start=2.0, step=0.25):
    days = pd.bdate_range("2018-01-01", periods=int(n_years * 252))
    vals = start + step * np.arange(len(days)) / 252.0  # steadily rising
    return pd.Series(vals, index=days)


# --------------------------------------------------------------------------
# 12-1 formation
# --------------------------------------------------------------------------
def test_mom_12_1_skips_most_recent_month():
    """The last month must NOT contribute: a spike in t-1 -> t is ignored."""
    prices = _panel()
    me = month_end_index(prices)
    mp = prices.loc[me]                       # mom_12_1 requires a month-end grid
    t = me[14]
    base = mom_12_1(mp, t)
    spiked = mp.copy()
    after = [x for x in spiked.index if me[13] < x <= me[14]]  # inside the skipped month
    spiked.loc[after] *= 5.0
    assert mom_12_1(spiked, t) == pytest.approx(base)


def test_mom_12_1_rejects_daily_data():
    """A daily frame would silently make iloc[-13] mean ~13 days, not 12 months."""
    prices = _panel()
    with pytest.raises(ValueError, match="month-end"):
        mom_12_1(prices, prices.index[-1])


def test_mom_12_1_empty_when_history_short():
    prices = _panel()
    me = month_end_index(prices)
    assert mom_12_1(prices.loc[me], me[5]) == {}


def test_mom_12_1_needs_twelve_months_not_thirteen():
    """Exactly 12 month-ends is enough: t-12 .. t-1 inclusive."""
    prices = _panel()
    me = month_end_index(prices)
    assert mom_12_1(prices.loc[me], me[11]) != {}   # 12 rows available
    assert mom_12_1(prices.loc[me], me[10]) == {}   # 11 rows -> not yet


# --------------------------------------------------------------------------
# B1: long-only, flat when negative
# --------------------------------------------------------------------------
def test_b1_never_goes_short_and_stays_fully_invested_when_positive():
    prices = _panel(n_months=40, symbols=("UP1", "UP2", "UP3", "DN1", "DN2", "DN3"))
    days = prices.index
    # make the UP names genuinely rise (the generic panel's drift is negative for
    # most columns) and the DN names genuinely fall
    for i, s in enumerate(("UP1", "UP2", "UP3")):
        prices[s] = 100.0 * np.cumprod(np.full(len(days), 1.0008 - i * 0.0002))
    for s in ("DN1", "DN2", "DN3"):
        prices[s] = 100.0 * np.cumprod(np.full(len(days), 0.9995))
    me = [t for t in month_end_index(prices) if len(prices.loc[:t]) >= 13]
    mrets = monthly_returns(prices, me)
    res = run_weights(mrets, b1_time_series(prices, list(mrets.index)), 5.0)
    live = [r for r in res["rows"][11:] if r["weights"]]  # post-formation only
    assert live
    for r in live:
        assert all(w > 0 for w in r["weights"].values())  # never short
        assert r["cash_weight"] == pytest.approx(0.0)      # uptrending names always exist


def test_b1_all_cash_when_everything_falls():
    n = 400
    days = pd.bdate_range("2018-01-01", periods=n)
    prices = pd.DataFrame({s: 100.0 * np.cumprod(np.full(n, 0.999))
                           for s in ("A", "B", "C", "D", "E", "F")}, index=days)
    me = [t for t in month_end_index(prices) if len(prices.loc[:t]) >= 13]
    mrets = monthly_returns(prices, me)
    res = run_weights(mrets, b1_time_series(prices, list(mrets.index)), 5.0)
    # after the 12-month formation window exists, everything is falling -> all cash
    for r in res["rows"][11:]:
        assert r["weights"] == {} and r["cash_weight"] == pytest.approx(1.0)


# --------------------------------------------------------------------------
# B2: cross-sectional
# --------------------------------------------------------------------------
def test_b2_is_dollar_neutral_with_equal_legs():
    prices = _panel()
    me = [t for t in month_end_index(prices) if len(prices.loc[:t]) >= 13]
    mrets = monthly_returns(prices, me)
    res = run_weights(mrets, b2_cross_sectional(prices, list(mrets.index), k=3), 5.0)
    rows = [r for r in res["rows"][11:] if r["weights"]]
    assert rows
    for r in rows:
        longs = [w for w in r["weights"].values() if w > 0]
        shorts = [w for w in r["weights"].values() if w < 0]
        assert len(longs) == 3 and len(shorts) == 3
        assert sum(longs) + sum(shorts) == pytest.approx(0.0, abs=1e-9)


def test_b2_falls_back_to_cash_with_too_few_symbols():
    prices = _panel(symbols=("A", "B", "C"))
    me = [t for t in month_end_index(prices) if len(prices.loc[:t]) >= 13]
    mrets = monthly_returns(prices, me)
    res = run_weights(mrets, b2_cross_sectional(prices, list(mrets.index), k=3), 5.0)
    assert all(r["cash_weight"] == pytest.approx(1.0) for r in res["rows"])


# --------------------------------------------------------------------------
# B3: yield rule must be as-of (no lookahead)
# --------------------------------------------------------------------------
def test_b3_decision_uses_only_yields_up_to_t():
    y = _yields()
    fn = b3_duration_timing(y)
    t = y.index[700]
    before = fn(t)[0]
    # blow up all FUTURE yields: the decision at t must not change
    tampered = y.copy()
    tampered.loc[tampered.index > t] *= 10.0
    assert b3_duration_timing(tampered)(t)[0] == before


def test_b3_goes_long_when_yields_fall():
    days = pd.bdate_range("2018-01-01", periods=1500)
    falling = pd.Series(5.0 - 2.0 * np.arange(len(days)) / len(days), index=days)
    fn = b3_duration_timing(falling)
    assert fn(days[1200])[0] == {"TLT": 1.0}


def test_b3_goes_flat_when_yields_rise():
    fn = b3_duration_timing(_yields())
    assert fn(_yields().index[1200])[0] == {}


def test_b3_cash_before_enough_history():
    y = _yields()
    fn = b3_duration_timing(y)
    assert fn(y.index[10]) == ({}, 1.0)


# --------------------------------------------------------------------------
# Cost monotonicity
# --------------------------------------------------------------------------
def test_cost_reduces_return_monotonically():
    prices = _panel()
    me = [t for t in month_end_index(prices) if len(prices.loc[:t]) >= 13]
    mrets = monthly_returns(prices, me)
    prev = np.inf
    for bp in (0.0, 5.0, 20.0):
        tot = np.prod(1.0 + run_weights(mrets, b1_time_series(prices, list(mrets.index)),
                                       bp, collect_rows=False)["monthly"])
        assert tot <= prev + 1e-12
        prev = tot
