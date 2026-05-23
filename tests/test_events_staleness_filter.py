"""Smoke test for the past-dated event staleness filter in
TORONTOEVENTS_ANTIGRAVITY/index.html.

Per CLAUDE.md Goal #3 ("zero stale events on the page") and the 4-AI panel
unanimous P0 verdict in reports/findings_validation_synthesis_2026_04_29.md
(Finding 8): 3,625 past-dated events still tagged status=UPCOMING were
inflating the events grid as of 2026-04-29.

ARCHITECTURE NOTE (2026-05-04 hotfix, reports/kimi_filter_bug_2026_05_04/):
The original fix lived at the fetch-interceptor (Path A - frontend filter
on the inbound events array). That filter created an asymmetry: React's
EventFeed renders the FULL unfiltered set, but __RAW_EVENTS__ was a subset,
so cards for past-dated events had eventData=null at applyFilters() time
and silently survived the past-events gate via __parseCardDisplayedDate__
year-ambiguous fallback. The 2026-05-04 hotfix moved the past-event drop
into applyFilters() (line ~3595), where eventData is now reliably looked
up against the full __RAW_EVENTS__ map. This test is a regression guard
for the post-hotfix architecture: the past-events filter must live in
applyFilters and run after the __RAW_EVENTS__ assignment.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX_HTML = ROOT / "TORONTOEVENTS_ANTIGRAVITY" / "index.html"


def _read_html() -> str:
    assert INDEX_HTML.exists(), f"missing: {INDEX_HTML}"
    return INDEX_HTML.read_text(encoding="utf-8", errors="replace")


def test_staleness_filter_sentinel_comment_present():
    """The applyFilters past-events gate must carry a grep-friendly
    sentinel so reviewers/audits can find it."""
    html = _read_html()
    assert "Past events filter" in html, (
        "Past-events filter sentinel comment missing from index.html "
        "applyFilters block. See "
        "reports/kimi_filter_bug_2026_05_04/FINDINGS.md (Bug A)."
    )


def test_staleness_filter_uses_today_iso_slice():
    """Filter must compute today as YYYY-MM-DD and compare via the
    canonical 10-char prefix slice. Post 2026-05-04 hotfix the filter
    uses substring(0, 10) on event date strings against a __todayStart
    Date object (more timezone-robust than the previous toISOString slice
    which produced UTC-day, dropping local-evening events early)."""
    html = _read_html()
    assert "substring(0, 10)" in html, (
        "Filter must compute YYYY-MM-DD via substring(0, 10) on event "
        "date strings (post 2026-05-04 hotfix)."
    )
    assert "__todayStart" in html, (
        "Filter must use __todayStart local-Date for today comparison "
        "(timezone-correct, see filter_bug_investigation_2026_05_03.md)."
    )


def test_staleness_filter_handles_multiple_date_fields():
    """Filter must check eventData.date and end_date/endDate to cover
    multi-day events. Post 2026-05-04 hotfix the past-events gate runs
    in applyFilters and reads eventData.* (looked up via __RAW_EVENTS__)
    instead of the inbound event.* shape that the old fetch-interceptor
    filter used."""
    html = _read_html()
    assert "eventData.date" in html, "filter must read eventData.date"
    assert "eventData.end_date" in html, (
        "filter must read eventData.end_date (snake_case) for multi-day events"
    )
    assert "eventData.endDate" in html, (
        "filter must read eventData.endDate (camelCase) for multi-day events"
    )


def test_staleness_filter_runs_before_raw_events_assignment():
    """Post 2026-05-04 hotfix: the past-events filter lives in
    applyFilters (NOT the fetch-interceptor) and runs against eventData
    looked up via the full __RAW_EVENTS__ map. The two components must
    coexist in this order in the source file:
      1. window.__RAW_EVENTS__ = events; (the assignment, near top)
      2. The applyFilters past-events gate (which reads eventData)
    so that by the time applyFilters runs, __RAW_EVENTS__ is populated
    and eventData lookups succeed (Bug A in
    reports/kimi_filter_bug_2026_05_04/FINDINGS.md)."""
    html = _read_html()
    assign_idx = html.find("window.__RAW_EVENTS__ = events;")
    assert assign_idx != -1, "missing window.__RAW_EVENTS__ assignment"
    sentinel_idx = html.find("Past events filter", assign_idx)
    assert sentinel_idx != -1, (
        "Past-events filter must appear after the __RAW_EVENTS__ assignment"
    )
    assert sentinel_idx > assign_idx, (
        "__RAW_EVENTS__ assignment must precede the applyFilters past-events gate"
    )
