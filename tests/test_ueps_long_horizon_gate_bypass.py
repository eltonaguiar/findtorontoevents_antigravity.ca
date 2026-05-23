"""Unit tests for UEPS long-horizon active-gate bypass.

Plan: reports/UEPS_GATE_FIX_PLAN_2026_05_01.md (3-AI unanimous Option B,
final SHIP-WITH-MINOR-EDITS reviewer added test 7).

Bypass surface: when UEPS_LONG_HORIZON_GATE_BYPASS_ENABLED=1 AND
source_system=ueps AND trade_timeframe=POSITION, three short-term-calibrated
filters are skipped: raw-score-55 floor, BLOCKED_SYMBOLS, elite_grade D.
All real-safety gates remain active.
"""
from __future__ import annotations

import importlib
import os

import pytest


def _reload_gates():
    import audit_trail.quality_gates as q
    importlib.reload(q)
    return q


def _ueps_pick(**overrides):
    """Build a UEPS-shaped pick from the empirical dashboard data."""
    base = {
        "id": "test_ueps_pick",
        "symbol": "META",
        "source_system": "ueps",
        "strategy": "magic_formula_x_piotroski_x_acquirers",
        "asset_class": "EQUITY",
        "direction": "LONG",
        "entry_price": 250.0,
        "take_profit": 270.0,
        "stop_loss": 238.0,
        "score": 19,
        "confidence": 0.74,
        "trust_score": 3,
        "trust_tier": "RELIABLE",
        "status": "OPEN",
        "trade_timeframe": "POSITION",
        "elite_grade": "B",
        "wf_verdict": None,
    }
    base.update(overrides)
    return base


@pytest.fixture(autouse=True)
def _restore_env(monkeypatch):
    monkeypatch.delenv("UEPS_LONG_HORIZON_GATE_BYPASS_ENABLED", raising=False)
    # PR #644 (per-asset-class smart-gate) flipped non-crypto active-gate
    # strictness to default-permissive (PER_ASSET_QUALITY_ACTIVE_PERMISSIVE=1).
    # The strict checks the UEPS-bypass tests exercise (score<55 floor,
    # BLOCKED_SYMBOLS active-gate, universal-40 floor) only fire when the
    # operator opts into strict mode. Test the strict-mode behavior.
    monkeypatch.setenv("PER_ASSET_QUALITY_ACTIVE_PERMISSIVE", "0")
    yield


# ── Test 1 — Default-OFF safety: current behavior preserved ────────────────
def test_default_off_blocks_low_score_ueps(monkeypatch):
    monkeypatch.delenv("UEPS_LONG_HORIZON_GATE_BYPASS_ENABLED", raising=False)
    q = _reload_gates()
    pick = _ueps_pick(symbol="META", score=19)
    assert q.passes_active_gate(pick) is False


# ── Test 2 — Flag ON skips raw-score floor for UEPS POSITION ──────────────
def test_flag_on_bypasses_score_floor(monkeypatch):
    monkeypatch.setenv("UEPS_LONG_HORIZON_GATE_BYPASS_ENABLED", "1")
    q = _reload_gates()
    pick = _ueps_pick(symbol="META", score=19)
    assert q.passes_active_gate(pick) is True


# ── Test 3 — Flag ON skips BLOCKED_SYMBOLS for UEPS, not for others ───────
def test_flag_on_bypasses_blocked_symbols_only_for_ueps(monkeypatch):
    monkeypatch.setenv("UEPS_LONG_HORIZON_GATE_BYPASS_ENABLED", "1")
    q = _reload_gates()
    # MATICUSDT is in BLOCKED_SYMBOLS and _DATA_QUALITY_BLOCKS (UEPS bypass allowed)
    assert "MATICUSDT" in q.BLOCKED_SYMBOLS
    ueps_matic = _ueps_pick(symbol="MATICUSDT", score=70, elite_grade="A")
    assert q.passes_active_gate(ueps_matic) is True
    # NVDA is in BLOCKED_SYMBOLS but NOT _DATA_QUALITY_BLOCKS (UEPS bypass blocked)
    assert "NVDA" in q.BLOCKED_SYMBOLS
    ueps_nvda = _ueps_pick(symbol="NVDA", score=70, elite_grade="A")
    assert q.passes_active_gate(ueps_nvda) is False
    non_ueps_nvda = _ueps_pick(
        symbol="NVDA",
        score=70,
        elite_grade="A",
        source_system="kimi_riseoftheclaw",
    )
    assert q.passes_active_gate(non_ueps_nvda) is False


# ── Test 4 — Flag ON skips elite_grade=D for UEPS only ────────────────────
def test_flag_on_bypasses_elite_grade_d(monkeypatch):
    monkeypatch.setenv("UEPS_LONG_HORIZON_GATE_BYPASS_ENABLED", "1")
    q = _reload_gates()
    pick = _ueps_pick(symbol="IBM", score=70, elite_grade="D")
    assert q.passes_active_gate(pick) is True
    # Grade F still hard-blocked (no exemption)
    pick_f = _ueps_pick(symbol="IBM", score=70, elite_grade="F")
    assert q.passes_active_gate(pick_f) is False


# ── Test 5 — Non-UEPS sources unaffected by the flag ──────────────────────
def test_non_ueps_unaffected_by_flag(monkeypatch):
    monkeypatch.setenv("UEPS_LONG_HORIZON_GATE_BYPASS_ENABLED", "1")
    q = _reload_gates()
    # kimi POSITION pick with score=19 must still be rejected
    other = _ueps_pick(
        symbol="META",
        score=19,
        source_system="kimi_riseoftheclaw",
    )
    # kimi is in _NC_SCORE_EXEMPT_SOURCES so it bypasses 55-floor too,
    # but is still subject to the universal 40-floor; score=19 must reject.
    assert q.passes_active_gate(other) is False


