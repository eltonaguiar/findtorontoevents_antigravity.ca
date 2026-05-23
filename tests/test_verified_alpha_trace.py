"""Smoke: verified-alpha helpers are importable and gates return booleans."""

from audit_trail.dashboard_generator import (
    _extract_verified_alpha_audit,
    _is_verified_alpha_pick,
)


def test_is_verified_alpha_pick_empty() -> None:
    assert _is_verified_alpha_pick({}) is False
    assert _is_verified_alpha_pick({"source_system": "unknown"}) is False


def test_extract_verified_alpha_audit_optional() -> None:
    pick = {"forward_wr": 0.62, "forward_trades": 12}
    meta = _extract_verified_alpha_audit(pick)
    assert meta is None or isinstance(meta, dict)
