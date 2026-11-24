"""End-to-end proof that the excluded-row summary is actually populated (Block 59).

Block 58 built ``summarize_excluded_rows`` and taught audit3's
``payload_coverage`` to read ``_excluded_cohort_rows``, but nothing wrote that
key, so on a live build ``coverage.excluded_summary`` was a zero-valued dict
(an absent key summaries as total 0, not None). This test exercises the REAL
collection + stamping path in ``audit_trail.dashboard_generator`` against a
synthetic input list -- the DB-facing loader is never called, no MySQL, no
generator run -- and asserts the summary is populated, attributed and
overlap-correct.

Stdlib + pytest only.
"""
from __future__ import annotations

import audit_trail.dashboard_generator as dg
from alpha_engine.audit3_tribunal import payload_coverage
from audit_trail.excluded_cohorts import summarize_excluded_rows


def _kept():
    # A row the validity predicate accepts: terminal status, closed_at, pnl.
    return {"symbol": "BTCUSDT", "asset_class": "CRYPTO", "pnl_pct": 2.0,
            "direction": "LONG", "id": "kept-1", "status": "WON",
            "closed_at": "2026-11-20T00:00:00Z"}


def _invalid_classless():
    # Rejected by the validity predicate (still open) and carries no class.
    return {"symbol": "", "asset_class": "", "pnl_pct": 1.0, "status": "OPEN"}


def _expired():
    return {"symbol": "ETHUSDT", "asset_class": "", "pnl_pct": 0.0,
            "status": "EXPIRED", "exit_reason": "STALE", "_auto_expired": True}


def _mirror():
    # Same economic trade as the kept row, second copy: valid, then deduped.
    return {"symbol": "BTCUSDT", "asset_class": "CRYPTO", "pnl_pct": 2.0,
            "direction": "LONG", "id": "mirror-1", "status": "WON",
            "closed_at": "2026-11-20T00:00:00Z"}


def _synthetic_input():
    kept, mirror = _kept(), _mirror()
    closed = [kept, mirror, _invalid_classless(), _expired()]
    valid_pre_dedupe = [p for p in closed if dg._is_valid_resolved_pick(p)]
    # Mirror rows are the duplicates dropped by the dedupe loop.
    mirror_rows = [mirror]
    auto_expired_rows = [p for p in closed if p.get("_auto_expired")]
    return closed, valid_pre_dedupe, mirror_rows, auto_expired_rows


def _collect():
    closed, valid, mirrors, expired = _synthetic_input()
    return dg._collect_excluded_cohort_rows(
        pre_filter_rows=closed,
        valid_rows=valid,
        mirror_rows=mirrors,
        auto_expired_rows=expired,
    )


def test_collection_returns_the_mapping_shape_the_summariser_reads():
    cohorts = _collect()
    # A flat list would be summed as zero rows; the shape must be cohort -> rows.
    assert isinstance(cohorts, dict)
    assert set(cohorts) == {"integrity_excluded", "mirror_duplicate", "auto_expired"}
    for rows in cohorts.values():
        assert isinstance(rows, list)


def test_summary_is_populated_not_none_and_counts_each_row_once():
    cohorts = _collect()
    out = summarize_excluded_rows(cohorts)
    assert out is not None
    # 3 distinct rows are dropped: classless-invalid, expired, mirror.
    assert out["total"] == 3
    assert sum(out["by_class"].values()) == out["total"]


def test_every_synthetic_reason_is_attributed():
    out = summarize_excluded_rows(_collect())
    assert out["by_reason"]["mirror_duplicate"] >= 1
    assert out["by_reason"]["auto_expired"] >= 1
    # The classless row is attributed by the existing reason classifier, which
    # names an empty exit_reason a non-performance exit before it looks at status.
    assert out["by_reason"]["non_performance_exit"] >= 1


def test_classless_rows_land_in_the_unknown_bucket():
    out = summarize_excluded_rows(_collect())
    # The invalid row has no symbol/class; _coerce_asset_class returns UNKNOWN.
    assert out["by_class"]["UNKNOWN"] >= 1


def test_asset_class_is_derived_when_missing():
    cohorts = _collect()
    expired = cohorts["auto_expired"][0]
    # ETHUSDT had asset_class="" but is unambiguously crypto by symbol.
    assert expired["asset_class"] == "CRYPTO"


def test_overlap_rule_row_in_two_cohorts_appears_once_in_total():
    # A single row object supplied to two cohorts: counted once in total,
    # once per distinct reason in by_reason.
    shared = {"symbol": "SOLUSDT", "asset_class": "CRYPTO", "pnl_pct": 0.0,
              "exclude_reason": "non_performance_exit"}
    out = summarize_excluded_rows({"integrity_excluded": [shared],
                                   "auto_expired": [shared]})
    assert out["total"] == 1
    assert out["by_reason"]["non_performance_exit"] == 1
    assert out["overlap"] is True


def test_stamping_never_mutates_the_input_rows():
    closed, valid, mirrors, expired = _synthetic_input()
    dg._collect_excluded_cohort_rows(
        pre_filter_rows=closed, valid_rows=valid,
        mirror_rows=mirrors, auto_expired_rows=expired,
    )
    for row in closed:
        assert "exclude_reason" not in row, (
            "the collector must copy before stamping: the same row object is "
            "still in use by the scored book"
        )


def test_payload_coverage_reads_the_collected_block():
    """The real consumer: audit3's payload_coverage over the collected rows."""
    cohorts = _collect()
    data = {
        "summary": {"total_closed_picks": 10, "valid_closed_picks": 4},
        "_excluded_cohort_rows": cohorts,
    }
    cov = payload_coverage(data, [{"asset_class": "CRYPTO", "pnl_pct": 2.0}])
    summary = cov["excluded_summary"]
    assert summary is not None
    assert summary["total"] == 3
    assert summary["by_reason"]["auto_expired"] >= 1
    assert summary["by_class"].get("UNKNOWN", 0) >= 1


def test_payload_coverage_without_the_block_is_zero_not_none():
    """Pins the brief's falsified premise: absent key summaries to total 0."""
    cov = payload_coverage({"summary": {"total_closed_picks": 10}},
                           [{"asset_class": "CRYPTO", "pnl_pct": 2.0}])
    assert cov["excluded_summary"] is not None
    assert cov["excluded_summary"]["total"] == 0
