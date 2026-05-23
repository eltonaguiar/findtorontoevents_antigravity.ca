"""Tests for M-009: PEAD strategy on EQUITY top-100.

Verifies core logic of alpha_engine/strategies/pead_equity.py without
hitting external data sources (uses synthetic earnings events).
"""
import os
import sys
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from alpha_engine.strategies.pead_equity import generate_pead_signals, PEAD_WINDOW_DAYS


def _event(
    symbol="AAPL",
    days_ago=0,
    eps_actual=2.0,
    eps_estimate=1.8,
    guidance_raised=True,
    market_cap_rank=1,
    asset_class="EQUITY",
):
    as_of = datetime.now(timezone.utc)
    earnings_date = as_of - timedelta(days=days_ago)
    return {
        "symbol": symbol,
        "earnings_date": earnings_date.isoformat(),
        "eps_actual": eps_actual,
        "eps_estimate": eps_estimate,
        "guidance_raised": guidance_raised,
        "market_cap_rank": market_cap_rank,
        "asset_class": asset_class,
    }


def test_clean_beat_generates_signal():
    """Earnings beat with guidance raise within 2d window must generate a LONG signal."""
    events = [_event("AAPL", days_ago=1, eps_actual=2.0, eps_estimate=1.5, guidance_raised=True)]
    as_of = datetime.now(timezone.utc)
    signals = generate_pead_signals(events, as_of=as_of)
    assert len(signals) > 0
    assert signals[0]["symbol"] == "AAPL"
    assert signals[0]["direction"] == "LONG"
    assert signals[0]["asset_class"] == "EQUITY"


def test_stale_earnings_outside_window_skipped():
    """Earnings event > PEAD_WINDOW_DAYS old must be ignored."""
    events = [_event("MSFT", days_ago=PEAD_WINDOW_DAYS + 3)]
    as_of = datetime.now(timezone.utc)
    signals = generate_pead_signals(events, as_of=as_of)
    assert not any(s["symbol"] == "MSFT" for s in signals)


def test_miss_no_signal():
    """Earnings miss (actual < estimate) must not generate a signal."""
    events = [_event("GOOG", days_ago=0, eps_actual=1.0, eps_estimate=1.5)]
    signals = generate_pead_signals(events, as_of=datetime.now(timezone.utc))
    assert not any(s["symbol"] == "GOOG" for s in signals)


def test_non_equity_asset_class_skipped():
    """Non-EQUITY asset_class events must be skipped."""
    events = [_event("BTC", days_ago=0, asset_class="CRYPTO")]
    signals = generate_pead_signals(events, as_of=datetime.now(timezone.utc))
    assert not any(s["symbol"] == "BTC" for s in signals)


def test_outside_top100_skipped():
    """Event with market_cap_rank > 100 must be skipped."""
    events = [_event("SMALLCO", days_ago=0, market_cap_rank=150)]
    signals = generate_pead_signals(events, as_of=datetime.now(timezone.utc))
    assert not any(s["symbol"] == "SMALLCO" for s in signals)


def test_signal_schema_compliance():
    """Generated signals must include required pick schema fields."""
    events = [_event("NVDA", days_ago=0, eps_actual=3.0, eps_estimate=2.0)]
    signals = generate_pead_signals(events, as_of=datetime.now(timezone.utc))
    if signals:
        s = signals[0]
        assert "pead" in str(s.get("strategy", "")).lower()
        assert s.get("asset_class") == "EQUITY"
        assert s.get("direction") == "LONG"
