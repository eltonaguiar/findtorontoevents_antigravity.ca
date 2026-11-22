"""Offline invariants for the carry break-even table and the forward pod gate.

The gate is the important part: a forward pod that can be declared ALIVE at n=6 is not a
forward pod, it is a mood. These tests pin the two behaviours that make it honest — a hard
refusal to judge before the gate opens, and a kill that fires only on stated criteria.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.funding_carry_breakeven import HOLDS, SECOND_HALF_BP, net_bp_day  # noqa: E402
from tools.funding_carry_forward import SPEC, evaluate  # noqa: E402


# ---- break-even arithmetic

def test_longer_hold_always_beats_a_shorter_one_at_the_same_cost():
    prev = None
    for h in HOLDS:
        n = net_bp_day(42.64, h)
        if prev is not None:
            assert n > prev, "a longer hold must dilute a fixed round trip"
        prev = n


def test_zero_cost_returns_the_forward_honest_gross_minus_rehedge():
    assert net_bp_day(0.0, 90, rehedge=0.0) == SECOND_HALF_BP


def test_cost_is_charged_once_per_hold_not_per_day():
    once = net_bp_day(30.0, 60, rehedge=0.0)
    assert abs((SECOND_HALF_BP - once) - 30.0 / 60) < 1e-9


# ---- forward pod gate

def _row(v, d="2026-11-23"):
    return {"date": d, "mean_bp": v, "pod_id": "POD-CRYPTO-CARRY-H229"}


def test_no_verdict_before_the_minimum_n():
    res = evaluate([_row(1.0)] * 5)
    assert res["gated"] is True
    assert res["verdict"].startswith("no_judgment")


def test_empty_pod_is_gated_not_killed():
    res = evaluate([])
    assert res["gated"] is True and res["n_days"] == 0


def test_gate_opens_at_min_n_and_then_judges():
    rows = [_row(1.5)] * SPEC["judgment_gate"]["min_n_days"]
    res = evaluate(rows)
    assert res["gated"] is False
    assert "verdict" in res and res["verdict"] in ("ALIVE", "KILL")


def test_a_negative_series_is_killed_by_k1():
    rows = [_row(-0.5)] * SPEC["judgment_gate"]["min_n_days"]
    res = evaluate(rows)
    assert "K1" in res["triggered"] and res["verdict"] == "KILL"


def test_a_steady_positive_series_survives():
    rows = [_row(3.0)] * SPEC["judgment_gate"]["min_n_days"]
    res = evaluate(rows)
    assert res["triggered"] == [] and res["verdict"] == "ALIVE"


def test_below_the_cash_hurdle_is_a_sizing_note_not_a_kill():
    """3.0 bp/day gross cannot cover a 42.64bp round trip spread over 20 days, so it does not
    beat cash — but that is a reason not to size it, not a reason to call the hypothesis dead.
    K4 additionally requires the pledged-collateral fact, which nobody has measured."""
    rows = [_row(3.0)] * SPEC["judgment_gate"]["min_n_days"]
    res = evaluate(rows)
    assert res["beats_cash"] is False
    assert "sizing_note" in res
    assert "K4" not in res["triggered"]
    assert res["verdict"] == "ALIVE"


def test_a_stress_print_is_flagged_and_does_not_shield_k1():
    """K5 flags the print; it must not relax the mean gate. One -420bp day in 20 drags the
    net CI-LB negative, and the pod is killed. Suppressing that because it is 'only one
    print' would be the gate weakening itself."""
    rows = [_row(1.5)] * 19 + [_row(-420.0)]
    res = evaluate(rows)
    assert "K5" in res["triggered"]
    assert res["net_ci_lb_bp"] <= 0
    assert res["verdict"] == "KILL"
