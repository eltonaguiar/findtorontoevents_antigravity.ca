"""Tests for M-015: Decay-alert REDUCE soft-demote framework.

Verifies:
1. REDUCE alert with > 50pp WR drop → -25 penalty
2. REDUCE alert with > 30pp WR drop → -20 penalty
3. REDUCE alert with > 15pp WR drop → -12 penalty
4. REDUCE alert with <= 15pp WR drop → -8 penalty
5. MONITOR alert (not REDUCE) → 0 penalty
6. Kill-switch: DECAY_SOFT_DEMOTE_ENABLED=0 → 0 penalty
7. Fail-open on missing dashboard_data.json
"""
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from audit_trail.quality_gates import _get_decay_soft_demote_penalty, _DECAY_SOFT_DEMOTE_CACHE


def _make_dashboard_with_alerts(alerts, tmp_path):
    """Write dashboard_data.json with given performance_alerts list."""
    payload = {"performance_alerts": alerts}
    p = tmp_path / "dashboard_data.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    return str(p)


def _reduce_alert(strategy, rolling_wr, baseline_wr):
    return {
        "action": "REDUCE",
        "severity": "HIGH",
        "type": "STRATEGY_DEGRADATION",
        "details": {"strategy": strategy, "rolling_wr": rolling_wr, "baseline_wr": baseline_wr, "n_recent": 20},
    }


def test_severe_drop_penalty(tmp_path):
    """WR drop > 50pp must yield -25 penalty."""
    path = _make_dashboard_with_alerts([_reduce_alert("bad_strat", 30.0, 90.0)], tmp_path)
    _DECAY_SOFT_DEMOTE_CACHE["mtime"] = 0.0
    with patch("audit_trail.quality_gates._DASHBOARD_DATA_PATH_QG", path):
        with patch.dict(os.environ, {"DECAY_SOFT_DEMOTE_ENABLED": "1"}):
            penalty = _get_decay_soft_demote_penalty("bad_strat")
    assert penalty == -25


def test_high_drop_penalty(tmp_path):
    """WR drop in (30pp, 50pp] must yield -20 penalty."""
    path = _make_dashboard_with_alerts([_reduce_alert("strat_b", 50.0, 85.0)], tmp_path)
    _DECAY_SOFT_DEMOTE_CACHE["mtime"] = 0.0
    with patch("audit_trail.quality_gates._DASHBOARD_DATA_PATH_QG", path):
        with patch.dict(os.environ, {"DECAY_SOFT_DEMOTE_ENABLED": "1"}):
            penalty = _get_decay_soft_demote_penalty("strat_b")
    assert penalty == -20


def test_moderate_drop_penalty(tmp_path):
    """WR drop in (15pp, 30pp] must yield -12 penalty."""
    path = _make_dashboard_with_alerts([_reduce_alert("strat_c", 45.0, 65.0)], tmp_path)
    _DECAY_SOFT_DEMOTE_CACHE["mtime"] = 0.0
    with patch("audit_trail.quality_gates._DASHBOARD_DATA_PATH_QG", path):
        with patch.dict(os.environ, {"DECAY_SOFT_DEMOTE_ENABLED": "1"}):
            penalty = _get_decay_soft_demote_penalty("strat_c")
    assert penalty == -12


def test_mild_drop_penalty(tmp_path):
    """WR drop in (5pp, 15pp] must yield -8 penalty."""
    path = _make_dashboard_with_alerts([_reduce_alert("strat_d", 30.0, 40.0)], tmp_path)
    _DECAY_SOFT_DEMOTE_CACHE["mtime"] = 0.0
    with patch("audit_trail.quality_gates._DASHBOARD_DATA_PATH_QG", path):
        with patch.dict(os.environ, {"DECAY_SOFT_DEMOTE_ENABLED": "1"}):
            penalty = _get_decay_soft_demote_penalty("strat_d")
    assert penalty == -8


def test_monitor_alert_no_penalty(tmp_path):
    """MONITOR alert (not REDUCE) must not apply any penalty."""
    monitor = {"action": "MONITOR", "details": {"strategy": "strat_e", "rolling_wr": 40.0, "baseline_wr": 80.0}}
    path = _make_dashboard_with_alerts([monitor], tmp_path)
    _DECAY_SOFT_DEMOTE_CACHE["mtime"] = 0.0
    with patch("audit_trail.quality_gates._DASHBOARD_DATA_PATH_QG", path):
        with patch.dict(os.environ, {"DECAY_SOFT_DEMOTE_ENABLED": "1"}):
            penalty = _get_decay_soft_demote_penalty("strat_e")
    assert penalty == 0


def test_kill_switch_disables(tmp_path):
    """DECAY_SOFT_DEMOTE_ENABLED=0 must disable all penalties."""
    path = _make_dashboard_with_alerts([_reduce_alert("bad_strat", 10.0, 90.0)], tmp_path)
    _DECAY_SOFT_DEMOTE_CACHE["mtime"] = 0.0
    with patch("audit_trail.quality_gates._DASHBOARD_DATA_PATH_QG", path):
        with patch.dict(os.environ, {"DECAY_SOFT_DEMOTE_ENABLED": "0"}):
            penalty = _get_decay_soft_demote_penalty("bad_strat")
    assert penalty == 0


def test_fail_open_on_missing_file():
    """Returns 0 (no penalty) when dashboard_data.json is missing."""
    _DECAY_SOFT_DEMOTE_CACHE["mtime"] = 0.0
    with patch("audit_trail.quality_gates._DASHBOARD_DATA_PATH_QG", "/nonexistent/path.json"):
        with patch.dict(os.environ, {"DECAY_SOFT_DEMOTE_ENABLED": "1"}):
            penalty = _get_decay_soft_demote_penalty("any_strat")
    assert penalty == 0
