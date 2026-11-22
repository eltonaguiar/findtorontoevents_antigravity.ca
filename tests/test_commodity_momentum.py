"""Unit tests for tools/commodity_momentum.py (item 33).

The two properties that matter most are tested first, because both were real bugs
caught during development: no lookahead in the monthly return alignment, and NaN
(missing) symbols never being ranked as if they were the worst.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.commodity_momentum import WeightRule, backtest  # noqa: E402
from tools.momentum_core import (  # noqa: E402
    formation_return, max_drawdown, month_end_index, monthly_returns, summarize,
)


def _toy_prices(n_months=8, symbols=("A", "B", "C", "D", "E", "F", "G")):
    """Synthetic daily panel: each symbol a distinct deterministic drift."""
    days = pd.bdate_range("2020-01-01", periods=n_months * 21, freq="C")
    data = {}
    for j, s in enumerate(symbols):
        drift = 0.0004 * (j - 3)  # some up, some down
        data[s] = 100.0 * np.cumprod(np.full(len(days), 1.0 + drift))
    return pd.DataFrame(data, index=days)


# --------------------------------------------------------------------------
# No-lookahead
# --------------------------------------------------------------------------
def test_monthly_returns_are_forward_and_labelled_by_start():
    """row me[k] must equal px[me[k+1]]/px[me[k]]-1 -- the return AFTER the decision date."""
    prices = _toy_prices()
    me = month_end_index(prices)
    m = monthly_returns(prices, me)
    for k, t in enumerate(m.index):
        for s in prices.columns:
            expected = prices.loc[me[k + 1], s] / prices.loc[me[k], s] - 1.0
            assert m.loc[t, s] == pytest.approx(expected), (t, s)
    assert len(m) == len(me) - 1


def test_backtest_ignores_future_prices_for_the_decision():
    """Mutating prices AFTER a rebalance date must not change that period's weights."""
    prices = _toy_prices()
    me = month_end_index(prices)
    base = backtest(prices, me, "V1", 5.0)
    tampered = prices.copy()
    cutoff = me[4]
    tampered.loc[tampered.index > cutoff] *= 3.0  # distort only the FUTURE
    after = backtest(tampered, me, "V1", 5.0)
    for r0, r1 in zip(base["rows"], after["rows"]):
        if r0["period_start"] <= cutoff.strftime("%Y-%m-%d"):
            assert r0["weights"] == r1["weights"], r0["period_start"]


def test_backtest_has_no_nan_returns():
    prices = _toy_prices()
    me = month_end_index(prices)
    res = backtest(prices, me, "V1", 5.0)
    assert not np.isnan(res["monthly"]).any()
    assert res["n_periods"] == len(me) - 1


# --------------------------------------------------------------------------
# Rank / sign logic
# --------------------------------------------------------------------------
def test_tercile_size_for_seven_symbols_is_three():
    scores = {s: float(i) for i, s in enumerate("ABCDEFG")}
    w, cash = WeightRule(variant="V1").weights(scores)
    assert sum(1 for v in w.values() if v > 0) == 3
    assert sum(1 for v in w.values() if v < 0) == 3
    assert "D" not in w  # middle rank unheld
    assert cash == 0.0


def test_missing_symbol_is_dropped_not_ranked_worst():
    """A NaN score must never enter the short leg (that would fabricate a short)."""
    scores = {"A": 0.10, "B": 0.05, "C": 0.01, "D": -0.02, "E": -0.05, "F": -0.09,
              "G": float("nan")}
    w, _ = WeightRule(variant="V1").weights(scores)
    assert "G" not in w
    # 6 valid symbols -> tercile size ceil(6/3) = 2
    assert sum(1 for v in w.values() if v > 0) == 2
    assert sum(1 for v in w.values() if v < 0) == 2


def test_all_missing_means_cash():
    w, cash = WeightRule(variant="V1").weights({"A": float("nan")})
    assert w == {} and cash == 1.0


def test_long_only_never_shorts():
    scores = {s: float(i) - 5 for i, s in enumerate("ABCDEFG")}  # mostly negative
    for variant in ("V2", "V3"):
        w, cash = WeightRule(variant=variant).weights(scores)
        assert all(v > 0 for v in w.values()), variant
        assert cash >= 0.0


def test_v3_absolute_filter_goes_flat_on_negative_momentum():
    scores = {s: -0.1 - i * 0.01 for i, s in enumerate("ABCDEFG")}
    w, cash = WeightRule(variant="V3").weights(scores)
    assert w == {} and cash == 1.0  # every top-3 name is negative -> all cash
    w2, _ = WeightRule(variant="V2").weights(scores)
    assert len(w2) == 3  # V2 still holds them: rank-selected, sign-ignored


def test_formation_return_uses_only_past_rows():
    """Formation at t computed on the full frame == computed on data truncated at t."""
    prices = _toy_prices(n_months=24)  # 504 rows: past the 252-day formation window
    t = prices.index[300]
    full = formation_return(prices, t)
    truncated = formation_return(prices.loc[:t], t)
    assert full and full.keys() == truncated.keys()
    for k in full:
        assert full[k] == pytest.approx(truncated[k])


def test_formation_return_empty_on_short_history():
    prices = _toy_prices()
    assert formation_return(prices, prices.index[10]) == {}


# --------------------------------------------------------------------------
# Metrics
# --------------------------------------------------------------------------
def test_max_drawdown_simple():
    assert max_drawdown(np.array([0.10, -0.50, 0.10])) == pytest.approx(-0.50)


def test_summarize_constant_series_has_zero_vol():
    st = summarize(np.full(12, 0.01))
    assert st["vol"] == pytest.approx(0.0)
    assert np.isnan(st["sharpe_vs_rf"])  # zero std -> undefined, not infinite


def test_summarize_short_series_is_nan_not_crash():
    assert np.isnan(summarize(np.array([0.01]))["cagr"])


def test_cost_reduces_cagr_monotonically():
    prices = _toy_prices()
    me = month_end_index(prices)
    prev = np.inf
    for bp in (0.0, 5.0, 10.0, 20.0):
        c = summarize(backtest(prices, me, "V1", bp, collect_rows=False)["monthly"])["cagr"]
        assert c <= prev + 1e-12
        prev = c
