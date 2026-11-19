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


# ───────────────────────── 2026-11-19: denominator reconciliation + counters ──
def test_scored_rows_above_valid_never_publish_over_100_pct():
    """Live: 8,605 canonical rows vs 8,175 valid → 105.26% is not a measurement."""
    rows = [_row() for _ in range(100)]
    cov = payload_coverage(
        _payload(rows, total_closed_picks=200, valid_closed_picks=80), rows)
    # 100 scored / 80 valid would be 125%; withhold the headline, keep the raw.
    assert cov["scored_share_of_valid_pct"] is None
    assert cov["scored_share_of_valid_pct_raw"] == 125.0
    assert cov["valid_denominator_inconsistent"] is True
    rec = cov["denominator_reconciliation"]
    assert rec["canonical_rows"] == 100
    assert rec["dashboard_valid_closed_picks"] == 80
    assert rec["delta"] == 20
    assert rec["scored_but_not_dashboard_valid"] == 20
    assert rec["consistent"] is False
    assert "two denominators disagree" in cov["statement"]
    assert "125.0%" not in cov["statement"]


def test_valid_denominator_consistent_still_publishes_share():
    rows = [_row() for _ in range(50)]
    cov = payload_coverage(
        _payload(rows, total_closed_picks=100, valid_closed_picks=100), rows)
    assert cov["scored_share_of_valid_pct"] == 50.0
    assert cov["scored_share_of_valid_pct_raw"] == 50.0
    assert cov["valid_denominator_inconsistent"] is False
    assert cov["denominator_reconciliation"]["consistent"] is True


def test_candidate_counters_match_their_own_tables():
    """summary.n_candidate counts strategy cells only; symbols/segments need their
    own counters so the KPI cannot contradict the tables it sits above."""
    rows = [_row(pnl_pct=p) for p in (1.0, -1.0, 0.5, 2.0, -0.2) * 6]
    rep = build_report(rows, "x.json", None)
    s = rep["summary"]
    assert s["n_candidate_symbols"] == sum(
        1 for x in rep["symbols"] if x.get("verdict") == "CANDIDATE")
    assert s["n_candidate_segments"] == sum(
        1 for x in rep["segments"] if x.get("verdict") == "CANDIDATE")
    assert s["n_proven_symbols"] == sum(
        1 for x in rep["symbols"] if x.get("verdict") == "PROVEN_T2")
