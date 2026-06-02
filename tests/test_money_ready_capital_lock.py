"""Capital lock helpers + quality_gates wiring (EAGLE2 A1)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

# 2026-06-02: skip module until tag_money_ready_capital_lock + helpers land.
# Orphan test file (commit 4d89d0e9) references symbols not yet on main, was
# blocking every PR's CI. Re-enable once the feature PR lands.
_missing = []
try:
    from audit_trail.quality_gates import tag_money_ready_capital_lock  # noqa: F401
except ImportError:
    _missing.append("audit_trail.quality_gates.tag_money_ready_capital_lock")
try:
    from audit_trail.quality_gates import _money_ready_capital_lock_reason  # noqa: F401
except ImportError:
    _missing.append("audit_trail.quality_gates._money_ready_capital_lock_reason")
try:
    from alpha_engine.money_ready_verdict import _verdict_rows_cached  # noqa: F401
except (ImportError, AttributeError):
    _missing.append("alpha_engine.money_ready_verdict._verdict_rows_cached")

if _missing:
    pytest.skip(
        "money_ready_capital_lock helpers not yet on main: " + ", ".join(_missing),
        allow_module_level=True,
    )


def test_sizing_multiplier_locked_when_not_money_ready(monkeypatch):
    from alpha_engine import money_ready_verdict as mrv

    monkeypatch.setattr(
        mrv,
        "_verdict_rows_cached",
        lambda: {
            "CRYPTO": {"verdict": "NOT_READY", "n": 200, "pf": 0.9},
            "COMMODITY": {"verdict": "MONEY_READY", "n": 100, "pf": 2.0},
        },
    )
    assert mrv.sizing_multiplier_for_class("CRYPTO") == 0.0
    assert mrv.is_capital_locked_class("CRYPTO") is True
    assert mrv.sizing_multiplier_for_class("COMMODITY") == 1.0
    assert mrv.class_verdict("CRYPTO") == "NOT_READY"


def test_tag_money_ready_capital_lock_on_pick():
    from audit_trail.quality_gates import tag_money_ready_capital_lock
    from audit_trail import quality_gates as qg

    orig = qg._money_ready_capital_lock_reason
    try:
        qg._money_ready_capital_lock_reason = lambda ac: (
            "money_ready_capital_lock:NOT_READY" if ac == "EQUITY" else None
        )
        pick = {"asset_class": "EQUITY", "symbol": "SPY"}
        tag_money_ready_capital_lock(pick)
        assert pick["_sizing_override"] == "zero"
        assert pick["_capital_lock"] is True
        assert pick["_sizing_multiplier"] == 0.0

        untouched = {"asset_class": "COMMODITY", "symbol": "CT=F"}
        tag_money_ready_capital_lock(untouched)
        assert "_capital_lock" not in untouched
    finally:
        qg._money_ready_capital_lock_reason = orig


def test_smart_gate_blocks_capital_locked_class():
    from audit_trail.quality_gates import passes_smart_gate
    from audit_trail import quality_gates as qg

    orig_active = qg.passes_active_gate
    orig_reason = qg._money_ready_capital_lock_reason
    try:
        qg.passes_active_gate = lambda p: True
        qg._money_ready_capital_lock_reason = lambda ac: (
            "money_ready_capital_lock:NOT_READY" if ac == "CRYPTO" else None
        )
        blocked = {"asset_class": "CRYPTO", "symbol": "BTCUSDT", "score": 80}
        assert passes_smart_gate(blocked) is False
        assert blocked.get("_hf_quality_gate_reason", "").startswith(
            "money_ready_capital_lock"
        )
    finally:
        qg.passes_active_gate = orig_active
        qg._money_ready_capital_lock_reason = orig_reason