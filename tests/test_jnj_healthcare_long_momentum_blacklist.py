"""Tests for the Healthcare cluster + GS LONG-momentum blacklist.

Phase 2-B EQUITY panel 9/9 UNANIMOUS systematic_sector_bias verdict
(reports/HFPA_PHASE-2-findings-EQUITY-2026-04-29.md). Surgical rejection of
LONG-momentum picks on JNJ / ABBV / MRK / GS only. Preserves SHORT exposure
and non-momentum strategy types.

Rollback flag: HEALTHCARE_LONG_MOMENTUM_BLACKLIST_DISABLED=1
"""
from datetime import datetime, timezone

import pytest

import audit_trail.quality_gates as qg
from audit_trail.quality_gates import (
    JNJ_HEALTHCARE_GS_LONG_MOMENTUM_BLACKLIST,
    MOMENTUM_STRATEGY_FAMILIES,
    _is_momentum_flavored,
    passes_active_gate,
)


def _equity_pick(**overrides):
    """Build a baseline EQUITY pick that would otherwise pass the active gate.

    Uses `pm_whale_signals` (not in BLOCKED_SOURCE_SYSTEMS, no matrix_symbol_gates
    allow-list restriction) so toggling the healthcare blacklist flag actually
    changes the gate's verdict — letting us isolate the blacklist's behavior.
    Note: originally used multi_asset_copytrader, but that is now restricted to
    EURGBP=X/GBPUSD=X/INTC/NVDA/USDCHF=X by matrix_symbol_gates (JNJ blocked).
    """
    pick = {
        "id": "eq-test-1",
        "symbol": "JNJ",
        "asset_class": "EQUITY",
        "source_system": "pm_whale_signals",
        "strategy": "Breakout Momentum",
        "status": "OPEN",
        "direction": "LONG",
        "entry_price": 150.0,
        "take_profit": 165.0,
        "stop_loss": 142.5,
        "score": 80,
        "elite_score": 80,
        "elite_grade": "B",
        "trust_score": 6,
        "trust_label": "MODERATE",
        "trust_tier": "RELIABLE",
        "confidence": 0.88,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source_tier": "PROVEN",
        "wf_verdict": "PASSING",
        "fwd_wr_pct": 60.0,
        "fwd_n": 25,
    }
    pick.update(overrides)
    return pick


# ── Blacklist hits ──

def test_jnj_long_breakout_momentum_blocked(monkeypatch):
    monkeypatch.delenv("HEALTHCARE_LONG_MOMENTUM_BLACKLIST_DISABLED", raising=False)
    pick = _equity_pick(symbol="JNJ", direction="LONG", strategy="Breakout Momentum")
    assert passes_active_gate(pick) is False


def test_jnj_long_classic_momentum_blocked(monkeypatch):
    monkeypatch.delenv("HEALTHCARE_LONG_MOMENTUM_BLACKLIST_DISABLED", raising=False)
    pick = _equity_pick(symbol="JNJ", direction="LONG", strategy="Classic Momentum")
    assert passes_active_gate(pick) is False


def test_abbv_long_momentum_blocked(monkeypatch):
    monkeypatch.delenv("HEALTHCARE_LONG_MOMENTUM_BLACKLIST_DISABLED", raising=False)
    pick = _equity_pick(symbol="ABBV", direction="LONG", strategy="classic_momentum")
    assert passes_active_gate(pick) is False


def test_mrk_long_momentum_blocked(monkeypatch):
    monkeypatch.delenv("HEALTHCARE_LONG_MOMENTUM_BLACKLIST_DISABLED", raising=False)
    pick = _equity_pick(symbol="MRK", direction="LONG", strategy="breakout_momentum")
    assert passes_active_gate(pick) is False


def test_gs_long_momentum_blocked(monkeypatch):
    monkeypatch.delenv("HEALTHCARE_LONG_MOMENTUM_BLACKLIST_DISABLED", raising=False)
    pick = _equity_pick(symbol="GS", direction="LONG", strategy="rs-breakout-scout")
    assert passes_active_gate(pick) is False


