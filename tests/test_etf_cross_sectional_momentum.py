"""Tests for H-003: ETF Cross-Sectional 12-1 Momentum strategy.

Unit tests for etf_cross_sectional_momentum() in alpha_engine/etf_strategies.py.
Tests use synthetic price series — no network calls.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
_ALPHA_ENGINE_DIR = str(REPO_ROOT / "alpha_engine")
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
# etf_strategies.py uses `from config import ...` which requires alpha_engine/ on path
if _ALPHA_ENGINE_DIR not in sys.path:
    sys.path.insert(0, _ALPHA_ENGINE_DIR)

from alpha_engine.etf_strategies import etf_cross_sectional_momentum, _H003_UNIVERSE, _ETF_BLACKLIST_EXCLUDE


def _make_df(n: int = 260, start_price: float = 100.0, trend: float = 0.0) -> pd.DataFrame:
    """Build a synthetic OHLCV DataFrame with optional trend."""
    prices = [start_price * (1 + trend) ** i for i in range(n)]
    noise = np.random.default_rng(42).normal(0, 0.005, n)
    close = np.array(prices) * (1 + noise)
    high = close * 1.005
    low = close * 0.995
    idx = pd.date_range(end=datetime.now(timezone.utc), periods=n, freq="D")
    return pd.DataFrame({"Open": close, "High": high, "Low": low, "Close": close, "Volume": 1_000_000}, index=idx)


def _build_universe(positive_etfs: list[str], flat_etfs: list[str] | None = None) -> dict[str, pd.DataFrame]:
    """Build synthetic data dict. positive_etfs get positive 12m-1m momentum."""
    data: dict[str, pd.DataFrame] = {}
    for sym in _H003_UNIVERSE:
        if sym in (flat_etfs or []):
            data[sym] = _make_df(260, trend=0.0)
        elif sym in positive_etfs:
            data[sym] = _make_df(260, trend=0.001)  # ~25% annual
        else:
            data[sym] = _make_df(260, trend=-0.0005)  # slightly negative
    return data


class TestH003CrossSectionalMomentum:

    def test_returns_empty_when_gate_disabled(self, monkeypatch):
        monkeypatch.setenv("ETF_CS_MOM_ENABLED", "0")
        data = _build_universe(["XLK", "QQQ", "SPY"])
        result = etf_cross_sectional_momentum(data)
        assert result == []

    def test_returns_empty_when_no_positive_momentum(self):
        """No ETF has positive 12m-1m return → no signals."""
        data = {sym: _make_df(260, trend=-0.0005) for sym in _H003_UNIVERSE}
        result = etf_cross_sectional_momentum(data)
        assert result == []

    def test_returns_at_most_3_signals(self):
        """Top 3 limit regardless of how many ETFs have positive momentum."""
        data = _build_universe(positive_etfs=["XLK", "QQQ", "SPY", "EEM", "EFA", "MTUM"])
        result = etf_cross_sectional_momentum(data)
        assert len(result) <= 3

    def test_signals_have_required_fields(self):
        data = _build_universe(positive_etfs=["XLK", "QQQ", "SPY"])
        result = etf_cross_sectional_momentum(data)
        if not result:
            pytest.skip("No signals generated with this data")
        for sig in result:
            assert sig["strategy"] == "etf_cross_sectional_momentum"
            assert sig["signal_type"] == "BUY"
            assert sig["asset_class"] == "ETF"
            assert sig["direction"] == "LONG"
            assert "entry_price" in sig
            assert "take_profit" in sig
            assert "stop_loss" in sig
            assert sig["confidence"] >= 0.55
            assert sig["risk_reward"] >= 1.20

    def test_blacklisted_symbols_excluded(self):
        """IWM, GLD, SLV must never appear in signals even if they have positive momentum."""
        data = _build_universe(positive_etfs=list(_H003_UNIVERSE))
        # Also add blacklisted symbols with high positive momentum
        for sym in _ETF_BLACKLIST_EXCLUDE:
            data[sym] = _make_df(260, trend=0.002)
        result = etf_cross_sectional_momentum(data)
        signal_symbols = {s["symbol"] for s in result}
        assert signal_symbols.isdisjoint(_ETF_BLACKLIST_EXCLUDE), (
            f"Blacklisted ETF found in signals: {signal_symbols & _ETF_BLACKLIST_EXCLUDE}"
        )

    def test_insufficient_data_skipped(self):
        """ETFs with fewer than 253 bars are skipped (need 12m-1m lookback)."""
        short_data = {sym: _make_df(100, trend=0.001) for sym in _H003_UNIVERSE}
        result = etf_cross_sectional_momentum(short_data)
        assert result == []

    def test_universe_excludes_etf_blacklist(self):
        """H003_UNIVERSE constant must not contain ETF_BLACKLIST symbols."""
        overlap = set(_H003_UNIVERSE) & _ETF_BLACKLIST_EXCLUDE
        assert not overlap, f"ETF_BLACKLIST symbols in H003_UNIVERSE: {overlap}"

    def test_strategy_registered_in_etf_strategies(self):
        """Verify strategy is in ETF_STRATEGIES registry."""
        from alpha_engine.etf_strategies import ETF_STRATEGIES
        assert "etf_cross_sectional_momentum" in ETF_STRATEGIES

    def test_strategy_registered_in_etf_scanner(self):
        """Verify strategy is in STRATEGIES list in etf_scanner."""
        from alpha_engine.etf_scanner import STRATEGIES
        names = [name for name, _ in STRATEGIES]
        assert "etf_cross_sectional_momentum" in names


class TestM111LeveragedETFRemoval:
    """M-111 (2026-05-18): TQQQ/SQQQ/SOXL removed from ETF_SYMBOLS.

    3x leveraged ETFs are structurally mismatched with Antonacci 12-month momentum —
    3x vol invalidates TP/SL calibration and SQQQ SHORT creates a confusing
    synthetic-long-via-double-inverse signal. Re-add only with a dedicated
    leveraged_etf_decay strategy using appropriate vol-adjusted parameters.
    """

    def test_leveraged_etfs_not_in_etf_symbols(self):
        """TQQQ, SQQQ, SOXL must not be in ETF_SYMBOLS (M-111 regression guard)."""
        from alpha_engine.config import ETF_SYMBOLS
        leveraged = {"TQQQ", "SQQQ", "SOXL"}
        present = leveraged & set(ETF_SYMBOLS)
        assert not present, (
            f"M-111: leveraged ETFs must not be in ETF_SYMBOLS: {present}. "
            "Re-add only with a dedicated vol-adjusted strategy (leveraged_etf_decay)."
        )

    def test_leveraged_etfs_not_in_h003_universe(self):
        """H003_UNIVERSE must not include leveraged ETFs."""
        leveraged = {"TQQQ", "SQQQ", "SOXL"}
        present = leveraged & set(_H003_UNIVERSE)
        assert not present, f"Leveraged ETFs must not be in H003_UNIVERSE: {present}"

    def test_vixy_not_in_etf_symbols(self):
        """M-112: VIXY (Short-Term VIX) must not be in ETF_SYMBOLS.

        VIX products have negative carry (VIX futures contango), strong mean-reversion,
        and no trend persistence — all of which invalidate momentum/trend strategies
        that are calibrated for equity ETFs. Re-add only to a dedicated REGIME_GATE_SYMBOLS
        config variable, not to ETF_SYMBOLS.
        """
        from alpha_engine.config import ETF_SYMBOLS
        vol_etfs = {"VIXY", "UVXY", "SVXY"}
        present = vol_etfs & set(ETF_SYMBOLS)
        assert not present, (
            f"M-112: VIX/vol ETFs must not be in ETF_SYMBOLS: {present}. "
            "These belong in a dedicated REGIME_GATE_SYMBOLS config, not the momentum universe."
        )
