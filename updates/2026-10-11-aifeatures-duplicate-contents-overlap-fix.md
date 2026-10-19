# 2026-10-11 — ServiceNow AI Features page: duplicate "Contents" navs overlapped the layout

## What was broken

On https://findtorontoevents.ca/servicenow/AIFeaturesOct2026/index.html the
page had **two** table-of-contents navigations visible at the same time on
desktop (≥1280px):

1. `nav.rail` — a `position: fixed` vertical list in the left gutter, built in
   JS from the in-page TOC, rendered with **full labels at ~334px wide** and
   vertically centred (`top: 50%`).
2. `nav.toc` — the in-page "CONTENTS" box inside `<main>`, also full width.

On top of that, `@media (min-width: 1280px) { body { padding-left: 372px; } }`
pushed the **entire page** — including the sticky menu bar and the centred
content column — 372px to the right, and `header.hero` was pulled back with a
negative margin. Net effect: the fixed Contents rail floated over/next to a
giant duplicate Contents box, the menu bar no longer spanned the full width,
and the whole thing read as "the contents is overlapping the rest".

(Only the AI Features page had the fixed `nav.rail`. The JavaScript, CIS-CSM and
CIS-VR pages use a normal two-column `.layout` grid, which was already fine.)

## Root cause

Two navigations with the same purpose (the fixed rail and the in-page box)
were both rendered, and the page was globally offset by a hard-coded 372px
body padding to make room for the wide, always-expanded rail.

## What was changed

`TORONTOEVENTS_ANTIGRAVITY/servicenow/AIFeaturesOct2026/index.html`:

- **Removed the `body { padding-left: 372px }`** (and the compensating
  `header.hero` negative margin). The sticky menu bar now spans the full
  viewport width and the content column is centred normally.
- **Collapsed the rail by default.** `.rail-label` now starts at
  `max-width: 0; opacity: 0` and expands to `max-width: 17rem; opacity: 1` on
  `:hover` / `:focus-within` of the rail. Collapsed rail is ~80px, so it fits
  the left gutter cleanly.
- **Reserved a matching left gutter** with a new `--rail-gutter` token applied
  to `main` and `header.hero` padding (not the body), so content clears the
  collapsed rail without shifting the menu bar.
- **Hid the duplicate in-page TOC** at ≥1280px: `nav.toc { display: none }`.
  The fixed rail already provides the same navigation there. Below 1280px the
  rail is hidden and the in-page Contents box shows as before.

## How it was verified

Served locally and drove with headless Chromium (Playwright) at
390 / 1024 / 1280 / 1366 / 1440 / 1536 px:

- ≥1280px: `nav.toc` display `none`, `nav.rail` display `flex`, rail width
  ~80px (collapsed), menu bar width == viewport width (full-bleed), and
  `rail.right < firstSection.left` (no overlap) at every width.
- Hovering the rail expands it 80px → 334px (expected flyout behaviour).
- <1280px: `nav.rail` `none`, `nav.toc` `block` — the in-page Contents box
  is the navigation, unchanged.

Re-checked the **live** page after deploy at 1440 / 1280 / 1024 / 390 px:
`toc none / rail flex / railW 80 / lnavW == viewport / no overlap` on desktop,
and `toc block / rail none` on narrow — matching the local result.

Deployed with `python3 upload_aifeatures.py`.
