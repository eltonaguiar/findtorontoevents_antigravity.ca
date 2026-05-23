"""Tests for crypto_onchain_momentum strategy + Glassnode fetcher."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, _REPO_ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


glass = _load("tools.glassnode_data_fetcher",
              "tools/glassnode_data_fetcher.py")
strat = _load("alpha_engine.crypto_onchain_momentum",
              "alpha_engine/crypto_onchain_momentum.py")
# Patch the imported handle inside the strategy module to our test instance
strat.glass = glass


# ------------------------------------------------------------------ #
# Glassnode fetcher
# ------------------------------------------------------------------ #

def test_fetcher_graceful_failure_on_missing_key(monkeypatch, tmp_path):
    monkeypatch.delenv("GLASSNODE_API_KEY", raising=False)
    monkeypatch.setattr(glass, "_CACHE_DIR", tmp_path)
    assert glass.fetch_mvrv_z("BTC") is None
    assert glass.fetch_active_addresses("BTC") is None
    assert glass.fetch_exchange_balance("ETH") is None


def test_fetcher_rejects_unsupported_asset(monkeypatch, tmp_path):
    monkeypatch.setenv("GLASSNODE_API_KEY", "fake-key")
    monkeypatch.setattr(glass, "_CACHE_DIR", tmp_path)
    assert glass.fetch_mvrv_z("DOGE") is None


def test_trend_30d_positive_and_negative():
    rising = [{"t": i, "v": float(i)} for i in range(1, 31)]
    falling = [{"t": i, "v": float(31 - i)} for i in range(1, 31)]
    flat = [{"t": i, "v": 5.0} for i in range(1, 31)]
    assert glass.trend_30d(rising) > 0
    assert glass.trend_30d(falling) < 0
    assert glass.trend_30d(flat) == 0.0
    assert glass.trend_30d(None) is None
    assert glass.trend_30d([{"t": 1, "v": 1.0}]) is None


def test_latest_value():
    assert glass.latest_value([{"t": 1, "v": 3.14}]) == pytest.approx(3.14)
    assert glass.latest_value(None) is None
    assert glass.latest_value([]) is None


# ------------------------------------------------------------------ #
# Strategy: default-OFF
# ------------------------------------------------------------------ #

def test_default_off(monkeypatch):
    monkeypatch.delenv(strat.ENABLED_ENV_VAR, raising=False)
    assert strat.is_enabled() is False
    assert strat.generate_signals() == []


def test_enabled_but_no_data(monkeypatch):
    monkeypatch.setenv(strat.ENABLED_ENV_VAR, "1")
    with patch.object(strat.glass, "fetch_mvrv_z", return_value=None):
        assert strat.generate_signals() == []


# ------------------------------------------------------------------ #
# Strategy: signal logic
# ------------------------------------------------------------------ #

def _series(value: float) -> list[dict]:
    return [{"t": i, "v": value} for i in range(30)]


def _rising_series() -> list[dict]:
    return [{"t": i, "v": float(i + 1)} for i in range(30)]


def _falling_series() -> list[dict]:
    return [{"t": i, "v": float(30 - i)} for i in range(30)]


def test_long_signal_when_mvrv_oversold_and_addresses_rising(monkeypatch):
    monkeypatch.setenv(strat.ENABLED_ENV_VAR, "1")

    def fake_mvrv(asset):
        return [{"t": 1, "v": -1.2}] if asset == "BTC" else [{"t": 1, "v": 0.5}]

    def fake_aa(asset):
        return _rising_series()

    def fake_eb(asset):
        return _series(100.0)

    with patch.object(strat.glass, "fetch_mvrv_z", side_effect=fake_mvrv), \
         patch.object(strat.glass, "fetch_active_addresses", side_effect=fake_aa), \
         patch.object(strat.glass, "fetch_exchange_balance", side_effect=fake_eb):
        picks = strat.generate_signals()

    longs = [p for p in picks if p["signal_type"] == "LONG"]
    assert len(longs) == 1
    p = longs[0]
    assert p["symbol"] == "BTCUSDT"
    assert p["strategy"] == "crypto_onchain_momentum"
    assert p["asset_class"] == "CRYPTO"
    assert 0.55 <= p["confidence"] <= 0.75
    assert "mvrv_z_score" in p["extra"]


def test_short_signal_when_mvrv_overbought_and_exchange_falling(monkeypatch):
    monkeypatch.setenv(strat.ENABLED_ENV_VAR, "1")

    def fake_mvrv(asset):
        return [{"t": 1, "v": 2.8}] if asset == "ETH" else [{"t": 1, "v": 0.0}]

    def fake_aa(asset):
        return _series(1000.0)

    def fake_eb(asset):
        return _falling_series()

    with patch.object(strat.glass, "fetch_mvrv_z", side_effect=fake_mvrv), \
         patch.object(strat.glass, "fetch_active_addresses", side_effect=fake_aa), \
         patch.object(strat.glass, "fetch_exchange_balance", side_effect=fake_eb):
        picks = strat.generate_signals()

    shorts = [p for p in picks if p["signal_type"] == "SHORT"]
    assert len(shorts) == 1
    p = shorts[0]
    assert p["symbol"] == "ETHUSDT"
    assert p["side"] == "SHORT"
    assert 0.55 <= p["confidence"] <= 0.75
    assert p["extra"]["exchange_balance_trend_30d"] < 0


def test_no_signal_when_mvrv_neutral(monkeypatch):
    monkeypatch.setenv(strat.ENABLED_ENV_VAR, "1")
    with patch.object(strat.glass, "fetch_mvrv_z", return_value=[{"t": 1, "v": 0.5}]):
        assert strat.generate_signals() == []


def test_pick_shape_has_required_fields(monkeypatch):
    monkeypatch.setenv(strat.ENABLED_ENV_VAR, "1")
    with patch.object(strat.glass, "fetch_mvrv_z", return_value=[{"t": 1, "v": -1.0}]), \
         patch.object(strat.glass, "fetch_active_addresses",
                      return_value=_rising_series()):
        picks = strat.generate_signals()
    assert picks
    p = picks[0]
    required = {"strategy", "symbol", "asset_class", "signal_type",
                "confidence", "timeframe", "reason", "timestamp", "extra"}
    assert required.issubset(p.keys())
