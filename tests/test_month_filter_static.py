"""
Static source-analysis tests for PR #751 month-filter fixes.

Verifies the surface-level shape of the fixes in
TORONTOEVENTS_ANTIGRAVITY/index.html so they can't be silently reverted
without a failing test. JS-runtime semantics are covered by
tests/test_month_filter.unit.test.js (node --test).

Per 5-engine 3-round swarm review (PR_751_5MODEL_3ROUND_REVIEW.md),
MERGE_AFTER_FIXES, 4/5 — must-fix item 1 (7 unit tests covering Fix
1/2/3) is satisfied jointly by this file + the JS file.

Run:  python -m pytest tests/test_month_filter_static.py -v
"""

import re
import pathlib

HTML_PATH = pathlib.Path(__file__).resolve().parents[1] / "TORONTOEVENTS_ANTIGRAVITY" / "index.html"


def _src() -> str:
    return HTML_PATH.read_text(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Fix 1 — pre-filter keeps running events
# ---------------------------------------------------------------------------

def test_pre_filter_keeps_running_event_with_past_start():
    """Fix 1: pre-filter must consider end_date so multi-day running
    events ('& Juliet' opens 2025-12-03, closes 2026-05-17) survive."""
    src = _src()
    head = src[:8000]
    has_filter = "events = events.filter(" in head
    assert has_filter, "pre-filter block missing — Fix 1 reverted"
    block = re.search(r"events\s*=\s*events\.filter\([^}]*\}\);", head, re.DOTALL)
    assert block, "pre-filter block could not be extracted"
    body = block.group(0)
    assert "end_date" in body or "endDate" in body, (
        "Fix 1 incomplete: pre-filter missing end_date/endDate consideration "
        "— would drop multi-day running events (Bug B)."
    )


def test_pre_filter_drops_event_with_past_end():
    """Fix 1: filter expression must drop events whose start AND end are
    before today. Verified by checking the OR-shaped condition."""
    src = _src()
    head = src[:8000]
    block = re.search(r"events\s*=\s*events\.filter\([^}]*\}\);", head, re.DOTALL)
    assert block, "pre-filter block missing"
    body = block.group(0)
    assert re.search(r">=\s*_today", body), "pre-filter must compare against _today"
    assert body.count(">= _today") >= 2 or body.count(">=_today") >= 2, (
        "pre-filter must check both start>=today AND end>=today (OR form); "
        "single comparison would re-introduce Bug B"
    )


# ---------------------------------------------------------------------------
# Fix 2 — shouldShow=false guard for null eventData when feed loaded
# ---------------------------------------------------------------------------

def test_show_returns_false_when_event_data_null_and_feed_loaded():
    """Fix 2: This Month branch must hide cards when eventData is null AND
    __RAW_EVENTS__ is loaded — they are year-ambiguous zombies."""
    src = _src()
    pattern = re.compile(
        r"if\s*\(\s*!\s*eventData\s*&&\s*window\.__RAW_EVENTS__\s*\)\s*\{\s*"
        r"(?:[^}]*?\n)*?[^}]*?shouldShow\s*=\s*false",
        re.DOTALL,
    )
    assert pattern.search(src), (
        "Fix 2 missing: no `if (!eventData && window.__RAW_EVENTS__) { ... "
        "shouldShow = false }` block in This Month branch."
    )


def test_show_returns_true_when_event_data_null_and_feed_not_loaded():
    """Fix 2 race-safety: when __RAW_EVENTS__ hasn't loaded yet, code must
    fall back to __parseCardDisplayedDate__ rather than blanking the grid."""
    src = _src()
    pattern = re.compile(
        r"!\s*eventData\s*&&\s*window\.__RAW_EVENTS__[^}]*?\}\s*else\s*\{[^}]*?"
        r"__parseCardDisplayedDate__",
        re.DOTALL,
    )
    assert pattern.search(src), (
        "Fix 2 race-safety: else-branch must call __parseCardDisplayedDate__ "
        "so a not-yet-loaded feed doesn't blank the grid."
    )


# ---------------------------------------------------------------------------
# Fix 3 — tightened date-pattern regex for badge-hide
# ---------------------------------------------------------------------------

# Production regex (mirrors index.html ~line 4247).
PROD_RE = re.compile(
    r"^[A-Z]{3}\s*\n?\s*\d{1,2}(\s+(?:[A-Z][a-z]+|\d{4}|,\s*\d{4}))?\s*$",
    re.IGNORECASE,
)


def _hide_predicate(text: str) -> bool:
    return bool(PROD_RE.match(text)) and len(text) <= 30


def test_label_hide_pattern_matches_MAY_8_format():
    """Fix 3: plain 'MAY 8' / 'JUN 12' / 'DEC 31' must be hidden behind
    the next-month badge overlay."""
    for label in ["MAY 8", "JUN 12", "DEC 31", "MAY 1"]:
        assert _hide_predicate(label), f"expected hide for {label!r}"


def test_label_hide_pattern_skips_long_description_text():
    """Fix 3: the tightened regex must reject arbitrary prose that the
    old length-only gate would have wrongly hidden."""
    rejects = [
        "MAY 8 is the best day for live music",
        "Ave 5 free admission tonight!",
        "Get 50% off in May",
        "A long description block with lots of words that runs past 30 chars",
    ]
    for text in rejects:
        assert not _hide_predicate(text), f"must NOT hide {text!r}"


def test_label_hide_pattern_matches_with_day_of_week_suffix():
    """Fix 3: React EventCard sometimes appends day-of-week or year —
    these must still be hidden so the JUNE badge isn't double-rendered."""
    accepts = ["MAY 8 Wednesday", "JUN 12 Friday", "MAY 8 2026"]
    for text in accepts:
        assert _hide_predicate(text), f"expected hide for {text!r}"


def test_fix_3_regex_is_anchored_in_source():
    """Sanity check: the tightened (anchored) regex is in the file."""
    src = _src()
    idx = src.find("data-nm-orig-visibility")
    assert idx > 0, "could not locate the badge-hide block"
    block = src[max(0, idx - 1200):idx]
    assert "[A-Z]{3}" in block, "badge-hide regex missing month-abbrev anchor"
    assert "$/i" in block or "?\\s*$" in block, (
        "badge-hide regex must be anchored to end-of-string to avoid prose "
        "false-positives (PR #751 swarm review must-fix)"
    )
