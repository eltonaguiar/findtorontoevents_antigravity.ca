"""Tests for VIX regime gate sidecar.

Per reports/equity_vix_regime_breakthrough_20260513.md.
"""
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from audit_trail import vix_regime_gate
from audit_trail.vix_regime_gate import (
    is_vix_above_threshold,
    reset_cache,
    should_reject_equity_pick,
)


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch):
    monkeypatch.delenv("VIX_REGIME_GATE_ENABLED", raising=False)
    monkeypatch.delenv("VIX_REGIME_GATE_THRESHOLD", raising=False)
    reset_cache()
    yield
    reset_cache()


def test_default_on_rejects_when_vix_high():
    pick = {"asset_class": "EQUITY", "symbol": "AAPL"}
    with patch.object(vix_regime_gate, "_fetch_vix_now", return_value=50.0):
        assert should_reject_equity_pick(pick) is True


def test_enabled_rejects_when_vix_above_threshold(monkeypatch):
    monkeypatch.setenv("VIX_REGIME_GATE_ENABLED", "1")
    pick = {"asset_class": "EQUITY", "symbol": "AAPL"}
    with patch.object(vix_regime_gate, "_fetch_vix_now", return_value=30.0):
        assert should_reject_equity_pick(pick) is True


def test_enabled_passes_when_vix_below_threshold(monkeypatch):
    monkeypatch.setenv("VIX_REGIME_GATE_ENABLED", "1")
    pick = {"asset_class": "EQUITY", "symbol": "AAPL"}
    with patch.object(vix_regime_gate, "_fetch_vix_now", return_value=15.0):
        assert should_reject_equity_pick(pick) is False


def test_threshold_configurable(monkeypatch):
    monkeypatch.setenv("VIX_REGIME_GATE_ENABLED", "1")
    monkeypatch.setenv("VIX_REGIME_GATE_THRESHOLD", "20.0")
    pick = {"asset_class": "EQUITY", "symbol": "AAPL"}
    with patch.object(vix_regime_gate, "_fetch_vix_now", return_value=21.0):
        assert should_reject_equity_pick(pick) is True
    reset_cache()
    with patch.object(vix_regime_gate, "_fetch_vix_now", return_value=19.0):
        assert should_reject_equity_pick(pick) is False


def test_only_affects_equity_and_etf(monkeypatch):
    """Extended 2026-05-13: VIX gate covers BOTH EQUITY and ETF per backtest.

    EQUITY/ETF: rejected when VIX high.
    CRYPTO/FOREX/BOND/COMMODITY/FUTURES: untouched.
    """
    monkeypatch.setenv("VIX_REGIME_GATE_ENABLED", "1")
    with patch.object(vix_regime_gate, "_fetch_vix_now", return_value=99.0):
        for ac in ("CRYPTO", "FOREX", "BOND", "COMMODITY", "FUTURES"):
            pick = {"asset_class": ac, "symbol": "X"}
            assert should_reject_equity_pick(pick) is False, f"VIX gate must NOT touch {ac}"
        # EQUITY and ETF SHOULD be rejected when VIX high
        for ac in ("EQUITY", "ETF"):
            pick = {"asset_class": ac, "symbol": "X"}
            assert should_reject_equity_pick(pick) is True, f"VIX gate MUST touch {ac}"


def test_fail_open_on_fetch_error(monkeypatch):
    """If VIX fetch fails, gate does NOT reject (fail-open)."""
    monkeypatch.setenv("VIX_REGIME_GATE_ENABLED", "1")
    pick = {"asset_class": "EQUITY", "symbol": "AAPL"}
    with patch.object(vix_regime_gate, "_fetch_vix_now", return_value=None):
        assert should_reject_equity_pick(pick) is False


def test_cache_hit_reduces_fetch_calls(monkeypatch):
    monkeypatch.setenv("VIX_REGIME_GATE_ENABLED", "1")
    call_count = {"n": 0}

    def _fake_fetch():
        call_count["n"] += 1
        return 30.0

    with patch.object(vix_regime_gate, "_fetch_vix_now", side_effect=_fake_fetch):
        pick = {"asset_class": "EQUITY", "symbol": "AAPL"}
        for _ in range(5):
            should_reject_equity_pick(pick)
    assert call_count["n"] == 1, f"VIX must be cached; got {call_count['n']} fetches"


def test_truthy_env_variants(monkeypatch):
    pick = {"asset_class": "EQUITY", "symbol": "AAPL"}
    for variant in ("1", "true", "yes", "on", "t", "y", "TRUE", "Yes"):
        monkeypatch.setenv("VIX_REGIME_GATE_ENABLED", variant)
        reset_cache()
        with patch.object(vix_regime_gate, "_fetch_vix_now", return_value=30.0):
            assert should_reject_equity_pick(pick) is True, f"variant {variant!r} must enable"


def test_smart_gate_integration_wired():
    """passes_smart_gate must reference vix_regime_gate module."""
    src = (ROOT / "audit_trail" / "quality_gates.py").read_text(encoding="utf-8")
    assert "vix_regime_gate" in src
    assert "vix_regime_high_vol" in src


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
