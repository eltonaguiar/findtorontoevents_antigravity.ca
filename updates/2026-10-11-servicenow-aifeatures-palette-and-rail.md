# ServiceNow AI Features guide — shared palette, dimmer background, fixed left rail

**Date:** 2026-10-11
**File:** [`TORONTOEVENTS_ANTIGRAVITY/servicenow/AIFeaturesOct2026/index.html`](../TORONTOEVENTS_ANTIGRAVITY/servicenow/AIFeaturesOct2026/index.html)
**Live URL:** https://findtorontoevents.ca/servicenow/AIFeaturesOct2026/

## What was wrong

Three separate things, all reported by the user as "weird colour":

1. **Off-family palette.** The guide used grass green `#62D84E` over a teal-navy ink scale
   (`#04101a`/`#062231`/`#082d40`). The JavaScript reference it sits next to uses teal-green
   `#62f5c7` + slate blue `#7aa2ff` over near-black navy `#080c14`. Side by side they read as
   two unrelated products.
2. **Background too bright.** Aurora blooms ran at `rgba(...,.30)` with `saturate(1.3)` and no
   darkening layer, so the decoration competed with body text.
3. **No persistent wayfinding.** The only navigation was an in-flow TOC block at the top of the
   article — once you scrolled past it there was no "where am I" at all.

## What changed

### 1. Palette aligned to the JavaScript reference

Retuned the `:root` tokens to the JS page's values, **keeping every variable name** so the
~1,400 lines that reference them needed no edits:

| Token | Before | After (JS page value) |
|---|---|---|
| `--brand-green` | `#62D84E` | `#62f5c7` |
| `--bg-0..3` | `#04101a #062231 #082d40 #0b3a51` | `#080c14 #0c1322 #0f1626 #121b2e` |
| `--t-1..3` | `#eef4f2 #a3bab3 #6d857f` | `#e6edf6 #a9b6c9 #8b98ac` |
| `--sage` | `#81B5A1` | `#8fa3bd` |
| `--critical` | `#22d3ee` | `#7aa2ff` |

The stylesheet also carried ~50 hardcoded `rgba(...)` values pinned to the *old* palette
(`rgba(99,223,78,…)`, `rgba(129,181,161,…)`, `rgba(3,45,66,…)`, `rgba(6,34,49,…)`). Each was
mapped to the new equivalent with its **alpha preserved**, so contrast relationships are
unchanged — only hue moved. Verified zero old-palette `rgba`/hex references remain outside the
doc comment.

### 2. Background dimmed, not removed

The user explicitly wanted to keep a continuous/dynamic background, so the aurora stays:

- Bloom alphas cut roughly in half (`.30` → `.13/.12/.08`).
- `filter: blur(68px) saturate(1.3)` → `blur(82px) saturate(1.05) brightness(.8)`.
- Layer opacity `.8`.
- New `.bg-veil` layer — a fixed vertical dark gradient sitting **above** the aurora/grain
  (z-index 1) but **below** all content (z-index 2), so text always wins regardless of where a
  bloom happens to drift.
- Film grain `.045` → `.03`.

### 3. Fixed left rail with scroll-spy

`<nav class="rail">`, `position: fixed`, vertically centred.

**Items are generated in JS from `nav.toc`**, not hand-maintained. That is deliberate: this
page previously shipped a TOC listing 10 of 13 sections *in the wrong order* — the root cause
was two independently-maintained lists of the same sections. Deriving the rail at runtime makes
drift structurally impossible. Verified live: `railItems: 13`, `tocItems: 13`.

Layout, because a naive fixed sidebar collides with the 1120px centred content column:

- **Collapsed by default:** marker + zero-padded number only. Measured **80px wide with a 68px
  gap** to `main` at 1440px — no overlap.
- **On hover/focus:** labels expand to full text. Measured **334px wide, 13/13 labels visible,
  0 clipped.**
- **Hidden below 1280px**, where the gutter is too narrow; the in-flow TOC covers those widths.
- Scroll-spy uses a rAF-throttled passive scroll listener and marks exactly one active item.
- `prefers-reduced-motion: reduce` disables the label transition.

Note on a bug caught during development: an earlier version added `body > nav.rail` to the
existing `position: relative` stacking-context rule. That rule has higher specificity than
`nav.rail { position: fixed }`, so it silently un-fixed the rail. Caught in verification and
removed, with a comment explaining why the rail must stay out of that selector.

## Verification

```
COLLAPSED: railWidth=80  gap=68  overlapsContent=false  hiddenLabels=13/13
HOVERED:   railWidth=334 visibleLabels=13 clippedLabels=[] 
SCROLL-SPY @ bottom: active=#course-recommendations count=1
[Sweep 390]  overflowPx=0 railVisible=false
[Sweep 768]  overflowPx=0 railVisible=false
[Sweep 1280] overflowPx=0 railVisible=true overlapsContent=false
[Sweep 1440] overflowPx=0 railVisible=true overlapsContent=false
[Sweep 1920] overflowPx=0 railVisible=true overlapsContent=false
PAGE ERRORS: none
```

Palette read back from the live page confirms `--brand-green:#62f5c7`, `--bg-0:#080c14`,
`--bg-2:#0f1626`, and `oldGreenLeft: false`. Live and local md5 identical
(`bcb7cb36e872498fedde85981925b68b`, 94,401 bytes).

Regression check on the sibling page: `node tools/verify_servicenow_es6_live.mjs` → `RESULT: PASS`
(QuickRef, Footer, Progress, DecisionTable and the 390–1440 sweep all still green).

## Deployment

`tools/deploy_servicenow_ai.py` (FTPS targeted upload — note this script reads `FTP_USER`/
`FTP_PASS` from the environment only, so source `.env` first; it does not load it itself).
