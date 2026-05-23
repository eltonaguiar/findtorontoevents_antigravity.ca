"""Static-grep regression tests for the Tier-2 hero-cards XSS hardening.

Cross-AI PR review (2026-04-28) flagged the original `renderTier2Heroes` /
`showTier2Detail` JS path in `audit_dashboard/template.html` as a recurring
XSS class — string-concat HTML built from `c.name`, `c.tier_reason`, etc.,
plus an inline `onclick="showTier2Detail('${c.name}')"` handler that breaks
on a single-quote in the strategy name.

This file pins the fix with five static checks:
 1. No raw `'+ c.name +'` interpolation pattern survives in the file.
 2. The inline `onclick="showTier2Detail('` handler is gone (event delegation only).
 3. The `_tier2EscapeHtml` helper is defined.
 4. The helper is referenced near the tier-2 render functions.
 5. The event-delegation listener (`grid._tier2DelegationWired`) exists.

These are deliberately Python static-grep tests, not Playwright/JSDOM, because:
 - The peer-cron branch-flip in this repo means JS-runtime tests get
   hard to keep stable in CI; plain text assertions on template.html
   are robust against branch churn.
 - The CLAUDE.md `feedback_js_validation.md` rule is a recurring-class
   bug; a grep tripwire is the cheapest reliable detector.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = REPO_ROOT / "audit_dashboard" / "template.html"


@pytest.fixture(scope="module")
def template_text() -> str:
    assert TEMPLATE.exists(), f"template.html not found at {TEMPLATE}"
    return TEMPLATE.read_text(encoding="utf-8", errors="replace")


def test_no_raw_c_name_interpolation(template_text: str) -> None:
    """No raw `'+ c.name +'` (string-concat into HTML) inside renderTier2Heroes.

    The fix replaces every such interpolation with `'+ nameEsc +'` where
    `nameEsc = _tier2EscapeHtml(c.name)`. This regex covers both spaced
    and unspaced variants in a single line.
    """
    raw_patterns = [
        r"'\s*\+\s*c\.name\s*\+\s*'",
        r"'\s*\+\s*c\.tier\s*\+\s*'",
        r"'\s*\+\s*c\.tier_reason\s*\+\s*'",
        r"'\s*\+\s*\(c\.tier_reason\s*\|\|\s*''\)\s*\+\s*'",
    ]
    offenders = []
    for pat in raw_patterns:
        for m in re.finditer(pat, template_text):
            # Confirm we're inside the tier2 render block (rough heuristic by line).
            line_start = template_text.rfind("\n", 0, m.start()) + 1
            line_end = template_text.find("\n", m.end())
            line = template_text[line_start:line_end]
            offenders.append((pat, line.strip()))
    assert not offenders, (
        "Raw c.* string-concat interpolation found — must use _tier2EscapeHtml. "
        f"Offenders: {offenders}"
    )


def test_no_inline_onclick_show_tier2_detail(template_text: str) -> None:
    """Inline onclick="showTier2Detail('...')" handler is gone (replaced by delegation).

    Comment-only references (e.g. a `// the old onclick="..." pattern` note)
    are allowed — those don't reach HTML output. We strip JS comment lines
    before scanning.
    """
    needle = 'onclick="showTier2Detail(\''
    offending_lines = []
    for i, line in enumerate(template_text.splitlines(), start=1):
        if needle not in line:
            continue
        stripped = line.lstrip()
        if stripped.startswith("//") or stripped.startswith("*"):
            continue
        offending_lines.append((i, line.strip()))
    assert not offending_lines, (
        "Inline onclick='showTier2Detail(...)' (in non-comment code) is "
        "XSS-vulnerable to single-quote in strategy names; must be replaced "
        f"by data-tier2-detail + delegation. Offenders: {offending_lines}"
    )


def test_escape_helper_defined_and_used(template_text: str) -> None:
    """`_tier2EscapeHtml` is defined and referenced from tier2 render functions."""
    # 1. Helper is defined.
    assert "function _tier2EscapeHtml(" in template_text, (
        "_tier2EscapeHtml helper is missing — tier2 render functions need it."
    )
    # 2. Helper escapes the canonical XSS chars.
    helper_start = template_text.find("function _tier2EscapeHtml(")
    helper_end = template_text.find("\n}", helper_start)
    helper_block = template_text[helper_start:helper_end]
    for char in ["&amp;", "&lt;", "&gt;", "&quot;", "&#39;"]:
        assert char in helper_block, f"_tier2EscapeHtml missing escape for {char!r}"

    # 3. Helper is called from tier2 render code (multiple call sites).
    call_count = template_text.count("_tier2EscapeHtml(")
    # Definition counts as 1; we expect helper plus several call sites.
    assert call_count >= 6, (
        f"_tier2EscapeHtml only appears {call_count} times — expected >=6 "
        "(definition + ≥5 call sites in renderTier2Heroes / showTier2Detail / "
        "_tier2RecentPicksHtml / flagged-dropouts)."
    )


def test_event_delegation_wired(template_text: str) -> None:
    """The data-tier2-detail click delegation listener exists, with idempotency guard."""
    assert "data-tier2-detail" in template_text, "data-tier2-detail attr missing"
    assert "_tier2DelegationWired" in template_text, (
        "Event-delegation idempotency flag _tier2DelegationWired is missing."
    )
    assert "addEventListener('click'" in template_text or 'addEventListener("click"' in template_text


def test_recent_picks_symbol_direction_escaped(template_text: str) -> None:
    """`_tier2RecentPicksHtml` escapes p.symbol and p.direction."""
    fn_start = template_text.find("function _tier2RecentPicksHtml(")
    assert fn_start >= 0, "_tier2RecentPicksHtml function missing"
    fn_end = template_text.find("\n}", fn_start)
    fn_block = template_text[fn_start:fn_end]
    # symbol/direction must flow through _tier2EscapeHtml.
    assert "_tier2EscapeHtml(p.symbol" in fn_block, (
        "p.symbol must be escaped via _tier2EscapeHtml in _tier2RecentPicksHtml."
    )
    assert "_tier2EscapeHtml(p.direction" in fn_block, (
        "p.direction must be escaped via _tier2EscapeHtml in _tier2RecentPicksHtml."
    )
