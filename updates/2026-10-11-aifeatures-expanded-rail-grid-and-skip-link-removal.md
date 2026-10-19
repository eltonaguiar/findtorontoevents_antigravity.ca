# 2026-10-11 — AI Features page: expanded rail by default (grid), skip link removed

Follow-up to `2026-10-11-aifeatures-duplicate-contents-overlap-fix.md`.

## Requests

1. Confirm no content was lost from the in-page "Contents" box when it was
   hidden on desktop.
2. Make the left numbered rail **expanded by default** and have it **push the
   content aside** rather than float over it.
3. Remove the "Skip to briefing" link — it appeared to do nothing.

## Findings

- **Nothing was lost.** The `nav.toc` markup (all 13 `<li><a href="#…">`
  entries) is untouched in the DOM. The rail is generated 1:1 from those same
  links at runtime (numbers + full label text + `title`), so every entry and
  target is still present. `display:none` only hid the duplicate box; it did
  not remove content.
- The skip link (`<a class="skip-link" href="#main-content">`) pointed at
  `#main-content`, but this page has no element with that id, so the link was
  inert — safe to remove.

## What was changed

`TORONTOEVENTS_ANTIGRAVITY/servicenow/AIFeaturesOct2026/index.html`:

- **Rail is now a real, expanded sidebar column** (labels visible by default).
  Removed the collapse-on-idle CSS (`max-width:0; opacity:0` + hover reveal) so
  `.rail-label` always shows its full text (max-width 17rem / 272px).
- **Two-column grid at ≥1280px**, replacing the previous fixed-overlay +
  reserved-gutter approach:
  ```
  body {
    display: grid;
    grid-template-columns: var(--rail-w) minmax(0, 1fr);
    grid-template-areas:
      "nav  nav"
      "hero hero"
      "rail main"
      "rail foot";
    align-items: start;
  }
  ```
  The rail is `position: sticky` (within its grid column) so it scrolls with
  the content but stays pinned below the menu bar. Because the rail and content
  are grid siblings, they can never overlap and the content is genuinely pushed
  aside — no `body { padding-left }` hack, so the sticky menu bar still spans
  the full width.
- **Removed the skip link** markup (and confirmed no orphaned CSS rule).
- Below 1280px: unchanged — rail hidden, in-page "Contents" box shown.

## How it was verified

Local + live, headless Chromium (Playwright) at 390 / 1024 / 1280 / 1440 /
1536 px, scrolled to mid-page:

| width | toc | rail | rail width | label max | menu bar width | overlap | skip-link |
|-------|-----|------|-----------|-----------|----------------|---------|-----------|
| 1280+ | none | flex | ~304px    | 272px     | == viewport    | no      | 0         |
| <1280 | block| none | 0         | 272px     | == viewport    | no      | 0         |

- `rail.right < main.left` at every desktop width → no overlap.
- Menu bar width == viewport width → full-bleed, not shifted.
- `document.querySelectorAll('.skip-link').length === 0` → link gone.
- Zero `pageerror` events at any width.
- Screenshots confirm: rail expanded with full labels beside the content,
  hero + menu bar full width, no skip link, mobile single-column with the
  Contents box intact.

Deployed with `python3 upload_aifeatures.py`; live re-check matched local.
