# Dimension 09: HTML Bug & Technical Issues Analysis

## Executive Summary

The "weird text" reported by the user in the US Equity Picks tab is caused by a **nested HTML comment bug** in `audit_dashboard/template.html`. An HTML comment block (lines ~1813-1825) contains an unescaped `-->` sequence inside a code-formatted string (`` `<\!-- ... -->` ``). The HTML parser interprets this inner `-->` as the comment terminator, causing the remainder of the comment text to leak out as **visible rendered text** on the page.

---

## Primary Bug: Nested HTML Comment in UEPS Section

### Bug Location
- **Repository**: `eltonaguiar/findtorontoevents_antigravity.ca`
- **File**: `audit_dashboard/template.html`
- **Lines**: ~1813-1825 (in the UEPS / US Equity Picks section)
- **Affected Tab**: **US Equity Picks (UEPS)** — data-tab="ueps"

### Bug Type
Nested HTML comment with premature comment terminator

### Current Code (Problematic)

```html
  <!--
    Mount point — populated server-side by audit_trail/dashboard_generator.py
    at HTML build time, via audit_dashboard.ueps_section_renderer
    .render_ueps_section() fed by alpha_engine/data/active_picks.json filtered
    to pick_type in {long_term_value, swing}. The marker placeholder below
    (UEPS_SECTION_HTML_PLACEHOLDER) is replaced server-side; the surrounding
    "Building n=0/100" placeholder remains visible if the marker is not
    substituted. The client-side IIFE further down ALSO fetches
    audit_dashboard/data/ueps_picks.json as a refresh path; both layers
    co-exist by design.
    Note: do NOT nest `<\!-- ... -->` inside this block — HTML does not
    support nested comments and the inner `-->` would close the outer.
  -->
```

### Root Cause Analysis

HTML comments are delimited by `<!--` (open) and `-->` (close). HTML does NOT support nested comments. The parser scans for the **first** occurrence of `-->` after `<!--` and treats it as the comment end, regardless of context (inside backticks, code blocks, or quoted strings).

In this bug, the comment contains the text:
```
`<\!-- ... -->`
```

The HTML parser processes this as:
1. `<!--` at line 1813 — **opens** the comment
2. All text is consumed as comment content
3. `-->` inside `` `<\!-- ... -->` `` at line 1824 — **PREMATURELY CLOSES** the comment!
4. Everything after that `-->` becomes **VISIBLE TEXT** on the page

### Leaked Visible Text

The text that leaks out and renders visibly is:

```
` inside this block — HTML does not
    support nested comments and the inner `-->` would close the outer.
  -->
```

This exactly matches the user's reported "weird text":
> "` inside this block — HTML does not support nested comments and the inner `-->` would close the outer. -->"

### Fix

**Option A: Remove the comment entirely** (Recommended — cleanest fix)

```html
  <!-- Mount point for UEPS section -->
  <div id="ueps-section-mount">
```

**Option B: Replace `-->` with HTML entity or alternative text**

```html
  <!--
    Mount point populated server-side by audit_trail/dashboard_generator.py
    via audit_dashboard.ueps_section_renderer.render_ueps_section().
    Client-side IIFE also fetches audit_dashboard/data/ueps_picks.json.
    Note: do NOT nest comment tags inside this block.
  -->
```

**Option C: Use -- (double dash) workaround**

Replace `-->` with `-- >` (space between -- and >) in the comment text:
```html
  <!--
    ... the inner `-- -- >` would close the outer.
  -->
```

### Why Option A is Best
This is an internal developer comment (describing server-side rendering architecture) that has no value for end users. It was already meant as a warning about the exact bug it causes. Removing it entirely eliminates the problem with zero risk of recurrence.

---

## Secondary Findings: Other HTML/JS Issues

### Finding 1: Large HTML Comment at Lines 1726-1732 (Safe — Not a Bug)

```html
<!-- ──────────────────────────────────────────────────────────────────────
     UEPS — US Equity Prediction System (long-term value + swing) tab
     Added 2026-04-28 alongside the UEPS module build (commit 1c95eec9f0).
     ...
     ────────────────────────────────────────────────────────────────────── -->
```

**Status: NOT A BUG** — This comment is properly formed. The `-->` at line 1732 correctly closes the `<!--` at line 1726. The decorative line of dashes does not contain `-->` anywhere, so it does not prematurely terminate the comment.

### Finding 2: Script Tag Balance

| Metric | Count | Status |
|--------|-------|--------|
| `<script>` (open) | 11 | OK |
| `</script>` (close) | 11 | OK |

