"""Unit tests for partial TP at tp1 + breakeven SL activation.

These exercise the exit state machine in
``alpha_engine.forward_test_portfolios._check_exits`` for two scenarios:

1. Long entry that touches tp1 then runs to full TP.  Verifies a partial
   exit is recorded at tp1 with 50% of the allocation, the remaining 50%
   closes at TP, and the average realized pnl_pct across the two records
   equals the midpoint of the tp1/TP price moves.

2. Long entry that hits tp1, pulls back after breakeven activates, and
   exits at the breakeven-moved stop with exit_reason == BREAKEVEN_SL
   and ~0 pnl on the remaining half.

The tests build a minimal portfolio directly and drive ``_check_exits``
bar-by-bar by monkeypatching ``fetch_price``.  Entry logic is *not*
touched — positions are seeded directly into ``portfolio["positions"]``.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

# Make the repo root importable so ``alpha_engine`` resolves.
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from alpha_engine import forward_test_portfolios as ftp  # noqa: E402


FAKE_PDEF = {
    "name": "TEST_PARTIAL_TP",
    "asset_class": "CRYPTO",
    "description": "unit test portfolio",
    "start_capital": 10_000.0,
    "max_hold_hours": 10_000,  # effectively disable MAX_HOLD for the test
}


def _make_position(
    entry: float,
    tp: float,
    sl: float,
    allocation: float = 1000.0,
    direction: str = "LONG",
    partial_tp_enabled: bool = True,
    breakeven_enabled: bool = True,
) -> dict:
    return {
        "symbol": "TESTUSDT",
        "direction": direction,
        "entry_price": entry,
        "take_profit": tp,
        "stop_loss": sl,
        "quantity": allocation / entry,
        "allocation": allocation,
        "strategy": "unit_test",
        "entry_time_utc": ftp._iso(datetime.now(timezone.utc)),
        "entry_score": 0,
        "trader_label": "",
        "asset_class": "CRYPTO",
        "paper_trade_only": False,
        "source_id": "unit_test::TESTUSDT::x",
        "last_price": entry,
        "unrealized_pnl_pct": 0.0,
        "unrealized_pnl_dollar": 0.0,
        "partial_tp_enabled": partial_tp_enabled,
        "breakeven_enabled": breakeven_enabled,
        "partial_tp_taken": False,
        "breakeven_activated": False,
    }


def _fresh_portfolio() -> dict:
    return ftp._new_portfolio_state(FAKE_PDEF)


def _run_path(monkeypatch, portfolio: dict, prices: list[float]) -> None:
    """Drive ``_check_exits`` once per synthetic bar, walking the given path."""
    state = {"i": 0}

    def _fake_fetch_price(symbol, asset_class):
        i = state["i"]
        return prices[min(i, len(prices) - 1)]

    monkeypatch.setattr(ftp, "fetch_price", _fake_fetch_price)

    for i in range(len(prices)):
        state["i"] = i
        ftp._check_exits(portfolio, FAKE_PDEF)
        if not portfolio["positions"]:
            # Position fully closed; no more bars to process.
            return


def test_partial_tp_then_full_tp(monkeypatch):
    """Long 100 -> 120 TP, tp1 = 110.  Path: 100 .. 112 .. 121.

    Expect: one TP1_PARTIAL record at 110 (half alloc), one TP_HIT record at
    120 (remaining half), total two closed records for this position.
    """
    entry, tp, sl = 100.0, 120.0, 90.0
    pos = _make_position(entry, tp, sl, allocation=1000.0)
    portfolio = _fresh_portfolio()
    portfolio["positions"].append(pos)

    # 20-bar synthetic path: gentle rise, touch tp1, more rise, hit full TP.
    prices = [
        100.5, 101.0, 102.0, 103.5, 105.0, 107.0, 108.5, 109.5,
        112.0,  # crosses tp1 (110)
        112.5, 113.0, 114.0, 115.0, 116.5, 117.0, 118.0, 118.5,
        119.5, 120.0,  # hits full TP (120) exactly
        121.0,
    ]
    assert len(prices) == 20

    _run_path(monkeypatch, portfolio, prices)

    closed = portfolio["closed_positions"]
    reasons = [c["exit_reason"] for c in closed]
    assert ftp.EXIT_TP1_PARTIAL in reasons, reasons
    assert ftp.EXIT_TP_HIT in reasons, reasons
    assert len(closed) == 2

    partial = next(c for c in closed if c["exit_reason"] == ftp.EXIT_TP1_PARTIAL)
    full = next(c for c in closed if c["exit_reason"] == ftp.EXIT_TP_HIT)

    # Partial exited at tp1 = 110, half the original allocation
    assert partial["exit_price"] == pytest.approx(110.0)
    assert partial["allocation"] == pytest.approx(500.0)
    assert partial["realized_pnl_pct"] == pytest.approx(10.0, abs=1e-3)

    # Remaining half closed at full TP == 120
    assert full["exit_price"] == pytest.approx(120.0)
    assert full["allocation"] == pytest.approx(500.0)
    assert full["realized_pnl_pct"] == pytest.approx(20.0, abs=1e-3)

    # Total pnl % across the two exits is the average of 10% and 20% = 15%
    avg_pnl = (partial["realized_pnl_pct"] + full["realized_pnl_pct"]) / 2.0
    assert avg_pnl == pytest.approx(15.0, abs=1e-3)

    # Position is gone
    assert portfolio["positions"] == []


def test_partial_tp_then_breakeven_stop(monkeypatch):
    """Long 100 -> 120 TP, 90 SL.  R = 10 => breakeven arms at +10 (price 110).

    Path: rises to 112 (tp1 partial + breakeven armed), pulls back to 99.5
    which is below the moved SL (100).  Expect a BREAKEVEN_SL exit on the
    remaining half with ~0 pnl.
    """
    entry, tp, sl = 100.0, 120.0, 90.0
    pos = _make_position(entry, tp, sl, allocation=1000.0)
    portfolio = _fresh_portfolio()
    portfolio["positions"].append(pos)

    prices = [
        101.0, 103.0, 105.0, 107.0, 109.0,
        112.0,  # crosses tp1 (110) AND +1R (also 110) -> partial + BE arm
        111.0, 108.0, 105.0, 102.0, 101.0,
        100.0,  # touches breakeven-moved SL (100) -> BREAKEVEN_SL
        99.0, 98.0, 97.0, 96.0, 95.0, 94.0, 93.0, 92.0,
    ]
    assert len(prices) == 20

    _run_path(monkeypatch, portfolio, prices)

    closed = portfolio["closed_positions"]
    reasons = [c["exit_reason"] for c in closed]
    assert ftp.EXIT_TP1_PARTIAL in reasons, reasons
    assert ftp.EXIT_BREAKEVEN_SL in reasons, reasons
    assert ftp.EXIT_SL_HIT not in reasons
    assert len(closed) == 2

    be = next(c for c in closed if c["exit_reason"] == ftp.EXIT_BREAKEVEN_SL)
    # Breakeven exit price is entry (100) so pnl on the remainder is ~0
    assert be["exit_price"] == pytest.approx(100.0)
    assert be["realized_pnl_pct"] == pytest.approx(0.0, abs=1e-6)
    assert be["allocation"] == pytest.approx(500.0)
    assert portfolio["positions"] == []


def test_backward_compat_flag_absent(monkeypatch):
    """A pick without partial_tp_enabled / breakeven_enabled flags must
    behave exactly as the legacy engine: no partial exits, no breakeven.
    """
    entry, tp, sl = 100.0, 120.0, 90.0
    pos = _make_position(
        entry, tp, sl, allocation=1000.0,
        partial_tp_enabled=False, breakeven_enabled=False,
    )
    portfolio = _fresh_portfolio()
    portfolio["positions"].append(pos)

    prices = [
        101.0, 103.0, 105.0, 107.0, 109.0,
        112.0,  # would have been tp1 partial
        111.0, 108.0, 105.0, 102.0, 101.0,
        99.5,  # would have been BE exit
        98.0, 97.0, 95.0, 93.0, 91.0,
        89.5,  # SL hit (90)
        85.0, 80.0,
    ]
    _run_path(monkeypatch, portfolio, prices)

    closed = portfolio["closed_positions"]
    assert len(closed) == 1
    assert closed[0]["exit_reason"] == ftp.EXIT_SL_HIT
