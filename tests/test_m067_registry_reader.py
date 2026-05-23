"""M-067: tests for _registry_backed_ac_breakdown() in dashboard_generator.

The reader lets /audit asset_class_health be SOURCED FROM the canonical
pf_registry.json (net policy-clean view) instead of recomputed, gated by the
AUDIT_HEALTH_SOURCE env flag. These tests pin the fail-open contract.
"""
import importlib
import os

import pytest


def _reader():
    mod = importlib.import_module("audit_trail.dashboard_generator")
    return mod._registry_backed_ac_breakdown


def test_flag_recompute_returns_none(monkeypatch):
    # M-067 default flipped to "registry" 2026-05-17. Only an EXPLICIT
    # AUDIT_HEALTH_SOURCE=recompute now disables the reader (rollback path).
    monkeypatch.setenv("AUDIT_HEALTH_SOURCE", "recompute")
    assert _reader()() is None


def test_flag_on_returns_none_or_valid_shape(monkeypatch):
    # With the flag on, the reader either fails open (None — registry missing,
    # stale, or non-canonical) or returns an ac_breakdown-shaped dict. It must
    # NEVER raise and must NEVER return a partial/garbage shape.
    monkeypatch.setenv("AUDIT_HEALTH_SOURCE", "registry")
    result = _reader()()
    if result is None:
        return  # fail-open is an acceptable outcome
    assert isinstance(result, dict) and result
    for ac, row in result.items():
        assert ac == ac.upper()
        for key in ("wins", "losses", "win_rate", "pnl", "profit_factor"):
            assert key in row, f"{ac} missing {key}"
        assert isinstance(row["wins"], int)
        assert isinstance(row["losses"], int)


def test_reader_output_feeds_compute_asset_class_health(monkeypatch):
    # The reader's output must be shape-compatible with
    # compute_asset_class_health (the whole point of the M-067 seam).
    monkeypatch.setenv("AUDIT_HEALTH_SOURCE", "registry")
    mod = importlib.import_module("audit_trail.dashboard_generator")
    breakdown = mod._registry_backed_ac_breakdown()
    if breakdown is None:
        pytest.skip("registry unavailable in this environment — fail-open path")
    health = mod.compute_asset_class_health(breakdown)
    assert isinstance(health, dict)
    for ac, h in health.items():
        assert "sizing_allowed" in h
        assert "status" in h
        assert "pf" in h
