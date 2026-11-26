"""Tests for tools/dsr_multiplicity_sensitivity.py (programme items D25 + D28).

The tool's job is to be trustworthy about a number that decided a verdict, so the
tests pin the three things that could quietly be wrong: the bisection direction,
monotonicity of DSR in the trial count, and reproduction of the artifact's own
DSR column for the cell under analysis.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from dsr_multiplicity_sensitivity import (dsr_of,
                                          k_of_n, norm_cdf, trials_to_clear)

ARTIFACT = ROOT / "reports" / "per_class_edge_2026-11-22.json"
REPORT = ROOT / "reports" / "dsr_multiplicity_2026-11-22.json"


def _scale(art):
    return float(art["expected_max_sharpe_daily"]) / k_of_n(int(art["n_trials_declared"]))


@pytest.mark.skipif(not ARTIFACT.exists(), reason="artifact absent")
def test_dsr_is_decreasing_in_trial_count():
    art = json.loads(ARTIFACT.read_text())
    scale = _scale(art)
    vals = [dsr_of(0.0736, 3744, n, scale) for n in (2, 10, 29, 100, 1000)]
    assert all(a > b for a, b in zip(vals, vals[1:])), vals


@pytest.mark.skipif(not ARTIFACT.exists(), reason="artifact absent")
def test_trials_to_clear_finds_last_passing_count():
    """Regression: the first draft searched for the first FAILING count and returned
    the cap (100000). The correct answer is the last cantrip passing count."""
    art = json.loads(ARTIFACT.read_text())
    scale = _scale(art)
    n = trials_to_clear(0.0736, 3744, scale)
    assert n is not None and 2 < n < 1000
    assert dsr_of(0.0736, 3744, n, scale) >= 0.95
    assert dsr_of(0.0736, 3744, n + 1, scale) < 0.95


@pytest.mark.skipif(not ARTIFACT.exists(), reason="artifact absent")
def test_reproduces_artifact_dsr_for_focus_cell():
    art = json.loads(ARTIFACT.read_text())
    scale = _scale(art)
    cell = next(c for c in art["cells"] if c["id"] == "H-201")
    mine = dsr_of(float(cell["sr_daily"]), int(cell["n_days"]), 29, scale)
    assert abs(mine - float(cell["dsr"])) < 0.01, (mine, cell["dsr"])


def test_k_of_n_increases_with_n():
    ks = [k_of_n(n) for n in (2, 5, 29, 100)]
    assert all(a < b for a, b in zip(ks, ks[1:])), ks


def test_norm_cdf_symmetry_and_median():
    assert abs(norm_cdf(0.0) - 0.5) < 1e-12
    assert abs(norm_cdf(1.959963984540054) - 0.975) < 1e-6


@pytest.mark.skipif(not REPORT.exists(), reason="report absent")
def test_report_states_the_margin_not_just_the_verdict():
    d = json.loads(REPORT.read_text())
    x = d["item_D28_multiplicity_breakeven"]
    assert x["margin_in_trials"] is not None
    assert x["min_trials_still_passing"] >= 2
    assert "NOT_PROVEN" in x["interpretation"]
    assert d["reproduction_check"]["focus_residual"] < d["reproduction_check"]["tolerance"]
