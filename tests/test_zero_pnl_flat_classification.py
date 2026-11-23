"""A zero PnL is two different things, and the rollup must tell them apart.

`is_performance_scored_row` quarantined EVERY zero-PnL row (P0.0a, added to stop
3,645 ``EXPIRED`` placeholder rows from inflating the denominator). The side
effect was that a trade which genuinely resolved at breakeven was deleted from
the book entirely: it left ``n``, left ``mean_net_pct`` and PF, and — because the
panel publishes a ``flat`` count and defines ``win_rate_pct`` as "decided trades
(excludes flat)" — ``flat`` was structurally unreachable. A statistic that can
only ever be zero is not a measurement.

The fix is a split, not a rollback: a zero row is admitted only when it carries
an exit reason that proves it resolved. Everything else stays quarantined.

These tests are deliberately independent of the golden snapshot — they pin the
RULE, so the ratio of flat to quarantined cannot drift again silently.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from alpha_engine.resolved_closed_view import (  # noqa: E402
    build_view,
    class_rollup,
    default_exclusion_reason,
    is_performance_scored_row,
)


def _row(pnl, exit_reason="TIME_EXIT", status="CLOSED", **extra):
    row = {
        "symbol": "TEST", "asset_class": "CRYPTO", "pnl_pct": pnl,
        "direction": "LONG", "strategy": "S1", "exit_reason": exit_reason,
        "status": status, "entry_price": 100.0,
        "closed_at": "2026-11-01T00:00:00+00:00",
    }
    row.update(extra)
    return row


# ── the admitted case ────────────────────────────────────────────────────────
def test_resolved_breakeven_is_scored():
    assert is_performance_scored_row(_row(0.0, "TIME_EXIT")) is True


def test_resolved_breakeven_counts_as_flat_not_as_a_loss():
    rows = build_view(
        [_row(2.0, "TIME_EXIT"), _row(-2.0, "TIME_EXIT"), _row(0.0, "TIME_EXIT")],
        generated_at="2026-11-20T00:00:00+00:00",
        validity=is_performance_scored_row,
    )["rows"]
    roll = class_rollup(rows)["CRYPTO"]
    assert roll["n"] == 3, "a breakeven trade is part of the book"
    assert roll["flat"] == 1, "and it is a flat outcome, not a deletion"
    assert roll["wins"] == 1 and roll["losses"] == 1
    # The published definition: win rate is over DECIDED trades, so a flat row
    # must not move it — the denominator has to stay 2, not become 3.
    assert roll["win_rate_pct"] == 50.0
    # Neither may it be graded as a loss: mean net keeps the breakeven row's
    # own net (0.0 - CRYPTO cost), which is what "flat after cost" means.
    assert roll["mean_net_pct"] == round((2.0 - 2.0 + 0.0) / 3 - roll["mean_cost_bps"] / 100.0, 4)


# ── the quarantined cases (the P0.0a intent must survive) ────────────────────
def test_expired_zero_row_stays_quarantined():
    assert is_performance_scored_row(_row(0.0, "EXPIRED", status="EXPIRED")) is False


def test_zero_row_without_resolution_evidence_stays_quarantined():
    assert is_performance_scored_row(
        _row(0.0, "TIME_EXIT", status="PENDING", closed_at=None)) is False


def test_auto_expired_marker_wins_over_a_resolved_reason():
    assert is_performance_scored_row(_row(0.0, "TIME_EXIT", _auto_expired=True)) is False


def test_non_zero_rows_are_unaffected():
    assert is_performance_scored_row(_row(0.5, "TIME_EXIT")) is True
    assert is_performance_scored_row(_row(-0.5, "EXPIRED", status="EXPIRED")) is True


# ── the provenance classifier must agree with the predicate ─────────────────
def test_exclusion_reason_agrees_with_predicate_on_zero_rows():
    admitted = _row(0.0, "TIME_EXIT")
    quarantined = _row(0.0, "EXPIRED", status="EXPIRED")
    assert is_performance_scored_row(admitted) and default_exclusion_reason(admitted) is None
    assert not is_performance_scored_row(quarantined)
    assert default_exclusion_reason(quarantined) == "zero_pnl_quarantined"
