"""Tests for VIX+YC combined regime gate.

Per reports/equity_vix_yc_combined_super_breakthrough_20260513.md.
Functions tested: get_cached_yc, is_yc_below_threshold, should_reject_combined.
"""
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from audit_trail import vix_regime_gate
from audit_trail.vix_regime_gate import (
    is_yc_below_threshold,
    reset_cache,
    reset_yc_cache,
    should_reject_combined,
    should_reject_equity_pick,
)


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch):
    monkeypatch.delenv("VIX_REGIME_GATE_ENABLED", raising=False)
    monkeypatch.delenv("YC_REGIME_GATE_ENABLED", raising=False)
    monkeypatch.delenv("VIX_REGIME_GATE_THRESHOLD", raising=False)
    monkeypatch.delenv("YC_REGIME_GATE_MIN_SPREAD", raising=False)
    reset_cache()
    reset_yc_cache()
    yield
    reset_cache()
    reset_yc_cache()


def test_combined_default_off_does_not_reject(monkeypatch):
    """YC_REGIME_GATE_ENABLED=0 => combined gate no-op (gate defaults to ON; must be explicit)."""
    monkeypatch.setenv("YC_REGIME_GATE_ENABLED", "0")
    reset_cache()
    reset_yc_cache()
    pick = {"asset_class": "EQUITY", "symbol": "AAPL"}
    with patch.object(vix_regime_gate, "_fetch_vix_now", return_value=99.0):
        with patch.object(vix_regime_gate, "_fetch_yc_now", return_value=-5.0):
            assert should_reject_combined(pick) is False


def test_combined_rejects_when_vix_high(monkeypatch):
    """VIX > threshold AND YC fine => REJECT (combined fires)."""
    monkeypatch.setenv("YC_REGIME_GATE_ENABLED", "1")
    pick = {"asset_class": "EQUITY", "symbol": "AAPL"}
    with patch.object(vix_regime_gate, "_fetch_vix_now", return_value=30.0):
        with patch.object(vix_regime_gate, "_fetch_yc_now", return_value=1.0):
            assert should_reject_combined(pick) is True


def test_combined_rejects_when_yc_inverted(monkeypatch):
    """YC < threshold AND VIX fine => REJECT."""
    monkeypatch.setenv("YC_REGIME_GATE_ENABLED", "1")
    pick = {"asset_class": "EQUITY", "symbol": "AAPL"}
    with patch.object(vix_regime_gate, "_fetch_vix_now", return_value=15.0):
        with patch.object(vix_regime_gate, "_fetch_yc_now", return_value=-0.5):
            assert should_reject_combined(pick) is True


def test_combined_passes_when_both_clean(monkeypatch):
    """VIX fine AND YC fine => PASS (no rejection)."""
    monkeypatch.setenv("YC_REGIME_GATE_ENABLED", "1")
    pick = {"asset_class": "EQUITY", "symbol": "AAPL"}
    with patch.object(vix_regime_gate, "_fetch_vix_now", return_value=15.0):
        with patch.object(vix_regime_gate, "_fetch_yc_now", return_value=1.5):
            assert should_reject_combined(pick) is False


def test_combined_etf_coverage(monkeypatch):
    """Combined gate covers ETF same as EQUITY."""
    monkeypatch.setenv("YC_REGIME_GATE_ENABLED", "1")
    pick = {"asset_class": "ETF", "symbol": "XLK"}
    with patch.object(vix_regime_gate, "_fetch_vix_now", return_value=30.0):
        with patch.object(vix_regime_gate, "_fetch_yc_now", return_value=1.0):
            assert should_reject_combined(pick) is True


