"""Tests for alpha_engine.kronos_overlay -- all use a mock predictor."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from alpha_engine import kronos_overlay as ko


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
def _ohlcv(n: int = 100, drift: float = 0.0, seed: int = 1) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    base = 100 * np.exp(np.linspace(0, drift, n)
                        + rng.normal(0, 0.001, n).cumsum())
    df = pd.DataFrame({
        "open": base, "high": base * 1.001, "low": base * 0.999,
        "close": base, "volume": rng.uniform(1000, 5000, n),
    }, index=pd.date_range("2026-01-01", periods=n, freq="h"))
    return df


class _ConstChangePredictor:
    """Returns a forecast that ends `change_pct` above current close."""
    def __init__(self, change_pct: float):
        self.change_pct = change_pct
        self.calls = 0

    def predict(self, df, x_timestamp, y_timestamp, pred_len,
                T=1.0, top_p=0.9, sample_count=1):
        self.calls += 1
        cur = float(df["close"].iloc[-1])
        target = cur * (1.0 + self.change_pct)
        future = np.linspace(cur, target, pred_len)
        return pd.DataFrame({"close": future})


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    """Drop cache + injected predictor + envs before every test."""
    ko.reset_cache()
    ko.set_predictor(None)
    for v in ("KRONOS_OVERLAY_DISABLED", "KRONOS_OVERLAY_DRY_RUN"):
        monkeypatch.delenv(v, raising=False)
    yield
    ko.set_predictor(None)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def test_no_op_when_kronos_unavailable(monkeypatch):
    monkeypatch.setattr(ko, "HAVE_KRONOS", False)
    ko.set_predictor(None)
    pick = {"symbol": "BTC", "direction": "LONG", "confidence": 0.5}
    out = ko.kronos_score_pick(pick, _ohlcv())
    assert out["multiplier"] == 1.0
    assert out["kronos_direction"] == "UNAVAILABLE"
    assert out["_stub"] is True


def test_rollback_env_disables(monkeypatch):
    monkeypatch.setenv("KRONOS_OVERLAY_DISABLED", "1")
    ko.set_predictor(_ConstChangePredictor(0.05))
    picks = [{"symbol": "BTC", "direction": "LONG", "confidence": 0.5}]
    out = ko.kronos_overlay_picks(picks, {"BTC": _ohlcv()})
    assert out[0]["confidence"] == 0.5
    assert "_kronos_overlay" not in out[0]


def test_dry_run_computes_score_but_doesnt_mutate(monkeypatch):
    monkeypatch.setenv("KRONOS_OVERLAY_DRY_RUN", "1")
    ko.set_predictor(_ConstChangePredictor(0.05))
    picks = [{"symbol": "BTC", "direction": "LONG", "confidence": 0.5}]
    out = ko.kronos_overlay_picks(picks, {"BTC": _ohlcv()})
    assert out[0]["confidence"] == 0.5  # unchanged
    assert out[0]["_kronos_overlay"]["multiplier"] == 1.2  # but stamped
    assert out[0]["_kronos_overlay"]["kronos_direction"] == "LONG"


def test_kronos_direction_inference():
    ko.set_predictor(_ConstChangePredictor(0.05))
    pick = {"symbol": "BTC", "direction": "LONG", "confidence": 0.5}
    out = ko.kronos_score_pick(pick, _ohlcv())
    assert out["kronos_direction"] == "LONG"
    assert out["kronos_predicted_change_pct"] > 0.04


def test_agree_boost():
    ko.set_predictor(_ConstChangePredictor(0.05))  # +5% high conviction
    picks = [{"symbol": "BTC", "direction": "LONG", "confidence": 0.5}]
    out = ko.kronos_overlay_picks(picks, {"BTC": _ohlcv()})
    assert out[0]["_kronos_overlay"]["multiplier"] == 1.2
    assert out[0]["_kronos_overlay"]["kronos_agree"] is True
    assert out[0]["confidence"] == pytest.approx(0.6)


def test_agree_low_conviction_smaller_boost():
    ko.set_predictor(_ConstChangePredictor(0.01))  # +1%, below 2% high conv
    picks = [{"symbol": "BTC", "direction": "LONG", "confidence": 0.5}]
    out = ko.kronos_overlay_picks(picks, {"BTC": _ohlcv()})
    assert out[0]["_kronos_overlay"]["multiplier"] == 1.1


def test_disagree_dampen():
    ko.set_predictor(_ConstChangePredictor(-0.05))  # forecast -5%
    picks = [{"symbol": "BTC", "direction": "LONG", "confidence": 0.5}]
    out = ko.kronos_overlay_picks(picks, {"BTC": _ohlcv()})
    assert out[0]["_kronos_overlay"]["multiplier"] == 0.6
    assert out[0]["_kronos_overlay"]["kronos_direction"] == "SHORT"
    assert out[0]["confidence"] == pytest.approx(0.3)


def test_neutral_passthrough():
    ko.set_predictor(_ConstChangePredictor(0.001))  # +0.1%, below 0.5%
    picks = [{"symbol": "BTC", "direction": "LONG", "confidence": 0.5}]
    out = ko.kronos_overlay_picks(picks, {"BTC": _ohlcv()})
    assert out[0]["_kronos_overlay"]["kronos_direction"] == "NEUTRAL"
    assert out[0]["_kronos_overlay"]["multiplier"] == 1.0
    assert out[0]["confidence"] == 0.5


def test_lru_cache_hits():
    pred = _ConstChangePredictor(0.05)
    ko.set_predictor(pred)
    df = _ohlcv()
    pick = {"symbol": "BTC", "direction": "LONG", "confidence": 0.5}
    ko.kronos_score_pick(pick, df)
    ko.kronos_score_pick(pick, df)
    ko.kronos_score_pick(pick, df)
    assert pred.calls == 1   # only the first call hit the predictor
    assert ko._CACHE.hits >= 2


def test_missing_ohlcv_returns_stub():
    ko.set_predictor(_ConstChangePredictor(0.05))
    out = ko.kronos_score_pick(
        {"symbol": "BTC", "direction": "LONG", "confidence": 0.5}, None)
    assert out["multiplier"] == 1.0
    assert out["_stub"] is True


def test_predictor_exception_returns_stub():
    class Boom:
        def predict(self, **kw):
            raise RuntimeError("boom")
    ko.set_predictor(Boom())
    out = ko.kronos_score_pick(
        {"symbol": "BTC", "direction": "LONG", "confidence": 0.5}, _ohlcv())
    assert out["multiplier"] == 1.0
    assert out["_stub"] is True
