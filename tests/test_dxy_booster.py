"""Tests for alpha_engine/dxy_booster.py (M-074)."""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from alpha_engine.dxy_booster import (
    _LONG_BONUS_WHEN_WEAK,
    _LONG_PENALTY_WHEN_STRONG,
    _SHORT_BONUS_WHEN_STRONG,
    _STALE_HOURS,
    dxy_score_adjustment,
    get_dxy_state_summary,
)


def _make_state(trend: str, age_hours: float = 1.0) -> dict:
    ts = datetime.now(timezone.utc) - timedelta(hours=age_hours)
    return {
        "generated_at": ts.isoformat(),
        "ticker": "DX-Y.NYB",
        "dxy_close": 99.27,
        "dxy_sma20": 98.43,
        "change_5d_pct": 1.46 if trend == "STRONG" else -0.6 if trend == "WEAK" else 0.1,
        "trend": trend,
    }


@pytest.fixture()
def state_file(tmp_path, monkeypatch):
    """Monkeypatches _STATE_FILE to a temp path."""
    p = tmp_path / "dxy_state.json"
    import alpha_engine.dxy_booster as mod
    monkeypatch.setattr(mod, "_STATE_FILE", p)
    return p


# ── Kill-switch ──────────────────────────────────────────────────────────────

def test_kill_switch_returns_zero(state_file, monkeypatch):
    state_file.write_text(json.dumps(_make_state("WEAK")))
    monkeypatch.setenv("DXY_BOOSTER_DISABLED", "1")
    pick = {"asset_class": "COMMODITY", "direction": "LONG"}
    assert dxy_score_adjustment(pick) == 0


@pytest.mark.parametrize("val", ("true", "True", "TRUE"))
def test_kill_switch_string_variants(val, state_file, monkeypatch):
    state_file.write_text(json.dumps(_make_state("WEAK")))
    monkeypatch.setenv("DXY_BOOSTER_DISABLED", val)
    pick = {"asset_class": "COMMODITY", "direction": "LONG"}
    assert dxy_score_adjustment(pick) == 0


# ── Non-COMMODITY picks return 0 ─────────────────────────────────────────────

@pytest.mark.parametrize("ac", ["EQUITY", "CRYPTO", "ETF", "FOREX", "BOND", "FUTURES", ""])
def test_non_commodity_returns_zero(ac, state_file, monkeypatch):
    monkeypatch.delenv("DXY_BOOSTER_DISABLED", raising=False)
    state_file.write_text(json.dumps(_make_state("WEAK")))
    pick = {"asset_class": ac, "direction": "LONG"}
    assert dxy_score_adjustment(pick) == 0


# ── WEAK trend (USD weakening → LONG bonus) ──────────────────────────────────

def test_weak_trend_long_gets_bonus(state_file, monkeypatch):
    monkeypatch.delenv("DXY_BOOSTER_DISABLED", raising=False)
    state_file.write_text(json.dumps(_make_state("WEAK")))
    pick = {"asset_class": "COMMODITY", "direction": "LONG"}
    assert dxy_score_adjustment(pick) == _LONG_BONUS_WHEN_WEAK


def test_weak_trend_buy_gets_bonus(state_file, monkeypatch):
    monkeypatch.delenv("DXY_BOOSTER_DISABLED", raising=False)
    state_file.write_text(json.dumps(_make_state("WEAK")))
    pick = {"asset_class": "COMMODITY", "direction": "BUY"}
    assert dxy_score_adjustment(pick) == _LONG_BONUS_WHEN_WEAK


def test_weak_trend_short_gets_zero(state_file, monkeypatch):
    monkeypatch.delenv("DXY_BOOSTER_DISABLED", raising=False)
    state_file.write_text(json.dumps(_make_state("WEAK")))
    pick = {"asset_class": "COMMODITY", "direction": "SHORT"}
    assert dxy_score_adjustment(pick) == 0


# ── STRONG trend (USD strengthening → LONG penalty, SHORT boost) ─────────────

def test_strong_trend_long_gets_penalty(state_file, monkeypatch):
    monkeypatch.delenv("DXY_BOOSTER_DISABLED", raising=False)
    state_file.write_text(json.dumps(_make_state("STRONG")))
    pick = {"asset_class": "COMMODITY", "direction": "LONG"}
    assert dxy_score_adjustment(pick) == _LONG_PENALTY_WHEN_STRONG


