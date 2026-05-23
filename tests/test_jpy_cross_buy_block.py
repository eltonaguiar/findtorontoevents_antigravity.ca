"""
Tests for JPY-cross BUY-direction surgical kill (Phase 2-C 6/7 panel, 2026-04-29).

Per reports/HFPA_PHASE-2-findings-FOREX-2026-04-29.md, JPY-cross pairs
(CADJPY/EURJPY/NZDJPY/GBPJPY/AUDJPY) BUY-direction picks drove the entire
-45.43% jpy_cross 30d loss. LONG and SHORT sub-cohorts are profitable.

Surgical kill: block BUY only on the 5-pair set; preserve LONG/SHORT.
USDJPY=X is excluded (panel: n=64 PF 9.50 historical — keep).

Rollback: JPY_CROSS_BUY_KILL_DISABLED=1
"""
import os
from datetime import datetime, timezone

import pytest

import audit_trail.quality_gates as qg
from audit_trail.quality_gates import (
    JPY_CROSS_PAIRS,
    passes_active_gate,
)


def _forex_pick(**overrides):
    """Forex pick base with conservative quality stats so non-JPY tests pass."""
    pick = {
        "id": "fx-pick-1",
        "symbol": "EURJPY=X",
        "asset_class": "FOREX",
        "source_system": "copy_trader_myfxbook",
        "strategy": "myfxbook_trend_follow",
        "status": "OPEN",
        "direction": "BUY",
        "entry_price": 150.0,
        "take_profit": 152.0,
        "stop_loss": 149.0,
        "score": 63,
        "elite_score": None,
        "trust_score": 6,
        "trust_label": "MODERATE",
        "confidence": 0.70,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source_tier": "PROVEN",
    }
    pick.update(overrides)
    return pick


@pytest.fixture(autouse=True)
def _clear_rollback_flag(monkeypatch):
    """Ensure each test starts with the kill ENABLED (default-on) unless flipped."""
    monkeypatch.delenv("JPY_CROSS_BUY_KILL_DISABLED", raising=False)
    # NS-E defaulted ON 2026-05-15 (FOREX class-wide halt). This file tests
    # the JPY-cross BUY rule specifically; bypass the class-wide halt so
    # rule-specific assertions are reachable.
    monkeypatch.setenv("FOREX_HARD_DISABLE", "0")
    # FOREX smart gate blocks all LONG/BUY picks; disable for JPY-rule isolation.
    monkeypatch.setenv("FOREX_SHORT_ONLY_GATE_DISABLED", "1")
    # M-078 FOREX session gate is time-dependent (08-16 UTC fail-closed);
    # disable for isolation tests not testing session behavior.
    monkeypatch.setenv("FOREX_SESSION_GATE_DISABLED", "1")
    yield


def test_jpy_cross_pairs_constant_excludes_usdjpy() -> None:
    """USDJPY=X should NOT be in the kill set per panel (PF 9.50 — keep)."""
    assert "USDJPY=X" not in JPY_CROSS_PAIRS
    assert "CADJPY=X" in JPY_CROSS_PAIRS
    assert "EURJPY=X" in JPY_CROSS_PAIRS
    assert "NZDJPY=X" in JPY_CROSS_PAIRS
    assert "GBPJPY=X" in JPY_CROSS_PAIRS
    assert "AUDJPY=X" in JPY_CROSS_PAIRS


def test_cadjpy_buy_blocked() -> None:
    pick = _forex_pick(symbol="CADJPY=X", direction="BUY")
    assert passes_active_gate(pick) is False


def test_eurjpy_buy_blocked() -> None:
    pick = _forex_pick(symbol="EURJPY=X", direction="BUY")
    assert passes_active_gate(pick) is False


def test_nzdjpy_buy_blocked() -> None:
    pick = _forex_pick(symbol="NZDJPY=X", direction="BUY")
    assert passes_active_gate(pick) is False


def test_gbpjpy_buy_blocked() -> None:
    pick = _forex_pick(symbol="GBPJPY=X", direction="BUY")
    assert passes_active_gate(pick) is False


def test_audjpy_buy_blocked() -> None:
    pick = _forex_pick(symbol="AUDJPY=X", direction="BUY")
    assert passes_active_gate(pick) is False


def test_usdjpy_buy_allowed(monkeypatch) -> None:
    """USDJPY=X is NOT in the kill set per panel (PF 9.50 — keep).

    Verifies the JPY-cross BUY rule does not affect USDJPY by toggling
    the JPY_CROSS_BUY_KILL_DISABLED flag and confirming the function
    returns the same verdict either way (the kill rule is a no-op for USDJPY).

    2026-05-02 fix: previous version asserted
    `passes_active_gate(pick) == passes_active_gate(pick.copy())`
    which failed nondeterministically when the time-of-day dead-zone
    penalty (hours 6-12 UTC) interacted with the first call's mutation
    of `pick._penalties` (the shallow copy shared the list reference).
    """
    # Authoritative invariant: USDJPY=X must not be in the JPY-cross ban set.
    assert "USDJPY=X" not in JPY_CROSS_PAIRS, (
        "USDJPY=X must be excluded from JPY-cross kill set per Phase 2-C panel"
    )

    # Behavioral check: toggle the env flag, confirm USDJPY verdict is invariant.
    pick_default = _forex_pick(symbol="USDJPY=X", direction="BUY")
    pick_disabled = _forex_pick(symbol="USDJPY=X", direction="BUY")

    monkeypatch.delenv("JPY_CROSS_BUY_KILL_DISABLED", raising=False)
    result_default = passes_active_gate(pick_default)

    monkeypatch.setenv("JPY_CROSS_BUY_KILL_DISABLED", "1")
    result_disabled = passes_active_gate(pick_disabled)

    # Both paths must agree — the kill rule is a no-op for USDJPY.
    assert result_default == result_disabled, (
        f"USDJPY BUY verdict changed when JPY_CROSS_BUY_KILL_DISABLED toggled: "
        f"default={result_default} disabled={result_disabled}. "
        "USDJPY=X should be invariant to that flag."
    )


