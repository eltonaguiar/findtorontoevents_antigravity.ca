"""Tests for the cost-headroom gate (todo #27).

Rule under test: ``breakeven_cost_bp > cost_high_bp``.

The gate answers "could the worst cost assumption in the repo kill this edge?".
It is intentionally advisory: it is computed and reported, but it does not demote
live picks on its own. These tests pin the semantics so that wiring it into
promotion later cannot quietly change what PASS means.
"""
import json
import pathlib
import subprocess
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.cost_sensitivity import (  # noqa: E402
    COST_HEADROOM_RULE,
    COST_HIGH_BP,
    analyse,
    cost_headroom_gate,
)


def test_rule_constant_is_the_stated_rule():
    assert COST_HEADROOM_RULE == "breakeven_cost_bp > cost_high_bp"


def test_passes_when_breakeven_clears_the_worst_cost():
    gate = cost_headroom_gate(500.0, COST_HIGH_BP)
    assert gate["status"] == "PASS"
    assert gate["headroom_bp"] == pytest.approx(475.0)
    assert gate["rule"] == COST_HEADROOM_RULE


def test_fails_when_breakeven_is_below_the_worst_cost():
    gate = cost_headroom_gate(6.16, COST_HIGH_BP)
    assert gate["status"] == "FAIL"
    assert gate["headroom_bp"] < 0


def test_equality_fails_because_the_comparison_is_strict():
    """A breakeven exactly at the high constant only survives the optimistic case."""
    gate = cost_headroom_gate(COST_HIGH_BP, COST_HIGH_BP)
    assert gate["status"] == "FAIL"
    assert gate["headroom_bp"] == pytest.approx(0.0)


def test_undefined_breakeven_is_unknown_not_pass():
    """Zero turnover means no cost drag, so the rule has nothing to say."""
    gate = cost_headroom_gate(None, COST_HIGH_BP)
    assert gate["status"] == "UNKNOWN"
    assert gate["breakeven_cost_bp"] is None
    assert "zero turnover" in gate["reason"]


def test_zero_turnover_analysis_reports_unknown_gate():
    out = analyse(gross_ann=0.05, turnover_per_year=0.0, hurdle_ann=0.0432)
    assert out["breakeven_cost_bp"] is None
    assert out["cost_headroom_gate"]["status"] == "UNKNOWN"


def test_analysis_emits_the_gate_additively():
    out = analyse(gross_ann=0.10, turnover_per_year=2.0, hurdle_ann=0.0432)
    gate = out["cost_headroom_gate"]
    # breakeven = 0.10*10000/2 = 500 bp, far above the 25 bp constant
    assert gate["status"] == "PASS"
    # pre-existing keys must survive: the change is additive
    for key in ("inputs", "at_measured_cost", "at_repo_constant",
                "sign_flip", "verdict_flip", "assessment", "interpretation"):
        assert key in out


def test_gate_agrees_with_robustly_killed_assessment():
    """A ROBUSTLY-KILLED strategy must not clear the cost-headroom gate."""
    out = analyse(gross_ann=0.0005, turnover_per_year=2.0, hurdle_ann=0.0432)
    assert out["assessment"] == "ROBUSTLY-KILLED"
    assert out["cost_headroom_gate"]["status"] == "FAIL"


def test_gate_agrees_with_robustly_passes_assessment():
    out = analyse(gross_ann=0.10, turnover_per_year=2.0, hurdle_ann=0.0432)
    assert out["assessment"] == "ROBUSTLY-PASSES"
    assert out["cost_headroom_gate"]["status"] == "PASS"


def test_hml_case_fails_the_gate_consistent_with_its_verdict(tmp_path):
    hml = REPO_ROOT / "reports/hml_result.json"
    if not hml.exists():
        pytest.skip("reports/hml_result.json not present")
    proc = subprocess.run(
        [sys.executable, "tools/cost_sensitivity.py", "--hml",
         "--out", str(tmp_path / "cs.json")],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True,
    )
    out = json.loads((tmp_path / "cs.json").read_text())
    assert out["assessment"] == "ROBUSTLY-KILLED"
    assert out["cost_headroom_gate"]["status"] == "FAIL"
    assert "cost headroom" in proc.stdout


def test_gate_flag_exits_nonzero_on_fail(tmp_path):
    proc = subprocess.run(
        [sys.executable, "tools/cost_sensitivity.py",
         "--gross-ann", "0.0005", "--turnover-per-year", "2",
         "--hurdle-ann", "0.0432", "--gate",
         "--out", str(tmp_path / "fail.json")],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    assert proc.returncode == 1
    assert "GATE FAILED" in proc.stderr


def test_gate_flag_exits_zero_on_pass(tmp_path):
    proc = subprocess.run(
        [sys.executable, "tools/cost_sensitivity.py",
         "--gross-ann", "0.10", "--turnover-per-year", "2",
         "--hurdle-ann", "0.0432", "--gate",
         "--out", str(tmp_path / "pass.json")],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    assert proc.returncode == 0
    assert "GATE FAILED" not in proc.stderr
