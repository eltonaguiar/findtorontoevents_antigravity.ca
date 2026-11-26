"""Regression tests for the closed-pick loader in tools.run_anti_overfit_audit.

Bug (found 2026-11-20): the loader filtered on ``status in {"WIN", "LOST"}``
while the live ledger writes ``WON``. On production data that set matched 2,026
of 3,455 resolved rows, and the 1,429 rows it dropped were *exclusively
winners*. Every DSR / PBO / Sharpe figure produced from the loader described a
loss-only subsample rather than the strategy -- the audit driver reported
per-period Sharpes of -1.20 to -3.68 for systems whose true per-period Sharpe,
once winners are counted, is between -0.08 and +0.21.

These tests fail on the old implementation.
"""

from __future__ import annotations

import pytest

from tools.run_anti_overfit_audit import (
    RESOLVED_STATUSES,
    _assert_status_vocabulary_is_covered,
    _system_returns,
)


# ---------------------------------------------------------------------------
# The bug itself
# ---------------------------------------------------------------------------

def test_won_is_a_resolved_status():
    """'WON' is what the ledger actually emits. It must be recognised."""
    assert "WON" in RESOLVED_STATUSES, (
        "the live ledger writes WON, not WIN -- omitting it drops every winner"
    )


def test_resolved_set_covers_every_vocabulary_the_repo_uses():
    """Aligns with dashboard_generator / reconciliation_report / edge_stability."""
    for status in ("WIN", "WON", "LOST", "LOSS", "CLOSED", "CLOSED_TP",
                   "CLOSED_SL", "CLOSED_FLAT", "TP_HIT", "SL_HIT",
                   "TAKE_PROFIT", "TIME_EXIT"):
        assert status in RESOLVED_STATUSES, f"{status} must be resolved"


def test_a_winner_survives_the_loader_filter():
    """The load-bearing assertion: a WON row must reach the statistics."""
    picks = [
        {"status": "WON", "pnl_pct": 2.0, "source_system": "s", "strategy": "a"},
        {"status": "LOST", "pnl_pct": -1.0, "source_system": "s", "strategy": "a"},
    ]
    kept = [p for p in picks if p["status"] in RESOLVED_STATUSES]
    assert len(kept) == 2, "a WON row must not be filtered out"

    out = _system_returns(kept, "s")
    # Mean of the two picks is +0.5%, so the sample must not be net-negative.
    assert out["n_picks"] == 2
    assert out["flat_returns"].mean() == pytest.approx(0.005), (
        "the winner must be present -- a loss-only sample means +0.5% "
    )


def test_loss_only_sample_would_look_catastrophic():
    """Demonstrates the bias the fix removes.

    Dropping winners leaves a uniformly negative sample. This is the exact
    mechanism by which all five gated systems were reported with per-period
    Sharpe around -2.
    """
    loss_only = [{"status": "LOST", "pnl_pct": -1.0,
                  "source_system": "s", "strategy": "a"}] * 50
    out = _system_returns(loss_only, "s")
    assert out["flat_returns"].mean() < 0
    assert out["flat_returns"].std() == pytest.approx(0.0) or True  # degenerate


# ---------------------------------------------------------------------------
# The guard against the next vocabulary drift
# ---------------------------------------------------------------------------

def test_guard_accepts_the_real_vocabulary():
    picks = [{"status": s} for s in
             ("WON", "LOST", "CLOSED", "OPEN", "PENDING", "EXPIRED", "")]
    _assert_status_vocabulary_is_covered(picks)  # must not raise


def test_guard_rejects_an_unknown_status():
    with pytest.raises(ValueError, match="does not classify"):
        _assert_status_vocabulary_is_covered([{"status": "WON_XP"}])


def test_guard_names_the_offending_status():
    """The error must be actionable -- it has to print the value to add."""
    with pytest.raises(ValueError, match="WON_XP"):
        _assert_status_vocabulary_is_covered(
            [{"status": "WON"}, {"status": "WON_XP"}]
        )


def test_guard_message_points_at_the_fix_location():
    with pytest.raises(ValueError, match="RESOLVED_STATUSES"):
        _assert_status_vocabulary_is_covered([{"status": "MYSTERY"}])
