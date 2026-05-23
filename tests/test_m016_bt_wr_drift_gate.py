"""Tests for M-016: Live-vs-backtest WR drift circuit breaker.

Verifies:
1. Gate is OFF by default (BT_WR_DRIFT_GATE_ENABLED not set)
2. Known-drifted strategy is blocked when gate is ON
3. Clean strategy (no WR decay) passes through
4. Fail-open on missing dashboard_data.json
5. Kill-switch: BT_WR_DRIFT_GATE_ENABLED=0 → no block even if strategy is drifted
6. Custom Z threshold via BT_WR_DRIFT_Z_THRESHOLD env var
"""
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from audit_trail.quality_gates import (
    _passes_bt_wr_drift_gate,
    _load_bt_wr_drift_state,
    _BT_WR_DRIFT_CACHE,
)


def _pick(strategy="my_strategy", asset_class="CRYPTO"):
    return {"strategy": strategy, "asset_class": asset_class, "symbol": "BTCUSDT"}


def _make_dashboard(rows, tmp_path):
    """Write a minimal dashboard_data.json with given fwd_vs_bt rows."""
    payload = {"fwd_vs_bt_divergence": {"rows": rows}}
    p = tmp_path / "dashboard_data.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    return str(p)


def test_gate_off_by_default(tmp_path):
    """Gate must be OFF by default — no block even for drifted strategies."""
    env = {k: v for k, v in os.environ.items() if k != "BT_WR_DRIFT_GATE_ENABLED"}
    with patch.dict(os.environ, env, clear=True):
        result = _passes_bt_wr_drift_gate(_pick("drifted_strat"))
    assert result is None


def test_gate_blocks_drifted_strategy(tmp_path):
    """When gate ON and strategy has wr_z < threshold, must return block reason."""
    dashboard_path = _make_dashboard(
        [{"strategy": "bad_strat", "wr_z": -4.5, "decay": -25.0, "flags": ["WR_2SIGMA"]}],
        tmp_path,
    )
    # Reset cache to force reload
    _BT_WR_DRIFT_CACHE["mtime"] = 0.0
    with patch("audit_trail.quality_gates._DASHBOARD_DATA_PATH_QG", dashboard_path):
        with patch.dict(os.environ, {"BT_WR_DRIFT_GATE_ENABLED": "1"}):
            reason = _passes_bt_wr_drift_gate(_pick("bad_strat"))
    assert reason is not None
    assert "bad_strat" in reason
    assert "m016" in reason.lower()


def test_gate_passes_clean_strategy(tmp_path):
    """Strategy with wr_z above threshold (not drifted) must pass through."""
    dashboard_path = _make_dashboard(
        [{"strategy": "bad_strat", "wr_z": -4.5, "decay": -25.0}],
        tmp_path,
    )
    _BT_WR_DRIFT_CACHE["mtime"] = 0.0
    with patch("audit_trail.quality_gates._DASHBOARD_DATA_PATH_QG", dashboard_path):
        with patch.dict(os.environ, {"BT_WR_DRIFT_GATE_ENABLED": "1"}):
            reason = _passes_bt_wr_drift_gate(_pick("clean_strat"))
    assert reason is None


def test_fail_open_on_missing_file():
    """Gate must fail open (return None) when dashboard_data.json is missing."""
    _BT_WR_DRIFT_CACHE["mtime"] = 0.0
    with patch("audit_trail.quality_gates._DASHBOARD_DATA_PATH_QG", "/nonexistent/path.json"):
        with patch.dict(os.environ, {"BT_WR_DRIFT_GATE_ENABLED": "1"}):
            result = _passes_bt_wr_drift_gate(_pick("any_strat"))
    assert result is None


def test_kill_switch_disables_gate(tmp_path):
    """BT_WR_DRIFT_GATE_ENABLED=0 must disable gate even for severely drifted strategy."""
    dashboard_path = _make_dashboard(
        [{"strategy": "bad_strat", "wr_z": -9.0, "decay": -50.0}],
        tmp_path,
    )
    _BT_WR_DRIFT_CACHE["mtime"] = 0.0
    with patch("audit_trail.quality_gates._DASHBOARD_DATA_PATH_QG", dashboard_path):
        with patch.dict(os.environ, {"BT_WR_DRIFT_GATE_ENABLED": "0"}):
            reason = _passes_bt_wr_drift_gate(_pick("bad_strat"))
    assert reason is None


def test_custom_z_threshold(tmp_path):
    """BT_WR_DRIFT_Z_THRESHOLD=-2.0 should block strategies with wr_z < -2.0."""
    dashboard_path = _make_dashboard(
        [{"strategy": "moderate_drift", "wr_z": -2.5, "decay": -10.0}],
        tmp_path,
    )
    _BT_WR_DRIFT_CACHE["mtime"] = 0.0
    with patch("audit_trail.quality_gates._DASHBOARD_DATA_PATH_QG", dashboard_path):
        with patch.dict(os.environ, {
            "BT_WR_DRIFT_GATE_ENABLED": "1",
            "BT_WR_DRIFT_Z_THRESHOLD": "-2.0",
        }):
            reason = _passes_bt_wr_drift_gate(_pick("moderate_drift"))
    assert reason is not None


def test_z_threshold_default_does_not_block_moderate(tmp_path):
    """Default threshold -3.5 must NOT block a strategy with wr_z=-2.0."""
    dashboard_path = _make_dashboard(
        [{"strategy": "mild_drift", "wr_z": -2.0, "decay": -5.0}],
        tmp_path,
    )
    _BT_WR_DRIFT_CACHE["mtime"] = 0.0
    with patch("audit_trail.quality_gates._DASHBOARD_DATA_PATH_QG", dashboard_path):
        with patch.dict(os.environ, {"BT_WR_DRIFT_GATE_ENABLED": "1"}):
            reason = _passes_bt_wr_drift_gate(_pick("mild_drift"))
    assert reason is None
