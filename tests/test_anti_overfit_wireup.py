"""Tests for the opt-in anti-overfit validator wire-in inside
``audit_trail.quality_gates.passes_smart_gate``.

Verifies:
  * default-OFF (no flag) does NOT change ``passes_smart_gate`` behavior even
    when a clearly-overfit return history is attached;
  * flag-ON path engages and rejects when DSR < 0.95 OR PBO > 0.50;
  * missing/short history => no opinion (no spurious reject under flag-ON);
  * ``alpha_engine.anti_overfit_validator.evaluate_strategy`` returns the
    expected keys and graceful NaN on degenerate input.
"""
from __future__ import annotations

import os
from typing import Any, Dict

import numpy as np
import pytest

from alpha_engine.anti_overfit_validator import evaluate_strategy
from audit_trail import quality_gates
from audit_trail.quality_gates import _anti_overfit_reject


def _baseline_pick(**overrides: Any) -> Dict[str, Any]:
    """Pick dict shaped well enough to reach the new check inside
    ``passes_smart_gate``. We do NOT need it to *pass* the rest of the gate;
    we only assert that the new reject hook fires or not."""
    p: Dict[str, Any] = {
        "symbol": "BTCUSDT",
        "asset_class": "CRYPTO",
        "direction": "LONG",
        "score": 60,
        "confidence": 70,
        "trust_label": "PROVEN",
        "forward_validated": True,
        "strategy": "wireup_test",
    }
    p.update(overrides)
    return p


# ---------------------------------------------------------------------------
# evaluate_strategy convenience API
# ---------------------------------------------------------------------------
def test_evaluate_strategy_returns_expected_keys():
    rng = np.random.default_rng(11)
    hist = rng.normal(0.001, 0.01, size=200).tolist()
    out = evaluate_strategy(hist, n_trials=5)
    assert set(["dsr", "pbo", "sharpe", "n"]).issubset(out.keys())
    assert out["n"] == 200
    # sharpe must be finite for non-degenerate history
    assert out["sharpe"] == out["sharpe"]  # not NaN


def test_evaluate_strategy_short_history_returns_nan():
    out = evaluate_strategy([0.01, -0.02], n_trials=1)
    assert out["n"] == 2
    assert out["dsr"] != out["dsr"]  # NaN
    assert out["pbo"] != out["pbo"]  # NaN


# ---------------------------------------------------------------------------
# Wire-in: default-OFF
# ---------------------------------------------------------------------------
def test_default_off_no_reject_even_with_overfit_history(monkeypatch):
    """Flag absent => _anti_overfit_reject must return False regardless."""
    monkeypatch.delenv("ANTI_OVERFIT_VALIDATOR_ENABLED", raising=False)
    # Pathological constant-positive history (would normally look overfit)
    pick = _baseline_pick(returns_history=[0.005] * 100)
    assert _anti_overfit_reject(pick) is False


def test_default_off_explicit_zero_no_reject(monkeypatch):
    monkeypatch.setenv("ANTI_OVERFIT_VALIDATOR_ENABLED", "0")
    pick = _baseline_pick(returns_history=[0.005] * 100)
    assert _anti_overfit_reject(pick) is False


# ---------------------------------------------------------------------------
# Wire-in: flag-ON
# ---------------------------------------------------------------------------
def test_flag_on_short_history_no_opinion(monkeypatch):
    monkeypatch.setenv("ANTI_OVERFIT_VALIDATOR_ENABLED", "1")
    # < 20 obs => "no evidence", do not reject
    pick = _baseline_pick(returns_history=[0.01, -0.01, 0.02])
    assert _anti_overfit_reject(pick) is False


def test_flag_on_missing_history_no_opinion(monkeypatch):
    monkeypatch.setenv("ANTI_OVERFIT_VALIDATOR_ENABLED", "1")
    pick = _baseline_pick()  # no returns_history key
    assert _anti_overfit_reject(pick) is False


def test_flag_on_rejects_obviously_overfit_history(monkeypatch):
    """Flag-ON + a return series with weak/no real edge should trip at least
    one of (DSR < 0.95, PBO > 0.50). We use pure white noise: DSR collapses."""
    monkeypatch.setenv("ANTI_OVERFIT_VALIDATOR_ENABLED", "1")
    if not quality_gates._ANTI_OVERFIT_AVAILABLE:
        pytest.skip("anti_overfit_validator not importable in this env")
    rng = np.random.default_rng(3)
    hist = rng.normal(0.0, 0.01, size=120).tolist()
    pick = _baseline_pick(returns_history=hist)
    # Zero-mean noise => Sharpe ~ 0 => DSR << 0.95 => reject expected.
    assert _anti_overfit_reject(pick) is True
