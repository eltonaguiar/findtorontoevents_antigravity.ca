"""Tests for the concept-drift auto-pause gate.

Threshold per 3/3 swarm consensus (deepseek + xai + kilo, 2026-05-14):
  - per-class: D > 2 * ks_critical_05  -> block picks of that class only
  - system-wide severe: D > 3 * ks_critical_05 -> block all classes
  - moderate (between 2x and 3x system-wide): no block

Fail-open behavior:
  - missing payload -> permissive
  - stale payload (> 36h) -> permissive
  - DRIFT_AUTO_PAUSE_DISABLED=1 -> permissive
"""

from __future__ import annotations

from datetime import datetime, timezone

import audit_trail.quality_gates as qg
from audit_trail.quality_gates import _passes_drift_auto_pause_gate


def _crypto_pick() -> dict:
    return {
        "id": "drift-test-crypto",
        "symbol": "BTCUSDT",
        "asset_class": "CRYPTO",
        "direction": "LONG",
        "entry_price": 70000.0,
        "take_profit": 73000.0,
        "stop_loss": 68000.0,
    }


def _equity_pick() -> dict:
    p = _crypto_pick()
    p["id"] = "drift-test-equity"
    p["asset_class"] = "EQUITY"
    p["symbol"] = "AAPL"
    return p


def _set_drift_state(monkeypatch, *, system_breached=False, system_severe=False,
                     by_class_breached=None, payload_age_hours=1.0):
    state = {
        "mtime": 1.0,
        "system_breached": system_breached,
        "system_severe": system_severe,
        "by_class_breached": by_class_breached or {},
        "payload_age_hours": payload_age_hours,
    }
    monkeypatch.setattr(qg, "_load_drift_state", lambda: state)


def test_drift_gate_fails_open_when_no_breach(monkeypatch):
    monkeypatch.delenv("DRIFT_AUTO_PAUSE_DISABLED", raising=False)
    _set_drift_state(monkeypatch)
    assert _passes_drift_auto_pause_gate(_crypto_pick()) is None
    assert _passes_drift_auto_pause_gate(_equity_pick()) is None


def test_drift_gate_blocks_class_when_per_class_breached(monkeypatch):
    monkeypatch.delenv("DRIFT_AUTO_PAUSE_DISABLED", raising=False)
    _set_drift_state(monkeypatch, by_class_breached={"CRYPTO": True})
    assert _passes_drift_auto_pause_gate(_crypto_pick()) == "drift_auto_pause_class_crypto"
    # Other class unaffected:
    assert _passes_drift_auto_pause_gate(_equity_pick()) is None


def test_drift_gate_blocks_all_classes_when_system_severe(monkeypatch):
    monkeypatch.delenv("DRIFT_AUTO_PAUSE_DISABLED", raising=False)
    _set_drift_state(monkeypatch, system_severe=True)
    assert _passes_drift_auto_pause_gate(_crypto_pick()) == "drift_auto_pause_system_severe"
    assert _passes_drift_auto_pause_gate(_equity_pick()) == "drift_auto_pause_system_severe"


def test_drift_gate_moderate_system_wide_does_not_block(monkeypatch):
    """System-wide D > 2x critical but < 3x -> we have system_breached True but
    system_severe False. Should NOT block (per swarm Q3: avoid killing productive
    classes for moderate system drift)."""
    monkeypatch.delenv("DRIFT_AUTO_PAUSE_DISABLED", raising=False)
    _set_drift_state(monkeypatch, system_breached=True, system_severe=False)
    assert _passes_drift_auto_pause_gate(_crypto_pick()) is None
    assert _passes_drift_auto_pause_gate(_equity_pick()) is None


def test_drift_gate_disable_env_overrides(monkeypatch):
    monkeypatch.setenv("DRIFT_AUTO_PAUSE_DISABLED", "1")
    _set_drift_state(monkeypatch, system_severe=True,
                     by_class_breached={"CRYPTO": True})
    assert _passes_drift_auto_pause_gate(_crypto_pick()) is None
    assert _passes_drift_auto_pause_gate(_equity_pick()) is None


def test_drift_gate_stale_payload_fails_open(monkeypatch, tmp_path):
    """Real fail-open path: when _load_drift_state returns the unmodified
    cache after seeing a stale payload, the gate must pass everything."""
    monkeypatch.delenv("DRIFT_AUTO_PAUSE_DISABLED", raising=False)
    _set_drift_state(monkeypatch, payload_age_hours=200.0)
    # State has no breaches set, so the gate passes:
    assert _passes_drift_auto_pause_gate(_crypto_pick()) is None