def test_combined_does_not_affect_crypto(monkeypatch):
    """CRYPTO/FOREX/BOND unaffected by combined gate."""
    monkeypatch.setenv("YC_REGIME_GATE_ENABLED", "1")
    with patch.object(vix_regime_gate, "_fetch_vix_now", return_value=99.0):
        with patch.object(vix_regime_gate, "_fetch_yc_now", return_value=-9.0):
            for ac in ("CRYPTO", "FOREX", "BOND", "COMMODITY", "FUTURES"):
                pick = {"asset_class": ac, "symbol": "X"}
                assert should_reject_combined(pick) is False


def test_yc_threshold_configurable(monkeypatch):
    monkeypatch.setenv("YC_REGIME_GATE_ENABLED", "1")
    monkeypatch.setenv("YC_REGIME_GATE_MIN_SPREAD", "0.25")
    pick = {"asset_class": "EQUITY", "symbol": "AAPL"}
    with patch.object(vix_regime_gate, "_fetch_vix_now", return_value=15.0):
        # YC=0.10 < 0.25 threshold => reject
        with patch.object(vix_regime_gate, "_fetch_yc_now", return_value=0.10):
            assert should_reject_combined(pick) is True
        reset_yc_cache()
        # YC=0.50 > 0.25 threshold => pass
        with patch.object(vix_regime_gate, "_fetch_yc_now", return_value=0.50):
            assert should_reject_combined(pick) is False


def test_combined_fail_open_on_yc_fetch_error(monkeypatch):
    """If YC fetch fails, combined gate falls back to VIX-only behavior."""
    monkeypatch.setenv("YC_REGIME_GATE_ENABLED", "1")
    pick = {"asset_class": "EQUITY", "symbol": "AAPL"}
    with patch.object(vix_regime_gate, "_fetch_vix_now", return_value=15.0):
        with patch.object(vix_regime_gate, "_fetch_yc_now", return_value=None):
            # YC unknown -> is_yc_below_threshold returns False (fail-open)
            # VIX=15 fine -> no rejection
            assert should_reject_combined(pick) is False


def test_combined_yc_cache_independent_from_vix(monkeypatch):
    """YC and VIX caches must be independent."""
    monkeypatch.setenv("YC_REGIME_GATE_ENABLED", "1")
    yc_calls = {"n": 0}
    vix_calls = {"n": 0}

    def _fake_yc():
        yc_calls["n"] += 1
        return 0.5

    def _fake_vix():
        vix_calls["n"] += 1
        return 18.0

    with patch.object(vix_regime_gate, "_fetch_yc_now", side_effect=_fake_yc):
        with patch.object(vix_regime_gate, "_fetch_vix_now", side_effect=_fake_vix):
            pick = {"asset_class": "EQUITY", "symbol": "AAPL"}
            for _ in range(3):
                should_reject_combined(pick)
    assert yc_calls["n"] == 1, f"YC must be cached (got {yc_calls['n']})"
    assert vix_calls["n"] == 1, f"VIX must be cached (got {vix_calls['n']})"


def test_smart_gate_uses_combined_function():
    """passes_smart_gate must wire combined gate via should_reject_combined."""
    src = (ROOT / "audit_trail" / "quality_gates.py").read_text(encoding="utf-8")
    assert "should_reject_combined" in src
    assert "vix_yc_regime_combined" in src


def test_combined_precedes_vix_only_in_call_order():
    """In passes_smart_gate, combined check fires BEFORE single-VIX check."""
    src = (ROOT / "audit_trail" / "quality_gates.py").read_text(encoding="utf-8")
    idx_combined = src.find("should_reject_combined")
    idx_vix_only = src.find("should_reject_equity_pick as _vix_reject")
    # Both refs should exist; combined check appears at/after import but
    # combined call must fire first
    assert idx_combined > 0
    # Find the actual call sites (not just import)
    idx_combined_call = src.find("_combined_reject(pick)")
    idx_vix_call = src.find("_vix_reject(pick)")
    assert idx_combined_call > 0 and idx_vix_call > 0
    assert idx_combined_call < idx_vix_call, (
        "Combined gate must be evaluated before VIX-only fallback"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
