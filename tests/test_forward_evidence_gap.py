import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.forward_evidence_gap import ci_summary, count_rows  # noqa: E402


def R(entry, exit_, side="LONG", slip=0.0, cls="CRYPTO"):
    return {"asset_class": cls, "entry_px": entry, "exit_px": exit_,
            "side": side, "slippage_bps": slip}


def test_cost_is_applied_exactly_once():
    # 1% gross move, 10bp slippage -> 0.9% net, NOT 0.8%.
    out = ci_summary([R(100.0, 101.0, slip=10.0)])
    assert out["n"] == 1
    assert out["mean"] == 0.9


def test_short_is_sign_flipped():
    out = ci_summary([R(100.0, 99.0, side="SHORT")])
    assert out["mean"] == 1.0


def test_ci_brackets_the_mean():
    rows = [R(100.0, 101.0), R(100.0, 99.0), R(100.0, 102.0), R(100.0, 98.0)]
    out = ci_summary(rows)
    lo, hi = out["ci"]
    assert lo <= out["mean"] <= hi


def test_rows_without_prices_are_skipped():
    out = ci_summary([R(100.0, 101.0), {"asset_class": "CRYPTO"}])
    assert out["n"] == 1


def test_empty_is_none_not_zero():
    out = ci_summary([])
    assert out["n"] == 0
    assert out["mean"] is None
    assert out["ci"] is None


def test_cost_multiplier_scales_the_deduction():
    one = ci_summary([R(100.0, 101.0, slip=10.0)], cost_mult=1)
    two = ci_summary([R(100.0, 101.0, slip=10.0)], cost_mult=2)
    assert one["mean"] == 0.9
    assert two["mean"] == 0.8
