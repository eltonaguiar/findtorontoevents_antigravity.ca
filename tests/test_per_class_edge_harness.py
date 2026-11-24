"""Invariants for the per-class edge harness.

These exist because the first run published a 30 bps/day equity result that was
purely an accounting artifact: weights leaked instead of going flat, so exposure
drifted above 1 and the "edge" was leverage.
"""
import numpy as np
import pandas as pd
import pytest

from tools.per_class_edge_harness import (block_bootstrap, expected_max_sr,
                                          monthly_trades, profit_factor,
                                          segment_trades, xsmom)


def _panel(n=400):
    idx = pd.bdate_range("2020-01-01", periods=n)
    a = 100 * np.cumprod(1 + np.full(n, 0.002))     # steady riser
    b = 100 * np.cumprod(1 + np.full(n, -0.001))    # steady faller
    c = 100 * np.cumprod(1 + np.full(n, 0.0005))
    d = 100 * np.cumprod(1 + np.full(n, 0.0))
    return pd.DataFrame({"A": a, "B": b, "C": c, "D": d}, index=idx)


def test_xsmom_exposure_never_exceeds_one():
    closes = _panel()
    net, w = xsmom(closes, lookback=20, top_k=2, cost_bps=10)
    assert float(w.sum(axis=1).max()) <= 1.0001
    assert (w.values >= -1e-12).all()


def test_xsmom_closes_a_name_that_drops_out():
    closes = _panel()
    _, w = xsmom(closes, lookback=20, top_k=1, cost_bps=10)
    # the loser must never be held, and the held name must rotate to flat rows
    assert w["B"].abs().sum() == 0
    assert w["A"].iloc[-1] > 0


def test_xsmom_has_no_lookahead():
    closes = _panel()
    _, w_full = xsmom(closes, lookback=20, top_k=2, cost_bps=10)
    tampered = closes.copy()
    tampered.iloc[-40:] *= 1.5                      # future prices only
    _, w_cut = xsmom(tampered, lookback=20, top_k=2, cost_bps=10)
    pd.testing.assert_frame_equal(w_full.iloc[:-40], w_cut.iloc[:-40])


def test_monthly_trades_gives_one_bucket_per_month():
    idx = pd.bdate_range("2021-01-01", periods=260)
    net = pd.Series(0.001, index=idx)
    trades = monthly_trades(net)
    assert 11 <= len(trades) <= 13
    assert all(t > 0 for t in trades)


def test_profit_factor_and_segment_trades():
    assert profit_factor([0.1, -0.05]) == pytest.approx(2.0)
    px = pd.Series([100.0, 110.0, 110.0], index=pd.bdate_range("2021-01-01", periods=3))
    pos = pd.Series([1.0, 1.0, 0.0], index=px.index)
    trades = segment_trades(pos, px, cost_bps=0)
    assert len(trades) == 1 and trades[0] == pytest.approx(0.1)


def test_block_bootstrap_brackets_the_mean():
    rng = np.random.default_rng(0)
    x = rng.normal(0.001, 0.01, 2000)
    lo, hi = block_bootstrap(x, n=300, block=5, seed=1)
    assert lo < x.mean() < hi


def test_expected_max_sharpe_grows_with_trials():
    assert expected_max_sr(2, 1e-4) < expected_max_sr(500, 1e-4)
    assert expected_max_sr(1, 1e-4) == 0.0


# ---- beta-free mechanisms (added 2026-11-22 with H-226/H-227/H-228)
from tools.per_class_edge_harness import funding_carry_daily, xsmom_ls  # noqa: E402


def test_xsmom_ls_is_dollar_neutral_with_gross_one():
    closes = _panel()
    _, w = xsmom_ls(closes, lookback=20, top_k=2, cost_bps=10)
    assert float(w.sum(axis=1).abs().max()) < 1e-9      # net exposure 0
    assert float(w.abs().sum(axis=1).max()) <= 1.0001   # gross exposure <= 1


def test_xsmom_ls_goes_long_the_winner_and_short_the_loser():
    closes = _panel()
    _, w = xsmom_ls(closes, lookback=20, top_k=1, cost_bps=10)
    assert w["A"].iloc[-1] > 0
    assert w["B"].iloc[-1] < 0


def test_funding_carry_aggregates_daily_and_charges_the_drag(tmp_path):
    import json as _json
    base = pd.Timestamp("2024-01-01")
    for sym, rate in (("AAAUSDT", 0.0001), ("BBBUSDT", 0.0003)):
        rows = []
        for d in range(3):
            for slot in range(3):                      # 3 settlements per day
                ts = base + pd.Timedelta(days=d, hours=8 * slot)
                rows.append({"symbol": sym,
                             "funding_time_ms": int(ts.timestamp() * 1000),
                             "funding_rate": rate, "source": "test"})
        (tmp_path / f"{sym}.jsonl").write_text("\n".join(_json.dumps(r) for r in rows))
    s = funding_carry_daily(tmp_path, daily_drag_bps=1.0)
    assert len(s) == 3
    expected = (3 * 0.0001 + 3 * 0.0003) / 2 - 1e-4
    assert s.iloc[0] == pytest.approx(expected, rel=1e-6)
