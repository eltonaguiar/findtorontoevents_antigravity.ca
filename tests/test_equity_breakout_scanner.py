"""
Tests for alpha_engine/equity_breakout_scanner.py
==================================================
All yfinance calls are mocked — no network traffic.
"""
from __future__ import annotations

import json
import os
import sys
import types
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure alpha_engine is importable without a full repo install
_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO))

import alpha_engine.equity_breakout_scanner as scanner


# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------

def _make_ticker(close=150.0, high_52w=152.0, today_vol=3_000_000, avg_vol=1_500_000,
                 history_rows=25, fail_info=False, fail_history=False):
    """Return a mock yf.Ticker with configurable data."""
    import pandas as pd
    import numpy as np

    ticker = MagicMock()

    if fail_info:
        ticker.info = {}
    else:
        ticker.info = {"fiftyTwoWeekHigh": high_52w}

    if fail_history:
        ticker.history.return_value = pd.DataFrame()
    else:
        # Build minimal OHLCV history
        volumes = [avg_vol] * (history_rows - 1) + [today_vol]
        closes = [close] * history_rows
        ticker.history.return_value = pd.DataFrame({
            "Close": closes,
            "Volume": volumes,
            "Open": closes,
            "High": closes,
            "Low": closes,
        })

    return ticker


def _make_yf_module(ticker_mock):
    """Return a fake yfinance module that returns ticker_mock for any symbol."""
    yf = types.ModuleType("yfinance")
    yf.Ticker = MagicMock(return_value=ticker_mock)
    return yf


