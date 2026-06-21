"""Shadow/monitor lane safety — sizing + display exclusion (2026-06-21)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from audit_trail.quality_gates import (
    _rsi5070_shadow_match,
    enforce_sizing_override,
    is_shadow_monitor_pick,
    tag_rsi5070_shadow,
)


def test_is_shadow_monitor_pick_monitor_mode():
    assert is_shadow_monitor_pick({"_monitor_mode": True}) is True
    assert is_shadow_monitor_pick({"_sizing_override": "zero"}) is True
    assert is_shadow_monitor_pick({"symbol": "BTCUSDT"}) is False


def test_enforce_sizing_override_zeros_capital_fields():
    pick = {"symbol": "ES=F", "_monitor_mode": True, "position_multiplier": 1.5}
    assert enforce_sizing_override(pick) is True
    assert pick["position_multiplier"] == 0.0
    assert pick["_sizing_multiplier"] == 0.0
    assert pick["position_size_usd"] == 0.0


def test_enforce_sizing_override_noop_on_normal_pick():
    pick = {"symbol": "AAPL", "position_multiplier": 1.0}
    assert enforce_sizing_override(pick) is False
    assert pick["position_multiplier"] == 1.0


def test_rsi5070_shadow_match_predicate():
    assert _rsi5070_shadow_match("CRYPTO", "LONG", 55.0, 15.0) is True
    assert _rsi5070_shadow_match("CRYPTO", "SHORT", 55.0, 15.0) is False
    assert _rsi5070_shadow_match("CRYPTO", "LONG", 45.0, 15.0) is False
    assert _rsi5070_shadow_match("EQUITY", "LONG", 55.0, 15.0) is False
    assert _rsi5070_shadow_match("CRYPTO", "LONG", 55.0, 22.0) is False


def test_tag_rsi5070_shadow_default_off():
    pick = {
        "asset_class": "CRYPTO",
        "direction": "LONG",
        "rsi_14_1h": 55.0,
    }
    tag_rsi5070_shadow(pick)
    assert "_monitor_mode" not in pick


def test_tag_rsi5070_shadow_tags_when_enabled(monkeypatch):
    monkeypatch.setenv("CRYPTO_RSI5070_SHADOW_ENABLE", "1")
    monkeypatch.setattr(
        "audit_trail.quality_gates._rsi5070_shadow_match",
        lambda *args, **kwargs: True,
    )
    pick = {
        "asset_class": "CRYPTO",
        "direction": "LONG",
        "rsi_14_1h": 55.0,
    }
    tag_rsi5070_shadow(pick)
    assert pick["_monitor_mode"] is True
    assert pick["forward_test_only"] is True
    assert pick["_monitor_tag"] == "RSI5070_SHADOW"
    assert pick["_sizing_override"] == "zero"


def test_passes_smart_gate_blocks_shadow_monitor(monkeypatch):
    from audit_trail import quality_gates as qg

    monkeypatch.setattr(qg, "passes_active_gate", lambda p: True)
    shadow = {
        "asset_class": "CRYPTO",
        "symbol": "BTCUSDT",
        "_monitor_mode": True,
        "_monitor_tag": "RSI5070_SHADOW",
        "score": 80,
    }
    assert qg.passes_smart_gate(shadow) is False


def test_get_position_size_shadow_lane():
    from alpha_engine.position_sizing import get_position_size

    out = get_position_size(
        {
            "symbol": "BTCUSDT",
            "entry_price": 50000.0,
            "stop_loss": 49000.0,
            "_monitor_mode": True,
        },
        account_equity=10000.0,
    )
    assert out["position_size_usd"] == 0.0
    assert out["capped_by"] == "shadow_monitor_lane"