**Status: BALANCED** — All script tags are properly closed.

### Finding 3: Duplicate ID Check

All HTML element IDs are unique. No duplicate IDs detected.

### Finding 4: HTML Entity Escaping

HTML special characters are properly escaped throughout:
- `&lt;` for `<`
- `&gt;` for `>`
- `&mdash;` for em-dash
- `&ndash;` for en-dash
- `&middot;` for middle dot
- `&ge;` for ≥
- `&le;` for ≤

**Status: PROPERLY ESCAPED**

### Finding 5: Console Logging (Minor — Non-Critical)

The JavaScript contains `console.log` and `console.warn` statements (15+ occurrences). These are appropriate for debugging but should be removed or gated in production:

```javascript
// Line ~2010
.catch(function (err) { console.warn('ueps_picks.json fetch failed:', err); });

// Line ~2213
console.log('[sports-filter] dropped ' + filtered + ' SPORTS picks at data load');

// Line ~2600
console.log('[Audit] Using external data (' + _extActive + ' active picks...');
```

**Impact**: Very low. These are useful for debugging but expose internal architecture details.
**Fix**: Wrap in a debug flag or remove in production builds.

### Finding 6: Meta Refresh Tag

```html
<meta http-equiv="refresh" content="300">
```

The page auto-refreshes every 5 minutes. This is intentional but can be disruptive during active analysis. Consider making this configurable or longer.

### Finding 7: Empty Tab Content

```html
<div id="tab-mlhealth" class="tab-content"></div>
```

The ML Health tab (`#tab-mlhealth`) has no content. This may be intentional (content loaded dynamically) but should be verified.

---

## Tab-by-Tab HTML Health Status

| Tab | Status | Notes |
|-----|--------|-------|
| Overview | Clean | No issues detected |
| Active Picks | Clean | No issues detected |
| Verified Alpha | Clean | No issues detected |
| Smart Picks | Clean | No issues detected |
| **US Equity Picks** | **BUG** | Nested comment causes text leak |
| Closed Picks | Clean | No issues detected |
| Portfolios | Clean | No issues detected |
| Dashboards | Clean | No issues detected |
| Strat. Leaderboard | Clean | No issues detected |
| Permutations | Clean | No issues detected |
| Performance | Clean | No issues detected |
| Score Tracker | Clean | No issues detected |
| ML Health | Empty | Tab content container is empty |
| Links | Clean | No issues detected |

---

## Fix Instructions

### Immediate Fix (Primary Bug)

Edit `audit_dashboard/template.html`, find the UEPS comment block (~lines 1813-1825) and replace it:

**BEFORE:**
```html
  <!--
    Mount point — populated server-side by audit_trail/dashboard_generator.py
    at HTML build time, via audit_dashboard.ueps_section_renderer
    .render_ueps_section() fed by alpha_engine/data/active_picks.json filtered
    to pick_type in {long_term_value, swing}. The marker placeholder below
    (UEPS_SECTION_HTML_PLACEHOLDER) is replaced server-side; the surrounding
    "Building n=0/100" placeholder remains visible if the marker is not
    substituted. The client-side IIFE further down ALSO fetches
    audit_dashboard/data/ueps_picks.json as a refresh path; both layers
    co-exist by design.
    Note: do NOT nest `<\!-- ... -->` inside this block — HTML does not
    support nested comments and the inner `-->` would close the outer.
  -->
```

**AFTER:**
```html
  <!-- UEPS mount point -->
```

### Preventive Measures

1. **Add an HTML comment linter** to the CI pipeline (e.g., `htmlhint` or custom grep check) to catch comments containing `-->`
2. **Document** in the project's coding standards that HTML comments must not contain `-->` sequences
3. **Prefer short comments** over multi-line essay comments that increase the risk of this bug

---

## Summary

| Item | Details |
|------|---------|
| **Primary Bug** | Nested HTML comment with premature `-->` terminator |
| **File** | `audit_dashboard/template.html` |
| **Lines** | ~1813-1825 |
| **Affected Tab** | US Equity Picks (UEPS) |
| **Root Cause** | HTML parser treats `-->` inside `` `<\!-- ... -->` `` as comment end |
| **Visible Effect** | Comment text leaks as rendered text on the page |
| **Fix** | Replace multi-line comment with single-line `<!-- UEPS mount point -->` |
| **Severity** | Medium — affects user experience on one tab |
| **Other Issues** | Minor: console.log statements, empty ML Health tab |
| **Overall HTML Health** | Good — one bug, otherwise well-structured |
