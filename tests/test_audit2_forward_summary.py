import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.audit2_forward_summary import merge_gate  # noqa: E402


def test_merge_gate_folds_reasons_into_matching_hypothesis():
    payload = {"by_hypothesis": {"H-1": {"n": 430, "benchmark_leg": 343,
                                         "intrabar": 430, "pods": []}}}
    ledger = {"forward_gate": {
        "enforced": True,
        "hypotheses": {"H-1": {"eligible": False,
                               "reasons": ["benchmark_leg_ret coverage 80% < 90%"],
                               "benchmark_coverage": 0.798,
                               "pf_ci_lb": 0.9213, "ir": 0.0429,
                               "n_forward": 430}},
        "pods": {}}}
    out = merge_gate(payload, ledger)
    g = out["by_hypothesis"]["H-1"]["gate"]
    assert out["gate_enforced"] is True
    assert g["eligible"] is False
    assert g["benchmark_coverage"] == 0.798
    assert "coverage 80%" in g["reasons"][0]
    assert g["pf_ci_lb"] == 0.9213


def test_merge_gate_is_noop_without_ledger():
    payload = {"by_hypothesis": {"H-1": {"n": 1, "benchmark_leg": 1,
                                         "intrabar": 1, "pods": []}}}
    out = merge_gate(payload, None)
    assert "gate" not in out["by_hypothesis"]["H-1"]
    assert out["gate_enforced"] is False


def test_merge_gate_carries_pod_level_verdicts():
    payload = {"by_hypothesis": {}}
    ledger = {"forward_gate": {"enforced": True, "hypotheses": {}, "pods": {
        "POD-A": {"hypothesis_id": "H-9", "eligible": False,
                  "reasons": ["no forward rows — nothing can promote"],
                  "pf_ci_lb": None, "ir": None, "n_forward": 0}}}}
    out = merge_gate(payload, ledger)
    g = out["by_hypothesis"]["H-9"]["gate"]
    assert g["eligible"] is False and g["n_forward"] == 0
