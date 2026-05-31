"""Incident #1: ml_enhanced_* strategies must pass walk-forward validation
(wf_verdict in {ELITE,STRONG,VIABLE,PASS}) AND have n>=100 forward trades
before they may claim the 'proven winner' score boost. Otherwise their likely
look-ahead-leakage edge (PF 99-1094 / DSR=0.9995) is credited as real.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from alpha_engine.smart_picks_engine import (
    _ml_enhanced_edge_validated,
    _ML_WF_MIN_N,
)


def _ensure_gate_on(monkeypatch):
    monkeypatch.setenv("ML_ENHANCED_WF_GATE_ENABLED", "1")


def test_validated_ml_enhanced_passes(monkeypatch):
    _ensure_gate_on(monkeypatch)
    pick = {"wf_verdict": "STRONG", "strat_fwd_trades": _ML_WF_MIN_N + 50}
    assert _ml_enhanced_edge_validated(pick, "ml_enhanced_FETUSDT_1d_B_lightgbm") is True


def test_ml_enhanced_below_n_blocked(monkeypatch):
    _ensure_gate_on(monkeypatch)
    pick = {"wf_verdict": "STRONG", "strat_fwd_trades": _ML_WF_MIN_N - 1}
    assert _ml_enhanced_edge_validated(pick, "ml_enhanced_x") is False


def test_ml_enhanced_missing_wf_blocked(monkeypatch):
    _ensure_gate_on(monkeypatch)
    pick = {"strat_fwd_trades": 500}  # plenty of n but never walk-forward validated
    assert _ml_enhanced_edge_validated(pick, "ml_enhanced_x") is False


def test_ml_enhanced_failing_wf_blocked(monkeypatch):
    _ensure_gate_on(monkeypatch)
    pick = {"wf_verdict": "FAILING", "strat_fwd_trades": 500}
    assert _ml_enhanced_edge_validated(pick, "ml_enhanced_x") is False


def test_non_ml_enhanced_unaffected(monkeypatch):
    _ensure_gate_on(monkeypatch)
    # A non-ml_enhanced proven strategy is never subject to this gate.
    assert _ml_enhanced_edge_validated({}, "copy_hl_NMTD_25M") is True


def test_gate_disabled_restores_legacy(monkeypatch):
    monkeypatch.setenv("ML_ENHANCED_WF_GATE_ENABLED", "0")
    pick = {"strat_fwd_trades": 0}  # would fail if gate were on
    assert _ml_enhanced_edge_validated(pick, "ml_enhanced_x") is True


def test_strat_fwd_n_alias_counts(monkeypatch):
    _ensure_gate_on(monkeypatch)
    pick = {"wf_verdict": "VIABLE", "strat_fwd_n": _ML_WF_MIN_N + 1}
    assert _ml_enhanced_edge_validated(pick, "ml_enhanced_x") is True
