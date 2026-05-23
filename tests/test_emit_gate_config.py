"""Tests for tools/emit_gate_config.py."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from tools.emit_gate_config import emit, get_gate_status, GATE_REGISTRY


def test_gate_registry_non_empty() -> None:
    assert len(GATE_REGISTRY) >= 10, "GATE_REGISTRY should have at least 10 gates"


def test_gate_registry_required_fields() -> None:
    required = {"id", "label", "description", "env_var", "default", "active_when", "severity"}
    for gate in GATE_REGISTRY:
        missing = required - gate.keys()
        assert not missing, f"Gate {gate.get('id')} missing fields: {missing}"


def test_gate_registry_unique_ids() -> None:
    ids = [g["id"] for g in GATE_REGISTRY]
    assert len(ids) == len(set(ids)), "GATE_REGISTRY ids must be unique"


def test_get_gate_status_active_when_env_set(monkeypatch) -> None:
    gate = {
        "id": "TEST_GATE",
        "label": "Test",
        "description": "test",
        "env_var": "TEST_GATE_VAR",
        "default": "1",
        "active_when": "1",
        "asset_class": "ALL",
        "category": "test",
        "severity": "P1",
    }
    monkeypatch.setenv("TEST_GATE_VAR", "1")
    result = get_gate_status(gate)
    assert result["active"] is True
    assert result["status"] == "ACTIVE"
    assert result["current"] == "1"


def test_get_gate_status_disabled_when_env_overrides(monkeypatch) -> None:
    gate = {
        "id": "TEST_GATE2",
        "label": "Test2",
        "description": "test",
        "env_var": "TEST_GATE_VAR2",
        "default": "1",
        "active_when": "1",
        "asset_class": "ALL",
        "category": "risk_gate",
        "severity": "P0",
    }
    monkeypatch.setenv("TEST_GATE_VAR2", "0")
    result = get_gate_status(gate)
    assert result["active"] is False
    assert result["status"] == "DISABLED"


def test_get_gate_status_shadow_gate_inactive(monkeypatch) -> None:
    gate = {
        "id": "SHADOW_TEST",
        "label": "Shadow Test",
        "description": "test",
        "env_var": "SHADOW_TEST_VAR",
        "default": "0",
        "active_when": "1",
        "asset_class": "ALL",
        "category": "shadow_gate",
        "severity": "P2",
    }
    monkeypatch.delenv("SHADOW_TEST_VAR", raising=False)
    result = get_gate_status(gate)
    assert result["active"] is False
    assert result["status"] == "SHADOW"


def test_get_gate_status_normalizes_true_string(monkeypatch) -> None:
    gate = {
        "id": "BOOL_GATE",
        "label": "Bool Gate",
        "description": "test",
        "env_var": "BOOL_GATE_VAR",
        "default": "1",
        "active_when": "1",
        "asset_class": "ALL",
        "category": "test",
        "severity": "P1",
    }
    monkeypatch.setenv("BOOL_GATE_VAR", "true")
    result = get_gate_status(gate)
    assert result["active"] is True


def test_emit_writes_valid_json(tmp_path: Path) -> None:
    out = tmp_path / "gate_config.json"
    payload = emit(out)

    assert out.exists()
    with out.open(encoding="utf-8") as f:
        loaded = json.load(f)

    assert loaded["gate_count"] == len(GATE_REGISTRY)
    assert "generated_at" in loaded
    assert isinstance(loaded["gates"], list)
    assert len(loaded["gates"]) == len(GATE_REGISTRY)


def test_emit_counts_match(tmp_path: Path) -> None:
    out = tmp_path / "gate_config.json"
    payload = emit(out)

    gates = payload["gates"]
    active = sum(1 for g in gates if g["active"])
    shadow = sum(1 for g in gates if g.get("status") == "SHADOW")
    disabled = sum(1 for g in gates if not g["active"] and g.get("status") != "SHADOW")

    assert payload["active_count"] == active
    assert payload["shadow_count"] == shadow
    assert payload["disabled_count"] == disabled
    assert active + shadow + disabled == len(gates)


def test_emit_forex_hard_disable_active_by_default(tmp_path: Path) -> None:
    # FOREX_HARD_DISABLE default is "1" and active_when is "1"
    out = tmp_path / "gate_config.json"
    payload = emit(out)
    gate = next((g for g in payload["gates"] if g["id"] == "FOREX_HARD_DISABLE"), None)
    assert gate is not None
    # In CI (no env var set), this should be ACTIVE (default "1" == active_when "1")
    assert gate["active"] is True
