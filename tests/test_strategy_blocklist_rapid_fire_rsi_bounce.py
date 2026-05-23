"""Pin the 2026-04-29 surgical kill of (rapid_fire, rsi_bounce).

Phase 2-A CRYPTO panel 8/8 unanimous Accepted "kill / quarantine
rapid_fire source" (see reports/HFPA_PHASE-2-findings-CRYPTO-2026-04-29.md
Edge-killers section). PR #509 already retired the sibling
(rapid_fire, macd_rsi_confluence) composite (n=133, sum -48.88%); this
test covers the second remaining rapid_fire composite, n=23 / WR 47.8%
/ sum -11.37% / 100% LONG / 100% BANNED trust_tier.

If this test starts failing because the entry has been removed, restore
the entry or delete the test with a written rationale in the commit
message and a linked report explaining why the kill is no longer
warranted (per `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` Stage-5
reversal section).
"""

from __future__ import annotations

import importlib

import pytest

import alpha_engine.strategy_blocklist as blocklist


@pytest.fixture(autouse=True)
def _restore_module(monkeypatch):
    """Ensure each test runs with the default rollback flag state."""
    monkeypatch.delenv("RAPID_FIRE_RSI_BOUNCE_KILL_DISABLED", raising=False)
    importlib.reload(blocklist)
    yield
    monkeypatch.delenv("RAPID_FIRE_RSI_BOUNCE_KILL_DISABLED", raising=False)
    importlib.reload(blocklist)


def test_rapid_fire_rsi_bounce_pair_in_retired_set():
    """Composite pair must be present in _RETIRED_SYSTEM_STRATEGY_PAIRS."""
    assert ("rapid_fire", "rsi_bounce") in (
        blocklist._RETIRED_SYSTEM_STRATEGY_PAIRS
    )


def test_rapid_fire_rsi_bounce_pick_blocked_by_default():
    pick = {
        "source_system": "rapid_fire",
        "strategy": "rsi_bounce",
        "symbol": "BTCUSDT",
        "direction": "LONG",
    }
    assert blocklist.is_blocked_pick(pick) is True
    assert blocklist.pick_block_reason(pick) == "retired-composite"


def test_rapid_fire_rsi_bounce_kill_can_be_disabled_via_env(monkeypatch):
    """Rollback path: RAPID_FIRE_RSI_BOUNCE_KILL_DISABLED=1 bypasses the composite."""
    monkeypatch.setenv("RAPID_FIRE_RSI_BOUNCE_KILL_DISABLED", "1")
    importlib.reload(blocklist)
    pick = {
        "source_system": "rapid_fire",
        "strategy": "rsi_bounce",
        "symbol": "BTCUSDT",
        "direction": "LONG",
    }
    assert blocklist.is_blocked_pick(pick) is False
    assert blocklist.pick_block_reason(pick) == ""


def test_rapid_fire_rsi_bounce_kill_falsy_env_keeps_kill_active(monkeypatch):
    """Falsy / unrecognized rollback values must NOT bypass the kill."""
    for v in ("0", "false", "no", "off", "", "garbage"):
        monkeypatch.setenv("RAPID_FIRE_RSI_BOUNCE_KILL_DISABLED", v)
        importlib.reload(blocklist)
        pick = {
            "source_system": "rapid_fire",
            "strategy": "rsi_bounce",
        }
        assert blocklist.is_blocked_pick(pick) is True, (
            f"Expected kill to remain active for env value {v!r}"
        )


def test_rsi_bounce_from_other_systems_not_affected():
    """Composite kill is system-specific, not strategy-wide."""
    pick = {
        "source_system": "alpha_engine",
        "strategy": "rsi_bounce",
    }
    # Not in _RETIRED_STRATEGIES (strategy-wide kill) and not in the
    # composite set under this system, so it must pass.
    assert blocklist.is_blocked_pick(pick) is False


def test_other_rapid_fire_strategies_not_affected_by_rsi_bounce_kill():
    """Surgical kill must NOT block other rapid_fire strategies (e.g. macd_crossover)."""
    pick = {
        "source_system": "rapid_fire",
        "strategy": "macd_crossover",  # different strategy, same system
        "symbol": "LINKUSDT",
        "direction": "SHORT",
    }
    # Note: macd_rsi_confluence under rapid_fire IS blocked (PR #509) but
    # macd_crossover is NOT, so we explicitly assert the rsi_bounce kill
    # didn't accidentally widen the scope.
    assert blocklist.is_blocked_pick(pick) is False


def test_macd_rsi_confluence_kill_unaffected_by_rsi_bounce_rollback(monkeypatch):
    """Per-pair rollback flags must be independent — disabling rsi_bounce
    must NOT also re-enable the macd_rsi_confluence composite."""
    monkeypatch.setenv("RAPID_FIRE_RSI_BOUNCE_KILL_DISABLED", "1")
    monkeypatch.delenv("RAPID_FIRE_MACD_KILL_DISABLED", raising=False)
    importlib.reload(blocklist)
    pick_macd = {
        "source_system": "rapid_fire",
        "strategy": "macd_rsi_confluence",
    }
    # macd_rsi_confluence kill (PR #509) must remain active independently.
    assert blocklist.is_blocked_pick(pick_macd) is True
    assert blocklist.pick_block_reason(pick_macd) == "retired-composite"
