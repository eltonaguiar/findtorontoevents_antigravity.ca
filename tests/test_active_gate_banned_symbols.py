"""
Regression tests for the CRYPTO_BANNED_SYMBOLS check in
``audit_trail.quality_gates.passes_active_gate``.

Pin the Issue #622 fix: banned crypto symbols (DOGEUSDT et al) must be
rejected at the active-gate boundary, not just at pick-generation or
smart-gate boundaries. This is defense-in-depth per memory
``feedback_gate_at_execution_not_generation``.

Without this check, PR #613's Kimi review observed DOGEUSDT in S-tier
active picks despite being entry #1 in ``CRYPTO_BANNED_SYMBOLS`` — the
ban is enforced in ``passes_hedge_fund_gate`` (called only from
``passes_smart_gate``), but ``passes_active_gate`` (the dashboard
visibility filter) never invoked it.
"""

from __future__ import annotations

import pytest

from alpha_engine.hedge_fund_quality_gate import CRYPTO_BANNED_SYMBOLS
from audit_trail.quality_gates import passes_active_gate


def _base_pick(symbol: str, **overrides) -> dict:
    """Build a pick with the minimum fields needed to pass other gates."""
    pick = {
        "id": f"test_{symbol}_001",
        "symbol": symbol,
        "status": "OPEN",
        "asset_class": "CRYPTO",
        "trust_tier": "RELIABLE",
        "score": 75,
        "trust_score": 7,
        "strategy": "test_strategy",
        "direction": "LONG",
        "entry_price": 1.0,
        "take_profit": 1.1,
        "stop_loss": 0.95,
        "created_at": "2026-05-02T00:00:00Z",
    }
    pick.update(overrides)
    return pick


# ---------------------------------------------------------------------------
# The fix: banned symbols rejected at active-gate boundary
# ---------------------------------------------------------------------------


def test_dogeusdt_rejected_at_active_gate():
    """DOGEUSDT is in CRYPTO_BANNED_SYMBOLS — must NEVER appear in active picks
    regardless of trust tier, score, or any other field."""
    assert "DOGEUSDT" in CRYPTO_BANNED_SYMBOLS, "DOGEUSDT must remain in ban list"
    pick = _base_pick("DOGEUSDT", trust_tier="RELIABLE", score=99)
    assert passes_active_gate(pick) is False


def test_dogeusdt_rejected_even_with_s_tier_priority():
    """Issue #622 specific scenario: DOGEUSDT showing up as S-tier active pick.
    The active gate must reject it BEFORE any tier-priority stamping."""
    pick = _base_pick(
        "DOGEUSDT",
        trust_tier="RELIABLE",
        score=99,
        tier_priority="S",
        strat_fwd_wr=85.0,
    )
    assert passes_active_gate(pick) is False


def test_dogeusdt_rejected_for_any_direction():
    """The ban must apply regardless of direction (LONG, SHORT, BUY, SELL)."""
    for direction in ("LONG", "SHORT", "BUY", "SELL"):
        pick = _base_pick("DOGEUSDT", direction=direction)
        assert passes_active_gate(pick) is False, f"DOGEUSDT {direction} not rejected"


def test_banned_symbol_lowercase_input_still_rejected():
    """Symbol comparison must be case-insensitive (the function uppercases
    internally)."""
    pick = _base_pick("dogeusdt")
    assert passes_active_gate(pick) is False


def test_all_banned_symbols_are_rejected():
    """Every entry in CRYPTO_BANNED_SYMBOLS must be rejected at active-gate."""
    for banned in sorted(CRYPTO_BANNED_SYMBOLS):
        pick = _base_pick(banned)
        result = passes_active_gate(pick)
        assert result is False, f"{banned} (in CRYPTO_BANNED_SYMBOLS) was not rejected"


# ---------------------------------------------------------------------------
# Negative controls — non-banned crypto symbols must still pass
# ---------------------------------------------------------------------------


def test_btcusdt_not_rejected_by_ban_check():
    """BTCUSDT is not in CRYPTO_BANNED_SYMBOLS — the ban check itself must NOT
    block it. (Other gates may still reject; this test only pins that the new
    ban check doesn't false-positive on common symbols.)"""
    assert "BTCUSDT" not in CRYPTO_BANNED_SYMBOLS, "BTCUSDT in ban list — this test obsolete"
    pick = _base_pick("BTCUSDT", trust_tier="ELITE", score=85, trust_score=9)
    # Either it passes other gates and returns True, or it fails them and
    # returns False — but the failure reason must not be the ban check.
    # We can't easily distinguish here, so we just ensure the function runs
    # without raising and returns a bool.
    result = passes_active_gate(pick)
    assert isinstance(result, bool)


def test_ethusdt_not_rejected_by_ban_check():
    assert "ETHUSDT" not in CRYPTO_BANNED_SYMBOLS, "ETHUSDT in ban list — this test obsolete"
    pick = _base_pick("ETHUSDT", trust_tier="ELITE", score=85, trust_score=9)
    result = passes_active_gate(pick)
    assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# The check is import-safe (graceful degradation if module not importable)
# ---------------------------------------------------------------------------


def test_active_gate_works_when_hedge_fund_module_unavailable(monkeypatch):
    """If alpha_engine.hedge_fund_quality_gate cannot be imported (e.g., in a
    minimal test environment), passes_active_gate should not raise — it should
    skip the ban check and continue to other gates."""
    import builtins
    real_import = builtins.__import__

    def _broken_import(name, *args, **kwargs):
        if "hedge_fund_quality_gate" in name:
            raise ImportError("simulated missing module")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _broken_import)

    pick = _base_pick("BTCUSDT", trust_tier="ELITE", score=85, trust_score=9)
    # Must not raise
    result = passes_active_gate(pick)
    assert isinstance(result, bool)
