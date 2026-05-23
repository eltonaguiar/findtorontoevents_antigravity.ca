"""Tests for COT dedup guard — PR-#994 (2026-05-15).

Background: multi_asset_cot emits repeated picks on the same symbol (CT=F,
cotton) every CFTC weekly release cycle.  94.3% of COMMODITY picks were CT=F,
making n=130 look impressive while the deduped reality is WR=40% / PF=0.17.

The guard (COT_DEDUP_SYSTEMS + COT_DEDUP_WINDOW_HOURS in quality_gates.py)
rejects a COT pick for symbol S from source_system X if any active pick with
the same (symbol, source_system) was admitted fewer than 72 hours ago.

These tests verify:
  1. test_duplicate_cot_pick_rejected_within_72h — duplicate within 72h → False
  2. test_cot_pick_allowed_after_72h            — same pair after 72h  → True
"""
from __future__ import annotations

import time
from typing import Any, Dict
from unittest.mock import patch

import pytest


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_cot_pick(
    symbol: str = "CT=F",
    source_system: str = "multi_asset_cot",
    asset_class: str = "COMMODITY",
    **extra: Any,
) -> Dict[str, Any]:
    """Minimal COMMODITY COT pick that satisfies passes_active_gate guards."""
    return {
        "symbol": symbol,
        "source_system": source_system,
        "asset_class": asset_class,
        "strategy": "cot_commercial_long",
        "direction": "long",
        "confidence": 0.90,
        "score": 80,
        "elite_score": 80,
        "trust_score": 5,
        "status": "OPEN",
        "entry_price": 70.0,
        "take_profit": 73.0,
        "stop_loss": 68.0,
        "pnl_pct": 0.0,
        **extra,
    }


def _make_active_pick(
    symbol: str = "CT=F",
    source_system: str = "multi_asset_cot",
    admitted_at_ts: float | None = None,
) -> Dict[str, Any]:
    """Simulate an already-active pick as it would appear in active_picks.json."""
    if admitted_at_ts is None:
        admitted_at_ts = time.time()
    return {
        "symbol": symbol,
        "source_system": source_system,
        "asset_class": "COMMODITY",
        "strategy": "cot_commercial_long",
        "direction": "long",
        "status": "OPEN",
        "admitted_at": admitted_at_ts,
    }


# ── constants sanity ──────────────────────────────────────────────────────────

def test_cot_dedup_constants_exported() -> None:
    """COT_DEDUP_SYSTEMS and COT_DEDUP_WINDOW_HOURS must be importable."""
    from audit_trail.quality_gates import COT_DEDUP_SYSTEMS, COT_DEDUP_WINDOW_HOURS

    assert "multi_asset_cot" in COT_DEDUP_SYSTEMS
    assert "cot_positioning" in COT_DEDUP_SYSTEMS
    assert "cftc_cot_commercial_signal" in COT_DEDUP_SYSTEMS
    assert COT_DEDUP_WINDOW_HOURS == 72


# ── core behaviour ────────────────────────────────────────────────────────────

def test_duplicate_cot_pick_rejected_within_72h(monkeypatch: pytest.MonkeyPatch) -> None:
    """A COT pick for CT=F from multi_asset_cot is rejected when an identical
    active pick was admitted only 1 hour ago (well within the 72h window)."""
    from audit_trail import quality_gates as qg

    # Active pick admitted 1 hour ago
    one_hour_ago = time.time() - 3600
    existing = _make_active_pick(admitted_at_ts=one_hour_ago)

    incoming = _make_cot_pick()

    # Patch _cached_active_picks_snapshot to return the existing pick
    # Patch all gates that read external data so only the dedup gate is live
    monkeypatch.setenv("COT_DEDUP_GATE_ENABLED", "1")
    monkeypatch.setenv("COT_MATCH_GATE_ENABLED", "0")
    monkeypatch.setenv("SAFETY_HALT_GATE_ENABLED", "0")
    monkeypatch.setenv("CONCENTRATION_CAP_ENABLED", "0")
    monkeypatch.setenv("CHARTER_CONCENTRATION_ENFORCE", "0")
    monkeypatch.setenv("FOREX_DIRECTIONAL_GATE_ENABLED", "0")

    with patch.object(qg, "_cached_active_picks_snapshot", return_value=[existing]):
        result = qg.passes_active_gate(incoming)

    assert result is False, (
        "Expected passes_active_gate to return False for a duplicate COT pick "
        "admitted 1 hour ago (within 72h dedup window)."
    )


