"""Forward clock sidecar: the pod join, the coverage label, the intrabar boolean.

2026-11-21 review: ``audit2_forward.json`` held one hypothesis (H-119, n=430,
``pods: []``) while all six registered pods had zero forward rows. The page
rendered "Benchmark leg 343" beside "Forward rows 430" as if both were counts and
"Intrabar first-touch 430" as if 430 intrabar events occurred. All three are
reproduced here as labelled facts.
"""
from tools.audit2_forward_summary import summarize

PODS = [
    {"id": "POD-A", "status": "observe", "hypothesis": "H-POD-A"},
    {"id": "POD-B", "status": "pre_registered", "hypothesis": "H-POD-B"},
]
# 430 rows on an orphan hypothesis: 400 carry a benchmark leg, all intrabar.
ROWS = ([{"hypothesis_id": "H-119", "benchmark_leg_ret": 0.1,
          "intrabar_first_touch": True}] * 400
        + [{"hypothesis_id": "H-119", "intrabar_first_touch": True}] * 30)
GATE = {"hypotheses": {"H-119": {"eligible": False,
                                 "reasons": ["benchmark_leg_ret coverage 80% < 90%"]}}}


def test_benchmark_leg_is_reported_as_coverage_not_a_second_count():
    h = summarize(ROWS, PODS, GATE)["by_hypothesis"]["H-119"]
    assert h["n"] == 430
    assert h["benchmark_leg"] == 400
    assert h["benchmark_coverage_pct"] == 93.0


def test_intrabar_is_a_boolean_over_the_denominator():
    h = summarize(ROWS, PODS, GATE)["by_hypothesis"]["H-119"]
    assert h["intrabar"] == 430 and h["intrabar_all"] is True


def test_orphan_hypothesis_is_named_and_cannot_be_gate_ready():
    d = summarize(ROWS, PODS, GATE)
    h = d["by_hypothesis"]["H-119"]
    assert d["orphan_hypotheses"] == ["H-119"]
    assert h["owned_by_pods"] is False and h["gate_ready"] is False
    assert "orphan" in h["status"]
    assert any("no registered pod owns" in r for r in h["reasons"])


def test_registered_pods_with_zero_forward_rows_are_listed():
    assert summarize(ROWS, PODS, GATE)["pods_without_rows"] == ["POD-A", "POD-B"]


def test_owned_hypothesis_joins_its_pod_and_reaches_gate_ready():
    rows = [{"hypothesis_id": "H-POD-A", "benchmark_leg_ret": 0.2,
             "intrabar_first_touch": True}] * 120
    d = summarize(rows, PODS, {"hypotheses": {}})
    h = d["by_hypothesis"]["H-POD-A"]
    assert h["owned_by_pods"] is True
    assert h["registered_owner_pods"] == ["POD-A"]
    assert h["gate_ready"] is True and h["status"] == "gate-ready"
    assert d["orphan_hypotheses"] == []


def test_ledger_reasons_are_carried_through():
    h = summarize(ROWS, PODS, GATE)["by_hypothesis"]["H-119"]
    assert "benchmark_leg_ret coverage 80% < 90%" in h["reasons"]
