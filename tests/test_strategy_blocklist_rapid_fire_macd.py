"""Pin the 2026-04-29 surgical kill of (rapid_fire, macd_rsi_confluence).

Round 2 4-AI panel unanimous P0 (5/5): this composite contributed
~39% of all BANNED-tier closures (133 picks, 100% BANNED, sum -48.88%).

If this test starts failing because the entry has been removed, restore the
entry or delete the test with a written rationale in the commit message and a
linked report explaining why the kill is no longer warranted (per
`docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` Stage-5 reversal section).
"""

from __future__ import annotations

import importlib
import os

import pytest

import alpha_engine.strategy_blocklist as blocklist


@pytest.fixture(autouse=True)
def _restore_module(monkeypatch):
    """Ensure each test runs with the default rollback flag state."""
    monkeypatch.delenv("RAPID_FIRE_MACD_KILL_DISABLED", raising=False)
    importlib.reload(blocklist)
    yield
    monkeypatch.delenv("RAPID_FIRE_MACD_KILL_DISABLED", raising=False)
    importlib.reload(blocklist)


def test_rapid_fire_macd_pair_in_retired_set():
    """Composite pair must be present in _RETIRED_SYSTEM_STRATEGY_PAIRS."""
    assert ("rapid_fire", "macd_rsi_confluence") in (
        blocklist._RETIRED_SYSTEM_STRATEGY_PAIRS
    )


def test_rapid_fire_macd_pick_blocked_by_default():
    pick = {
        "source_system": "rapid_fire",
        "strategy": "macd_rsi_confluence",
        "symbol": "BTCUSDT",
        "direction": "LONG",
    }
    assert blocklist.is_blocked_pick(pick) is True
    assert blocklist.pick_block_reason(pick) == "retired-composite"


def test_rapid_fire_macd_kill_can_be_disabled_via_env(monkeypatch):
    """Rollback path: RAPID_FIRE_MACD_KILL_DISABLED=1 bypasses the composite."""
    monkeypatch.setenv("RAPID_FIRE_MACD_KILL_DISABLED", "1")
    importlib.reload(blocklist)
    pick = {
        "source_system": "rapid_fire",
        "strategy": "macd_rsi_confluence",
        "symbol": "BTCUSDT",
        "direction": "LONG",
    }
    assert blocklist.is_blocked_pick(pick) is False
    assert blocklist.pick_block_reason(pick) == ""


def test_rapid_fire_macd_kill_falsy_env_keeps_kill_active(monkeypatch):
    """Falsy / unrecognized rollback values must NOT bypass the kill."""
    for v in ("0", "false", "no", "off", "", "garbage"):
        monkeypatch.setenv("RAPID_FIRE_MACD_KILL_DISABLED", v)
        importlib.reload(blocklist)
        pick = {
            "source_system": "rapid_fire",
            "strategy": "macd_rsi_confluence",
        }
        assert blocklist.is_blocked_pick(pick) is True, (
            f"Expected kill to remain active for env value {v!r}"
        )


def test_other_rapid_fire_strategies_not_affected():
    """Surgical kill must NOT block other rapid_fire strategies."""
    pick = {
        "source_system": "rapid_fire",
        "strategy": "macd_crossover",  # different strategy, same system
        "symbol": "LINKUSDT",
        "direction": "SHORT",
    }
    assert blocklist.is_blocked_pick(pick) is False


def test_macd_rsi_confluence_from_other_systems_not_affected():
    """Composite kill is system-specific, not strategy-wide."""
    pick = {
        "source_system": "alpha_engine",
        "strategy": "macd_rsi_confluence",
    }
    # Not in _RETIRED_STRATEGIES (strategy-wide kill) and not in the
    # composite set under this system, so it must pass.
    assert blocklist.is_blocked_pick(pick) is False
