"""Pin the 2026-05-18 surgical kill of (rapid_fire, volume_spike_breakout).

C-006 backtest verdict (reports/C006_rapid_fire_backtest_2026_05_18.md):
  n=78 closed CRYPTO picks, WR=0.0% (zero winners), PF=0.000, cumPnL=-30.9%.
  PBO=1.000 — every random permutation beats actual rapid_fire selection.
  Root cause: buying volume spikes in CRYPTO = adverse-selection trap (retail
  FOMO at pump peak, professional capital on the other side).

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
    monkeypatch.delenv("RAPID_FIRE_VSB_KILL_DISABLED", raising=False)
    importlib.reload(blocklist)
    yield
    monkeypatch.delenv("RAPID_FIRE_VSB_KILL_DISABLED", raising=False)
    importlib.reload(blocklist)


def test_rapid_fire_vsb_pair_in_retired_set():
    """Composite pair must be present in _RETIRED_SYSTEM_STRATEGY_PAIRS."""
    assert ("rapid_fire", "volume_spike_breakout") in (
        blocklist._RETIRED_SYSTEM_STRATEGY_PAIRS
    )


def test_rapid_fire_vsb_pick_blocked_by_default():
    pick = {
        "source_system": "rapid_fire",
        "strategy": "volume_spike_breakout",
        "symbol": "BTCUSDT",
        "direction": "LONG",
    }
    assert blocklist.is_blocked_pick(pick) is True
    assert blocklist.pick_block_reason(pick) == "retired-composite"


def test_rapid_fire_vsb_kill_can_be_disabled_via_env(monkeypatch):
    """Rollback path: RAPID_FIRE_VSB_KILL_DISABLED=1 bypasses the composite."""
    monkeypatch.setenv("RAPID_FIRE_VSB_KILL_DISABLED", "1")
    importlib.reload(blocklist)
    pick = {
        "source_system": "rapid_fire",
        "strategy": "volume_spike_breakout",
        "symbol": "BTCUSDT",
        "direction": "LONG",
    }
    assert blocklist.is_blocked_pick(pick) is False
    assert blocklist.pick_block_reason(pick) == ""


def test_rapid_fire_vsb_kill_falsy_env_keeps_kill_active(monkeypatch):
    """Falsy / unrecognized rollback values must NOT bypass the kill."""
    for v in ("0", "false", "no", "off", "", "garbage"):
        monkeypatch.setenv("RAPID_FIRE_VSB_KILL_DISABLED", v)
        importlib.reload(blocklist)
        pick = {
            "source_system": "rapid_fire",
            "strategy": "volume_spike_breakout",
        }
        assert blocklist.is_blocked_pick(pick) is True, (
            f"Expected kill to remain active for env value {v!r}"
        )


def test_volume_spike_breakout_from_other_systems_not_affected():
    """Composite kill is system-specific, not strategy-wide."""
    pick = {
        "source_system": "alpha_engine",
        "strategy": "volume_spike_breakout",
    }
    assert blocklist.is_blocked_pick(pick) is False


def test_other_rapid_fire_strategies_not_affected_by_vsb_kill():
    """Surgical kill must NOT block other rapid_fire strategies (e.g. macd_crossover)."""
    pick = {
        "source_system": "rapid_fire",
        "strategy": "macd_crossover",
        "symbol": "LINKUSDT",
        "direction": "SHORT",
    }
    assert blocklist.is_blocked_pick(pick) is False


def test_macd_rsi_confluence_kill_unaffected_by_vsb_rollback(monkeypatch):
    """Per-pair rollback flags must be independent — disabling VSB must NOT
    also re-enable the macd_rsi_confluence composite."""
    monkeypatch.setenv("RAPID_FIRE_VSB_KILL_DISABLED", "1")
    monkeypatch.delenv("RAPID_FIRE_MACD_KILL_DISABLED", raising=False)
    importlib.reload(blocklist)
    pick_macd = {
        "source_system": "rapid_fire",
        "strategy": "macd_rsi_confluence",
    }
    assert blocklist.is_blocked_pick(pick_macd) is True
    assert blocklist.pick_block_reason(pick_macd) == "retired-composite"


def test_rsi_bounce_kill_unaffected_by_vsb_rollback(monkeypatch):
    """Disabling VSB must NOT also re-enable the rsi_bounce composite."""
    monkeypatch.setenv("RAPID_FIRE_VSB_KILL_DISABLED", "1")
    monkeypatch.delenv("RAPID_FIRE_RSI_BOUNCE_KILL_DISABLED", raising=False)
    importlib.reload(blocklist)
    pick_rsi = {
        "source_system": "rapid_fire",
        "strategy": "rsi_bounce",
    }
    assert blocklist.is_blocked_pick(pick_rsi) is True
    assert blocklist.pick_block_reason(pick_rsi) == "retired-composite"
