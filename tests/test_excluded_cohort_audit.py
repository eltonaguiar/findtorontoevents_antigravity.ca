"""N6 excluded-cohort audit (2026-11-19).

The export slice drops rows before audit3 can see them. `_excluded_cohort_audit`
records how the excluded rows performed, per diagnostic reason, so N6 can tell a
random exclusion from a biased one. These are pure-function tests — no payload,
no DB.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from audit_trail.dashboard_generator import _excluded_cohort_audit  # noqa: E402


def test_kept_rows_are_not_counted_as_excluded():
    kept = [{"symbol": "SPY", "pnl_pct": 1.0, "direction": "LONG"}]
    closed = kept + [{"symbol": "QQQ", "pnl_pct": 2.0, "direction": "LONG"}]
    out = _excluded_cohort_audit(closed, kept)
    assert out["n_excluded"] == 1
    assert out["by_reason"]["other"]["n"] == 1


def test_auto_expired_and_paper_and_missing_pnl_are_separated():
    kept = [{"symbol": "SPY", "pnl_pct": 1.0}]
    closed = kept + [
        {"symbol": "AAA", "pnl_pct": 0, "status": "expired", "direction": "LONG"},
        {"symbol": "BBB", "pnl_pct": 2.0, "paper_trade": True, "direction": "SHORT"},
        {"symbol": "CCC", "pnl_pct": None},
    ]
    out = _excluded_cohort_audit(closed, kept)
    assert out["by_reason"]["auto_expired"]["n"] == 1
    assert out["by_reason"]["paper_trade"]["n"] == 1
    assert out["by_reason"]["missing_pnl"]["n"] == 1
    assert out["n_excluded"] == 3


def test_per_reason_stats_are_well_formed():
    kept = []
    closed = [
        {"symbol": "W", "pnl_pct": 4.0, "paper_trade": True, "direction": "LONG"},
        {"symbol": "L", "pnl_pct": -2.0, "paper_trade": True, "direction": "SHORT"},
    ]
    out = _excluded_cohort_audit(closed, kept)
    b = out["by_reason"]["paper_trade"]
    assert b["n"] == 2
    assert b["n_with_pnl"] == 2
    assert b["wr"] == 0.5
    assert b["pf"] == 2.0
    assert b["mean_pnl_pct"] == 1.0
    assert b["long"] == 1 and b["short"] == 1
    assert len(b["samples"]) == 2


def test_empty_input_is_safe():
    out = _excluded_cohort_audit([], [])
    assert out["n_excluded"] == 0
    assert out["by_reason"] == {}
    assert out["note"]
