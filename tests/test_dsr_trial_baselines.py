"""Every class the book tests must have a real trial-count baseline.

A DSR baseline of 1 applies no multiple-testing correction; a baseline larger
than the number of strategy cells actually tested invents trials that were never
run. Both are wrong, in opposite directions, so the map is checked against the
canonical registry view that money_ready_verdict itself reads.
"""
import json
from pathlib import Path

import pytest

from alpha_engine.money_ready_verdict import NB_TRIALS_BY_CLASS, _dsr_gate
from tools.dsr_trial_baseline_report import audit, measure

REGISTRY = Path(__file__).resolve().parents[1] / "audit_dashboard" / "data" / "pf_registry.json"
# Alternating, non-degenerate-variance fixture (n=80).
RETURNS = [0.4, -0.2] * 40


def test_previously_skipped_classes_now_have_baselines():
    # These four were absent from the map, so their DSR was skipped entirely.
    for cls in ("EQUITY", "ETF", "BOND", "FUTURES"):
        assert NB_TRIALS_BY_CLASS.get(cls, 0) >= 2, f"{cls} still has no baseline"


def test_baseline_never_exceeds_the_search_space_actually_tested():
    if not REGISTRY.exists():
        pytest.skip("pf_registry.json not present")
    registry = json.loads(REGISTRY.read_text())
    bad = [r for r in audit(measure(registry))
           if r["state"] in ("MISSING", "UNDER", "OVER")]
    assert not bad, bad


def test_equity_dsr_is_computed_with_its_baseline():
    r = _dsr_gate(RETURNS, "EQUITY")
    assert r.get("skipped") is not True
    assert r["nb_trials"] == NB_TRIALS_BY_CLASS["EQUITY"]


def test_a_class_with_no_tested_cell_still_skips():
    # MUTUAL_FUND has zero strategy cells in the canonical registry: there is
    # nothing to deflate, so skipping is the honest answer, not a pass.
    r = _dsr_gate(RETURNS, "MUTUAL_FUND")
    assert r["ok"] is None and r["skipped"] is True
    assert r["nb_trials"] is None
