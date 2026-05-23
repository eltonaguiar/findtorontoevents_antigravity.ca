"""Pin the 2026-04-29 surgical kill of goldmine_stocks source on EQUITY.

Orchestrator + Copilot cross-check (reports/COPILOT_CROSS_CHECK_2026_04_29.md):
goldmine_stocks on EQUITY = n=13, WR 0.0%, sum pnl_pct -53.36%, all LONG,
across 6 distinct blue-chip defensives and all three consensus tiers
(5x/6x/7x). Largest single-source drag on EQUITY's 30d cohort.

If this test starts failing because the entries have been removed, restore
them or delete the test with a written rationale in the commit message and a
linked report explaining why the kill is no longer warranted (per
`docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` Stage-5 reversal section).
"""

from __future__ import annotations

import importlib

import pytest

import alpha_engine.strategy_blocklist as blocklist


@pytest.fixture(autouse=True)
def _restore_module(monkeypatch):
    """Ensure each test runs with the default rollback flag state."""
    monkeypatch.delenv("GOLDMINE_STOCKS_KILL_DISABLED", raising=False)
    importlib.reload(blocklist)
    yield
    monkeypatch.delenv("GOLDMINE_STOCKS_KILL_DISABLED", raising=False)
    importlib.reload(blocklist)


@pytest.mark.parametrize(
    "strategy",
    ["goldmine_5x_consensus", "goldmine_6x_consensus", "goldmine_7x_consensus"],
)
def test_goldmine_stocks_pair_in_retired_set(strategy):
    """All three goldmine_stocks composite pairs must be present."""
    assert ("goldmine_stocks", strategy) in (
        blocklist._RETIRED_SYSTEM_STRATEGY_PAIRS
    )


@pytest.mark.parametrize(
    "strategy",
    ["goldmine_5x_consensus", "goldmine_6x_consensus", "goldmine_7x_consensus"],
)
def test_goldmine_stocks_pick_blocked_by_default(strategy):
    """A pick from goldmine_stocks with a killed strategy must be blocked."""
    pick = {
        "source_system": "goldmine_stocks",
        "strategy": strategy,
        "symbol": "JNJ",
        "asset_class": "EQUITY",
        "direction": "LONG",
    }
    assert blocklist.is_blocked_pick(pick) is True
    assert blocklist.pick_block_reason(pick) == "retired-composite"


def test_goldmine_stocks_kill_can_be_disabled_via_env(monkeypatch):
    """Rollback path: GOLDMINE_STOCKS_KILL_DISABLED=1 bypasses all 3 pairs."""
    monkeypatch.setenv("GOLDMINE_STOCKS_KILL_DISABLED", "1")
    importlib.reload(blocklist)
    for strategy in (
        "goldmine_5x_consensus",
        "goldmine_6x_consensus",
        "goldmine_7x_consensus",
    ):
        pick = {
            "source_system": "goldmine_stocks",
            "strategy": strategy,
            "symbol": "JNJ",
            "asset_class": "EQUITY",
            "direction": "LONG",
        }
        assert blocklist.is_blocked_pick(pick) is False, (
            f"Rollback flag must un-block {strategy}"
        )
        assert blocklist.pick_block_reason(pick) == ""


def test_goldmine_stocks_kill_falsy_env_keeps_kill_active(monkeypatch):
    """Falsy / unrecognized rollback values must NOT bypass the kill."""
    for v in ("0", "false", "no", "off", "", "garbage"):
        monkeypatch.setenv("GOLDMINE_STOCKS_KILL_DISABLED", v)
        importlib.reload(blocklist)
        pick = {
            "source_system": "goldmine_stocks",
            "strategy": "goldmine_6x_consensus",
            "asset_class": "EQUITY",
        }
        assert blocklist.is_blocked_pick(pick) is True, (
            f"Expected kill to remain active for env value {v!r}"
        )


def test_other_sources_emitting_goldmine_strategies_not_affected():
    """Surgical kill is system-specific — other sources must remain unblocked."""
    pick = {
        "source_system": "alpha_engine",  # different system, same strategy name
        "strategy": "goldmine_6x_consensus",
        "symbol": "JNJ",
        "asset_class": "EQUITY",
        "direction": "LONG",
    }
    # Strategy name is not in _RETIRED_STRATEGIES (strategy-wide kill) and
    # not paired with this system, so it must pass.
    assert blocklist.is_blocked_pick(pick) is False


def test_other_goldmine_stocks_strategies_not_affected():
    """A hypothetical future goldmine_stocks strategy outside the killed
    triple must not be auto-blocked."""
    pick = {
        "source_system": "goldmine_stocks",
        "strategy": "goldmine_4x_consensus",  # not in killed set
        "symbol": "JNJ",
        "asset_class": "EQUITY",
        "direction": "LONG",
    }
    assert blocklist.is_blocked_pick(pick) is False


def test_rapid_fire_macd_kill_unaffected_by_goldmine_flag(monkeypatch):
    """The goldmine rollback flag must not affect the rapid_fire kill."""
    monkeypatch.setenv("GOLDMINE_STOCKS_KILL_DISABLED", "1")
    importlib.reload(blocklist)
    pick = {
        "source_system": "rapid_fire",
        "strategy": "macd_rsi_confluence",
        "symbol": "BTCUSDT",
        "direction": "LONG",
    }
    assert blocklist.is_blocked_pick(pick) is True
    assert blocklist.pick_block_reason(pick) == "retired-composite"
