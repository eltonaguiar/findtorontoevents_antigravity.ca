"""Tests for speculative EQUITY + VIX active gates (EAGLE 2026-05-27)."""
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from audit_trail.quality_gates import (
    passes_speculative_equity_gate,
    passes_vix_regime_active_gate,
)


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("EQUITY_SPECULATIVE_GATE_ENABLED", "1")
    monkeypatch.setenv("VIX_REGIME_ACTIVE_GATE_ENABLED", "1")
    monkeypatch.setenv("VIX_REGIME_GATE_ENABLED", "1")


def test_speculative_blocks_gme():
    pick = {"asset_class": "EQUITY", "symbol": "GME"}
    assert passes_speculative_equity_gate(pick) is False


def test_speculative_allows_aapl():
    pick = {"asset_class": "EQUITY", "symbol": "AAPL"}
    assert passes_speculative_equity_gate(pick) is True


def test_speculative_kill_switch(monkeypatch):
    monkeypatch.setenv("EQUITY_SPECULATIVE_GATE_ENABLED", "0")
    pick = {"asset_class": "EQUITY", "symbol": "GME"}
    assert passes_speculative_equity_gate(pick) is True


def test_vix_active_rejects_high_vix():
    pick = {"asset_class": "EQUITY", "symbol": "NVDA"}
    with patch("audit_trail.vix_regime_gate._fetch_vix_now", return_value=35.0):
        from audit_trail import vix_regime_gate
        vix_regime_gate.reset_cache()
        assert passes_vix_regime_active_gate(pick) is False
        vix_regime_gate.reset_cache()


def test_vix_active_passes_low_vix():
    pick = {"asset_class": "EQUITY", "symbol": "NVDA"}
    with patch("audit_trail.vix_regime_gate._fetch_vix_now", return_value=15.0):
        from audit_trail import vix_regime_gate
        vix_regime_gate.reset_cache()
        assert passes_vix_regime_active_gate(pick) is True
        vix_regime_gate.reset_cache()
