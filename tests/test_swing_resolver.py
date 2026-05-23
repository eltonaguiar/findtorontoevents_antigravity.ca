"""Tests for alpha_engine.swing_resolver.

Opt-in sidecar (per CLAUDE.md Wire-Up Rule). No production caller in this commit.
Wiring plan: Phase 14 GHA workflows.

The most important regression test in this file is
`test_resolver_uses_open_for_gap_not_intrabar_spot`. Legacy
`outcome_resolver.py:384-405` printed the SL value as the realized exit
even when the next bar's OPEN had already gapped through the stop. This
suite locks the corrected behaviour.
"""
from __future__ import annotations

import pytest

from alpha_engine.long_term_pick_contract import make_long_term_value_pick, make_swing_pick
from alpha_engine.swing_resolver import BarOHLC, ResolverDecision, SwingResolver

# Reuse contract-test fixtures so we can build a long_term_value pick to
# exercise the short-circuit path.
from tests.test_long_term_pick_contract import (
    SAMPLE_DIVIDEND_RECORD,
    SAMPLE_EARNINGS_HISTORY,
    SAMPLE_FUNDAMENTAL_SNAPSHOT,
    SAMPLE_THESIS_BREAK_RULES,
)


def _bar(
    date: str = "2026-04-01",
    open_: float = 100.0,
    high: float = 100.0,
    low: float = 100.0,
    close: float = 100.0,
    volume: float = 1_000.0,
) -> BarOHLC:
    return BarOHLC(date=date, open=open_, high=high, low=low, close=close, volume=volume)


def _swing_long(
    *,
    entry: float = 100.0,
    tp: float = 110.0,
    sl: float = 95.0,
) -> dict:
    return make_swing_pick(
        symbol="MSFT",
        direction="LONG",
        entry_price=entry,
        take_profit=tp,
        stop_loss=sl,
    )


def _swing_short(
    *,
    entry: float = 100.0,
    tp: float = 90.0,
    sl: float = 105.0,
) -> dict:
    return make_swing_pick(
        symbol="META",
        direction="SHORT",
        entry_price=entry,
        take_profit=tp,
        stop_loss=sl,
    )


# ---------------------------------------------------------------------------
# TP / SL — basic four directions
# ---------------------------------------------------------------------------
def test_resolver_closes_on_tp_hit_long():
    pick = _swing_long(entry=100.0, tp=110.0, sl=95.0)
    bars = [
        _bar("2026-04-01", 100, 101, 99, 100),  # entry bar
        _bar("2026-04-02", 100, 109, 99, 105),  # nothing yet
        _bar("2026-04-03", 105, 112, 104, 111),  # TP hit (high=112 >= 110)
    ]
    resolver = SwingResolver()
    decision = resolver.resolve(pick, bars, entry_bar_idx=0)
    assert isinstance(decision, ResolverDecision)
    assert decision.should_close is True
    assert decision.reason == "tp_hit"
    assert decision.exit_price == 110.0
    assert decision.bars_held == 2


def test_resolver_closes_on_sl_hit_long():
    pick = _swing_long(entry=100.0, tp=110.0, sl=95.0)
    bars = [
        _bar("2026-04-01", 100, 101, 99, 100),
        _bar("2026-04-02", 100, 102, 94, 96),  # low=94 trips SL=95
    ]
    decision = SwingResolver().resolve(pick, bars, entry_bar_idx=0)
    assert decision.should_close is True
    assert decision.reason == "sl_hit"
    assert decision.exit_price == 95.0
    assert decision.bars_held == 1


def test_resolver_closes_on_tp_hit_short():
    pick = _swing_short(entry=100.0, tp=90.0, sl=105.0)
    bars = [
        _bar("2026-04-01", 100, 101, 99, 100),
        _bar("2026-04-02", 100, 102, 89, 91),  # low=89 <= TP=90
    ]
    decision = SwingResolver().resolve(pick, bars, entry_bar_idx=0)
    assert decision.should_close is True
    assert decision.reason == "tp_hit"
    assert decision.exit_price == 90.0


