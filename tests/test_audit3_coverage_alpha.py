"""Tests for the audit3 coverage block and the selection-alpha join (2026-11-19).

Two claims need to stay true:

1. The page states what fraction of the closed book it judges, and never implies
   the export slice is the whole ledger.
2. Selection alpha is joined onto the class aggregates when a sidecar exists, and
   the report says plainly when it does not instead of silently omitting it.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alpha_engine.audit3_tribunal import (  # noqa: E402
    build_report,
    load_rows,
    payload_coverage,
)


def _row(**kw):
    base = {"asset_class": "ETF", "strategy": "s1", "symbol": "SPY",
            "direction": "LONG", "pnl_pct": 1.0, "status": "WON",
            "closed_at": "2026-11-01T00:00:00Z"}
    base.update(kw)
    return base


def _payload(rows, **summary):
    return {"generated_at": "2026-11-19T04:04:16Z",
            "picks": {"recent_closed": rows}, "summary": summary}


def test_coverage_states_share_of_the_book():
    rows = [_row() for _ in range(500)]
    cov = payload_coverage(
        _payload(rows, total_closed_picks=1000, valid_closed_picks=800,
                 integrity_excluded=300, auto_expired_excluded=200), rows)
    assert cov["scored_rows"] == 500
    assert cov["scored_share_of_total_pct"] == 50.0
    assert cov["scored_share_of_valid_pct"] == 62.5
    assert cov["unscored_rows"] == 500
    assert "scores 500 of 1,000 closed picks (50.0%)" in cov["statement"]
    assert "integrity-excluded" in cov["statement"]
    assert "auto-expired" in cov["statement"]


def test_coverage_flags_overlapping_cohorts():
    rows = [_row()]
    cov = payload_coverage(
        _payload(rows, total_closed_picks=1000, integrity_excluded=700,
                 auto_expired_excluded=400), rows)
    assert cov["cohorts_overlap"] is True
    assert "do not sum to the gap" in cov["statement"]
    assert cov["unscored_rows"] == 999


def test_coverage_without_summary_counts_is_honest():
    rows = [_row(), _row()]
    cov = payload_coverage([_row()], rows)  # flat-list source carries no counts
    assert cov["total_closed_picks"] is None
    assert cov["scored_share_of_total_pct"] is None
    assert "cannot state what share" in cov["statement"]


def test_load_rows_counts_every_dropped_row(tmp_path):
    payload = _payload([
        _row(id="a"),
        _row(id="a"),                                  # duplicate id
        "nonsense",                                    # not a record
        {"id": "b", "pnl_pct": None},                  # no numeric pnl
        {"id": "c", "pnl_pct": 1.0, "status": "OPEN"},  # not closed
    ], total_closed_picks=10)
    path = tmp_path / "dd.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    drops: dict[str, int] = {}
    rows, generated_at = load_rows(str(path), drops=drops)
    assert len(rows) == 1
    assert generated_at == "2026-11-19T04:04:16Z"
    assert drops == {"duplicate": 1, "no_numeric_pnl": 1,
                     "not_a_record": 1, "not_closed": 1}


def test_report_carries_coverage_and_alpha():
    rows = [_row(pnl_pct=2.0) for _ in range(25)]
    alpha = {
        "by_class": {"ETF": {"n": 25, "alpha_pct": -0.272,
                             "alpha_ci": [-0.504, -0.037],
                             "alpha_wr": 0.41, "hold_net_pct": 0.31}},
        "covered": 25, "n_universe": 25,
        "overall": {"n": 25, "alpha_pct": -0.272},
    }
    rep = build_report(rows, "x.json", None, alpha=alpha)
    assert rep["coverage"]["scored_rows"] == 25
    cls = [c for c in rep["classes"] if c["asset_class"] == "ETF"][0]
    assert cls["alpha_pct"] == -0.272
    assert cls["alpha_n"] == 25
    assert rep["selection_alpha"]["available"] is True
    assert rep["selection_alpha"]["covered"] == 25


def test_report_without_alpha_says_so():
    rows = [_row() for _ in range(3)]
    rep = build_report(rows, "x.json", None)
    assert rep["selection_alpha"]["available"] is False
    assert all("alpha_pct" not in c for c in rep["classes"])
    assert rep["coverage"]["scored_rows"] == 3


def test_report_stays_json_safe():
    rows = [_row(pnl_pct=p) for p in (1.0, -1.0, 0.5, 2.0, -0.2) * 5]
    rep = build_report(rows, "x", None)
    json.dumps(rep, allow_nan=False)

def test_share_of_valid_is_nulled_when_it_exceeds_100():
    # Canonical scored rows (120) vs a narrower payload "valid" figure (100):
    # publishing 120% invites misreading, so the share is dropped with a note.
    rows = [_row() for _ in range(120)]
    cov = payload_coverage(
        _payload(rows, total_closed_picks=1000, valid_closed_picks=100), rows)
    assert cov["scored_rows"] == 120
    assert cov["scored_share_of_valid_pct"] is None
    assert "exceeded 100%" in cov["scored_share_of_valid_note"]
    # Normal ratios are untouched.
    rows2 = [_row() for _ in range(50)]
    cov2 = payload_coverage(
        _payload(rows2, total_closed_picks=1000, valid_closed_picks=100), rows2)
    assert cov2["scored_share_of_valid_pct"] == 50.0
    assert cov2["scored_share_of_valid_note"] is None
