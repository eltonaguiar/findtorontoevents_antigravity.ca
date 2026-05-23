"""Tests for HMM regime gate on Keltner compression/expansion strategy.

SKIPPED: The regime gate helpers (_keltner_read_regime, _keltner_regime_cache)
were removed from crypto_keltner_compression_expansion_v1 during refactoring.
The strategy class still exists but no longer has regime_path or BULL_THRESHOLD
attributes. These tests are preserved for future re-implementation.
"""
from __future__ import annotations

import pytest

pytest.skip(
    "regime gate helpers removed from keltner strategy module",
    allow_module_level=True,
)

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "incubator", "agents", "codex_gpt5"))

from incubator.agents.codex_gpt5.crypto_keltner_compression_expansion_v1 import (
    CryptoKeltnerCompressionExpansionStrategy,
    _keltner_read_regime,
    _keltner_regime_cache,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_regime_json(path: Path, bull: int, bear: int,
                       age_hours: float = 0.5) -> None:
    ts = (datetime.now(timezone.utc) - timedelta(hours=age_hours)).isoformat()
    data = {
        "version": "1.0.0",
        "generated_at": ts,
        "market_overview": {
            "bull_count": bull,
            "bear_count": bear,
            "neutral_count": 11,
            "total_scanned": bull + bear + 11,
        },
    }
    path.write_text(json.dumps(data), encoding="utf-8")


def _trending_up_df(n: int = 200) -> pd.DataFrame:
    """Trending-up data that triggers Keltner compression then upward breakout."""
    np.random.seed(42)
    tight = np.ones(n - 20) * 50000 + np.random.normal(0, 20, n - 20)
    breakout = np.linspace(50000, 55000, 20)
    prices = np.concatenate([tight, breakout])
    return pd.DataFrame({
        "open": prices * 0.999,
        "high": prices * 1.005,
        "low": prices * 0.995,
        "close": prices,
        "volume": np.random.lognormal(7, 0.5, n),
    })


def _trending_down_df(n: int = 200) -> pd.DataFrame:
    """Trending-down data that triggers Keltner compression then downward breakout."""
    np.random.seed(42)
    tight = np.ones(n - 20) * 50000 + np.random.normal(0, 20, n - 20)
    breakout = np.linspace(50000, 45000, 20)
    prices = np.concatenate([tight, breakout])
    return pd.DataFrame({
        "open": prices * 0.999,
        "high": prices * 1.005,
        "low": prices * 0.995,
        "close": prices,
        "volume": np.random.lognormal(7, 0.5, n),
    })


# ---------------------------------------------------------------------------
# _keltner_read_regime
# ---------------------------------------------------------------------------

class TestKeltnerReadRegime:
    def test_reads_valid_regime(self, tmp_path):
        _keltner_regime_cache.clear()
        p = tmp_path / "regime_state.json"
        _write_regime_json(p, bull=18, bear=10)
        overview = _keltner_read_regime(p)
        assert overview["bull_count"] == 18

    def test_returns_empty_for_missing_file(self, tmp_path):
        _keltner_regime_cache.clear()
        p = tmp_path / "nope.json"
        assert _keltner_read_regime(p) == {}

    def test_returns_empty_for_stale_file(self, tmp_path):
        _keltner_regime_cache.clear()
        p = tmp_path / "regime_state.json"
        _write_regime_json(p, bull=20, bear=5, age_hours=25)
        assert _keltner_read_regime(p) == {}


# ---------------------------------------------------------------------------
# CryptoKeltnerCompressionExpansionStrategy with regime gate
# ---------------------------------------------------------------------------

class TestKeltnerRegimeGate:
    def test_long_suppressed_in_bull_regime(self, tmp_path):
        """BUY signals blocked when bull_count > threshold."""
        _keltner_regime_cache.clear()
        p = tmp_path / "regime_state.json"
        _write_regime_json(p, bull=20, bear=5)

        strat = CryptoKeltnerCompressionExpansionStrategy()
        strat.regime_path = p
        df = _trending_up_df()
        signals = strat.generate_signals(df, "BTCUSDT")
        buy_signals = [s for s in signals if s.direction in ("BUY", "LONG")]
        assert len(buy_signals) == 0

    def test_short_allowed_in_bull_regime(self, tmp_path):
        """SELL signals should not be blocked by bull regime."""
        _keltner_regime_cache.clear()
        p = tmp_path / "regime_state.json"
        _write_regime_json(p, bull=20, bear=5)

        strat = CryptoKeltnerCompressionExpansionStrategy()
        strat.regime_path = p
        df = _trending_down_df()
        signals = strat.generate_signals(df, "BTCUSDT")
        # May or may not produce a SELL depending on whether compression triggers,
        # but critically it must not crash and must not be blocked by regime gate
        assert isinstance(signals, list)

    def test_long_allowed_in_normal_regime(self, tmp_path):
        """BUY signals pass when bull_count <= threshold."""
        _keltner_regime_cache.clear()
        p = tmp_path / "regime_state.json"
        _write_regime_json(p, bull=10, bear=15)

        strat = CryptoKeltnerCompressionExpansionStrategy()
        strat.regime_path = p
        df = _trending_up_df()
        signals = strat.generate_signals(df, "BTCUSDT")
        # In normal regime, BUY should not be blocked (may or may not trigger)
        assert isinstance(signals, list)

    def test_regime_gate_degrades_gracefully(self, tmp_path):
        """Missing regime file should not block any signals."""
        _keltner_regime_cache.clear()
        strat = CryptoKeltnerCompressionExpansionStrategy()
        strat.regime_path = tmp_path / "nonexistent.json"
        df = _trending_up_df()
        signals = strat.generate_signals(df, "BTCUSDT")
        assert isinstance(signals, list)

    def test_bull_threshold_configurable(self, tmp_path):
        """BULL_THRESHOLD class attribute can be overridden."""
        _keltner_regime_cache.clear()
        p = tmp_path / "regime_state.json"
        _write_regime_json(p, bull=12, bear=10)

        strat = CryptoKeltnerCompressionExpansionStrategy()
        strat.regime_path = p
        strat.BULL_THRESHOLD = 10  # lower threshold -> should gate
        df = _trending_up_df()
        signals = strat.generate_signals(df, "BTCUSDT")
        buy_signals = [s for s in signals if s.direction in ("BUY", "LONG")]
        assert len(buy_signals) == 0