def test_resolver_closes_on_sl_hit_short():
    pick = _swing_short(entry=100.0, tp=90.0, sl=105.0)
    bars = [
        _bar("2026-04-01", 100, 101, 99, 100),
        _bar("2026-04-02", 101, 106, 100, 104),  # high=106 >= SL=105
    ]
    decision = SwingResolver().resolve(pick, bars, entry_bar_idx=0)
    assert decision.should_close is True
    assert decision.reason == "sl_hit"
    assert decision.exit_price == 105.0


# ---------------------------------------------------------------------------
# Gap-fill semantics (the primary bug-fix vs outcome_resolver)
# ---------------------------------------------------------------------------
def test_resolver_handles_gap_down_below_sl():
    """LONG: bar.open below SL → exit_price is bar.open, NOT the SL."""
    pick = _swing_long(entry=100.0, tp=110.0, sl=95.0)
    bars = [
        _bar("2026-04-01", 100, 101, 99, 100),
        _bar("2026-04-02", 90, 92, 88, 89),  # gap-down: open=90 < SL=95
    ]
    decision = SwingResolver().resolve(pick, bars, entry_bar_idx=0)
    assert decision.should_close is True
    assert decision.reason == "sl_hit"
    assert decision.exit_price == 90.0
    assert "gap_through_stop" in decision.triggered_rules


def test_resolver_uses_open_for_gap_not_intrabar_spot():
    """REGRESSION TEST — gap exit MUST be bar.open, not SL.

    The legacy outcome_resolver.py printed the SL price as the exit and
    silently understated losses on gap moves. Pin this here permanently.
    """
    pick = _swing_long(entry=200.0, tp=220.0, sl=190.0)
    bars = [
        _bar("2026-04-01", 200, 202, 198, 200),
        _bar("2026-04-02", 175, 178, 170, 173),  # severe gap: open=175 < SL=190
    ]
    decision = SwingResolver().resolve(pick, bars, entry_bar_idx=0)
    assert decision.should_close is True
    assert decision.reason == "sl_hit"
    # Exit price MUST be the bar OPEN, not the stop_loss.
    assert decision.exit_price == 175.0, (
        "exit_price is SL — this is the legacy bug. Must use bar.open on gap."
    )
    assert decision.exit_price != 190.0
    # PnL is realistic: -12.5%, not the -5% the legacy resolver reported.
    assert decision.realized_pnl_pct == pytest.approx(-0.125)


def test_resolver_handles_gap_up_above_sl_short():
    """SHORT mirror: bar.open above SL → exit_price is bar.open."""
    pick = _swing_short(entry=200.0, tp=180.0, sl=210.0)
    bars = [
        _bar("2026-04-01", 200, 202, 198, 200),
        _bar("2026-04-02", 225, 228, 220, 223),  # gap-up: open=225 > SL=210
    ]
    decision = SwingResolver().resolve(pick, bars, entry_bar_idx=0)
    assert decision.should_close is True
    assert decision.reason == "sl_hit"
    assert decision.exit_price == 225.0
    # SHORT loses money when price goes up.
    assert decision.realized_pnl_pct == pytest.approx((200 - 225) / 200)


# ---------------------------------------------------------------------------
# Same-bar TP+SL — SL wins
# ---------------------------------------------------------------------------
def test_resolver_handles_same_bar_tp_and_sl():
    """If a bar's range covers BOTH TP and SL, SL must win (conservative)."""
    pick = _swing_long(entry=100.0, tp=110.0, sl=95.0)
    bars = [
        _bar("2026-04-01", 100, 101, 99, 100),
        _bar("2026-04-02", 100, 112, 94, 100),  # high>=TP AND low<=SL
    ]
    decision = SwingResolver().resolve(pick, bars, entry_bar_idx=0)
    assert decision.should_close is True
    assert decision.reason == "sl_hit"
    assert decision.exit_price == 95.0
    assert "same_bar_tp_sl" in decision.triggered_rules


# ---------------------------------------------------------------------------
# Time-stop and short history
# ---------------------------------------------------------------------------
def test_resolver_time_stops_at_30_bars():
    pick = _swing_long(entry=100.0, tp=200.0, sl=10.0)  # neither will hit
    # Build 32 quiet bars (entry + 31 follow-ups).
    bars = [_bar(f"2026-04-{i+1:02d}", 100, 101, 99, 100) for i in range(32)]
    resolver = SwingResolver(max_bars_held=30)
    decision = resolver.resolve(pick, bars, entry_bar_idx=0)
    assert decision.should_close is True
    assert decision.reason == "time_stop"
    assert decision.bars_held == 30
    assert decision.exit_price == 100.0  # close of bar 30


