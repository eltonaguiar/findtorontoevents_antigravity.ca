"""Tests for alpha_engine/run_atr_gate and atr_percentile_gate_scanner."""

from __future__ import annotations

import pandas as pd
import numpy as np
from alpha_engine.proven_edge_strategies import atr_percentile_gate_scanner


def _make_mock_df(bars: int = 200, base_price: float = 100.0) -> pd.DataFrame:
    """Generate synthetic OHLCV data for testing."""
    np.random.seed(42)
    closes = base_price + np.cumsum(np.random.randn(bars) * 0.5)
    highs = closes + np.abs(np.random.randn(bars) * 0.3)
    lows = closes - np.abs(np.random.randn(bars) * 0.3)
    volumes = np.random.randint(1000, 10000, bars)
    return pd.DataFrame({
        "Close": closes, "High": highs, "Low": lows, "Volume": volumes,
    })


def test_atr_gate_returns_list():
    """atr_percentile_gate_scanner should return a list (possibly empty)."""
    data = {"BTC-USD": _make_mock_df()}
    signals = atr_percentile_gate_scanner(data)
    assert isinstance(signals, list)


def test_atr_gate_includes_required_keys():
    """Each signal should have symbol, direction, confidence, entry, TP, SL."""
    data = {"ETH-USD": _make_mock_df(bars=300, base_price=2000.0)}
    signals = atr_percentile_gate_scanner(data)
    for s in signals:
        for key in ("symbol", "direction", "confidence", "entry_price",
                    "take_profit", "stop_loss", "strategy"):
            assert key in s, f"Missing key: {key}"


def test_atr_gate_strategy_label():
    """All signals should be tagged with the correct strategy name."""
    data = {"SOL-USD": _make_mock_df(bars=200, base_price=150.0)}
    signals = atr_percentile_gate_scanner(data)
    for s in signals:
        assert s["strategy"] == "atr_percentile_gate_scanner"


def test_atr_gate_skips_insufficient_data():
    """Scanner should return empty list if data has < 110 bars."""
    data = {"BTC-USD": _make_mock_df(bars=50)}
    signals = atr_percentile_gate_scanner(data)
    assert len(signals) == 0


def test_atr_gate_confidence_bounds():
    """Confidence should be between 0 and 1."""
    data = {"BTC-USD": _make_mock_df(bars=300)}
    signals = atr_percentile_gate_scanner(data)
    for s in signals:
        assert 0 < s["confidence"] <= 1.0, f"Bad confidence: {s['confidence']}"