def test_cot_pick_allowed_after_72h(monkeypatch: pytest.MonkeyPatch) -> None:
    """A COT pick for CT=F from multi_asset_cot is allowed when the most recent
    active pick for that (symbol, source) was admitted 80 hours ago (outside the
    72h window)."""
    from audit_trail import quality_gates as qg

    # Active pick admitted 80 hours ago — outside the 72h window
    eighty_hours_ago = time.time() - (80 * 3600)
    old_existing = _make_active_pick(admitted_at_ts=eighty_hours_ago)

    incoming = _make_cot_pick()

    monkeypatch.setenv("COT_DEDUP_GATE_ENABLED", "1")
    monkeypatch.setenv("COT_MATCH_GATE_ENABLED", "0")
    monkeypatch.setenv("SAFETY_HALT_GATE_ENABLED", "0")
    monkeypatch.setenv("CONCENTRATION_CAP_ENABLED", "0")
    monkeypatch.setenv("CHARTER_CONCENTRATION_ENFORCE", "0")
    monkeypatch.setenv("FOREX_DIRECTIONAL_GATE_ENABLED", "0")

    with patch.object(qg, "_cached_active_picks_snapshot", return_value=[old_existing]):
        result = qg.passes_active_gate(incoming)

    # Gate should NOT reject — the old pick is outside the 72h window.
    # (The function may still return False due to other gates like blocked symbols,
    # but it must NOT be blocked by the COT dedup gate specifically.)
    # We verify by checking the pick was NOT tagged with a COT dedup rejection.
    # If no other gate blocks CT=F we expect True; we also accept True from this call.
    # Because other gates may legitimately fire, we only assert the dedup guard
    # does not short-circuit — we check by running with an empty active cache first
    # (baseline) and confirm 80h case matches baseline (not a stricter reject).
    with patch.object(qg, "_cached_active_picks_snapshot", return_value=[]):
        baseline = qg.passes_active_gate(dict(incoming))  # fresh copy

    with patch.object(qg, "_cached_active_picks_snapshot", return_value=[old_existing]):
        result_80h = qg.passes_active_gate(dict(incoming))  # fresh copy

    assert result_80h == baseline, (
        f"Expected 80h-old active pick to NOT trigger dedup reject "
        f"(baseline={baseline}, 80h result={result_80h}). "
        "COT dedup guard is incorrectly blocking picks outside the 72h window."
    )


def test_cot_dedup_kill_switch(monkeypatch: pytest.MonkeyPatch) -> None:
    """With COT_DEDUP_GATE_ENABLED=0 the guard is fully disabled — a pick that
    would normally be rejected within the 72h window should pass the dedup gate
    (though other gates may still apply)."""
    from audit_trail import quality_gates as qg

    # Active pick admitted 1 hour ago — would normally trigger dedup
    one_hour_ago = time.time() - 3600
    existing = _make_active_pick(admitted_at_ts=one_hour_ago)

    monkeypatch.setenv("COT_DEDUP_GATE_ENABLED", "0")  # kill-switch
    monkeypatch.setenv("COT_MATCH_GATE_ENABLED", "0")
    monkeypatch.setenv("SAFETY_HALT_GATE_ENABLED", "0")
    monkeypatch.setenv("CONCENTRATION_CAP_ENABLED", "0")
    monkeypatch.setenv("CHARTER_CONCENTRATION_ENFORCE", "0")
    monkeypatch.setenv("FOREX_DIRECTIONAL_GATE_ENABLED", "0")

    incoming = _make_cot_pick()

    with patch.object(qg, "_cached_active_picks_snapshot", return_value=[existing]):
        # With dedup disabled, result should match empty-cache baseline
        result_kill = qg.passes_active_gate(dict(incoming))

    with patch.object(qg, "_cached_active_picks_snapshot", return_value=[]):
        result_baseline = qg.passes_active_gate(dict(incoming))

    assert result_kill == result_baseline, (
        f"COT_DEDUP_GATE_ENABLED=0 kill-switch did not disable the dedup guard "
        f"(kill={result_kill}, baseline={result_baseline})."
    )


def test_cot_dedup_different_symbol_not_blocked(monkeypatch: pytest.MonkeyPatch) -> None:
    """The dedup guard must NOT block a pick for GC=F (gold) just because
    CT=F (cotton) has an active pick from the same source within 72h."""
    from audit_trail import quality_gates as qg

    one_hour_ago = time.time() - 3600
    cotton_active = _make_active_pick(symbol="CT=F", admitted_at_ts=one_hour_ago)
    gold_incoming = _make_cot_pick(symbol="GC=F")

    monkeypatch.setenv("COT_DEDUP_GATE_ENABLED", "1")
    monkeypatch.setenv("COT_MATCH_GATE_ENABLED", "0")
    monkeypatch.setenv("SAFETY_HALT_GATE_ENABLED", "0")
    monkeypatch.setenv("CONCENTRATION_CAP_ENABLED", "0")
    monkeypatch.setenv("CHARTER_CONCENTRATION_ENFORCE", "0")
    monkeypatch.setenv("FOREX_DIRECTIONAL_GATE_ENABLED", "0")

    with patch.object(qg, "_cached_active_picks_snapshot", return_value=[]):
        baseline = qg.passes_active_gate(dict(gold_incoming))

    with patch.object(qg, "_cached_active_picks_snapshot", return_value=[cotton_active]):
        result = qg.passes_active_gate(dict(gold_incoming))

    assert result == baseline, (
        "COT dedup guard incorrectly blocked GC=F pick because CT=F was active. "
        "Dedup must be (symbol, source_system) scoped, not source_system-only."
    )
