"""Tests for AUDIT_PICK_SANITY_GATE in passes_active_gate."""

from datetime import datetime, timezone

import pytest

from audit_trail.quality_gates import passes_active_gate


def _crypto_pick(**overrides):
    pick = {
        "id": "sanity-gate-test-1",
        "symbol": "BTCUSDT",
        "asset_class": "CRYPTO",
        "source_system": "alpha_engine",
        "strategy": "test_strategy_sanity_gate",
        "status": "OPEN",
        "direction": "LONG",
        "entry_price": 100.0,
        "take_profit": 110.0,
        "stop_loss": 95.0,
        "score": 60.0,
        "confidence": 0.7,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    pick.update(overrides)
    return pick


def test_sanity_gate_off_allows_extreme_risk_reward(monkeypatch):
    """When AUDIT_PICK_SANITY_GATE is OFF, all gates including R:R should pass."""
    monkeypatch.delenv("AUDIT_PICK_SANITY_GATE", raising=False)
    monkeypatch.setenv("PHASE1_CONF_GATE_ENABLED", "0")
    monkeypatch.setenv("PHASE1_CONF_DEADZONE_ENABLED", "0")
    monkeypatch.setenv("MATRIX_SYMBOL_GATES", "0")
    pick = _crypto_pick(risk_reward=50.0)
    assert passes_active_gate(pick) is True


def test_sanity_gate_on_rejects_extreme_risk_reward(monkeypatch):
    """When AUDIT_PICK_SANITY_GATE is ON, extreme R:R should be rejected."""
    monkeypatch.setenv("AUDIT_PICK_SANITY_GATE", "1")
    monkeypatch.setenv("PHASE1_CONF_GATE_ENABLED", "0")
    monkeypatch.setenv("PHASE1_CONF_DEADZONE_ENABLED", "0")
    pick = _crypto_pick(risk_reward=50.0)
    assert passes_active_gate(pick) is False


def test_sanity_gate_on_skips_prediction_market(monkeypatch):
    """Prediction market sources should bypass R:R gate when AUDIT_PICK_SANITY_GATE is ON."""
    monkeypatch.setenv("AUDIT_PICK_SANITY_GATE", "1")
    monkeypatch.setenv("PHASE1_CONF_GATE_ENABLED", "0")
    monkeypatch.setenv("PHASE1_CONF_DEADZONE_ENABLED", "0")
    pick = _crypto_pick(
        source_system="pm_whale_signals",
        strategy="pm_whale_0xtest",
        risk_reward=50.0,
        trust_score=6,
        trust_label="MODERATE",
        source_tier="PROVEN",
    )
    assert passes_active_gate(pick) is True
