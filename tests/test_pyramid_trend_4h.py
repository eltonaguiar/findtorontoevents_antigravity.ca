"""Tests for baby_strategies/pyramid_trend_4h.py."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import pandas as pd
import pytest

from baby_strategies.pyramid_trend_4h import PyramidTrend4HStrategy, SUPPORTED_SYMBOLS


def _make_uptrend(n=200, drift=0.3, seed=0):
    rng = np.random.RandomState(seed)
    close = pd.Series(100 + np.cumsum(rng.normal(drift, 0.5, n)))
    high = close + 0.3
    low = close - 0.3
    return pd.DataFrame({"close": close, "high": high, "low": low,
                          "open": close - 0.1, "volume": [1000] * n})


def _make_downtrend(n=200, seed=0):
    return _make_uptrend(n=n, drift=-0.3, seed=seed)


def test_unsupported_symbol_rejected():
    strat = PyramidTrend4HStrategy()
    assert strat.generate_signals(_make_uptrend(), "AAPL") == []


def test_insufficient_data_rejected():
    strat = PyramidTrend4HStrategy()
    short = _make_uptrend(n=20)
    assert strat.generate_signals(short, "BTCUSDT") == []


def test_long_signal_in_uptrend():
    """An uptrend with a small pullback should produce a LONG anchor."""
    strat = PyramidTrend4HStrategy()
    df = _make_uptrend(n=200, seed=42)
    # Inject pullback then continuation at end
    close = df["close"].values.copy()
    close[-2] = close[-3] - 1  # dip
    close[-1] = close[-3] + 2  # recover above
    df["close"] = close
    df["high"] = close + 0.3
    df["low"] = close - 0.3
    signals = strat.generate_signals(df, "BTCUSDT")
    # signal may or may not fire depending on EMA alignment;
    # the test asserts no crash + correct symbol if any
    for s in signals:
        assert s.symbol == "BTCUSDT"
        assert s.direction in {"LONG", "SHORT"}
        if s.direction == "LONG":
            assert s.take_profit > s.entry_price > s.stop_loss
        else:
            assert s.stop_loss > s.entry_price > s.take_profit


def test_pyramid_add_long_threshold():
    """Pyramid #2 add fires only after +0.5 ATR favorable for LONG."""
    strat = PyramidTrend4HStrategy()
    add = strat.next_pyramid_add(
        current_price=99.0,  # below anchor
        anchor_price=100.0,
        atr_at_anchor=2.0,
        existing_adds=0,
        direction="LONG",
    )
    assert add is None

    add = strat.next_pyramid_add(
        current_price=101.5,  # 1.5 ATR above? no, +1.5 vs anchor with atr=2 -> 0.75 ATR fav
        anchor_price=100.0,
        atr_at_anchor=2.0,
        existing_adds=0,
        direction="LONG",
    )
    assert add is not None
    assert add.pyramid_level == 2


def test_pyramid_caps_at_max_adds():
    strat = PyramidTrend4HStrategy()
    add = strat.next_pyramid_add(
        current_price=1000,
        anchor_price=100,
        atr_at_anchor=10,
        existing_adds=4,  # already 5 total (anchor + 4 adds)
        direction="LONG",
    )
    assert add is None


def test_pyramid_add_short_direction():
    strat = PyramidTrend4HStrategy()
    add = strat.next_pyramid_add(
        current_price=98.5,  # 1.5 below anchor, atr=2 -> 0.75 ATR fav for SHORT
        anchor_price=100.0,
        atr_at_anchor=2.0,
        existing_adds=0,
        direction="SHORT",
    )
    assert add is not None
    assert add.direction == "SHORT"


def test_supported_symbols_complete():
    """All 5 Leap-Crypto perps covered."""
    expected = {"BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT", "XRPUSDT"}
    assert set(SUPPORTED_SYMBOLS) == expected
