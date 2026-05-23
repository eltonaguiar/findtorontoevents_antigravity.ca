"""Tests for CRYPTO_SHORT_REGIME_GATE_ENABLED default flip to ON."""
from __future__ import annotations
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from audit_trail import quality_gates as qg


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    for k in ("CRYPTO_SHORT_REGIME_GATE_ENABLED", "CRYPTO_SHORT_DISABLED"):
        monkeypatch.delenv(k, raising=False)
    yield


def _short_pick():
    return {"asset_class": "CRYPTO", "symbol": "BTCUSDT", "direction": "SHORT"}


def _long_pick():
    return {"asset_class": "CRYPTO", "symbol": "BTCUSDT", "direction": "LONG"}


def test_default_on_blocks_short_in_bull_regime(monkeypatch):
    monkeypatch.setattr(qg, "_is_crypto_bull_regime", lambda: True)
    assert qg._crypto_short_gate_block_reason(_short_pick()) == "crypto_short_blocked_in_bull_regime"


def test_default_on_passes_short_in_non_bull_regime(monkeypatch):
    monkeypatch.setattr(qg, "_is_crypto_bull_regime", lambda: False)
    assert qg._crypto_short_gate_block_reason(_short_pick()) is None


def test_explicit_off_override_restores_pass_through(monkeypatch):
    monkeypatch.setenv("CRYPTO_SHORT_REGIME_GATE_ENABLED", "0")
    monkeypatch.setattr(qg, "_is_crypto_bull_regime", lambda: True)
    assert qg._crypto_short_gate_block_reason(_short_pick()) is None


def test_non_crypto_short_never_blocked(monkeypatch):
    monkeypatch.setattr(qg, "_is_crypto_bull_regime", lambda: True)
    pick = {"asset_class": "FOREX", "symbol": "EURUSD", "direction": "SHORT"}
    assert qg._crypto_short_gate_block_reason(pick) is None


def test_crypto_long_never_blocked(monkeypatch):
    monkeypatch.setattr(qg, "_is_crypto_bull_regime", lambda: True)
    assert qg._crypto_short_gate_block_reason(_long_pick()) is None


def test_kill_switch_wins_over_regime_gate(monkeypatch):
    monkeypatch.setenv("CRYPTO_SHORT_DISABLED", "1")
    monkeypatch.setattr(qg, "_is_crypto_bull_regime", lambda: False)
    assert qg._crypto_short_gate_block_reason(_short_pick()) == "crypto_short_killed_globally"


def test_env_one_explicit_still_works(monkeypatch):
    monkeypatch.setenv("CRYPTO_SHORT_REGIME_GATE_ENABLED", "1")
    monkeypatch.setattr(qg, "_is_crypto_bull_regime", lambda: True)
    assert qg._crypto_short_gate_block_reason(_short_pick()) == "crypto_short_blocked_in_bull_regime"


def test_current_regime_state_is_no_op(monkeypatch):
    monkeypatch.setattr(qg, "_is_crypto_bull_regime", lambda: False)
    assert qg._crypto_short_gate_block_reason(_short_pick()) is None
