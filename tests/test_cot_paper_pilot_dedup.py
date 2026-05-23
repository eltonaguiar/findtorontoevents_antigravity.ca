#!/usr/bin/env python3
"""Unit tests for the COT paper-pilot over-emission dedup fix.

Falsification context:
  reports/cot_paper_pilot_overemission_falsified_20260513.md
  reports/cot_timing_leakage_audit_2026-05-13.md

The pilot re-emits the same weekly CFTC COT release every scanner cycle.
These tests pin the dedup-by-release-week logic and the tier/DSR gate.
"""
import sys
from datetime import datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "alpha_engine" / "strategies"))

import cot_paper_pilot as cpp  # noqa: E402


def test_release_week_key_collapses_same_week():
    """Picks fired Tue..Mon of one CFTC report period share a release key."""
    # 2026-04-28 is a Tuesday -> report period start.
    tue = cpp.cot_release_week_key(datetime(2026, 4, 28, 9, 0))
    wed = cpp.cot_release_week_key(datetime(2026, 4, 29, 23, 0))
    fri = cpp.cot_release_week_key(datetime(2026, 5, 1, 14, 0))
    mon = cpp.cot_release_week_key(datetime(2026, 5, 4, 8, 0))  # next Monday
    assert tue == wed == fri == mon, (tue, wed, fri, mon)


def test_release_week_key_splits_across_releases():
    """The next Tuesday begins a new CFTC release -> different key."""
    week1 = cpp.cot_release_week_key(datetime(2026, 4, 28, 12, 0))
    week2 = cpp.cot_release_week_key(datetime(2026, 5, 5, 12, 0))  # next Tuesday
    assert week1 != week2


def test_dedupe_keeps_one_trade_per_release_week():
    """50 re-emissions of one weekly signal collapse to a single trade."""
    rows = [
        {"id": f"p{i}", "status": "WON", "pnl_pct": 0.05,
         "created_at": f"2026-04-28 {h:02d}:00:00"}
        for i, h in enumerate(range(8, 18))  # 10 picks, same Tue
    ] + [
        {"id": f"q{i}", "status": "WON", "pnl_pct": 0.05,
         "created_at": f"2026-04-29 {h:02d}:00:00"}
        for i, h in enumerate(range(8, 18))  # 10 more picks, same release week
    ]
    deduped = cpp.dedupe_by_release_week(rows)
    assert len(deduped) == 1, f"expected 1 unique release, got {len(deduped)}"
    # First chronological pick of the cycle is the canonical trade.
    assert deduped[0]["id"] == "p0"
    assert deduped[0]["release_week"] == cpp.cot_release_week_key(
        datetime(2026, 4, 28, 8, 0))


def test_compute_paper_pnl_reports_over_emission_ratio():
    """compute_paper_pnl exposes raw-vs-deduped emission accounting."""
    rows = [
        {"id": f"p{i}", "status": "WON", "direction": "SHORT",
         "entry_price": 80.0, "exit_price": 76.0, "pnl_pct": 0.05,
         "created_at": f"2026-04-28 {h:02d}:00:00", "closed_at": ""}
        for i, h in enumerate(range(0, 20))  # 20 re-emissions, 1 release week
    ]
    stats = cpp.compute_paper_pnl(rows)
    assert stats["n_total"] == 1
    assert stats["n_raw_emissions"] == 20
    assert stats["over_emission_ratio"] == 20.0


def test_tier_gate_downgrades_on_insufficient_unique_releases():
    """n<20 unique releases -> SHADOW_INSUFFICIENT_N, DSR withheld (null)."""
    gate = cpp.gate_tier_and_dsr({"n_total": 5})
    assert gate["tier"] == cpp.INSUFFICIENT_N_TIER
    assert gate["tier"] != "TIER_1_RENAISSANCE"
    assert gate["dsr"] is None
    assert "over-emission" in gate["dsr_note"]


def test_tier_gate_does_not_emit_dsr_one_on_small_n():
    """The falsified DSR=1.0 must never be emitted below the n-floor."""
    for n in (1, 5, 19):
        gate = cpp.gate_tier_and_dsr({"n_total": n})
        assert gate["dsr"] is None
        assert gate["dsr"] != 1.0
        assert gate["tier"] == cpp.INSUFFICIENT_N_TIER


def test_tier_gate_holds_pending_above_floor():
    """n>=20 clears the floor but DSR stays null pending honest recompute."""
    gate = cpp.gate_tier_and_dsr({"n_total": 25})
    assert gate["tier"] == "TIER_PENDING_DEDUPED_DSR"
    assert gate["dsr"] is None


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
