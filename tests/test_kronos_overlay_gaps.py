"""Branches of alpha_engine.kronos_overlay that test_kronos_overlay.py misses.

Every test injects a mock predictor, so none needs torch or Kronos weights.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from alpha_engine import kronos_overlay as ko


def _ohlcv(n: int = 100, seed: int = 1) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    base = 100 * np.exp(rng.normal(0, 0.001, n).cumsum())
    return pd.DataFrame({
        "open": base, "high": base * 1.001, "low": base * 0.999,
        "close": base, "volume": rng.uniform(1000, 5000, n),
    }, index=pd.date_range("2026-01-01", periods=n, freq="h"))


class _ConstChangePredictor:
    def __init__(self, change_pct: float):
        self.change_pct = change_pct
        self.calls = 0

    def predict(self, df, x_timestamp, y_timestamp, pred_len,
                T=1.0, top_p=0.9, sample_count=1):
        self.calls += 1
        cur = float(df["close"].iloc[-1])
        return pd.DataFrame({"close": np.linspace(cur, cur * (1 + self.change_pct),
                                                 pred_len)})


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    ko.reset_cache()
    ko.set_predictor(None)
    for v in ("KRONOS_OVERLAY_DISABLED", "KRONOS_OVERLAY_DRY_RUN"):
        monkeypatch.delenv(v, raising=False)
    yield
    ko.set_predictor(None)


# --- multiplier band boundaries -------------------------------------------
def test_exactly_two_percent_is_not_high_conviction():
    # The code uses a strict `>`, so 2% exactly gets the low-conviction boost.
    assert ko._multiplier_for("LONG", "LONG", 0.02) == (1.1, True)


def test_just_over_two_percent_is_high_conviction():
    assert ko._multiplier_for("LONG", "LONG", 0.0201) == (1.2, True)


def test_exactly_two_percent_disagreement_is_soft_dampen():
    assert ko._multiplier_for("LONG", "SHORT", -0.02) == (0.8, False)


def test_just_over_two_percent_disagreement_is_hard_dampen():
    assert ko._multiplier_for("LONG", "SHORT", -0.0201) == (0.6, False)


def test_exactly_half_percent_is_neutral():
    # `_classify` uses strict `>`, so 0.5% exactly is NEUTRAL.
    assert ko._classify(0.005) == "NEUTRAL"
    assert ko._classify(0.0051) == "LONG"
    assert ko._classify(-0.0051) == "SHORT"


# --- missing direction ----------------------------------------------------
def test_missing_direction_returns_identity():
    assert ko._multiplier_for(None, "LONG", 0.05) == (1.0, False)
    assert ko._multiplier_for("", "LONG", 0.05) == (1.0, False)


# --- SHORT agreeing with a SHORT forecast ----------------------------------
def test_short_pick_agreeing_with_short_forecast_is_boosted():
    ko.set_predictor(_ConstChangePredictor(-0.05))
    out = ko.kronos_overlay_picks(
        [{"symbol": "BTC", "direction": "SHORT", "confidence": 0.5}],
        {"BTC": _ohlcv()})
    assert out[0]["_kronos_overlay"]["multiplier"] == 1.2
    assert out[0]["_kronos_overlay"]["kronos_agree"] is True


# --- short history guard ---------------------------------------------------
def test_fewer_than_sixteen_bars_returns_stub():
    ko.set_predictor(_ConstChangePredictor(0.05))
    out = ko.kronos_score_pick(
        {"symbol": "BTC", "direction": "LONG", "confidence": 0.5}, _ohlcv(15))
    assert out["_stub"] is True and out["multiplier"] == 1.0


def test_sixteen_bars_is_enough():
    ko.set_predictor(_ConstChangePredictor(0.05))
    out = ko.kronos_score_pick(
        {"symbol": "BTC", "direction": "LONG", "confidence": 0.5}, _ohlcv(16))
    assert out["_stub"] is False


# --- disabled env on the single-pick entry --------------------------------
def test_disabled_env_stubs_score_pick(monkeypatch):
    monkeypatch.setenv("KRONOS_OVERLAY_DISABLED", "1")
    ko.set_predictor(_ConstChangePredictor(0.05))
    out = ko.kronos_score_pick(
        {"symbol": "BTC", "direction": "LONG", "confidence": 0.5}, _ohlcv())
    assert out["_stub"] is True and out["multiplier"] == 1.0


# --- LRU eviction ---------------------------------------------------------
def test_lru_evicts_oldest_beyond_maxsize():
    cache = ko._LRU(maxsize=2)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    assert cache.get_or_none("a") is None      # evicted
    assert cache.get_or_none("b") == 2
    assert len(cache) == 2


def test_lru_hit_moves_to_end():
    cache = ko._LRU(maxsize=2)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.get_or_none("a")                    # 'a' is now most-recent
    cache.put("c", 3)
    assert cache.get_or_none("a") == 1        # survived
    assert cache.get_or_none("b") is None     # evicted instead


# --- non-numeric confidence -----------------------------------------------
def test_non_numeric_confidence_is_left_alone():
    ko.set_predictor(_ConstChangePredictor(0.05))
    pick = {"symbol": "BTC", "direction": "LONG", "confidence": "n/a"}
    out = ko.kronos_overlay_picks([pick], {"BTC": _ohlcv()})
    assert out[0]["confidence"] == "n/a"      # guard swallowed the TypeError
    assert out[0]["_kronos_overlay"]["multiplier"] == 1.2
