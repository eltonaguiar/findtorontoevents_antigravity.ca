"""Tests for alpha_engine.incubator_grad_strategies.

Covers both forward-deployed Tier 1 backtest champions:
  * volume_weighted_candle_sequence
  * market_structure_volume

Verifies graceful no-op on bad input, signal firing on planted patterns,
rollback-env kill switches, and signal-dict schema completeness.
"""
from __future__ import annotations

import os
from datetime import datetime

import numpy as np
import pandas as pd
import pytest

from alpha_engine.incubator_grad_strategies import (
    market_structure_volume,
    volume_weighted_candle_sequence,
)


REQUIRED_KEYS = {
    "symbol", "direction", "strategy", "asset_class", "category",
    "timeframe", "entry_price", "stop_loss", "take_profit",
    "confidence", "generated_at",
}


# --------------------------------------------------------------------------- #
#  Fixtures
# --------------------------------------------------------------------------- #

def _flat_df(n: int = 100, base: float = 100.0) -> pd.DataFrame:
    """Boring flat data — no signal should fire."""
    rng = np.random.default_rng(0)
    close = base + rng.normal(0, 0.1, n)
    return pd.DataFrame({
        "open": close + rng.normal(0, 0.02, n),
        "high": close + 0.05,
        "low": close - 0.05,
        "close": close,
        "volume": np.full(n, 200.0),
    })


def _vw_uptrend_df(n: int = 80, base: float = 100.0) -> pd.DataFrame:
    """OHLCV with the last 5 bars: strong consecutive up + top-quartile volume."""
    rng = np.random.default_rng(7)
    close = base + np.cumsum(rng.normal(0, 0.05, n))
    volume = rng.uniform(100, 200, n)
    # Make the trailing 5 bars strictly increasing with very high volume
    for i in range(n - 5, n):
        close[i] = close[i - 1] + 0.5  # +0.5 each bar, deterministic up
        volume[i] = 1500.0             # well above any rolling 0.75 quantile
    high = close + 0.10
    low = close - 0.10
    open_ = close - 0.05
    return pd.DataFrame({
        "open": open_, "high": high, "low": low, "close": close,
        "volume": volume,
    })


def _msv_bullish_bos_df(n: int = 200) -> pd.DataFrame:
    """Plant a textbook bullish BOS: HH after a LH, with terminal volume spike."""
    rng = np.random.default_rng(3)
    close = np.full(n, 100.0)
    # Build: rise to 110, dip to 105 (prev_sh=110), rise to 108 (lower high
    # at last_sh=108 <= prev_sh=110), dip to 103 (last_sl), then break out
    # above 110 on the last bar.
    seg_len = (n - 5) // 5
    # Segment 1: rise 100 -> 110
    close[0:seg_len] = np.linspace(100, 110, seg_len)
    # Segment 2: dip 110 -> 105
    close[seg_len:2 * seg_len] = np.linspace(110, 105, seg_len)
    # Segment 3: rise 105 -> 108  (LH = 108)
    close[2 * seg_len:3 * seg_len] = np.linspace(105, 108, seg_len)
    # Segment 4: dip 108 -> 103   (HL = 103)
    close[3 * seg_len:4 * seg_len] = np.linspace(108, 103, seg_len)
    # Segment 5: rise 103 -> 109  (close to but below prev_sh)
    close[4 * seg_len:n - 5] = np.linspace(103, 109, n - 5 - 4 * seg_len)
    # Final 5 bars: BOS — break above prev_sh=110 with volume spike
    close[n - 5:] = [110.5, 111.0, 111.5, 112.0, 113.0]
    high = close + 0.20
    low = close - 0.20
    open_ = close - 0.10
    volume = rng.uniform(100, 200, n)
    volume[-1] = 5000.0  # massive volume spike on the breakout bar
    return pd.DataFrame({
        "open": open_, "high": high, "low": low, "close": close,
        "volume": volume,
    })


# --------------------------------------------------------------------------- #
#  Empty / bad input
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("fn", [
    volume_weighted_candle_sequence,
    market_structure_volume,
])
def test_empty_data_returns_empty_list(fn):
    assert fn({}) == []
    assert fn(None) == []  # type: ignore[arg-type]


@pytest.mark.parametrize("fn", [
    volume_weighted_candle_sequence,
    market_structure_volume,
])
def test_insufficient_bars_returns_empty(fn):
    df = _flat_df(n=10)  # below MIN_BARS=60
    assert fn({"BTCUSDT": df}) == []


@pytest.mark.parametrize("fn", [
    volume_weighted_candle_sequence,
    market_structure_volume,
])
def test_missing_columns_returns_empty(fn):
    df = pd.DataFrame({"close": np.arange(100)})
    assert fn({"BTCUSDT": df}) == []


