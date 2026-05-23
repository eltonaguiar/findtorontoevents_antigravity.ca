"""
Tests for the earnings calendar filter on earnings_momentum_pead.

See FOCUSED_NONCRYPTO_BACKTEST_REPORT_2026-04-07.md §Earnings Momentum PEAD
for the rationale: PEAD is on probation until it clears 100 trades, so we
gate entries on a real earnings event being recent.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytest

from multi_asset import equity_strategies
from multi_asset.equity_strategies import (
    days_since_earnings,
    earnings_momentum_pead,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _build_pead_df() -> pd.DataFrame:
    """
    Build a 90-bar OHLCV DataFrame that triggers the PEAD pattern:
      * 60+ bars of slow uptrend so price > SMA50
      * an earnings-style gap up (>3% open) on >2x avg volume 5 days ago
      * price holds above the gap
      * RSI not overbought
    """
    n = 90
    rng = pd.date_range(end=pd.Timestamp.utcnow().normalize(),
                        periods=n, freq="D")
    # Flat baseline at 100 with oscillation so RSI is well-defined and moderate
    rng_seed = np.random.default_rng(42)
    base = np.full(n, 100.0) + rng_seed.normal(0, 0.6, n)
    close = base.copy()
    open_ = close - rng_seed.normal(0, 0.2, n)
    high = np.maximum(open_, close) + 0.3
    low = np.minimum(open_, close) - 0.3
    volume = np.full(n, 1_000_000.0)

    # Inject the gap up at index n-5 (5 days before "now")
    gap_idx = n - 5
    prev_close = close[gap_idx - 1]
    open_[gap_idx] = prev_close * 1.035  # 3.5% gap up (just over PEAD threshold)
    close[gap_idx] = prev_close * 1.04
    high[gap_idx] = prev_close * 1.045
    low[gap_idx] = prev_close * 1.034
    volume[gap_idx] = 3_500_000.0        # 3.5x volume

    # Hold above gap on subsequent days but oscillate so RSI stays moderate
    for i in range(gap_idx + 1, n):
        offset = ((i - gap_idx) % 3) - 1  # -1, 0, 1 cycle
        close[i] = close[gap_idx] + 0.15 * offset
        open_[i] = close[gap_idx] + 0.05 * offset
        high[i] = max(open_[i], close[i]) + 0.2
        low[i] = min(open_[i], close[i]) - 0.2

    return pd.DataFrame({
        "Open": open_,
        "High": high,
        "Low": low,
        "Close": close,
        "Volume": volume,
    }, index=rng)


class _MockTicker:
    """Mimics yfinance.Ticker — exposes earnings_dates as a DataFrame."""
    def __init__(self, earnings_dt):
        self._dt = earnings_dt

    @property
    def earnings_dates(self):
        if self._dt is None:
            return pd.DataFrame()
        idx = pd.DatetimeIndex([pd.Timestamp(self._dt)])
        return pd.DataFrame({"Reported EPS": [1.5]}, index=idx)


@pytest.fixture(autouse=True)
def _clear_earnings_cache():
    equity_strategies._EARNINGS_MEM_CACHE.clear()
    yield
    equity_strategies._EARNINGS_MEM_CACHE.clear()


# ---------------------------------------------------------------------------
# days_since_earnings unit tests
# ---------------------------------------------------------------------------

def test_days_since_earnings_with_known_date():
    today = datetime(2026, 4, 12, tzinfo=timezone.utc)
    factory = lambda s: _MockTicker(datetime(2026, 4, 5, tzinfo=timezone.utc))
    assert days_since_earnings("AMZN", today=today, ticker_factory=factory) == 7


def test_days_since_earnings_returns_none_when_unknown():
    factory = lambda s: _MockTicker(None)
    assert days_since_earnings("ZZZZ", ticker_factory=factory) is None


# ---------------------------------------------------------------------------
# earnings_momentum_pead gate tests
# ---------------------------------------------------------------------------

def _info():
    return {"cat": "stock"}


def test_pead_passes_when_earnings_in_window():
    df = _build_pead_df()
    recent = datetime.now(timezone.utc) - timedelta(days=5)
    factory = lambda s: _MockTicker(recent)

    sigs = earnings_momentum_pead(
        df, "AMZN", _info(), ticker_factory=factory)

    assert len(sigs) == 1, "PEAD should fire when earnings are in window"
    sig = sigs[0]
    assert sig["earnings_beat_gate"] is True
    assert sig["earnings_window"] == "in_window"
    assert sig["max_hold_days"] == 10
    assert sig["earnings_days_ago"] == 5


def test_pead_filtered_when_earnings_outside_window():
    df = _build_pead_df()
    stale = datetime.now(timezone.utc) - timedelta(days=120)
    factory = lambda s: _MockTicker(stale)

    sigs = earnings_momentum_pead(
        df, "AMZN", _info(), ticker_factory=factory)

    assert sigs == [], "PEAD must be blocked when earnings are stale"


def test_pead_passes_when_earnings_unknown():
    df = _build_pead_df()
    factory = lambda s: _MockTicker(None)

    sigs = earnings_momentum_pead(
        df, "AMZN", _info(), ticker_factory=factory)

    assert len(sigs) == 1, "Graceful default: unknown earnings must pass"
    sig = sigs[0]
    assert sig["earnings_beat_gate"] is None
    assert sig["earnings_window"] == "unknown"
    assert sig["max_hold_days"] == 10
