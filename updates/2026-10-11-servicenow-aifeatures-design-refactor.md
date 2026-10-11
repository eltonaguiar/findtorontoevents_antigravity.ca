# ServiceNow AI Features Page — Design Refactor

**Date:** 2026-10-11
**Target file:** `TORONTOEVENTS_ANTIGRAVITY/servicenow/AIFeaturesOct2026/index.html`
**Live URL:** https://findtorontoevents.ca/servicenow/AIFeaturesOct2026/index.html
**Type:** Formatting / visual refactor — no content changes

---

## 1. What Was Broken

### User-facing complaints
The page "looked boring" and was "too AI of a page," with a "boring and odd purple" background.

### Actual defects found in the code (fixed)

1. **Broken CSS rule #1** — `index.html:133` had a stray backslash after the declaration:
   `border-left: 3px solid var(--pk-400);\`
   This silently killed the entire `.callout` rule, so no callout box was ever styled.

2. **Broken CSS rule #2** — `index.html:147` had `}` followed by a stray backslash, killing the `footer a` link rule.

3. **Malformed HTML** — `index.html:740` had a stray `<li>` wrapped around a `<td>` inside a table row:
   `<li><td>Skill/agent development</td>...`
   The RACI table's second row was malformed markup.

4. **Table of contents was incomplete and out of order** — listed 10 entries while the page has 13 sections. Missing `#nask-practical`, `#production-readiness`, and `#servicenow-resources` entirely. Additionally, `#core-features` was listed in position 2 but actually renders 7th, and `#extended-features` was listed 9th but actually renders 12th — so the numbered list misrepresented reading order.

5. **Wide tables crushed on mobile** — the RACI table has 10 columns and seven other tables have 5. At mobile widths they were simply squashed with no horizontal scroll affordance, making content unreadable.

6. **Off-brand palette** — the page is about ServiceNow but used purple (`#9333ea`, `#a855f7`, `#c084fc`). ServiceNow's brand is green/teal and contains no purple at all.

---

## 2. Design Direction

**Reference: ServiceNow's own brand identity.** Not an invented palette.

| Token | Hex | Source / role |
|---|---|---|
| Pastel Green | `#62D84E` | Signature accent, CTAs, links |
| Blue Whale | `#032D42` | Deep ink base — panels, table heads |
| Dark Green | `#293E40` | Secondary ink |
| Sage | `#81B5A1` | Secondary text, muted accents |

This was a deliberate choice. The obvious move — swapping the purple aurora for a purple/blue aurora — is the generic AI-template look, and the current purple already reads as off-brand. Grounding the palette in the subject's actual brand fixes a real inconsistency instead of adding decoration.

**Techniques applied** (from current front-end practice):
- Dark-first base with elevation via lightness steps rather than drop shadows
- CSS-only aurora background — four drifting radial blooms over the ink base, heavily blurred. No canvas, no WebGL, zero JS.
- Film-grain overlay via inline SVG turbulence data-URI, to stop the gradient reading as flat.
- Glassmorphism surfaces (`backdrop-filter`) for panels, cards, and tables.
- Native scroll-driven animation (`animation-timeline: scroll()`) for the reading-progress bar — no scroll listeners, no JS.
- `prefers-reduced-motion` guards on every ambient animation.

---

## 3. Changes Made

### Stylesheet — fully replaced
New token scale, ink layers, brand accents, and status colors. Every class used by the body was preserved: `kicker, subtitle, meta, actions, btn, btn.ghost, disclaimer-banner, illustrative, example-box, audience-tag, risk-tier (+low/medium/high/critical), servicenow-links, sn-link, checklist, raci-table, raci-cell, toc, course-card (+title/type/duration/reason/actions), stats, pill, findings, grid-2, figure`. These were verified against a full inventory of classes used in the document.

### Background layers added to `<body>`
```html
<div class="bg-aurora" aria-hidden="true"></div>
<div class="bg-grain" aria-hidden="true"></div>
<div class="scroll-progress" aria-hidden="true"></div>
```

### Bug fixes
- Both stray backslashes removed (fixes `.callout` and `footer a`).
- Stray `<li>` removed from the RACI row — now a valid `<tr>`.
- TOC rebuilt with all 13 sections in true DOM order.
- All 18 tables wrapped in `<div class="table-wrap">` for horizontal scrolling on narrow viewports.

### Typography / layout
- System font stack with tightened letter-spacing on headings.
- `scroll-padding-top` so anchor jumps don't hide headings under the viewport edge.
- Sticky table headers, zebra striping, tabular numerals on numeric cells.
- Collapsible `example-box` given a proper `▸/▾` disclosure marker.
- Mobile breakpoints adjusted at 760px and 600px.

---

## 4. Verification

All checks run against the rendered page in headless Chromium.

| Check | Result |
|---|---|
| HTML tag balance (div, table, thead, tbody, tr, td, th, ul, ol, li, section, details, summary, pre, span, code, a, p, strong, em) | **All balanced** |
| Anchor links resolve | 13 links / 13 ids — **no broken anchors** |
| Section count | 13 — matches original |
| Content preservation (word-level diff vs. pre-refactor backup) | 6098 → 6098 words — **zero content lost** |
| Purple token residue | **None** |
| Aurora animation active | `aurora-drift`, `blur(68px) saturate(1.3)` confirmed |
| Scroll-progress bar math | 0 at top, 0.443 at 44.3% scroll, 1.0 at bottom — correct |
| `prefers-reduced-motion` | Aurora animation resolves to `none` |
| Desktop horizontal overflow (1440px) | None — scrollWidth 1440 = clientWidth 1440 |
| Mobile horizontal overflow (390px) | None — scrollWidth 390 = clientWidth 390 |
| Wide table scrolls in own container at 390px | Yes — 750px content inside a 355px viewport |
| JS / console errors | None |
| "Back to events" button wrapping | Fixed — 46px tall, single line |

### Two issues found and fixed during verification
- **Sticky TOC regression.** The initial build made the TOC `position: sticky`. Rendered, it consumed 67% of a 950px viewport, making it impossible to read the page. Reverted to static — the TOC sits at the top of the page as a normal element and scrolls away.
- **Button text wrap.** "Back to events" wrapped onto two lines on mobile. Fixed with `white-space: nowrap`.

---

## 5. Files

| File | Purpose |
|---|---|
| `TORONTOEVENTS_ANTIGRAVITY/servicenow/AIFeaturesOct2026/index.html` | The refactor |
| `updates/2026-10-11-servicenow-aifeatures-design-refactor.md` | This document |
| `updates/2026-10-11-servicenow-aifeatures-design-refactor-PLAN.md` | Pre-work plan and research notes |

---

## 6. Note for Follow-Up

The page states (line ~478) tier Assist allocations as approximate figures — "Foundation: ~500/mo/user; Advanced: ~2,000/mo/user; Prime: ~5,000+/mo/user" — while line ~276 says the *previous* illustrative ranges "have been removed." This is an internal inconsistency about stated allowances. Left as-is since it is a content/policy question rather than a formatting one, and changing it would alter a claim on a page that carries a strong verify-before-deciding disclaimer. Flagging for the page owner to resolve.