def test_cadjpy_long_blocked_by_jpy_buy_rule() -> None:
    """LONG direction must be blocked — taxonomy fix 2026-05-02.

    Original 2026-04-29 test asserted LONG should pass. That assertion was
    tautologically true because the rule's `_jpy_dir == "BUY"` check never
    fired against production picks (which arrive tagged direction="LONG"
    after `_normalize_direction()` upstream). Live data 2026-05-02 confirmed
    the bypass: 90 LONG JPY-cross picks landed in 7d with -40.8% sum PnL.
    The rule's intent was to block long-side bets on JPY crosses; "LONG" is
    the canonical long-side label, so it must be blocked along with raw "BUY".
    """
    pick = _forex_pick(symbol="CADJPY=X", direction="LONG")
    assert passes_active_gate(pick) is False


def test_cadjpy_bullish_blocked_by_jpy_buy_rule() -> None:
    """BULLISH direction (alias of LONG) must also be blocked."""
    pick = _forex_pick(symbol="CADJPY=X", direction="BULLISH")
    assert passes_active_gate(pick) is False


def test_cadjpy_short_allowed_when_jpy_buy_killed() -> None:
    """SHORT direction profitable per panel — must NOT be blocked by the BUY rule."""
    pick = _forex_pick(symbol="CADJPY=X", direction="SHORT")
    assert passes_active_gate(pick) is True


def test_cadjpy_sell_allowed_when_jpy_buy_killed() -> None:
    """SELL direction (alias of SHORT) — must NOT be blocked by the BUY rule."""
    pick = _forex_pick(symbol="CADJPY=X", direction="SELL")
    assert passes_active_gate(pick) is True


def test_eurusd_buy_allowed_not_jpy_cross() -> None:
    """Non-JPY-cross BUY must NOT be blocked by the JPY rule."""
    pick = _forex_pick(symbol="EURUSD=X", direction="BUY")
    assert passes_active_gate(pick) is True


def test_rollback_flag_allows_jpy_cross_buy(monkeypatch) -> None:
    """JPY_CROSS_BUY_KILL_DISABLED=1 must restore pre-fix behavior."""
    monkeypatch.setenv("JPY_CROSS_BUY_KILL_DISABLED", "1")

    for sym in ("CADJPY=X", "EURJPY=X", "NZDJPY=X", "GBPJPY=X", "AUDJPY=X"):
        pick = _forex_pick(symbol=sym, direction="BUY")
        # With rollback flag ON, the JPY BUY rule must NOT trigger.
        # Pick passes the rule (other quality gates may still apply, but the
        # JPY-cross-specific rejection must be off).
        assert passes_active_gate(pick) is True, (
            f"{sym} BUY should pass when JPY_CROSS_BUY_KILL_DISABLED=1"
        )


def test_rollback_flag_zero_keeps_block_active(monkeypatch) -> None:
    """JPY_CROSS_BUY_KILL_DISABLED=0 keeps the default-on block."""
    monkeypatch.setenv("JPY_CROSS_BUY_KILL_DISABLED", "0")
    pick = _forex_pick(symbol="EURJPY=X", direction="BUY")
    assert passes_active_gate(pick) is False


def test_non_forex_jpy_symbol_not_blocked() -> None:
    """The rule is FOREX-asset-class-scoped — a non-FOREX EURJPY=X is unaffected.

    2026-05-03 fix: build two fresh picks (one per call) — `passes_active_gate`
    mutates `pick._penalties` in-place (audit_trail/quality_gates.py:4106-4118),
    so reusing the same dict across two calls picks up the first call's mutation.
    Mirrors the pattern in test_usdjpy_buy_allowed at :99-104.
    """
    # EQUITY EURJPY is not blocked by JPY rule (other gates may apply, but
    # the JPY-cross-BUY rule specifically should not be the cause).
    # We validate by toggling the env and confirming both branches behave
    # identically for asset_class != FOREX.
    pick_default = _forex_pick(symbol="EURJPY=X", direction="BUY", asset_class="EQUITY")
    pick_disabled = _forex_pick(symbol="EURJPY=X", direction="BUY", asset_class="EQUITY")
    result_default = passes_active_gate(pick_default)
    os.environ["JPY_CROSS_BUY_KILL_DISABLED"] = "1"
    try:
        result_disabled = passes_active_gate(pick_disabled)
    finally:
        del os.environ["JPY_CROSS_BUY_KILL_DISABLED"]
    assert result_default == result_disabled
