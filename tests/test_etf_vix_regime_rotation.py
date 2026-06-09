"""Tests for alpha_engine/etf_vix_regime_rotation."""

from __future__ import annotations

import pandas as pd
import numpy as np
from alpha_engine.etf_vix_regime_rotation import (
    etf_vix_regime_rotation,
    VIX_SECTOR_SYMBOLS,
)


def _mock_etf_df(bars: int = 500, base: float = 100.0, trend: float = 0.001) -> pd.DataFrame:
    """Monotonic uptrend → high momentum → triggers LONG signal."""
    np.random.seed(42)
    prices = base * (1 + trend) ** np.arange(bars) + np.cumsum(np.random.randn(bars) * 0.2)
    closes = prices
    highs = closes * 1.02
    lows = closes * 0.98
    volumes = np.random.randint(50000, 200000, bars)
    return pd.DataFrame({
        "Close": closes, "High": highs, "Low": lows, "Volume": volumes,
    })


def test_vix_rotation_returns_list():
    """Should return a list (possibly empty)."""
    vix_df = pd.DataFrame({"Close": [20.0] * 300})
    data = {"^VIX": vix_df}
    for sym in VIX_SECTOR_SYMBOLS[:3]:
        data[sym] = _mock_etf_df()
    signals = etf_vix_regime_rotation(data)
    assert isinstance(signals, list)


def test_vix_rotation_blocked_when_vix_high():
    """No signals when VIX > 25."""
    vix_df = pd.DataFrame({"Close": [30.0] * 300})
    data = {"^VIX": vix_df}
    for sym in VIX_SECTOR_SYMBOLS[:3]:
        data[sym] = _mock_etf_df()
    signals = etf_vix_regime_rotation(data)
    assert len(signals) == 0, "Expected no signals when VIX > 25"


def test_vix_rotation_includes_required_keys():
    """Each signal should have standard pick keys."""
    vix_df = pd.DataFrame({"Close": [15.0] * 300})
    data = {"^VIX": vix_df}
    for sym in VIX_SECTOR_SYMBOLS[:5]:
        data[sym] = _mock_etf_df()
    signals = etf_vix_regime_rotation(data)
    for s in signals:
        for key in ("symbol", "strategy", "signal_type", "entry_price",
                    "take_profit", "stop_loss", "confidence", "risk_reward"):
            assert key in s, f"Missing key: {key}"


def test_vix_rotation_strategy_label():
    """Strategy name should match."""
    vix_df = pd.DataFrame({"Close": [18.0] * 300})
    data = {"^VIX": vix_df}
    for sym in VIX_SECTOR_SYMBOLS[:3]:
        data[sym] = _mock_etf_df()
    signals = etf_vix_regime_rotation(data)
    for s in signals:
        assert s["strategy"] == "etf_vix_regime_rotation"


def test_vix_rotation_category():
    """Category should be 'etf'."""
    vix_df = pd.DataFrame({"Close": [22.0] * 300})
    data = {"^VIX": vix_df}
    for sym in VIX_SECTOR_SYMBOLS[:3]:
        data[sym] = _mock_etf_df()
    signals = etf_vix_regime_rotation(data)
    for s in signals:
        assert s.get("category") == "etf"
