"""Tests for audit_trail.proven_gate and audit_trail.pnl_totals_audit.

Covers the 2026-11-16 audit findings: a PROVEN badge must not survive a losing
ledger, and the P&L totals must carry their basis plus the pre-clamp value.
"""

import pytest

from audit_trail.proven_gate import (
    check_pick_proven,
    demoted_tier,
    ledger_stats,
    proven_eligibility,
    stats_from_pick,
)
from audit_trail.pnl_totals_audit import (
    build_pnl_headline,
    compute_resolver_anomalies,
)


# ── proven gate ────────────────────────────────────────────────────────────
def test_proven_eligibility_accepts_published_bar():
    ok, reason = proven_eligibility({"n": 20, "wr": 50.0, "pf": 1.5})
    assert ok is True, reason


def test_proven_eligibility_rejects_short_sample():
    ok, reason = proven_eligibility({"n": 19, "wr": 80.0, "pf": 4.0})
    assert ok is False
    assert reason.startswith("insufficient_sample")


def test_proven_eligibility_rejects_losing_strategy():
    # ml_bg_system_f / extreme_fear shape from the live payload.
    ok, reason = proven_eligibility({"n": 52, "wr": 9.6, "pf": 0.12})
    assert ok is False
    assert reason.startswith("wr_below_floor")


def test_proven_eligibility_requires_known_pf():
    ok, reason = proven_eligibility({"n": 40, "wr": 60.0, "pf": None})
    assert ok is False
    assert reason.startswith("pf_unknown")


def test_stats_from_pick_normalizes_fraction_and_percent():
    frac = stats_from_pick({"strat_fwd_wr": 0.55, "strat_fwd_trades": 25})
    pct = stats_from_pick({"strat_fwd_wr": 55.0, "strat_fwd_trades": 25})
    assert frac["wr"] == pytest.approx(55.0)
    assert pct["wr"] == pytest.approx(55.0)


def test_check_pick_proven_demotes_live_ml_bg_system_f_row():
    pick = {
        "source_system": "ml_bg_system_f",
        "strategy": "extreme_fear",
        "strat_fwd_wr": 0.206,
        "strat_fwd_trades": 97,
        "strat_fwd_pf": 0.31,
    }
    ok, reason, stats = check_pick_proven(pick)
    assert ok is False
    # WR is evaluated before PF, so the live row fails on WR first; either
    # floor is a valid rejection reason for this shape.
    assert reason.startswith(("wr_below_floor", "pf_below_floor")), reason
    assert demoted_tier(stats) == "WATCH"


def test_check_pick_proven_keeps_genuine_edge():
    stats = {"n": 96, "wr": 55.0, "pf": 1.6}
    ok, reason, _ = check_pick_proven({"strategy": "quality-minus-junk"}, stats)
    assert ok is True, reason


def test_check_pick_proven_treats_missing_stats_as_unverifiable():
    ok, reason, _ = check_pick_proven({"strategy": "extreme_fear"})
    assert ok is False
    assert reason.startswith("unverifiable")


def test_ledger_stats_ignores_flat_and_unresolved_rows():
    rows = [
        {"status": "WON", "pnl_pct": 2.0},
        {"status": "LOST", "pnl_pct": -1.0},
        {"status": "OPEN", "pnl_pct": 9.0},
        {"status": "EXPIRED", "pnl_pct": 0.0},
    ]
    stats = ledger_stats(rows)
    assert stats["n"] == 2
    assert stats["wr"] == pytest.approx(50.0)
    assert stats["pf"] == pytest.approx(2.0)


# ── P&L reconciliation ─────────────────────────────────────────────────────
def test_headline_labels_every_total_and_preserves_pre_floor():
    head = build_pnl_headline(
        headline=-77.67,
        rolling_100=-77.67,
        sum_raw=-1356.44,
        compounded_ew=-99.0,
        compounded_ew_pre_floor=-1356.44,
        geomean_annualized=-99.9,
    )
    assert head["primary_metric"] == "total_pnl_pct"
    assert head["compounded_ew_floored"] is True
    assert head["compounded_ew_pre_floor"] == pytest.approx(-1356.44)
    assert head["values"]["raw_additive_sum"] == pytest.approx(-1356.44)
    assert set(head["values"]) >= {
        "rolling_100_compounded_ew",
        "raw_additive_sum",
        "full_ledger_compounded_ew",
        "annualized_geomean",
    }


def test_headline_not_marked_floored_when_unaltered():
    head = build_pnl_headline(
        headline=12.0,
        rolling_100=12.0,
        sum_raw=40.0,
        compounded_ew=12.0,
        compounded_ew_pre_floor=12.0,
    )
    assert head["compounded_ew_floored"] is False


def test_resolver_anomalies_flags_nearusdt_style_clamped_stale_exit():
    rows = [
        {
            "symbol": "NEARUSDT",
            "status": "EXPIRED",
            "exit_reason": "STALE (auto-expire >5809h)",
            "entry_price": 1.356,
            "stop_loss": 1.37973,
            "pnl_pct": -99.0,
            "pnl_pct_pre_clamp": -135.472,
            "closed_at": "",
        }
    ]
    out = compute_resolver_anomalies(rows)
    assert out["stale_exit_beyond_planned_stop"] == 1
    assert out["clamped_loss_rows"] == 1
    assert out["expired_zero_pnl_rows"] == 0


def test_resolver_anomalies_flags_expired_zero_and_missing_closed_at():
    rows = [
        {"status": "EXPIRED", "exit_reason": "STALE", "pnl_pct": 0.0},
        {"status": "WON", "pnl_pct": 1.2, "closed_at": ""},
        {"status": "WON", "pnl_pct": 1.2, "closed_at": "2026-11-01T00:00:00Z"},
    ]
    out = compute_resolver_anomalies(rows)
    assert out["expired_zero_pnl_rows"] == 1
    assert out["closed_rows_missing_closed_at"] == 1


def test_resolver_anomalies_ignores_ordinary_stop_out():
    rows = [
        {
            "status": "LOST",
            "exit_reason": "SL_HIT",
            "entry_price": 100.0,
            "stop_loss": 98.0,
            "pnl_pct": -2.0,
            "closed_at": "2026-11-01T00:00:00Z",
        }
    ]
    out = compute_resolver_anomalies(rows)
    assert out["stale_exit_beyond_planned_stop"] == 0
    assert out["clamped_loss_rows"] == 0