def test_strong_trend_short_gets_bonus(state_file, monkeypatch):
    monkeypatch.delenv("DXY_BOOSTER_DISABLED", raising=False)
    state_file.write_text(json.dumps(_make_state("STRONG")))
    pick = {"asset_class": "COMMODITY", "direction": "SHORT"}
    assert dxy_score_adjustment(pick) == _SHORT_BONUS_WHEN_STRONG


def test_strong_trend_sell_gets_bonus(state_file, monkeypatch):
    monkeypatch.delenv("DXY_BOOSTER_DISABLED", raising=False)
    state_file.write_text(json.dumps(_make_state("STRONG")))
    pick = {"asset_class": "COMMODITY", "direction": "SELL"}
    assert dxy_score_adjustment(pick) == _SHORT_BONUS_WHEN_STRONG


# ── NEUTRAL trend ─────────────────────────────────────────────────────────────

def test_neutral_trend_returns_zero(state_file, monkeypatch):
    monkeypatch.delenv("DXY_BOOSTER_DISABLED", raising=False)
    state_file.write_text(json.dumps(_make_state("NEUTRAL")))
    pick = {"asset_class": "COMMODITY", "direction": "LONG"}
    assert dxy_score_adjustment(pick) == 0


# ── Stale state ──────────────────────────────────────────────────────────────

def test_stale_state_returns_zero(state_file, monkeypatch):
    monkeypatch.delenv("DXY_BOOSTER_DISABLED", raising=False)
    state_file.write_text(json.dumps(_make_state("WEAK", age_hours=_STALE_HOURS + 1)))
    pick = {"asset_class": "COMMODITY", "direction": "LONG"}
    assert dxy_score_adjustment(pick) == 0


# ── Missing state file ────────────────────────────────────────────────────────

def test_missing_state_returns_zero(tmp_path, monkeypatch):
    monkeypatch.delenv("DXY_BOOSTER_DISABLED", raising=False)
    import alpha_engine.dxy_booster as mod
    monkeypatch.setattr(mod, "_STATE_FILE", tmp_path / "nonexistent.json")
    pick = {"asset_class": "COMMODITY", "direction": "LONG"}
    assert dxy_score_adjustment(pick) == 0


# ── Corrupt state file ────────────────────────────────────────────────────────

def test_corrupt_state_returns_zero(state_file, monkeypatch):
    monkeypatch.delenv("DXY_BOOSTER_DISABLED", raising=False)
    state_file.write_text("NOT_JSON{{{{")
    pick = {"asset_class": "COMMODITY", "direction": "LONG"}
    assert dxy_score_adjustment(pick) == 0


# ── Invalid pick ─────────────────────────────────────────────────────────────

def test_non_dict_pick_returns_zero(state_file, monkeypatch):
    monkeypatch.delenv("DXY_BOOSTER_DISABLED", raising=False)
    state_file.write_text(json.dumps(_make_state("WEAK")))
    assert dxy_score_adjustment("not_a_dict") == 0
    assert dxy_score_adjustment(None) == 0


# ── signal field fallback ─────────────────────────────────────────────────────

def test_signal_field_used_when_direction_missing(state_file, monkeypatch):
    monkeypatch.delenv("DXY_BOOSTER_DISABLED", raising=False)
    state_file.write_text(json.dumps(_make_state("WEAK")))
    pick = {"asset_class": "COMMODITY", "signal": "LONG"}
    assert dxy_score_adjustment(pick) == _LONG_BONUS_WHEN_WEAK


# ── get_dxy_state_summary ────────────────────────────────────────────────────

def test_summary_available(state_file, monkeypatch):
    monkeypatch.delenv("DXY_BOOSTER_DISABLED", raising=False)
    state_file.write_text(json.dumps(_make_state("STRONG")))
    result = get_dxy_state_summary()
    assert result["available"] is True
    assert result["trend"] == "STRONG"
    assert result["dxy_close"] == 99.27


def test_summary_unavailable_when_missing(tmp_path, monkeypatch):
    import alpha_engine.dxy_booster as mod
    monkeypatch.setattr(mod, "_STATE_FILE", tmp_path / "nonexistent.json")
    result = get_dxy_state_summary()
    assert result["available"] is False
    assert result["trend"] == "UNKNOWN"