@pytest.mark.parametrize("fn", [
    volume_weighted_candle_sequence,
    market_structure_volume,
])
def test_flat_data_no_signal(fn):
    sigs = fn({"BTCUSDT": _flat_df(n=120)})
    assert sigs == []


# --------------------------------------------------------------------------- #
#  Signal firing on planted patterns
# --------------------------------------------------------------------------- #

def test_vwcandle_fires_long_on_planted_uptrend():
    sigs = volume_weighted_candle_sequence({"SOLUSDT": _vw_uptrend_df()})
    assert len(sigs) == 1, f"expected 1 signal, got {len(sigs)}"
    s = sigs[0]
    assert s["direction"] == "LONG"
    assert s["strategy"] == "volume_weighted_candle_sequence"
    assert s["symbol"] == "SOLUSDT"
    assert s["asset_class"] == "CRYPTO"
    assert s["take_profit"] > s["entry_price"] > s["stop_loss"]
    assert 0.50 <= s["confidence"] <= 0.95


def test_msv_fires_long_on_planted_bos():
    sigs = market_structure_volume({"ETHUSDT": _msv_bullish_bos_df()})
    assert len(sigs) == 1, f"expected 1 signal, got {len(sigs)}"
    s = sigs[0]
    assert s["direction"] == "LONG"
    assert s["strategy"] == "market_structure_volume"
    assert s["symbol"] == "ETHUSDT"
    assert s["asset_class"] == "CRYPTO"
    assert s["take_profit"] > s["entry_price"] > s["stop_loss"]
    assert 0.50 <= s["confidence"] <= 0.95


def test_vwcandle_handles_equity_symbol():
    df = _vw_uptrend_df()
    sigs = volume_weighted_candle_sequence({"AAPL": df})
    assert len(sigs) == 1
    assert sigs[0]["asset_class"] == "EQUITY"


def test_msv_handles_equity_symbol():
    df = _msv_bullish_bos_df()
    sigs = market_structure_volume({"AAPL": df})
    assert len(sigs) == 1
    assert sigs[0]["asset_class"] == "EQUITY"


# --------------------------------------------------------------------------- #
#  Rollback envs
# --------------------------------------------------------------------------- #

def test_vwcandle_rollback_env_disables(monkeypatch):
    monkeypatch.setenv("VWCANDLE_DISABLED", "1")
    sigs = volume_weighted_candle_sequence({"SOLUSDT": _vw_uptrend_df()})
    assert sigs == []


def test_msv_rollback_env_disables(monkeypatch):
    monkeypatch.setenv("MSV_DISABLED", "1")
    sigs = market_structure_volume({"ETHUSDT": _msv_bullish_bos_df()})
    assert sigs == []


# --------------------------------------------------------------------------- #
#  Signal schema validation
# --------------------------------------------------------------------------- #

def _assert_schema(s: dict) -> None:
    missing = REQUIRED_KEYS - set(s.keys())
    assert not missing, f"signal missing keys: {missing}"
    assert s["direction"] in {"LONG", "SHORT"}
    assert s["asset_class"] in {"CRYPTO", "EQUITY"}
    assert isinstance(s["entry_price"], (int, float))
    assert isinstance(s["stop_loss"], (int, float))
    assert isinstance(s["take_profit"], (int, float))
    assert isinstance(s["confidence"], (int, float))
    assert 0.0 <= s["confidence"] <= 1.0
    # generated_at must parse as ISO
    datetime.fromisoformat(s["generated_at"])


def test_vwcandle_schema():
    sigs = volume_weighted_candle_sequence({"SOLUSDT": _vw_uptrend_df()})
    assert sigs
    _assert_schema(sigs[0])


def test_msv_schema():
    sigs = market_structure_volume({"ETHUSDT": _msv_bullish_bos_df()})
    assert sigs
    _assert_schema(sigs[0])


# --------------------------------------------------------------------------- #
#  Multi-symbol fan-out
# --------------------------------------------------------------------------- #

def test_vwcandle_multi_symbol_fanout():
    # Truly flat: constant close + constant volume — no direction, no vol
    # spike — guarantees no signal.
    n = 100
    flat = pd.DataFrame({
        "open": np.full(n, 100.0),
        "high": np.full(n, 100.0),
        "low": np.full(n, 100.0),
        "close": np.full(n, 100.0),
        "volume": np.full(n, 200.0),
    })
    data = {
        "SOLUSDT": _vw_uptrend_df(),
        "BORING": flat,
    }
    sigs = volume_weighted_candle_sequence(data)
    syms = {s["symbol"] for s in sigs}
    assert "SOLUSDT" in syms
    assert "BORING" not in syms