def test_jnj_long_lowercase_symbol_blocked(monkeypatch):
    """Symbol comparison is case-insensitive (uses .upper())."""
    monkeypatch.delenv("HEALTHCARE_LONG_MOMENTUM_BLACKLIST_DISABLED", raising=False)
    pick = _equity_pick(symbol="jnj", direction="LONG", strategy="Breakout Momentum")
    assert passes_active_gate(pick) is False


# Helper: assert that the new blacklist gate is the ONLY thing rejecting a pick.
# We do this by toggling the rollback env-var and asserting behavior flips
# (rejected when default-on, accepted when disabled). This isolates the
# blacklist's effect from other gates that may also reject the synthetic pick.
def _blacklist_is_the_decider(pick, monkeypatch):
    """Return True iff toggling the rollback flag flips the gate result."""
    monkeypatch.delenv("HEALTHCARE_LONG_MOMENTUM_BLACKLIST_DISABLED", raising=False)
    default_on = passes_active_gate(dict(pick))
    monkeypatch.setenv("HEALTHCARE_LONG_MOMENTUM_BLACKLIST_DISABLED", "1")
    rollback = passes_active_gate(dict(pick))
    return default_on != rollback


def _blacklist_is_inert(pick, monkeypatch):
    """Return True iff toggling the rollback flag does NOT change the result."""
    monkeypatch.delenv("HEALTHCARE_LONG_MOMENTUM_BLACKLIST_DISABLED", raising=False)
    default_on = passes_active_gate(dict(pick))
    monkeypatch.setenv("HEALTHCARE_LONG_MOMENTUM_BLACKLIST_DISABLED", "1")
    rollback = passes_active_gate(dict(pick))
    return default_on == rollback


# ── SHORT exposure preserved (panel: 5/4 keep optionality) ──

def test_jnj_short_momentum_not_blacklisted(monkeypatch):
    """Panel-recommended: SHORT direction NOT blacklisted. Toggling the
    rollback flag must NOT change the gate result for a SHORT pick — proving
    the blacklist is direction-aware and isn't responsible for any SHORT
    rejection."""
    pick = _equity_pick(symbol="JNJ", direction="SHORT", strategy="Breakout Momentum")
    assert _blacklist_is_inert(pick, monkeypatch)


def test_abbv_short_momentum_not_blacklisted(monkeypatch):
    pick = _equity_pick(symbol="ABBV", direction="SHORT", strategy="classic_momentum")
    assert _blacklist_is_inert(pick, monkeypatch)


# ── Non-momentum strategies still allowed (only momentum blocked) ──

def test_jnj_long_bollinger_mr_not_blacklisted(monkeypatch):
    """Bollinger MR is mean-reversion, not momentum — blacklist must be inert."""
    pick = _equity_pick(symbol="JNJ", direction="LONG", strategy="Bollinger MR")
    assert _blacklist_is_inert(pick, monkeypatch)


def test_jnj_long_dividend_strategy_not_blacklisted(monkeypatch):
    pick = _equity_pick(symbol="JNJ", direction="LONG", strategy="dividend_capture")
    assert _blacklist_is_inert(pick, monkeypatch)


# ── Other symbols unaffected ──

def test_aapl_long_momentum_not_blacklisted(monkeypatch):
    """AAPL not in blacklist — toggle must NOT change the gate result."""
    pick = _equity_pick(symbol="AAPL", direction="LONG", strategy="Breakout Momentum")
    assert _blacklist_is_inert(pick, monkeypatch)


def test_msft_long_momentum_not_blacklisted(monkeypatch):
    pick = _equity_pick(symbol="MSFT", direction="LONG", strategy="Classic Momentum")
    assert _blacklist_is_inert(pick, monkeypatch)


