"""Guard the /audit truth-claims against silent reversion by a template rebuild.

2026-11-16: the major-goal footer's "DB health GREEN: ghost rows 0" was reworded in
#828 (`a154912f8c4c`), then a later template rebuild (`3ce350d60ab5`, PM/theory
wiring) re-introduced the reverted copy while live `db_health.json` still reported
22,947 quarantined rows. The header simultaneously claimed "0/6 money-ready" and
"EQUITY 60% PF2.13 n=72" while the live ledger said 10 classes and EQUITY PF 0.94.

These assertions make that class of regression loud instead of silent. They are
static (no network): they encode invariants that must survive any rebuild.
"""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "audit_dashboard" / "template.html"
FRESHNESS = ROOT / "audit_dashboard" / "dashboard_freshness.js"


needs_template = pytest.mark.skipif(
    not TEMPLATE.exists(), reason="audit template not present in this checkout"
)


@needs_template
def test_no_hardcoded_zero_ghost_rows_claim():
    """`ok: true` on the ghost_rows check does NOT mean zero rows — it means the
    harness tolerated them. A rebuild must not restore the flat 'ghost rows 0'."""
    html = TEMPLATE.read_text(encoding="utf-8")
    assert "DB health GREEN: ghost rows 0" not in html
    assert "quarantined" in html.lower(), "the quarantine-not-delete wording must survive"


@needs_template
def test_no_zero_of_six_money_ready_claim():
    """money_ready_verdict.json exposes 10 classes, not 6."""
    html = TEMPLATE.read_text(encoding="utf-8")
    assert "0/6 money-ready" not in html


@needs_template
def test_static_per_class_snapshot_is_labelled_not_live():
    """JS pushes the dated static spans into a <details> the user can open, so the
    snapshot must be labelled with its vintage or it reads as current."""
    html = TEMPLATE.read_text(encoding="utf-8")
    assert "Forensic snapshot (static HTML, 2026-05/06" in html, (
        "the static per-class spans are 2026-05/06 vintage; label them so they are "
        "not mistaken for live figures"
    )


@needs_template
def test_major_goal_header_declares_its_snapshot_date():
    html = TEMPLATE.read_text(encoding="utf-8")
    assert "snapshot 2026-11-16" in html, (
        "the static intrabar sentence must declare the date it was measured"
    )


@pytest.mark.skipif(not FRESHNESS.exists(), reason="freshness script not present")
def test_freshness_banner_counts_missing_sources():
    """A source that fails to load has timestamp: null and used to be excluded from
    the verdict, so the panel could print 'ALL SOURCES CURRENT' over 'No data'."""
    js = FRESHNESS.read_text(encoding="utf-8")
    assert "hasMissing" in js
    assert "SOURCE NOT LOADING" in js