# ── Test 6 — Status-closed real-safety gate still blocks UEPS ─────────────
def test_status_closed_still_blocks(monkeypatch):
    monkeypatch.setenv("UEPS_LONG_HORIZON_GATE_BYPASS_ENABLED", "1")
    q = _reload_gates()
    pick = _ueps_pick(symbol="GOOGL", score=70, status="SL_HIT")
    assert q.passes_active_gate(pick) is False


# ── Test 7 — Forward-WR floor still enforced under bypass (final-review) ──
def test_forward_wr_floor_still_enforced_under_bypass(monkeypatch):
    """When UEPS picks accumulate >=20 closed trades, the forward-WR floor
    must still hard-reject sub-edge cohorts. The bypass only skips three
    short-term-calibrated filters; it must NOT skip realized-evidence gates.
    """
    monkeypatch.setenv("UEPS_LONG_HORIZON_GATE_BYPASS_ENABLED", "1")
    q = _reload_gates()
    # Synthesize a UEPS pick with enough forward trades and a sub-edge WR.
    pick = _ueps_pick(
        symbol="MSFT",
        score=70,
        elite_grade="A",
        forward_wr=0.20,           # 20% WR — well below non-crypto floor
        forward_trades=50,         # >= ACTIVE_NON_CRYPTO_MIN_FORWARD_TRADES (20)
        strat_fwd_wr=0.20,
        strat_fwd_trades=50,
    )
    assert q.passes_active_gate(pick) is False


# ── TF-guard: bypass only fires for trade_timeframe=POSITION ──────────────
def test_bypass_only_applies_to_position_timeframe(monkeypatch):
    monkeypatch.setenv("UEPS_LONG_HORIZON_GATE_BYPASS_ENABLED", "1")
    q = _reload_gates()
    # UEPS pick with INTRADAY tf — should NOT bypass
    pick = _ueps_pick(symbol="META", score=19, trade_timeframe="INTRADAY")
    assert q.passes_active_gate(pick) is False


# ── Test 8 — Universal score-40 floor bypass is INTENTIONAL ──────────────
# Per Copilot's review of PR #599: the implementation bypasses 4 filters,
# not the 3 named in the original plan doc (score-55 floor, BLOCKED_SYMBOLS,
# elite_grade D). The 4th is the universal raw-score 40 floor at
# quality_gates.py:4577. This test pins that the 4-filter behavior is
# intentional and documents the empirical reason: with only the 3 plan-spec'd
# filters bypassed, only 20/30 UEPS picks passed when the env flag was ON
# (META=19, IBM=38, AVGO=37, BMY=34, BA=31, XOM=25, AAPL=21 still failed
# the universal 40 floor). Adding the universal-40 bypass got 29/30 through
# (the 30th — GOOGL — correctly stayed blocked for status=SL_HIT).
#
# The universal-40 floor is also short-term-calibrated (UEPS scoring
# distribution is naturally lower than short-term technical scoring), so
# bypassing it is consistent with the plan's intent of skipping
# short-term-calibrated rejecters.
#
# Plan doc updated 2026-05-02 to reflect 4 filters, not 3, in
# reports/UEPS_GATE_FIX_PLAN_2026_05_01.md.
def test_universal_40_floor_bypass_is_intentional(monkeypatch):
    """Score below universal 40 floor (e.g., META=19) must pass for UEPS
    POSITION with flag ON. Confirms intentional 4th-filter bypass.
    """
    monkeypatch.setenv("UEPS_LONG_HORIZON_GATE_BYPASS_ENABLED", "1")
    q = _reload_gates()
    # META score=19 from the empirical 30-pick run — below universal 40 floor
    pick = _ueps_pick(symbol="META", score=19, elite_grade="B")
    assert q.passes_active_gate(pick) is True, (
        "UEPS POSITION pick with score < 40 (universal floor) must pass when "
        "flag is ON — universal-40 bypass is intentional per empirical 30-pick "
        "verification (Flag ON: 29/30 UEPS pass; without universal-40 bypass "
        "only 20/30 would pass)"
    )

    # Negative control: non-UEPS pick with same score must still fail at universal-40
    other = _ueps_pick(
        symbol="AAPL",
        score=19,
        source_system="kimi_riseoftheclaw",
    )
    assert q.passes_active_gate(other) is False, (
        "Non-UEPS pick with score < 40 must still hit universal floor (no leak)"
    )


# ── Helper invariants (defense-in-depth) ──────────────────────────────────
def test_helper_returns_false_when_flag_unset(monkeypatch):
    monkeypatch.delenv("UEPS_LONG_HORIZON_GATE_BYPASS_ENABLED", raising=False)
    q = _reload_gates()
    pick = _ueps_pick()
    assert q._ueps_long_horizon_bypass_active(pick) is False


def test_helper_returns_true_when_all_conditions_met(monkeypatch):
    monkeypatch.setenv("UEPS_LONG_HORIZON_GATE_BYPASS_ENABLED", "1")
    q = _reload_gates()
    pick = _ueps_pick()
    assert q._ueps_long_horizon_bypass_active(pick) is True


def test_helper_rejects_non_ueps_source(monkeypatch):
    monkeypatch.setenv("UEPS_LONG_HORIZON_GATE_BYPASS_ENABLED", "1")
    q = _reload_gates()
    pick = _ueps_pick(source_system="kimi_riseoftheclaw")
    assert q._ueps_long_horizon_bypass_active(pick) is False
