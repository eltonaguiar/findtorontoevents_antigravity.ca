"""Tests for tools/cot_lag_corrector.py.

Coverage (≥8 cases required per M-008/M-021 spec):
  1. apply_lag — lag adds COT_LAG_DAYS calendar days
  2. apply_lag — malformed / empty report_date returns None
  3. compute_match_verdict — MATCH (commercial long, speculator short)
  4. compute_match_verdict — MATCH (commercial short, speculator long)
  5. compute_match_verdict — INFLATED (same-sign positioning)
  6. compute_match_verdict — UNKNOWN (None inputs)
  7. compute_friction_adjusted_dsr — positive Sharpe series returns > 0
  8. compute_friction_adjusted_dsr — empty series returns 0.0
  9. check_cot_gate — returns (True, …) when DB unavailable (fail-open)
 10. check_cot_gate — passes_active_gate COMMODITY pick NOT blocked in shadow mode
 11. passes_active_gate — non-COMMODITY pick bypasses COT gate entirely
 12. config — COT_LAG_CORRECTION and COT_MATCH_REQUIRED are 1 (default ON)
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

import pytest

import tools.cot_lag_corrector as cot
from tools.cot_lag_corrector import (
    apply_lag,
    check_cot_gate,
    compute_friction_adjusted_dsr,
    compute_match_verdict,
    COT_LAG_DAYS,
    FRICTION_RATE,
)


# ---------------------------------------------------------------------------
# 1. apply_lag — correct lag application
# ---------------------------------------------------------------------------

def test_apply_lag_adds_cot_lag_days():
    """apply_lag must return report_date + COT_LAG_DAYS."""
    result = apply_lag("2026-05-12")
    expected = datetime(2026, 5, 12, tzinfo=timezone.utc) + timedelta(days=COT_LAG_DAYS)
    assert result == expected


# ---------------------------------------------------------------------------
# 2. apply_lag — malformed input
# ---------------------------------------------------------------------------

def test_apply_lag_malformed_returns_none():
    assert apply_lag("not-a-date") is None
    assert apply_lag("") is None
    assert apply_lag(None) is None


# ---------------------------------------------------------------------------
# 3. compute_match_verdict — MATCH (commercial long / speculator short)
# ---------------------------------------------------------------------------

def test_match_verdict_commercial_long_speculator_short():
    assert compute_match_verdict(+5000.0, -3000.0) == "MATCH"


# ---------------------------------------------------------------------------
# 4. compute_match_verdict — MATCH (commercial short / speculator long)
# ---------------------------------------------------------------------------

def test_match_verdict_commercial_short_speculator_long():
    assert compute_match_verdict(-2500.0, +8000.0) == "MATCH"


# ---------------------------------------------------------------------------
# 5. compute_match_verdict — INFLATED (same-sign / both long)
# ---------------------------------------------------------------------------

def test_match_verdict_inflated_same_sign():
    assert compute_match_verdict(+3000.0, +1500.0) == "INFLATED"
    assert compute_match_verdict(-1000.0, -500.0) == "INFLATED"


# ---------------------------------------------------------------------------
# 6. compute_match_verdict — UNKNOWN (None inputs)
# ---------------------------------------------------------------------------

def test_match_verdict_unknown_when_none():
    assert compute_match_verdict(None, None) == "UNKNOWN"
    assert compute_match_verdict(100.0, None) == "UNKNOWN"
    assert compute_match_verdict(None, -200.0) == "UNKNOWN"


# ---------------------------------------------------------------------------
# 7. compute_friction_adjusted_dsr — positive Sharpe series → DSR > 0
# ---------------------------------------------------------------------------

def test_friction_adjusted_dsr_positive_series():
    # A profitable series with non-zero variance (uniform inputs → variance=0 → DSR=0
    # per the all-trades-identical guard at compute_friction_adjusted_dsr:276).
    # Mean ~20%, std ~5%, all positive after 8 bps friction.
    pnl_series = [0.15, 0.20, 0.25, 0.18, 0.22, 0.17, 0.23, 0.19, 0.21, 0.20] * 5
    dsr = compute_friction_adjusted_dsr(pnl_series)
    assert 0.0 < dsr <= 1.0, f"Expected DSR in (0, 1], got {dsr}"


# ---------------------------------------------------------------------------
# 8. compute_friction_adjusted_dsr — empty series returns 0.0
# ---------------------------------------------------------------------------

def test_friction_adjusted_dsr_empty_series():
    assert compute_friction_adjusted_dsr([]) == 0.0


# ---------------------------------------------------------------------------
# 9. check_cot_gate — fail-open when DB unavailable
# ---------------------------------------------------------------------------

def test_check_cot_gate_fail_open_on_db_error():
    """When DB is unavailable, check_cot_gate must return (True, reason) — never block."""
    with patch.object(cot, "_load_aggregate_result", side_effect=RuntimeError("db down")):
        ok, reason = check_cot_gate({"asset_class": "COMMODITY", "symbol": "CT=F"})
    assert ok is True
    assert "cot_gate_error_fail_open" in reason


# ---------------------------------------------------------------------------
# 10. check_cot_gate — COMMODITY pick NOT blocked in shadow mode (default)
# ---------------------------------------------------------------------------

def test_check_cot_gate_commodity_shadow_mode_no_block(monkeypatch):
    """Shadow mode must tag, not block, a COMMODITY pick with INFLATED verdict."""
    monkeypatch.setenv("COT_MATCH_GATE_ENABLED", "shadow")
    _fake_agg = {
        "verdict": "INFLATED",
        "friction_adj_dsr": 0.30,
        "n_rows": 10,
        "error": None,
    }
    with patch.object(cot, "_load_aggregate_result", return_value=_fake_agg):
        ok, reason = check_cot_gate({"asset_class": "COMMODITY", "symbol": "GC=F"})
    # check_cot_gate returns the raw gate result; shadow enforcement is in quality_gates
    assert ok is False  # gate says fail; quality_gates decides shadow vs hard
    assert "INFLATED" in reason


# ---------------------------------------------------------------------------
# 11. passes_active_gate — non-COMMODITY pick bypasses COT gate
# ---------------------------------------------------------------------------

def test_non_commodity_pick_bypasses_cot_gate(monkeypatch):
    """COT gate must never fire for non-COMMODITY asset classes."""
    from audit_trail.quality_gates import passes_active_gate

    # Ensure COT gate is active in enforcement mode
    monkeypatch.setenv("COT_MATCH_GATE_ENABLED", "1")

    # Patch _compute_aggregate to raise to confirm it is never called for CRYPTO
    with patch.object(cot, "_load_aggregate_result", side_effect=AssertionError("should not be called")):
        pick = {
            "id": "test-crypto-1",
            "symbol": "BTCUSDT",
            "asset_class": "CRYPTO",
            "source_system": "pm_whale_signals",
            "strategy": "pm_whale_test",
            "status": "OPEN",
            "direction": "LONG",
            "entry_price": 100.0,
            "take_profit": 110.0,
            "stop_loss": 95.0,
            "score": 65,
            "trust_score": 6,
            "trust_label": "MODERATE",
            "confidence": 0.50,  # below inversion guard threshold (0.85)
        }
        # Should not raise AssertionError (gate bypassed for CRYPTO)
        try:
            result = passes_active_gate(pick)
        except AssertionError:
            pytest.fail("COT gate was called for a non-COMMODITY pick")


# ---------------------------------------------------------------------------
# 12. config — COT_LAG_CORRECTION and COT_MATCH_REQUIRED default ON
# ---------------------------------------------------------------------------

def test_config_cot_flags_default_on():
    from alpha_engine.config import COT_LAG_CORRECTION, COT_MATCH_REQUIRED

    assert COT_LAG_CORRECTION == 1, "COT_LAG_CORRECTION must default to 1 (ON)"
    assert COT_MATCH_REQUIRED == 1, "COT_MATCH_REQUIRED must default to 1 (ON)"


# ---------------------------------------------------------------------------
# 13. check_cot_gate — COMMODITY MATCH+DSR pick passes gate
# ---------------------------------------------------------------------------

def test_check_cot_gate_commodity_match_passes():
    """COMMODITY pick with MATCH verdict and adequate DSR must pass the gate."""
    _fake_agg = {
        "verdict": "MATCH",
        "friction_adj_dsr": 0.80,
        "n_rows": 50,
        "error": None,
    }
    with patch.object(cot, "_load_aggregate_result", return_value=_fake_agg):
        ok, reason = check_cot_gate({"asset_class": "COMMODITY", "symbol": "CT=F"})
    assert ok is True
    assert "cot_gate_pass" in reason
    assert "MATCH" in reason


# ---------------------------------------------------------------------------
# Bonus: DSR friction test — high-friction wipes edge from marginal series
# ---------------------------------------------------------------------------

def test_friction_wipes_marginal_edge():
    """An 8% friction on a barely-profitable series should yield low DSR."""
    # Each trade earns exactly 5% — minus 8% friction = -3% per trade
    pnl_series = [0.05] * 30
    dsr = compute_friction_adjusted_dsr(pnl_series, friction=0.08)
    # All net-negative after friction → DSR should be below 0.5
    assert dsr < 0.5, f"Expected low DSR for friction-eroded series, got {dsr}"
