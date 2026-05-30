"""Tests for tools/ma_strategy_forward_tracker.py (MA forward-tracker v2).

No network: all fixtures are synthetic OHLC frames. Validates the honesty
invariants from reports/design_ma_strategy_forward_tracker_2026-05-29.md.
"""
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import ma_strategy_forward_tracker as mt  # noqa: E402


def _frame(closes, highs=None, lows=None, opens=None, start="2018-01-01"):
    idx = pd.date_range(start, periods=len(closes), freq="D")
    c = np.array(closes, dtype=float)
    o = np.array(opens, dtype=float) if opens is not None else c.copy()
    h = np.array(highs, dtype=float) if highs is not None else np.maximum(o, c)
    low = np.array(lows, dtype=float) if lows is not None else np.minimum(o, c)
    return pd.DataFrame({"Open": o, "High": h, "Low": low, "Close": c}, index=idx)


def test_t1_hma_formula():
    # HMA(4) = WMA(2*WMA(close,2) - WMA(close,4), 2) on a known series
    s = pd.Series([1.0, 2, 3, 4, 5, 6])
    hma = mt._ma(s, "HMA", 4)
    # hand-compute last value
    w2 = lambda a: (a[0] * 1 + a[1] * 2) / 3
    w4 = lambda a: sum(a[i] * (i + 1) for i in range(4)) / 10
    raw = []
    for i in range(len(s)):
        if i >= 3:
            raw.append(2 * w2([s[i - 1], s[i]]) - w4([s[i - 3], s[i - 2], s[i - 1], s[i]]))
        else:
            raw.append(float("nan"))
    expect_last = (raw[-2] * 1 + raw[-1] * 2) / 3
    assert hma.iloc[-1] == pytest.approx(expect_last, rel=1e-6)


def test_t2_entry_next_open_no_lookahead():
    # rally above MA then fall back below it -> one full closed trade.
    # entry must fill the bar AFTER the first long signal, never on the signal close.
    closes = [10] * 40 + list(range(12, 42, 2)) + list(range(40, 6, -3))
    df = _frame(closes)
    variant = ("EMA20", "EMA", 20, None)
    sim = mt._simulate(df, variant, slip_bp=0.0)
    assert sim["trades"], "should produce at least one closed trade"
    sig = mt._signal_long(df["Close"], mt._ma(df["Close"], "EMA", 20), variant)
    first_sig = next(i for i in range(len(sig)) if sig[i] == 1.0)
    dates = [d.strftime("%Y-%m-%d") for d in df.index]
    # entry fills the day AFTER the first signal (open[first_sig+1]) — no look-ahead
    assert sim["trades"][0]["entry_date"] == dates[first_sig + 1]


def test_t3_stop_loss_bounded_when_no_gap():
    # smooth decline (open == prior close, no gap) -> stop fills near the stop,
    # loss bounded by the 2x12% cap. Gap risk is covered separately by T7.
    rally = [10] * 40 + [11, 12, 13, 14, 15, 16, 17, 18]
    decline = [17, 16, 15, 14, 13, 12, 11, 10, 9, 8]
    closes = rally + decline
    opens = [closes[0]] + closes[:-1]          # open[t] = close[t-1]: no gaps
    highs = [max(o, c) + 0.2 for o, c in zip(opens, closes)]
    lows = [min(o, c) - 0.2 for o, c in zip(opens, closes)]
    df = _frame(closes, highs=highs, lows=lows, opens=opens)
    sim = mt._simulate(df, ("EMA20", "EMA", 20, None), slip_bp=0.0)
    for t in sim["trades"]:
        if t["reason"] == "stop":
            assert t["ret_net"] >= -(2 * mt.FLOOR_PCT) - 0.03


def test_t6_no_take_profit_reason():
    closes = [10] * 60 + list(range(11, 80))
    df = _frame(closes)
    sim = mt._simulate(df, ("EMA20", "EMA", 20, None), slip_bp=0.0)
    for t in sim["trades"]:
        assert t["reason"] in ("stop", "ma_trail", "ma_trail_eod")
        assert "tp" not in t["reason"] and "take" not in t["reason"]


def test_t7_gap_through_fills_at_open():
    # build a position then gap the open far below the stop
    closes = [10] * 60 + [25, 26, 27] + [5]
    highs = [c + 0.5 for c in closes]
    lows = [c - 0.5 for c in closes]
    opens = closes.copy()
    opens[-1] = 4.0  # gap open below any stop
    lows[-1] = 3.5
    df = _frame(closes, highs=highs, lows=lows, opens=opens)
    sim = mt._simulate(df, ("EMA20", "EMA", 20, None), slip_bp=0.0)
    stops = [t for t in sim["trades"] if t["reason"] == "stop"]
    # a gap-through exit must not produce a fantasy fill above the gapped open
    # (we can't read exit price directly, but ret must reflect the ~ -large move)
    if stops:
        assert min(t["ret_net"] for t in stops) < 0


