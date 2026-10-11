# ServiceNow AI Features Page — Design Refactor Plan

**Target file:** `TORONTOEVENTS_ANTIGRAVITY/servicenow/AIFeaturesOct2026/index.html` (957 lines)
**Live URL:** https://findtorontoevents.ca/servicenow/AIFeaturesOct2026/index.html
**Date:** 2026-10-11

---

## 1. User Request

The page "looks boring" and is "too AI of a page." Asked to:
1. Research best ways to make a professional, even fun, top-notch site.
2. Refactor the site formatting.
3. Replace the "dynamic beautiful background" to get rid of the "boring and odd purple."

---

## 2. Research Findings

Searched current (2026) design practice. The patterns that actually hold up:

- **Dark-first is the default**, not the inverse of light. Elevation comes from lightness steps, not drop shadows. Near-black bases (`#050505`/`#0a0a0f`) read richer than pure black.
- **Aurora / mesh-gradient backgrounds** — layered radial gradients over a dark base, blurred, with slow drift. CSS-only versions ship with no JS and no perf cost. The mandatory conditions: dark base is required (aurora over light backgrounds dies), and contrast must be guarded because moving gradient bands can push on-gradient text below WCAG AA.
- **Glassmorphism for surfaces** — semi-transparent panels + `backdrop-filter: blur()`. Keeps content legible while letting the background breathe.
- **Scroll-driven animation** is now native CSS (`animation-timeline: scroll()`), no scroll listeners needed.
- **Accessibility is non-negotiable** — `prefers-reduced-motion` guards on every ambient animation.
- **Typography does the heavy lifting** — hierarchy and rhythm matter more than ornament.

### Deliberate design constraint

`SOUL.md` lists "AI slop: blue-purple gradients" as a disgust. The user independently flagged the current purple as "boring and odd." So the obvious move (swap purple aurora in) is the *wrong* move. The palette has to be earned from a real reference.

**Reference chosen: ServiceNow's own brand**, which is green/teal and has no business being purple:

| Token | Hex | Role |
|---|---|---|
| Pastel Green | `#62D84E` | Signature accent, CTAs, links |
| Blue Whale | `#032D42` | Deep ink base — panels, table heads |
| Dark Green | `#293E40` | Secondary ink |
| Sage | `#81B5A1` | Secondary text / muted accents |

This is on-brand, it is not the blue-purple gradient cliché, and it fixes an actual inconsistency: the page is *about* ServiceNow while wearing a color ServiceNow does not use.

---

## 3. Bugs Found in the Current File

These are real defects, not style nits — they get fixed as part of the pass:

1. **`index.html:133`** — stray backslash after `border-left: 3px solid var(--pk-400);\` breaks the `.callout` rule.
2. **`index.html:147`** — stray backslash `}\` breaks the `footer a` rule.
3. **`index.html:740`** — `<li>` wrapped around a `<td>` inside the RACI `<tr>` ("Skill/agent development" row). Malformed markup.
4. **TOC is incomplete** — lists 10 sections, page has 13. Missing: `#nask-practical`, `#production-readiness`, `#servicenow-resources`. Also missing: `#core-features` and `#extended-features` are listed but sit *after* the setup guides in the DOM order, so the numbered list misrepresents reading order.
5. **Assist allocation numbers removed from one paragraph but still present in a table** (`Foundation: ~500/mo/user`, line 478) — internal inconsistency about stated allowances.

---

## 4. Implementation Plan

### Design system rewrite (CSS)
- Replace the purple token block with the ServiceNow green/teal scale.
- Real dark-base layering: `#05090c` → `#0a1218` → ink panels at `#032D42`.
- **Animated aurora background**, CSS-only: 4 radial blooms in brand green / sage / teal over the ink base, heavily blurred, slow drift. No canvas, no JS.
- Film-grain overlay via inline SVG turbulence data-URI. Kills the flat-gradient look and adds texture.
- Glass surfaces for panels, cards, TOC.
- Scroll-progress bar using native `animation-timeline: scroll()`.
- `prefers-reduced-motion: reduce` guard on all ambient motion.

### Layout / formatting
- Sticky glass TOC with a live active-section indicator.
- Wide-table handling: horizontal scroll containers so the 8-column RACI table doesn't crush on mobile (currently it just gets squashed).
- Sticky table headers, zebra striping, tabular numerals for any numeric column.
- Consistent heading rhythm and section anchors.
- Bento-style stat/feature grids where content is list-shaped.

### Bug fixes (as above)
- Remove both stray backslashes.
- Fix the malformed RACI row.
- Rebuild TOC with all 13 sections in DOM order.
- Resolve the Assist-allocation inconsistency.

### Content policy
**All 957 lines of content are preserved verbatim.** This is a formatting refactor, not an edit. No claims, disclaimers, or figures altered except the internal inconsistency in item 5.

---

## 5. Verification

- HTML structure validated (no malformed rows, all anchors resolve).
- All 13 TOC links point at real `id`s that exist.
- All 13 sections still present.
- Every external link and CSS class preserved.
- Reduced-motion path confirmed present.
- Visual check via local server.

---

## 6. Deliverables

- Refactored `index.html`
- `updates/2026-10-11-servicenow-aifeatures-design-refactor.md`
