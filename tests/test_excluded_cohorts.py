import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from audit_trail.excluded_cohorts import (  # noqa: E402
    bias_report, split_auto_expired, summarize_excluded)


def R(sym, pnl=None, cls="CRYPTO", dirn="LONG", reason=None, won=None, **kw):
    d = {"symbol": sym, "pnl_pct": pnl, "asset_class": cls, "direction": dirn}
    if reason:
        d["exclude_reason"] = reason
    if won is not None:
        d["won"] = won
    d.update(kw)
    return d


def test_per_reason_counts_and_stats():
    rows = [R("A", 1.0, reason="invalid_row"), R("A", -0.5, reason="invalid_row"),
            R("B", 2.0, reason="mirror_duplicate", dirn="SHORT")]
    out = summarize_excluded(rows)
    assert out["total_excluded"] == 3
    inv = out["by_reason"]["invalid_row"]
    assert inv["n"] == 2 and inv["n_with_pnl"] == 2
    assert inv["win_rate"] == 0.5
    assert inv["mean_pnl_pct"] == 0.25
    assert inv["long"] == 2 and inv["short"] == 0
    mir = out["by_reason"]["mirror_duplicate"]
    assert mir["short"] == 1 and mir["top_symbols"] == {"B": 1}


def test_rows_without_pnl_are_counted_but_not_in_mean():
    out = summarize_excluded([R("A", None), R("A", 1.0)])
    b = out["by_reason"]["unknown"]
    assert b["n"] == 2 and b["n_with_pnl"] == 1 and b["mean_pnl_pct"] == 1.0


def test_won_flag_used_when_pnl_missing():
    out = summarize_excluded([R("A", won=True), R("A", won=False)])
    b = out["by_reason"]["unknown"]
    assert b["win_rate"] == 0.5 and b["mean_pnl_pct"] is None


def test_reason_override_applies_to_all():
    out = summarize_excluded([R("A", 1.0), R("B", 2.0)], reason="auto_expired")
    assert list(out["by_reason"]) == ["auto_expired"]
    assert out["by_reason"]["auto_expired"]["n"] == 2


def test_bias_report_gap():
    inc = [R("A", 1.0), R("A", 1.0)]
    exc = [R("B", -1.0, reason="invalid_row"), R("B", -3.0, reason="invalid_row")]
    out = bias_report(inc, exc)
    assert out["included"]["mean_pnl_pct"] == 1.0
    assert out["excluded"]["mean_pnl_pct"] == -2.0
    assert out["retained_minus_excluded_pp"] == 3.0
    assert "selection risk" in out["note"]


def test_bias_report_handles_missing_pnl():
    out = bias_report([R("A", None)], [R("B", None, reason="x")])
    assert out["retained_minus_excluded_pp"] is None


def test_split_auto_expired_detects_marker_and_stale_reason():
    real, auto = split_auto_expired([
        R("A", 1.0),
        R("B", 0.0, _auto_expired=True),
        R("C", 0.0, exit_reason="STALE (auto-expired >168h)"),
    ])
    assert [r["symbol"] for r in real] == ["A"]
    assert [r["symbol"] for r in auto] == ["B", "C"]


def test_empty_input():
    out = summarize_excluded([])
    assert out == {"total_excluded": 0, "by_reason": {}}
