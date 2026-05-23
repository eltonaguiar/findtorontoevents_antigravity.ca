"""Tests for the ETF Economic Momentum strategy + FRED fetcher.

Per CLAUDE.md Wire-Up Rule: this strategy is OPT-IN. Tests exercise the
pure helpers + the env-gated entry point without touching the network.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _load(mod_name: str, rel_path: str):
    spec = importlib.util.spec_from_file_location(mod_name, REPO_ROOT / rel_path)
    assert spec and spec.loader, f"could not load {rel_path}"
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


fred = _load("tools.fred_data_fetcher", "tools/fred_data_fetcher.py")
strat = _load("alpha_engine.etf_economic_momentum", "alpha_engine/etf_economic_momentum.py")


# ----- 1. FRED fetcher graceful failure (no key, no network) -----

def test_fetch_series_no_api_key_returns_missing(monkeypatch, tmp_path):
    monkeypatch.delenv("FRED_API_KEY", raising=False)
    rec = fred.fetch_series("NAPM", cache_dir=tmp_path, use_cache=False)
    assert rec["source"] == "missing"
    assert rec["observations"] == []
    assert "FRED_API_KEY" in rec.get("error", "")


def test_fetch_series_http_failure_returns_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("FRED_API_KEY", "fake")

    def boom(url):
        raise OSError("network down")

    rec = fred.fetch_series("NAPM", http_get=boom, cache_dir=tmp_path, use_cache=False)
    assert rec["source"] == "missing"
    assert "OSError" in rec.get("error", "")


# ----- 2. Momentum z-score math -----

def test_compute_momentum_zscore_basic():
    observations = [
        {"date": "2025-06-01", "value": 100.0},
        {"date": "2025-07-01", "value": 102.0},
        {"date": "2025-08-01", "value": 101.0},
        {"date": "2025-09-01", "value": 103.0},
        {"date": "2025-10-01", "value": 102.0},
        {"date": "2025-11-01", "value": 104.0},
        {"date": "2026-05-01", "value": 120.0},  # latest, large positive shock
    ]

    def stub_fetch(series_id, **_kwargs):
        return {"observations": observations, "source": "stub"}

    z = fred.compute_momentum_zscore("X", lookback_days=400, fetcher=stub_fetch)
    assert z is not None
    assert z > 5.0  # 120 is way above ~102 mean with tiny stdev


def test_compute_yoy_growth_basic():
    observations = [
        {"date": "2025-05-12", "value": 100.0},
        {"date": "2026-05-12", "value": 110.0},
    ]

    def stub_fetch(series_id, **_kwargs):
        return {"observations": observations, "source": "stub"}

    g = fred.compute_yoy_growth("X", fetcher=stub_fetch)
    assert g == pytest.approx(0.10, rel=1e-6)


def test_compute_momentum_zscore_insufficient_data():
    def stub_fetch(series_id, **_kwargs):
        return {"observations": [{"date": "2026-01-01", "value": 1.0}], "source": "stub"}

    assert fred.compute_momentum_zscore("X", fetcher=stub_fetch) is None


# ----- 3. Default-OFF env gate -----

def test_generate_picks_default_off(monkeypatch):
    monkeypatch.delenv("ETF_ECONOMIC_MOMENTUM_ENABLED", raising=False)
    picks = strat.generate_picks()
    assert picks == []
    assert strat.is_enabled() is False


def test_is_enabled_truthy_values(monkeypatch):
    for val in ("1", "true", "YES", "on"):
        monkeypatch.setenv("ETF_ECONOMIC_MOMENTUM_ENABLED", val)
        assert strat.is_enabled() is True


# ----- 4. LONG / SHORT / NEUTRAL regime logic -----

class _FakeFred:
    """Stub matching the public surface used in evaluate_macro."""

    def __init__(self, ism, m2_yoy, gdp_z):
        self.ism = ism
        self.m2_yoy = m2_yoy
        self.gdp_z = gdp_z

    def fetch_series(self, series_id, **_kwargs):
        if series_id == "NAPM" and self.ism is not None:
            return {"observations": [{"date": "2026-05-01", "value": self.ism}], "source": "stub"}
        return {"observations": [], "source": "stub"}

    def compute_yoy_growth(self, series_id, **_kwargs):
        return self.m2_yoy

    def compute_momentum_zscore(self, series_id, **_kwargs):
        return self.gdp_z


def test_long_regime_emits_buys_for_full_universe(monkeypatch):
    monkeypatch.setenv("ETF_ECONOMIC_MOMENTUM_ENABLED", "1")
    fake = _FakeFred(ism=55.0, m2_yoy=0.04, gdp_z=1.2)
    picks = strat.generate_picks(fred_module=fake)
    assert len(picks) == len(strat.ETF_UNIVERSE)
    assert all(p["signal_type"] == "BUY" for p in picks)
    assert all(p["category"] == "etf" for p in picks)
    assert all(p["strategy"] == "etf_economic_momentum" for p in picks)


def test_short_regime_emits_sells(monkeypatch):
    monkeypatch.setenv("ETF_ECONOMIC_MOMENTUM_ENABLED", "1")
    fake = _FakeFred(ism=46.0, m2_yoy=-0.01, gdp_z=-1.5)
    picks = strat.generate_picks(fred_module=fake)
    assert len(picks) == len(strat.ETF_UNIVERSE)
    assert all(p["signal_type"] == "SELL" for p in picks)


def test_neutral_regime_emits_nothing(monkeypatch):
    monkeypatch.setenv("ETF_ECONOMIC_MOMENTUM_ENABLED", "1")
    fake = _FakeFred(ism=51.0, m2_yoy=0.03, gdp_z=0.1)  # ISM>50 but z<0.5
    assert strat.generate_picks(fred_module=fake) == []


# ----- 5. Pick shape + confidence range -----

def test_pick_shape_and_confidence_band(monkeypatch):
    monkeypatch.setenv("ETF_ECONOMIC_MOMENTUM_ENABLED", "1")
    fake = _FakeFred(ism=58.0, m2_yoy=0.06, gdp_z=1.8)
    picks = strat.generate_picks(fred_module=fake)
    assert picks, "expected picks in strong-LONG regime"
    p = picks[0]
    for key in ("strategy", "symbol", "category", "signal_type", "confidence",
                "reason", "timeframe", "extra", "timestamp"):
        assert key in p, f"missing key {key}"
    assert p["timeframe"] == "12h"
    assert strat.CONFIDENCE_FLOOR <= p["confidence"] <= strat.CONFIDENCE_CEIL
    assert p["extra"]["regime"] == "LONG"
    assert p["extra"]["ism"] == 58.0
