# 2026-10-11 — ServiceNow guides: sticky menu bar overlapping TOC/section content

## What was broken

On all four ServiceNow learning guides the sticky guide-switcher bar
(`.sn-lnav`, `position: sticky; top: 0; z-index: 50`) was overlaying content
that used its own fixed `top` offset:

- `nav.toc` was `position: sticky; top: 24px` (or `top: 24px` on the sidebar
  variants). With only 24px of clearance, the menu bar (≈58px tall at desktop,
  up to ≈136–203px when it wraps to two/three rows on narrow viewports) covered
  the top of the table-of-contents box — the "Contents" / "On this page"
  heading was clipped and became unclickable.
- Ashore, anchored jumps (`#section` links) landed content under the bar
  because `scroll-padding-top` / `section { scroll-margin-top }` were smaller
  than the bar's real height, and did not account for the bar wrapping on
  mobile.

Reported page: https://findtorontoevents.ca/servicenow/AIFeaturesOct2026/index.html
(the "Contents" box was being overlapped by the menu bar as the user scrolled).

## Root cause

The menu's height was not modeled anywhere. Two hard-coded magic numbers
(`top: 24px`, `scroll-margin-top: 90px` / `scroll-padding-top: 6rem`) assumed
a single-row bar, so any wrap (common below ~900px) broke the offset.

## What was changed

Introduced a single source of truth — the CSS custom property
`--sn-nav-h` — for the height of the sticky guide switcher, and made the
sticky/anchored offsets derive from it:

- `:root { --sn-nav-h: 58px; }` as a CSS-only fallback.
- A small runtime script measures the **real** rendered height of `.sn-lnav`
  (which wraps on narrow viewports) and writes it back to `--sn-nav-h` on
  load, on resize, on font load, and via `ResizeObserver`. This keeps every
  dependent offset correct at all widths.
- `html { scroll-padding-top: calc(var(--sn-nav-h) + 16px); }` so anchored
  jumps clear the bar.
- `section { scroll-margin-top: calc(var(--sn-nav-h) + <gap>); }` on the pages
  that define it.
- `nav.toc { position: sticky; top: calc(var(--sn-nav-h) + <gap>); … }` so the
  TOC box always sits just below the menu bar instead of under it.
- Sidebar TOCs also had their `max-height` re-derived from the token so a
  taller (wrapped) bar can never push the TOC content past the viewport.

Per file:

- `TORONTOEVENTS_ANTIGRAVITY/servicenow/AIFeaturesOct2026/index.html`
  - added `--sn-nav-h`; `scroll-padding-top` and `section { scroll-margin-top }`
    now use it; `nav.toc` made `position: sticky; top: calc(var(--sn-nav-h) + .75rem)`;
    added runtime height-sync script.
- `findtorontoevents.ca/servicenow/javascript/index.html`
  - added `--sn-nav-h`; `scroll-padding-top`, `section { scroll-margin-top }`,
    and the sidebar `nav.toc` `top`/`max-height` now use it; added runtime
    height-sync script.
- `findtorontoevents.ca/CIS-CSM/index.html`
  - added `--sn-nav-h`; `scroll-padding-top` and `.toc`
    `top`/`max-height` now use it; added runtime height-sync script.
- `.worktrees/cis-vr-coding-guide/findtorontoevents.ca/CIS-VR/index.html`
  - added `--sn-nav-h`; `scroll-padding-top` and `.toc`
    `top`/`max-height` now use it; added runtime height-sync script.

### Bonus fix

`findtorontoevents.ca/CIS-CSM/index.html` had a malformed, duplicated `:root`
block (a second `:root {` opened inside the first without closing it), which
made the first token declarations unreliable. The duplicates were collapsed
into a single valid `:root`.

## How it was verified

Served the working copies locally (`python3 -m http.server 8123`) and drove
them with headless Chromium (Playwright) at widths **390 / 768 / 1280**,
scrolling to mid-page and measuring the gap between the menu bar's bottom edge
and the TOC's top edge:

| page              | w=390        | w=768 | w=1280 |
|-------------------|--------------|-------|--------|
| AIFeaturesOct2026 | +12px        | +12px | +12px  |
| CIS-CSM           | static (ok)  | +16px | +16px  |
| CIS-VR            | static (ok)  | +16px | +16px  |
| javascript        | +16px        | +16px | +16px  |

- Positive gap = TOC sits below the bar (no overlap). "static" = the narrow
  breakpoint intentionally drops the TOC to `position: static`, so it scrolls
  away normally (no overlap possible).
- `--sn-nav-h` resolved to the real bar height at each width
  (136 / 101 / 58 px etc.), confirming the runtime sync works.
- **Zero `pageerror` events** on any page at any width.
- Visual confirmation via screenshot at desktop scroll: the "Contents" heading
  on the AI Features page is now fully visible below the menu bar.

Deployed with the project FTP helpers and re-checked the live pages:

- `python3 upload_aifeatures.py`
- `python3 upload_cisvr.py`
- `python3 upload_csism.py`
- `python3 upload_javascript.py`

Live re-check against https://findtorontoevents.ca/… at 390 and 1280 px showed
the same non-overlapping gaps and zero JS errors.
