"""Tests for M-004: CRYPTO drag auto-quarantine gate.

Verifies that:
1. _cached_system_concentration() loads from system_concentration.json (fail-open)
2. passes_active_gate() shadow-logs (but doesn't block) picks from high-concentration
   low-PF systems when CRYPTO_CONCENTRATION_GATE=0 (default)
3. passes_active_gate() blocks picks when CRYPTO_CONCENTRATION_GATE=1 + threshold met
4. picks from systems below the threshold are unaffected
5. fail-open: missing file or bad data never blocks picks
"""
import json
import os
import sys
import tempfile

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _patch_concentration_file(tmp_path, by_class_data):
    """Write a fake system_concentration.json to audit_trail/data/."""
    data_dir = os.path.join(ROOT, "audit_trail", "data")
    os.makedirs(data_dir, exist_ok=True)
    conc_path = os.path.join(data_dir, "system_concentration.json")
    payload = {"generated_at": "2026-05-17T00:00:00Z", "by_class": by_class_data}
    with open(conc_path, "w") as f:
        json.dump(payload, f)
    return conc_path


def _reset_cache():
    from audit_trail.quality_gates import _reset_system_concentration_cache
    _reset_system_concentration_cache()


def _make_pick(source_system="test_sys", asset_class="CRYPTO"):
    return {
        "source_system": source_system,
        "strategy": "test_strategy",
        "symbol": "BTCUSDT",
        "asset_class": asset_class,
        "direction": "LONG",
        "confidence": 0.8,
        "status": "OPEN",
        "entry_price": 50000.0,
        "timestamp": "2026-05-17T00:00:00Z",
    }


def test_concentration_cache_loads_file(tmp_path):
    """_cached_system_concentration should load from file."""
    _reset_cache()
    _patch_concentration_file(tmp_path, {"CRYPTO": {"bad_sys": {"pf": 0.5, "vol_pct": 55.0, "resolved_n": 1000}}})
    from audit_trail.quality_gates import _cached_system_concentration
    _reset_cache()
    data = _cached_system_concentration()
    assert "CRYPTO" in data
    assert "bad_sys" in data["CRYPTO"]
    assert data["CRYPTO"]["bad_sys"]["vol_pct"] == 55.0


def test_concentration_cache_fail_open_missing_file():
    """_cached_system_concentration returns {} if file missing."""
    _reset_cache()
    # Temporarily rename file if it exists
    conc_path = os.path.join(ROOT, "audit_trail", "data", "system_concentration.json")
    backup = conc_path + ".bak_test"
    renamed = False
    if os.path.exists(conc_path):
        os.rename(conc_path, backup)
        renamed = True
    try:
        from audit_trail.quality_gates import _cached_system_concentration
        _reset_cache()
        data = _cached_system_concentration()
        assert isinstance(data, dict)
    finally:
        if renamed:
            os.rename(backup, conc_path)
        _reset_cache()


def test_shadow_mode_does_not_block(tmp_path, monkeypatch):
    """In shadow mode (CRYPTO_CONCENTRATION_GATE=0), >40% PF<1 system is NOT blocked."""
    monkeypatch.delenv("CRYPTO_CONCENTRATION_GATE", raising=False)
    _patch_concentration_file(tmp_path, {
        "CRYPTO": {"bad_sys": {"pf": 0.5, "vol_pct": 55.0, "resolved_n": 1000}}
    })
    _reset_cache()
    from audit_trail.quality_gates import passes_active_gate
    pick = _make_pick(source_system="bad_sys", asset_class="CRYPTO")
    result = passes_active_gate(pick)
    # Shadow mode: should NOT block on M-004 alone (other gates may still block)
    # The pick might be blocked by other gates — just verify M-004 isn't the blocker
    reason = pick.get("_hf_quality_gate_reason", "")
    assert reason != "m004_crypto_concentration_quarantine", \
        "Shadow mode must not set m004_crypto_concentration_quarantine reason"


def test_enforce_mode_blocks_high_concentration_low_pf(tmp_path, monkeypatch):
    """CRYPTO_CONCENTRATION_GATE=1 must block picks from >40% concentration AND PF<1 systems."""
    monkeypatch.setenv("CRYPTO_CONCENTRATION_GATE", "1")
    _patch_concentration_file(tmp_path, {
        "CRYPTO": {"bad_sys": {"pf": 0.5, "vol_pct": 55.0, "resolved_n": 1000}}
    })
    _reset_cache()
    from audit_trail.quality_gates import passes_active_gate
    pick = _make_pick(source_system="bad_sys", asset_class="CRYPTO")
    result = passes_active_gate(pick)
    assert result is False, "Enforce mode must block high-concentration low-PF system"
    assert pick.get("_hf_quality_gate_reason") == "m004_crypto_concentration_quarantine"


def test_below_threshold_not_blocked(tmp_path, monkeypatch):
    """Systems with vol_pct<=40 or PF>=1 must NOT be blocked even in enforce mode."""
    monkeypatch.setenv("CRYPTO_CONCENTRATION_GATE", "1")
    _patch_concentration_file(tmp_path, {
        "CRYPTO": {
            "good_pf_sys": {"pf": 1.5, "vol_pct": 55.0, "resolved_n": 1000},
            "low_vol_sys": {"pf": 0.5, "vol_pct": 20.0, "resolved_n": 200},
        }
    })
    _reset_cache()
    from audit_trail.quality_gates import passes_active_gate
    # Good PF system — not blocked by M-004
    pick1 = _make_pick(source_system="good_pf_sys", asset_class="CRYPTO")
    passes_active_gate(pick1)
    assert pick1.get("_hf_quality_gate_reason") != "m004_crypto_concentration_quarantine"

    # Low vol system — not blocked by M-004
    pick2 = _make_pick(source_system="low_vol_sys", asset_class="CRYPTO")
    passes_active_gate(pick2)
    assert pick2.get("_hf_quality_gate_reason") != "m004_crypto_concentration_quarantine"


def test_nonexistent_system_not_blocked(tmp_path, monkeypatch):
    """Systems not in the concentration file must NOT be blocked (fail-open)."""
    monkeypatch.setenv("CRYPTO_CONCENTRATION_GATE", "1")
    _patch_concentration_file(tmp_path, {"CRYPTO": {}})
    _reset_cache()
    from audit_trail.quality_gates import passes_active_gate
    pick = _make_pick(source_system="unknown_sys", asset_class="CRYPTO")
    passes_active_gate(pick)
    assert pick.get("_hf_quality_gate_reason") != "m004_crypto_concentration_quarantine", \
        "Unknown system must not be blocked (fail-open)"
