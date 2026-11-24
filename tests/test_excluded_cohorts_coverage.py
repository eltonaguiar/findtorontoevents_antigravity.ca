import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from audit_trail.excluded_cohorts import coverage_excluded_summary  # noqa: E402


def R(sym, pnl=None, cls="CRYPTO", dirn="LONG", **kw):
    d = {"symbol": sym, "pnl_pct": pnl, "asset_class": cls, "direction": dirn}
    d.update(kw)
    return d


def test_empty_cohort_reports_zero_not_null():
    out = coverage_excluded_summary([])
    assert out["total"] == 0
    assert out["n_with_pnl"] == 0
    assert out["by_reason"] == {}
    assert out["scope"] == "auto_expired_only"


def test_reason_is_forced_onto_every_row():
    # The generator stamps `_auto_expired`, which summarize_excluded cannot see.
    # If reason were not forced, these would land under "unknown".
    rows = [R("A", 1.0, _auto_expired=True), R("B", -2.0, _auto_expired=True)]
    out = coverage_excluded_summary(rows)
    assert list(out["by_reason"]) == ["auto_expired"]
    assert out["by_reason"]["auto_expired"]["n"] == 2
    assert out["total"] == 2


def test_total_and_n_with_pnl_are_both_exposed():
    rows = [R("A", 1.0), R("B", 3.0), R("C", None)]
    out = coverage_excluded_summary(rows)
    assert out["total"] == 3
    assert out["n_with_pnl"] == 2
    assert out["by_reason"]["auto_expired"]["mean_pnl_pct"] == 2.0


def test_missing_pnl_yields_null_win_rate_not_zero():
    out = coverage_excluded_summary([R("A", None)])
    assert out["by_reason"]["auto_expired"]["win_rate"] is None
    assert out["n_with_pnl"] == 0


def test_note_states_the_measurement_is_partial():
    out = coverage_excluded_summary([R("A", 1.0)])
    assert "auto-expired" in out["note"]
    assert "not the full" in out["note"]
