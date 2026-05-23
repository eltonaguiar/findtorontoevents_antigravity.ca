"""M-017: position_sizer.py standalone (no `indicators` package dependency)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from alpha_engine.position_sizer import (
    PositionSizer,
    REGIME_SIZE_MULTIPLIERS,
    ema,
    sma,
    rsi,
    atr,
    adx,
    bollinger_bands,
)


def _make_ohlcv(n: int = 150, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = pd.Series(100.0 + np.cumsum(rng.standard_normal(n) * 0.5))
    high = close + rng.uniform(0.1, 0.5, n)
    low = close - rng.uniform(0.1, 0.5, n)
    return pd.DataFrame({"close": close, "high": high, "low": low})


class TestInlineIndicators:
    def test_ema_length(self):
        s = pd.Series([float(x) for x in range(50)])
        result = ema(s, 9)
        assert len(result) == 50

    def test_sma_length(self):
        s = pd.Series([float(x) for x in range(50)])
        result = sma(s, 10)
        assert len(result) == 50

    def test_rsi_bounded(self):
        df = _make_ohlcv()
        result = rsi(df["close"], 14).dropna()
        assert result.between(0, 100).all(), "RSI must be in [0, 100]"

    def test_atr_positive(self):
        df = _make_ohlcv()
        result = atr(df["high"], df["low"], df["close"], 14).dropna()
        assert (result >= 0).all(), "ATR must be non-negative"

    def test_adx_returns_series(self):
        df = _make_ohlcv()
        result = adx(df["high"], df["low"], df["close"], 14)
        assert len(result) == len(df)

    def test_bollinger_bandwidth_positive(self):
        df = _make_ohlcv()
        bb = bollinger_bands(df["close"], 20)
        assert "bandwidth" in bb
        assert (bb["bandwidth"].dropna() >= 0).all()


class TestRegimeMultipliers:
    def test_all_cells_present(self):
        for trend in ("BULL", "BEAR", "NEUTRAL"):
            for vol in ("EXPANSION", "COMPRESSION", "NORMAL"):
                key = f"{trend}_{vol}"
                assert key in REGIME_SIZE_MULTIPLIERS, f"Missing {key}"

    def test_bull_expansion_is_max(self):
        assert REGIME_SIZE_MULTIPLIERS["BULL_EXPANSION"] >= max(
            v for k, v in REGIME_SIZE_MULTIPLIERS.items() if "BEAR" in k
        )


class TestPositionSizer:
    def test_size_signals_adds_keys(self):
        df = _make_ohlcv()
        sizer = PositionSizer()
        signals = [{"symbol": "A", "confidence": 0.6}]
        result = sizer.size_signals(signals, {"A": df})
        assert "position_size_pct" in result[0]
        assert "regime_cell" in result[0]
        assert "regime_multiplier" in result[0]

    def test_size_capped_at_max(self):
        df = _make_ohlcv()
        sizer = PositionSizer(base_risk_pct=10.0, max_risk_pct=5.0)
        signals = [{"symbol": "A", "confidence": 1.0}]
        result = sizer.size_signals(signals, {"A": df})
        assert result[0]["position_size_pct"] <= 5.0

    def test_missing_data_fallback(self):
        sizer = PositionSizer()
        signals = [{"symbol": "MISSING", "confidence": 0.5}]
        result = sizer.size_signals(signals, {})
        assert result[0]["regime_cell"] == "NEUTRAL_NORMAL"

    def test_kelly_fraction_positive_edge(self):
        k = PositionSizer.kelly_fraction(0.60, 0.03, 0.02)
        assert k > 0, "Positive-edge strategy should have positive Kelly"
        assert k <= 0.25, "Kelly capped at 25%"

    def test_kelly_fraction_negative_edge(self):
        k = PositionSizer.kelly_fraction(0.40, 0.02, 0.03)
        assert k == 0.0, "Negative-edge strategy should return 0"

    def test_portfolio_kelly_size_total_cap(self):
        df = _make_ohlcv()
        sizer = PositionSizer(base_risk_pct=5.0)
        signals = [
            {"symbol": "A", "confidence": 0.9, "win_rate": 0.6, "avg_win_pct": 0.05, "avg_loss_pct": 0.02},
            {"symbol": "B", "confidence": 0.9, "win_rate": 0.6, "avg_win_pct": 0.05, "avg_loss_pct": 0.02},
            {"symbol": "C", "confidence": 0.9, "win_rate": 0.6, "avg_win_pct": 0.05, "avg_loss_pct": 0.02},
            {"symbol": "D", "confidence": 0.9, "win_rate": 0.6, "avg_win_pct": 0.05, "avg_loss_pct": 0.02},
            {"symbol": "E", "confidence": 0.9, "win_rate": 0.6, "avg_win_pct": 0.05, "avg_loss_pct": 0.02},
        ]
        data = {s["symbol"]: df for s in signals}
        result = sizer.portfolio_kelly_size(signals, data, max_total_risk_pct=20.0)
        total = sum(r["position_size_pct"] for r in result)
        assert total <= 20.01, f"Total risk {total:.2f}% exceeded 20% cap"

    def test_portfolio_kelly_size_adds_position_usd(self):
        df = _make_ohlcv()
        sizer = PositionSizer()
        signals = [{"symbol": "A", "confidence": 0.5}]
        result = sizer.portfolio_kelly_size(signals, {"A": df}, portfolio_value=10000.0)
        assert "position_usd" in result[0]
        assert result[0]["position_usd"] >= 0

    def test_compute_var_structure(self):
        returns = pd.Series(np.random.randn(100) * 0.01)
        v = PositionSizer.compute_var(returns)
        assert "var" in v and "cvar" in v and "n_obs" in v
        assert v["var"] >= 0
        assert v["cvar"] >= v["var"]
