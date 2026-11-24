import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.class_coverage import coverage  # noqa: E402


def row(n=100, alpha_n=60, ok=True, **kw):
    d = {"asset_class": "TEST", "n": n,
         "alpha_gate": {"alpha_n": alpha_n, "alpha_coverage_ok": ok}}
    d.update(kw)
    return d


def test_coverage_pct_is_alpha_n_over_n():
    out = coverage(row(n=1000, alpha_n=242))
    assert out["coverage_pct"] == 24.2


def test_below_floor_is_flagged():
    assert coverage(row(n=1000, alpha_n=242))["below_floor"] is True


def test_at_or_above_floor_is_not_flagged():
    # 50% is the floor; 50.0 must pass, not fail, on the boundary.
    assert coverage(row(n=100, alpha_n=50))["below_floor"] is False


def test_ledger_flag_is_reported_not_recomputed():
    # The ledger says ok=True while the arithmetic says 24%: surface both.
    out = coverage(row(n=1000, alpha_n=242, ok=True))
    assert out["ledger_says_ok"] is True
    assert out["below_floor"] is True


def test_zero_n_does_not_divide_by_zero():
    out = coverage(row(n=0, alpha_n=0))
    assert out["coverage_pct"] == 0.0


def test_missing_alpha_gate_is_none_not_zero():
    out = coverage({"asset_class": "X", "n": 10})
    assert out["coverage_pct"] is None