@pytest.fixture()
def tmp_picks(tmp_path):
    """Return a temp active_picks.json path (initially empty list)."""
    p = tmp_path / "active_picks.json"
    p.write_text("[]", encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Test 1: breakout fires when price near 52wk high AND volume high
# ---------------------------------------------------------------------------

def test_breakout_detected_when_conditions_met(tmp_picks):
    """Signal should fire when price within 3% of 52wk high and vol >= 1.5x."""
    ticker = _make_ticker(close=149.0, high_52w=151.0, today_vol=3_000_000, avg_vol=1_000_000)
    yf = _make_yf_module(ticker)

    with patch.dict(sys.modules, {"yfinance": yf}):
        picks = scanner.run_scanner(
            symbols=["AAPL"],
            dry_run=True,
            active_picks_path=tmp_picks,
        )

    assert len(picks) == 1
    p = picks[0]
    assert p["symbol"] == "AAPL"
    assert p["direction"] == "LONG"
    assert p["asset_class"] == "EQUITY"
    assert p["source"] == "equity_breakout_scanner"
    assert p["strategy"] == "52wk_high_breakout"


# ---------------------------------------------------------------------------
# Test 2: no signal when volume is too low
# ---------------------------------------------------------------------------

def test_no_signal_low_volume(tmp_picks):
    """Volume ratio < 1.5x must suppress the signal."""
    # vol_ratio = 1_000_000 / 1_000_000 = 1.0x < 1.5x
    ticker = _make_ticker(close=149.0, high_52w=151.0, today_vol=1_000_000, avg_vol=1_000_000)
    yf = _make_yf_module(ticker)

    with patch.dict(sys.modules, {"yfinance": yf}):
        picks = scanner.run_scanner(
            symbols=["MSFT"],
            dry_run=True,
            active_picks_path=tmp_picks,
        )

    assert picks == []


# ---------------------------------------------------------------------------
# Test 3: no signal when price is far from 52-week high
# ---------------------------------------------------------------------------

def test_no_signal_price_far_from_high(tmp_picks):
    """Price more than 3% below 52wk high must suppress the signal."""
    # pct_from_high = (152 - 140) / 152 = 7.9% > 3%
    ticker = _make_ticker(close=140.0, high_52w=152.0, today_vol=3_000_000, avg_vol=1_000_000)
    yf = _make_yf_module(ticker)

    with patch.dict(sys.modules, {"yfinance": yf}):
        picks = scanner.run_scanner(
            symbols=["NVDA"],
            dry_run=True,
            active_picks_path=tmp_picks,
        )

    assert picks == []


# ---------------------------------------------------------------------------
# Test 4: exact threshold boundary — just outside 3.0% must NOT fire
# ---------------------------------------------------------------------------

def test_boundary_just_outside_threshold_no_signal(tmp_picks):
    """pct_from_high slightly > 3.0% must not fire (e.g. 3.1% from 52wk high)."""
    high = 100.0
    close = high * (1.0 - (scanner.PCT_FROM_HIGH_THRESHOLD + 0.001))  # 3.1% below
    ticker = _make_ticker(close=close, high_52w=high, today_vol=3_000_000, avg_vol=1_000_000)
    yf = _make_yf_module(ticker)

    with patch.dict(sys.modules, {"yfinance": yf}):
        picks = scanner.run_scanner(
            symbols=["JPM"],
            dry_run=True,
            active_picks_path=tmp_picks,
        )

    assert picks == []


# ---------------------------------------------------------------------------
# Test 5: deduplication — skip symbol with existing open pick within 5 days
# ---------------------------------------------------------------------------

def test_deduplication_skips_existing_open_pick(tmp_picks):
    """Should not emit a second pick for the same symbol within DEDUP_WINDOW_DAYS."""
    today = datetime.now(timezone.utc).date().isoformat()
    existing = [{
        "id": f"eq_breakout_AAPL_{today}",
        "symbol": "AAPL",
        "asset_class": "EQUITY",
        "direction": "LONG",
        "source": "equity_breakout_scanner",
        "strategy": "52wk_high_breakout",
        "status": "open",
        "entry_date": today,
        "confidence": 0.7,
        "entry_price": 149.0,
        "take_profit": 160.0,
        "stop_loss": 141.0,
        "extra": {},
    }]
    tmp_picks.write_text(json.dumps(existing), encoding="utf-8")

    ticker = _make_ticker(close=149.0, high_52w=151.0, today_vol=3_000_000, avg_vol=1_000_000)
    yf = _make_yf_module(ticker)

    with patch.dict(sys.modules, {"yfinance": yf}):
        picks = scanner.run_scanner(
            symbols=["AAPL"],
            dry_run=True,
            active_picks_path=tmp_picks,
        )

    assert picks == []


# ---------------------------------------------------------------------------
# Test 6: deduplication does NOT block picks for different symbols
# ---------------------------------------------------------------------------

def test_deduplication_allows_different_symbol(tmp_picks):
    """Existing AAPL pick must not block MSFT."""
    today = datetime.now(timezone.utc).date().isoformat()
    existing = [{
        "id": f"eq_breakout_AAPL_{today}",
        "symbol": "AAPL",
        "source": "equity_breakout_scanner",
        "status": "open",
        "entry_date": today,
    }]
    tmp_picks.write_text(json.dumps(existing), encoding="utf-8")

    ticker = _make_ticker(close=149.0, high_52w=151.0, today_vol=3_000_000, avg_vol=1_000_000)
    yf = _make_yf_module(ticker)

    with patch.dict(sys.modules, {"yfinance": yf}):
        picks = scanner.run_scanner(
            symbols=["MSFT"],
            dry_run=True,
            active_picks_path=tmp_picks,
        )

    assert len(picks) == 1
    assert picks[0]["symbol"] == "MSFT"


# ---------------------------------------------------------------------------
# Test 7: fail-open on yfinance error — continue to next symbol
# ---------------------------------------------------------------------------

def test_fail_open_on_yfinance_error(tmp_picks):
    """A yfinance exception on one symbol must not abort the scan; others continue."""
    import pandas as pd

    call_count = [0]

    def fake_ticker(symbol):
        call_count[0] += 1
        t = MagicMock()
        if symbol == "BADTICKER":
            t.info = {}
            t.history.side_effect = RuntimeError("network timeout")
        else:
            t.info = {"fiftyTwoWeekHigh": 151.0}
            t.history.return_value = pd.DataFrame({
                "Close": [149.0] * 25,
                "Volume": [1_000_000] * 24 + [3_000_000],
                "Open": [149.0] * 25,
                "High": [149.0] * 25,
                "Low": [149.0] * 25,
            })
        return t

    yf = types.ModuleType("yfinance")
    yf.Ticker = fake_ticker

    with patch.dict(sys.modules, {"yfinance": yf}):
        picks = scanner.run_scanner(
            symbols=["BADTICKER", "AAPL"],
            dry_run=True,
            active_picks_path=tmp_picks,
        )

    assert len(picks) == 1
    assert picks[0]["symbol"] == "AAPL"


# ---------------------------------------------------------------------------
# Test 8: pick dict has ALL required fields
# ---------------------------------------------------------------------------

REQUIRED_FIELDS = [
    "id", "symbol", "asset_class", "direction", "source", "strategy",
    "status", "confidence", "entry_price", "take_profit", "stop_loss",
    "entry_date", "extra",
]
REQUIRED_EXTRA_FIELDS = ["pct_from_52wk_high", "volume_ratio", "fifty_two_week_high"]


def test_pick_has_all_required_fields(tmp_picks):
    """Every generated pick must contain the full field set required by quality_gates."""
    ticker = _make_ticker(close=149.0, high_52w=151.0, today_vol=3_000_000, avg_vol=1_000_000)
    yf = _make_yf_module(ticker)

    with patch.dict(sys.modules, {"yfinance": yf}):
        picks = scanner.run_scanner(
            symbols=["AAPL"],
            dry_run=True,
            active_picks_path=tmp_picks,
        )

    assert len(picks) == 1
    p = picks[0]
    for field in REQUIRED_FIELDS:
        assert field in p, f"Missing field: {field}"
    for ef in REQUIRED_EXTRA_FIELDS:
        assert ef in p["extra"], f"Missing extra field: {ef}"


# ---------------------------------------------------------------------------
# Test 9: dry-run does NOT modify active_picks.json
# ---------------------------------------------------------------------------

def test_dry_run_does_not_write(tmp_picks):
    """Dry-run must leave active_picks.json unchanged."""
    original_content = tmp_picks.read_text(encoding="utf-8")

    ticker = _make_ticker(close=149.0, high_52w=151.0, today_vol=3_000_000, avg_vol=1_000_000)
    yf = _make_yf_module(ticker)

    with patch.dict(sys.modules, {"yfinance": yf}):
        picks = scanner.run_scanner(
            symbols=["AAPL"],
            dry_run=True,
            active_picks_path=tmp_picks,
        )

    assert picks  # picks were returned
    assert tmp_picks.read_text(encoding="utf-8") == original_content  # file unchanged


# ---------------------------------------------------------------------------
# Test 10: live run (non-dry) writes picks to active_picks.json
# ---------------------------------------------------------------------------

def test_live_run_writes_picks(tmp_picks):
    """A non-dry-run should append new picks to active_picks.json."""
    ticker = _make_ticker(close=149.0, high_52w=151.0, today_vol=3_000_000, avg_vol=1_000_000)
    yf = _make_yf_module(ticker)

    with patch.dict(sys.modules, {"yfinance": yf}):
        picks = scanner.run_scanner(
            symbols=["AAPL"],
            dry_run=False,
            active_picks_path=tmp_picks,
        )

    assert len(picks) == 1

    saved = json.loads(tmp_picks.read_text(encoding="utf-8"))
    assert isinstance(saved, list)
    assert len(saved) == 1
    assert saved[0]["symbol"] == "AAPL"
    assert saved[0]["source"] == "equity_breakout_scanner"


# ---------------------------------------------------------------------------
# Test 11: confidence is bounded [0, 1] and varies with signal strength
# ---------------------------------------------------------------------------

def test_confidence_scaling():
    """Confidence must be in [0, 1] and increase with proximity / volume."""
    # Very near high, very high volume → high confidence
    c_high = scanner._compute_confidence(pct_from_high=0.001, volume_ratio=4.0)
    # Just at threshold boundary, just at volume threshold → lower confidence
    c_low = scanner._compute_confidence(pct_from_high=0.029, volume_ratio=1.51)

    assert 0.0 < c_low < c_high <= 0.95


# ---------------------------------------------------------------------------
# Test 12: take-profit and stop-loss geometry is correct
# ---------------------------------------------------------------------------

def test_pick_geometry(tmp_picks):
    """TP = entry * 1.08, SL = entry * 0.95 (within float rounding tolerance)."""
    ticker = _make_ticker(close=100.0, high_52w=101.0, today_vol=3_000_000, avg_vol=1_000_000)
    yf = _make_yf_module(ticker)

    with patch.dict(sys.modules, {"yfinance": yf}):
        picks = scanner.run_scanner(
            symbols=["AAPL"],
            dry_run=True,
            active_picks_path=tmp_picks,
        )

    assert len(picks) == 1
    p = picks[0]
    assert abs(p["take_profit"] - p["entry_price"] * 1.08) < 0.01
    assert abs(p["stop_loss"] - p["entry_price"] * 0.95) < 0.01


# ---------------------------------------------------------------------------
# Test 13: yfinance missing fiftyTwoWeekHigh → skip symbol (fail-open)
# ---------------------------------------------------------------------------

def test_missing_52wk_high_skips_symbol(tmp_picks):
    """If info has no fiftyTwoWeekHigh, the symbol must be skipped gracefully."""
    ticker = _make_ticker(close=149.0, high_52w=None, today_vol=3_000_000, avg_vol=1_000_000,
                          fail_info=True)
    yf = _make_yf_module(ticker)

    with patch.dict(sys.modules, {"yfinance": yf}):
        picks = scanner.run_scanner(
            symbols=["AAPL"],
            dry_run=True,
            active_picks_path=tmp_picks,
        )

    assert picks == []


# ---------------------------------------------------------------------------
# Test 14: pick ID is deterministic and contains symbol + date
# ---------------------------------------------------------------------------

def test_pick_id_format(tmp_picks):
    """Pick ID must match pattern eq_breakout_<SYMBOL>_<YYYY-MM-DD>."""
    import re

    ticker = _make_ticker(close=149.0, high_52w=151.0, today_vol=3_000_000, avg_vol=1_000_000)
    yf = _make_yf_module(ticker)

    with patch.dict(sys.modules, {"yfinance": yf}):
        picks = scanner.run_scanner(
            symbols=["AAPL"],
            dry_run=True,
            active_picks_path=tmp_picks,
        )

    assert picks
    pattern = re.compile(r"^eq_breakout_AAPL_\d{4}-\d{2}-\d{2}$")
    assert pattern.match(picks[0]["id"]), f"Bad ID format: {picks[0]['id']}"
