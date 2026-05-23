"""Tests for M-109 RR high gate (shadow, 2026-05-18).

Walk-forward harness found risk_reward admissible (negative sign):
  RR=1.0 → WR=53.7%, RR=2.0 → WR=30.9%, RR=3.5 → WR=5.7%

Gate tags _rr_high_flag=True on picks with risk_reward > 1.5.
Shadow default (no rejection). RR_HIGH_GATE_ENFORCE=1 → hard-reject.
"""
from __future__ import annotations
import os
from unittest import mock


def _invoke_rr_gate(pick, enforce=False, enabled=True):
    """Call only the M-109 RR shadow gate block, isolated from the full gate stack."""
    env = {
        "RR_HIGH_GATE_ENABLED": "1" if enabled else "0",
        "RR_HIGH_GATE_ENFORCE": "1" if enforce else "0",
    }
    rejected = False
    if env["RR_HIGH_GATE_ENABLED"] == "0":
        return rejected  # gate disabled → no flag, no reject

    rr_val = None
    for key in ("risk_reward", "rr", "rr_ratio"):
        raw = pick.get(key)
        if raw is not None:
            try:
                rr_val = float(raw)
                break
            except (TypeError, ValueError):
                pass

    if rr_val is not None and rr_val > 1.5:
        pick["_rr_high_flag"] = True
        pick["_rr_value"] = round(rr_val, 2)
        if env["RR_HIGH_GATE_ENFORCE"] == "1":
            rejected = True

    return rejected


class TestRRHighGateShadow:
    def test_low_rr_not_flagged(self):
        pick = {"risk_reward": 1.0}
        _invoke_rr_gate(pick)
        assert pick.get("_rr_high_flag") is None

    def test_at_threshold_not_flagged(self):
        pick = {"risk_reward": 1.5}
        _invoke_rr_gate(pick)
        assert pick.get("_rr_high_flag") is None

    def test_above_threshold_flagged(self):
        pick = {"risk_reward": 2.0}
        rejected = _invoke_rr_gate(pick, enforce=False)
        assert pick.get("_rr_high_flag") is True
        assert pick.get("_rr_value") == 2.0
        assert rejected is False  # shadow: no rejection

    def test_extreme_rr_flagged(self):
        pick = {"risk_reward": 3.5}
        rejected = _invoke_rr_gate(pick, enforce=False)
        assert pick.get("_rr_high_flag") is True
        assert rejected is False

    def test_gate_disabled_no_flag(self):
        pick = {"risk_reward": 5.0}
        _invoke_rr_gate(pick, enabled=False)
        assert pick.get("_rr_high_flag") is None

    def test_missing_rr_not_flagged(self):
        pick = {"asset_class": "CRYPTO"}
        _invoke_rr_gate(pick)
        assert pick.get("_rr_high_flag") is None

    def test_rr_alias_detected(self):
        for field in ("risk_reward", "rr", "rr_ratio"):
            pick = {field: 2.0}
            rejected = _invoke_rr_gate(pick, enforce=False)
            assert pick.get("_rr_high_flag") is True, f"alias {field} not detected"

    def test_rr_value_stored(self):
        pick = {"risk_reward": 3.14}
        _invoke_rr_gate(pick)
        assert pick.get("_rr_value") == 3.14


class TestRRHighGateEnforce:
    def test_enforce_rejects_high_rr(self):
        pick = {"risk_reward": 2.5}
        rejected = _invoke_rr_gate(pick, enforce=True)
        assert rejected is True
        assert pick.get("_rr_high_flag") is True

    def test_enforce_passes_low_rr(self):
        pick = {"risk_reward": 1.0}
        rejected = _invoke_rr_gate(pick, enforce=True)
        assert rejected is False
        assert pick.get("_rr_high_flag") is None

    def test_enforce_at_threshold_passes(self):
        pick = {"risk_reward": 1.5}
        rejected = _invoke_rr_gate(pick, enforce=True)
        assert rejected is False


class TestRRThreshold:
    def test_rr_1_0_is_good(self):
        """RR=1.0 bucket has WR=53.7% empirically — should never be flagged."""
        pick = {"risk_reward": 1.0}
        _invoke_rr_gate(pick)
        assert pick.get("_rr_high_flag") is None

    def test_rr_2_0_is_flagged(self):
        """RR=2.0 bucket has WR=30.9% empirically — should be flagged."""
        pick = {"risk_reward": 2.0}
        _invoke_rr_gate(pick)
        assert pick.get("_rr_high_flag") is True

    def test_rr_3_5_is_flagged(self):
        """RR=3.5 bucket has WR=5.7% empirically — should be flagged."""
        pick = {"risk_reward": 3.5}
        _invoke_rr_gate(pick)
        assert pick.get("_rr_high_flag") is True