# ── Rollback flag ──

def test_rollback_flag_disables_blacklist_for_jnj_long_momentum(monkeypatch):
    """HEALTHCARE_LONG_MOMENTUM_BLACKLIST_DISABLED=1 must flip the gate result
    for a blacklisted JNJ LONG-momentum pick (rejected → accepted-by-this-gate).

    We verify that with the flag set, `passes_active_gate` no longer rejects
    the pick *due to the blacklist*. Combined with the
    test_jnj_long_breakout_momentum_blocked test (default rejects), this proves
    the toggle works.
    """
    pick = _equity_pick(symbol="JNJ", direction="LONG", strategy="Breakout Momentum")
    assert _blacklist_is_the_decider(pick, monkeypatch)


def test_rollback_flag_zero_keeps_blacklist_active(monkeypatch):
    """Explicit '0' (default) keeps the blacklist active — JNJ LONG momentum rejected."""
    monkeypatch.setenv("HEALTHCARE_LONG_MOMENTUM_BLACKLIST_DISABLED", "0")
    pick = _equity_pick(symbol="JNJ", direction="LONG", strategy="Breakout Momentum")
    assert passes_active_gate(pick) is False


# ── Defense-in-depth: non-EQUITY asset classes not affected ──

def test_crypto_jnj_pseudo_pick_not_blocked_by_this_gate(monkeypatch):
    """Defense-in-depth: JNJ symbol on a CRYPTO pick (impossible in practice)
    must NOT be rejected by this gate (asset_class guard ensures it). This
    isolates the blacklist to EQUITY only.
    """
    monkeypatch.delenv("HEALTHCARE_LONG_MOMENTUM_BLACKLIST_DISABLED", raising=False)
    pick = _equity_pick(
        symbol="JNJ",
        asset_class="CRYPTO",
        direction="LONG",
        strategy="Breakout Momentum",
        # Make CRYPTO pick legal in other gates
        source_system="alpha_engine",
        score=70,
    )
    # We don't assert pass/fail of the whole gate (other CRYPTO gates may
    # legitimately reject a JNJ-symboled CRYPTO pick), only that this gate's
    # rejection reason is NOT the healthcare blacklist. We assert by toggling
    # the rollback flag and checking the result is identical (blacklist gate
    # contributes nothing).
    result_default = passes_active_gate(dict(pick))
    monkeypatch.setenv("HEALTHCARE_LONG_MOMENTUM_BLACKLIST_DISABLED", "1")
    result_disabled = passes_active_gate(dict(pick))
    assert result_default == result_disabled


# ── Helper unit tests ──

def test_is_momentum_flavored_exact_strings():
    assert _is_momentum_flavored("Classic Momentum") is True
    assert _is_momentum_flavored("Breakout Momentum") is True
    assert _is_momentum_flavored("classic_momentum") is True
    assert _is_momentum_flavored("breakout_momentum") is True


def test_is_momentum_flavored_substring_tokens():
    assert _is_momentum_flavored("price-accel-scout") is True
    assert _is_momentum_flavored("vol-contraction-scout") is True
    assert _is_momentum_flavored("rs-breakout-scout") is True
    assert _is_momentum_flavored("Some Custom Momentum Variant") is True


def test_is_momentum_flavored_negative():
    assert _is_momentum_flavored("Bollinger MR") is False
    assert _is_momentum_flavored("dividend_capture") is False
    assert _is_momentum_flavored("mean_reversion") is False
    assert _is_momentum_flavored("") is False
    assert _is_momentum_flavored(None) is False


def test_blacklist_constant_is_frozenset_with_expected_symbols():
    assert isinstance(JNJ_HEALTHCARE_GS_LONG_MOMENTUM_BLACKLIST, frozenset)
    assert JNJ_HEALTHCARE_GS_LONG_MOMENTUM_BLACKLIST == frozenset(
        {"JNJ", "ABBV", "MRK", "GS"}
    )