def test_resolver_returns_still_active_with_short_history():
    """Not enough forward bars to evaluate yet → still_active."""
    pick = _swing_long(entry=100.0, tp=110.0, sl=95.0)
    bars = [_bar("2026-04-01", 100, 101, 99, 100)]  # only entry bar
    decision = SwingResolver().resolve(pick, bars, entry_bar_idx=0)
    assert decision.should_close is False
    assert decision.reason == "still_active"
    assert decision.exit_price is None


def test_resolver_short_circuits_for_long_term_value_pick():
    """A long_term_value pick must NOT be evaluated by SwingResolver."""
    long_term = make_long_term_value_pick(
        symbol="AAPL",
        direction="LONG",
        entry_price=180.0,
        intrinsic_value=215.0,
        thesis="value thesis",
        thesis_break_rules=SAMPLE_THESIS_BREAK_RULES,
        fundamental_snapshot=SAMPLE_FUNDAMENTAL_SNAPSHOT,
        earnings_history=SAMPLE_EARNINGS_HISTORY,
        next_earnings_date=None,
        dividend_record=SAMPLE_DIVIDEND_RECORD,
        catalyst_dates=[],
    )
    bars = [_bar("2026-04-01", 100, 101, 99, 100)]  # arbitrary
    decision = SwingResolver().resolve(long_term, bars, entry_bar_idx=0)
    assert decision.should_close is False
    assert decision.reason == "still_active"


# ---------------------------------------------------------------------------
# PnL math
# ---------------------------------------------------------------------------
def test_pnl_calculation_long():
    pick = _swing_long(entry=100.0, tp=110.0, sl=95.0)
    bars = [
        _bar("2026-04-01", 100, 101, 99, 100),
        _bar("2026-04-02", 100, 112, 99, 110),
    ]
    decision = SwingResolver().resolve(pick, bars, entry_bar_idx=0)
    assert decision.reason == "tp_hit"
    assert decision.realized_pnl_pct == pytest.approx((110 - 100) / 100)


def test_pnl_calculation_short():
    pick = _swing_short(entry=100.0, tp=90.0, sl=105.0)
    bars = [
        _bar("2026-04-01", 100, 101, 99, 100),
        _bar("2026-04-02", 100, 102, 88, 90),
    ]
    decision = SwingResolver().resolve(pick, bars, entry_bar_idx=0)
    assert decision.reason == "tp_hit"
    # SHORT pnl = (entry - exit)/entry = +10%
    assert decision.realized_pnl_pct == pytest.approx((100 - 90) / 100)


# ---------------------------------------------------------------------------
# Batch + edge cases
# ---------------------------------------------------------------------------
def test_resolve_batch_handles_mix():
    a = _swing_long(entry=100, tp=110, sl=95)
    a["symbol"] = "AAA"
    b = _swing_long(entry=100, tp=110, sl=95)
    b["symbol"] = "BBB"

    bars_a = [
        _bar("2026-04-01", 100, 101, 99, 100),
        _bar("2026-04-02", 100, 112, 99, 110),
    ]
    bars_b = [
        _bar("2026-04-01", 100, 101, 99, 100),
        _bar("2026-04-02", 100, 102, 94, 96),
    ]
    out = SwingResolver().resolve_batch(
        [a, b],
        bars_map={"AAA": bars_a, "BBB": bars_b},
    )
    assert out["AAA"].reason == "tp_hit"
    assert out["BBB"].reason == "sl_hit"


def test_resolve_batch_missing_history_stays_active():
    pick = _swing_long(entry=100, tp=110, sl=95)
    pick["symbol"] = "ZZZ"
    out = SwingResolver().resolve_batch([pick], bars_map={})
    assert out["ZZZ"].reason == "still_active"
    assert out["ZZZ"].should_close is False


def test_resolver_constructor_validates_max_bars_held():
    with pytest.raises(ValueError):
        SwingResolver(max_bars_held=0)
