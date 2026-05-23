"""Regression test for round 3 panel finding (5/5 consensus):

PR #497's phantom-HALT fix sums ``unrealized_pnl_pct`` from open-status
rows but does NOT normalize units. Some sources store ``pnl_pct`` /
``unrealized_pnl_pct`` as decimal (0.012 = 1.2%); others as percent
(1.2 = 1.2%). When summed naively, mixed-unit HALT triggers can:
  - Under-trigger (sum stays in decimal range when reality is a real
    portfolio drawdown, so the alert never fires)
  - Over-trigger (sum crosses threshold sooner than reality, producing
    a phantom HALT)

This test demonstrates the bug. It is MARKED XFAIL because the fix is
larger scope (P0-DATA ``pnl_pct`` unit normalization at ingest, per
``reports/round3_bugs_qa_synthesis_2026_04_29.md`` P0 item #3 and #5).

References:
- ``reports/round3_bugs_qa_synthesis_2026_04_29.md`` (5/5 panel consensus)
- ``reports/round3_bugs_qa_briefing_2026_04_29.md`` (Finding F2)
- PR #497 (b546feb1b6): the partial fix this test layers on top of
- ``cross_aggregation/performance_alerts.py::_daily_loss``: the
  un-normalized summation site
"""

import pytest

from cross_aggregation.performance_alerts import _daily_loss


@pytest.mark.xfail(
    reason=(
        "P0-DATA scope: pnl_pct unit normalization at ingest required first. "
        "Round 3 panel 5/5 consensus, "
        "reports/round3_bugs_qa_synthesis_2026_04_29.md (P0 items #3 and #5)."
    ),
    strict=True,
)
def test_phantom_halt_with_mixed_pnl_units_under_triggers():
    """Reproducing the panel's documented under-trigger bug.

    Six open-status picks: 3 store ``unrealized_pnl_pct`` as decimal,
    3 as percent. All represent -10% drawdowns (so true portfolio total
    in canonical % units is -60%, well past the -5% CRITICAL HALT
    threshold in ``_daily_loss``).

    Naive sum (what PR #497 does today):
        -0.10 * 3  +  -10.0 * 3  =  -0.30 + -30.0  =  -30.30

    The numeric value -30.30 IS less than -5, so a CRITICAL HALT does
    fire — but the message reads ``-30.3%`` when the canonical-unit
    portfolio loss is actually ``-60%``. That is a 2x mis-statement of
    severity in the alert payload, AND the unit-mixed sum is meaningless
    even when it happens to cross the threshold (could equally be
    -3.30 in another scenario where it would NOT fire).

    A correct (post-P0-DATA) implementation would normalize each row
    to one canonical unit (decimal or percent, consistently) before
    summing, so the reported total reflects reality.

    The XFAIL assertion below pins the canonical-unit total: when unit
    normalization lands, the summed total must equal -60.0% (within
    floating-point tolerance), not -30.30.
    """
    mixed_picks = [
        # Decimal-format (e.g., multi_asset_copytrader convention):
        # unrealized_pnl_pct stored as a fraction (-0.10 == -10%).
        {"id": "p1", "status": "OPEN", "unrealized_pnl_pct": -0.10},
        {"id": "p2", "status": "OPEN", "unrealized_pnl_pct": -0.10},
        {"id": "p3", "status": "OPEN", "unrealized_pnl_pct": -0.10},
        # Percent-format (e.g., stocks_competition convention):
        # unrealized_pnl_pct stored as a percent (-10.0 == -10%).
        {"id": "p4", "status": "OPEN", "unrealized_pnl_pct": -10.0},
        {"id": "p5", "status": "OPEN", "unrealized_pnl_pct": -10.0},
        {"id": "p6", "status": "OPEN", "unrealized_pnl_pct": -10.0},
    ]

    alerts = _daily_loss(mixed_picks)
    assert alerts, "Expected at least one DAILY_LOSS alert from the -60% portfolio"

    halt_alerts = [a for a in alerts if a["action"] == "HALT"]
    assert halt_alerts, "Mixed-unit -60% portfolio must produce a HALT"

    reported_total = halt_alerts[0]["details"]["total_unrealized_pnl_pct"]

    # Canonical-unit truth: every pick is a -10% loss; portfolio sum = -60%.
    # Pre-fix, reported_total is the raw mixed-unit sum (-30.3), which is
    # roughly half of reality. This assertion FAILS today (XFAIL passes)
    # and will PASS once unit-normalization lands.
    assert reported_total == pytest.approx(-60.0, abs=0.01), (
        "Phantom-HALT severity is mis-stated when pnl_pct units are mixed: "
        f"reported {reported_total}% vs reality -60.0%. The naive sum "
        "(-0.30 + -30.0 = -30.3) interprets decimal rows as if they were "
        "already percent-scaled. Round 3 panel 5/5 consensus -> bundle "
        "with P0-DATA pnl_pct unit normalization at ingest."
    )
