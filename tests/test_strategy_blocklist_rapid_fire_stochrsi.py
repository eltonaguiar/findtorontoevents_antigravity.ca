"""Pin the 2026-05-18 surgical kill of (rapid_fire, stochrsi_macd_combo).

C-006 second-pass autopsy (reports/C006_rapid_fire_backtest_2026_05_18.md):
  n=17 closed CRYPTO picks, WR=11.8%, PF=0.200, cumPnL=-0.24%.
  Below NOISE floor — insufficient n to rescue.

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
    monkeypatch.delenv("RAPID_FIRE_STOCHRSI_KILL_DISABLED", raising=False)
    importlib.reload(blocklist)
    yield
    monkeypatch.delenv("RAPID_FIRE_STOCHRSI_KILL_DISABLED", raising=False)
    importlib.reload(blocklist)


def test_rapid_fire_stochrsi_pair_in_retired_set():
    assert ("rapid_fire", "stochrsi_macd_combo") in blocklist._RETIRED_SYSTEM_STRATEGY_PAIRS


def test_rapid_fire_stochrsi_pick_blocked_by_default():
    pick = {"source_system": "rapid_fire", "strategy": "stochrsi_macd_combo", "symbol": "BTCUSDT"}
    assert blocklist.is_blocked_pick(pick) is True
    assert blocklist.pick_block_reason(pick) == "retired-composite"


def test_rapid_fire_stochrsi_kill_can_be_disabled_via_env(monkeypatch):
    monkeypatch.setenv("RAPID_FIRE_STOCHRSI_KILL_DISABLED", "1")
    importlib.reload(blocklist)
    pick = {"source_system": "rapid_fire", "strategy": "stochrsi_macd_combo"}
    assert blocklist.is_blocked_pick(pick) is False


def test_rapid_fire_stochrsi_falsy_env_keeps_kill_active(monkeypatch):
    for v in ("0", "false", "no", "off", "", "garbage"):
        monkeypatch.setenv("RAPID_FIRE_STOCHRSI_KILL_DISABLED", v)
        importlib.reload(blocklist)
        pick = {"source_system": "rapid_fire", "strategy": "stochrsi_macd_combo"}
        assert blocklist.is_blocked_pick(pick) is True, f"Expected kill active for env={v!r}"


def test_stochrsi_from_other_systems_not_affected():
    pick = {"source_system": "alpha_engine", "strategy": "stochrsi_macd_combo"}
    assert blocklist.is_blocked_pick(pick) is False


def test_macd_crossover_not_affected_by_stochrsi_kill():
    """macd_crossover is viable (WR=68.8%, PF=4.09) — must NOT be blocked."""
    pick = {"source_system": "rapid_fire", "strategy": "macd_crossover"}
    assert blocklist.is_blocked_pick(pick) is False


def test_vsb_kill_unaffected_by_stochrsi_rollback(monkeypatch):
    monkeypatch.setenv("RAPID_FIRE_STOCHRSI_KILL_DISABLED", "1")
    monkeypatch.delenv("RAPID_FIRE_VSB_KILL_DISABLED", raising=False)
    importlib.reload(blocklist)
    pick = {"source_system": "rapid_fire", "strategy": "volume_spike_breakout"}
    assert blocklist.is_blocked_pick(pick) is True
