"""Tests for tools/backtest_forex_cot.py (FOREX COT reversal backtest)."""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from tools.backtest_forex_cot import (  # noqa: E402
    PAIR_TO_YF,
    _confirmed_signals,
    aggregate,
    generate_synthetic_signals,
    verdict,
)


def test_synthetic_is_deterministic_per_pair():
    a1 = generate_synthetic_signals("EURUSD", weeks=80)
    a2 = generate_synthetic_signals("EURUSD", weeks=80)
    b = generate_synthetic_signals("GBPUSD", weeks=80)
    assert a1 == a2, "same pair must reproduce exactly (seed=42)"
    assert a1 != b, "different pairs must produce different streams"
    assert len(a1) == 80
    assert all(s["direction"] in {"LONG", "SHORT", "NEUTRAL"} for s in a1)
    assert all(0.0 <= s["pct"] <= 100.0 for s in a1)
    # All 4 spec pairs must produce signal streams.
    for p in PAIR_TO_YF:
        assert len(generate_synthetic_signals(p, weeks=60)) == 60


def test_confirmation_requires_two_consecutive_extremes():
    stream = [
        {"date": "2026-01-01", "pct": 90.0, "direction": "SHORT"},  # solo, drops
        {"date": "2026-01-08", "pct": 50.0, "direction": "NEUTRAL"},
        {"date": "2026-01-15", "pct": 85.0, "direction": "SHORT"},  # pair start
        {"date": "2026-01-22", "pct": 88.0, "direction": "SHORT"},  # confirmed
        {"date": "2026-01-29", "pct": 50.0, "direction": "NEUTRAL"},
        {"date": "2026-02-05", "pct": 10.0, "direction": "LONG"},
        {"date": "2026-02-12", "pct": 5.0,  "direction": "LONG"},   # confirmed
    ]
    out = _confirmed_signals(stream)
    dates = [s["date"] for s in out]
    assert dates == ["2026-01-22", "2026-02-12"], dates


def test_aggregate_and_verdict_math():
    empty = aggregate([])
    assert empty["n"] == 0 and empty["pf"] == 0.0
    trades = [
        {"pnl_pct": 2.0},
        {"pnl_pct": -1.0},
        {"pnl_pct": 1.0},
        {"pnl_pct": -0.5},
    ]
    agg = aggregate(trades)
    assert agg["n"] == 4
    assert agg["wr_pct"] == 50.0
    # wins=3.0, losses=1.5 -> PF=2.0
    assert agg["pf"] == 2.0
    assert verdict(2.0) == "PASS"
    assert verdict(1.2) == "WARN"
    assert verdict(0.5) == "FAIL"
    assert verdict("inf") == "PASS"


def test_pair_universe_matches_spec():
    # Spec: EURUSD, GBPUSD, USDJPY, AUDUSD with USDJPY -> JPY=X yfinance ticker.
    assert set(PAIR_TO_YF) == {"EURUSD", "GBPUSD", "USDJPY", "AUDUSD"}
    assert PAIR_TO_YF["USDJPY"] == "JPY=X"
    assert PAIR_TO_YF["EURUSD"] == "EURUSD=X"
