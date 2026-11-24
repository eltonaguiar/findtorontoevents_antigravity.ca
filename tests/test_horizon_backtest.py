"""Horizon backtest math: the parts that must be right before any number counts.

The tests pin the two things that silently invalidate a backtest: a signal that
sees the future, and a metric that is computed wrong. They do not test that the
strategy is good — that is what the run is for.
"""
import math

import pytest

import tools.horizon_backtest as hb


def test_shift_is_past_only():
    xs = [1.0, 2.0, 3.0, 4.0]
    assert hb._shift(xs, 1, 0.0) == [0.0, 1.0, 2.0, 3.0]
    assert hb._shift(xs, 2, 0.0) == [0.0, 0.0, 1.0, 2.0]


def test_tsmom_cannot_trade_the_price_it_saw():
    # a step up on the last bar must NOT produce exposure on that same bar
    closes = [100.0] * 20 + [200.0]
    exp = hb.tsmom_exposure(closes, lookback=10)
    assert exp[-1] == 0.0, "signal is lagged one day by construction"
    assert len(exp) == len(closes)


def test_exposure_backtest_charges_every_switch():
    closes = [100.0, 110.0, 110.0]
    cash = [100.0, 100.0, 100.0]
    exp = [0.0, 1.0, 1.0]          # enter on day 2, stay day 3
    out = hb.run_exposure(closes, exp, cash, cost_bps=50.0)
    assert out["switches"] == 1
    # 10% gain on the invested day, minus one 50 bps switch
    assert out["final_equity"] == pytest.approx(1.095, abs=1e-9)


def test_sharpe_is_excess_over_cash():
    rets = [0.001, 0.002, -0.001, 0.003] * 25
    assert hb.sharpe(rets, [0.001, 0.002, -0.001, 0.003] * 25) == pytest.approx(0.0, abs=1e-9)
    assert hb.sharpe(rets, [0.0] * 100) > 1.0


def test_max_drawdown_and_cagr():
    closes = [100.0, 80.0, 120.0]
    assert hb.max_drawdown(closes) == pytest.approx(-0.2)
    assert hb.ann_return([100.0, 110.0], periods=1) == pytest.approx(0.1)


def test_horizon_returns_are_overlapping_and_counted():
    closes = [float(i) for i in range(1, 11)]
    hr = hb.horizon_returns(closes, years=1, periods=2)   # 2-bar windows
    assert len(hr) == 8
    assert hr[0] == pytest.approx(2.0)   # 3/1 - 1


def test_vol_scaling_is_capped_and_flat_in_cash():
    closes = [100.0 + i * 0.5 for i in range(120)]
    exp = hb.tsmom_exposure(closes, lookback=30, target_vol=0.10, cap=1.5)
    assert all(0.0 <= e <= 1.5 + 1e-9 for e in exp)
    # a flat, rising line has near-zero vol, so leverage hits the cap, never beyond
    assert max(exp) > 0.0


def test_faber_signal_applies_from_next_month():
    # five months of three sessions: Jan/Feb/Mar at 100, Apr/May at 300
    dates = [f"2026-{m:02d}-{d:02d}" for m in range(1, 6) for d in range(1, 4)]
    closes = [100.0] * 9 + [300.0] * 6
    exp = hb.faber_exposure(dates, closes, months=1)
    # April's close is above its 1-month SMA, but that decision can only be held
    # from MAY onward: indices 12-14. Everything before that stays in cash.
    assert exp[:12] == [0.0] * 12
    assert exp[12:] == [1.0] * 3


def test_mer_drag_is_monotonic_and_material():
    out = hb.mer_drag(gross=0.07, years=30)
    vals = list(out["terminal_multiple"].values())
    assert vals == sorted(vals, reverse=True)
    gap = out["gap_vs_cheapest_pct"]["1.50%"]
    assert 20.0 < gap < 40.0, gap


def test_align_inner_joins_on_date():
    a = [["2026-01-01", 1.0], ["2026-01-02", 2.0]]
    b = [["2026-01-02", 10.0], ["2026-01-03", 20.0]]
    dates, cols = hb.align({"a": a, "b": b})
    assert dates == ["2026-01-02"]
    assert cols["a"] == [2.0] and cols["b"] == [10.0]