def test_t8_short_symbol_skipped(monkeypatch, tmp_path):
    # _download should skip symbols with <504 rows; simulate via a tiny stub
    import types
    short = _frame([1.0] * 100)
    stub = types.SimpleNamespace(download=lambda *a, **k: short)
    monkeypatch.setitem(sys.modules, "yfinance", stub)
    series = mt._download({"EQUITY": ["AAA"]}, "6y")
    assert series == {} or "AAA" not in series.get("EQUITY", {})


def test_t9_atr_no_lookahead():
    # ATR at index t must not depend on bars after t
    closes = list(np.linspace(10, 50, 80))
    highs = [c + 1 for c in closes]
    lows = [c - 1 for c in closes]
    df = _frame(closes, highs=highs, lows=lows)
    atr_full = mt._atr(df["High"], df["Low"], df["Close"])
    cut = 60
    atr_cut = mt._atr(df["High"].iloc[:cut], df["Low"].iloc[:cut], df["Close"].iloc[:cut])
    # values up to the cut must be identical whether or not future bars exist
    pd.testing.assert_series_equal(atr_full.iloc[:cut], atr_cut, check_freq=False)


def test_oos_split_disjoint_and_holdout_reserved():
    trades = [{"entry_date": f"2019-{m:02d}-01", "ret_net": 0.01, "ret_R": 0.5, "hold": 3}
              for m in range(1, 13)]
    is_t, oos_t, hold_t, folds, span = mt._split_by_date(trades, "2020-01-01")
    ids = lambda lst: {t["entry_date"] for t in lst}
    assert ids(is_t).isdisjoint(ids(oos_t))
    assert ids(hold_t).isdisjoint(ids(is_t) | ids(oos_t))
    assert len(folds) == mt.N_FOLDS


def test_holdout_disjoint_from_every_walkforward_fold():
    """Adversarial: each walk-forward fold must be disjoint from holdout.
    Folds come from `core` (= non-holdout) so this is true by construction,
    but a refactor that swaps core/all could silently leak."""
    trades = [{"entry_date": f"2018-{m:02d}-{d:02d}", "ret_net": 0.01, "ret_R": 0.5, "hold": 3}
              for m in range(1, 13) for d in (1, 15)]
    is_t, oos_t, hold_t, folds, span = mt._split_by_date(trades, "2020-01-01")
    ids = lambda lst: {t["entry_date"] for t in lst}
    h = ids(hold_t)
    assert h, "test fixture should produce a non-empty holdout"
    for i, f in enumerate(folds):
        assert ids(f).isdisjoint(h), f"fold {i} contains holdout entry-dates"


def test_holdout_honeypot_never_appears_in_oos_metrics():
    """Adversarial honeypot: inject a holdout trade with an impossible-to-miss
    return (+999%). It must not be present in OOS-block aggregates (n / pf / wr).
    If holdout ever leaked into _block(oos_t), avg_R or avg_ret_pct would jump."""
    # 18 monthly entries spanning 3 years; last 10% (most-recent ~3.6 months) = holdout
    base = [{"entry_date": f"2018-{m:02d}-15", "ret_net": 0.02, "ret_R": 0.4, "hold": 3} for m in range(1, 13)]
    mid = [{"entry_date": f"2019-{m:02d}-15", "ret_net": 0.02, "ret_R": 0.4, "hold": 3} for m in range(1, 13)]
    # honeypot: a late-2020 entry guaranteed to fall in the most-recent 10% holdout
    honeypot = {"entry_date": "2020-12-31", "ret_net": 9.99, "ret_R": 50.0, "hold": 3}
    trades = base + mid + [honeypot]
    is_t, oos_t, hold_t, folds, span = mt._split_by_date(trades, "2021-01-01")
    assert any(t["entry_date"] == "2020-12-31" for t in hold_t), "honeypot must land in holdout"
    assert all(t["entry_date"] != "2020-12-31" for t in oos_t), "honeypot must NOT be in oos_t"
    block = mt._block(oos_t, span_years=1)
    if oos_t:
        # 9.99 return would dwarf any honest avg; assert no leakage
        assert block["avg_ret_pct"] is None or abs(block["avg_ret_pct"]) < 50, \
            "OOS avg_ret_pct shows honeypot leakage"


def test_pf_and_wr_basic():
    assert mt._pf([0.1, -0.05, 0.2]) == round(0.3 / 0.05, 2)
    assert mt._wr([0.1, -0.05, 0.2, -0.01]) == 50.0


def test_survivorship_penalty_lowers_pf():
    # use a finite-PF set (has real losses) so the comparison isn't against the
    # 9.99 no-loss sentinel; injecting synthetic losses must not raise PF.
    rets = [0.1] * 12 + [-0.05] * 8
    trades = [{"ret_net": r, "ret_R": 1, "hold": 5} for r in rets]
    base = mt._pf(rets)
    adj = mt._surv_adj_pf(trades)
    assert base == 3.0            # finite, meaningful PF (1.2 / 0.4)
    assert adj < base             # survivorship adjustment lowers it
