# Why CIS-CSM and CIS-VR look plain — diagnosis and beautification plan

**Date:** 2026-10-11
**Pages:** https://findtorontoevents.ca/servicenow/CIS-CSM/ · https://findtorontoevents.ca/servicenow/CIS-VR/
**Files:** [`findtorontoevents.ca/CIS-CSM/index.html`](../findtorontoevents.ca/CIS-CSM/index.html) · [`findtorontoevents.ca/CIS-VR/index.html`](../findtorontoevents.ca/CIS-VR/index.html)

All numbers below are measured from the live pages with Playwright at 1440×900, not inferred from the markup. Re-measured at 08:2x after the pages changed mid-investigation (see *Concurrency* at the end).

---

## TL;DR

Both pages now carry **the same defect**, and it is a single root cause:

> The five-layer ambient background stack is fully present in the markup, but the three `@keyframes` those layers animate on were never pasted in. The layers render completely static.

Measured live, both pages identical:

```
[CIS-CSM]  keyframes defined : progress-grow
           animated elements : 3
           DEAD (no keyframes): bg-scene->scene-drift, bg-aurora->aurora-drift, bg-orbit->orbit-drift
           transform changes : false (animating: false)
           palette           : {"brand":"#51c7ba","accent":"#f0b36e","paper":"#101820"}
           overflow px       : 0
           sn-lnav/footerNav : 0 / 0
           dev veil-slider present: true

[CIS-VR]   keyframes defined : progress-grow
           animated elements : 3
           DEAD (no keyframes): bg-scene->scene-drift, bg-aurora->aurora-drift, bg-orbit->orbit-drift
           transform changes : false (animating: false)
           palette           : {"brand":"#51c7ba","accent":"#f0b36e","paper":"#101820"}
           overflow px       : 0
           sn-lnav/footerNav : 0 / 0
           dev veil-slider present: true
```

Three contributing factors on top of that:

1. **Off-family palette** — dull teal `#51c7ba`, orange `#f0b36e`, grey base `#101820`.
2. **No shared chrome** — neither page links to any sibling guide.
3. **A dev-only debug slider is shipped to production** on both pages (`#veil-slider-container`, `z-index: 1000`).

The pages are not "broken" in the rendering sense — `overflowPx: 0`, zero page errors, `prefers-reduced-motion` already declared. They look plain because the animation layer is inert and the colour is off-family.

---

## Root cause

### 1. The background stack is present but frozen — on both pages

Both pages declare the same five layers and animate three of them:

```
.bg-scene  { animation: scene-drift  ... }   ← @keyframes scene-drift  NOT DEFINED
.bg-aurora { animation: aurora-drift ... }   ← @keyframes aurora-drift NOT DEFINED
.bg-orbit  { animation: orbit-drift  ... }   ← @keyframes orbit-drift  NOT DEFINED
```

Only `@keyframes progress-grow` (the scroll-progress bar) was copied across. The reader sees three static gradient blobs under a static blur — the *appearance* of the family's ambient background with none of the movement.

This is a copy-paste failure, and it is worth stating plainly because it is cheap to fix: the layers were duplicated without their keyframes. The giveaway is that `prefers-reduced-motion` on both pages *correctly lists* `.bg-scene, .bg-aurora, .bg-orbit` as animated — the author clearly intended motion, then omitted the definitions.

**A grep for `animation:` is not sufficient proof of animation.** Both pages pass that check while sitting completely still. The keyframes must exist by name, and `transform` must measurably change between two samples.

### 2. Off-family palette

The two rebuilt pages (JS reference, AI Features) share one token set. The CIS pages use a separate one:

| Token role | Family (JS / AI) | CIS pages | Difference |
|---|---|---|---|
| Accent | `#62f5c7` bright teal-green | `#51c7ba` muted sea-green | duller, lower chroma |
| Base | `#080c14` near-black navy | `#101820` grey-slate | ~12% lighter, flatter |
| Panel | `#0f1626` | `#18232c` | lighter, less depth |
| Secondary | `#7aa2ff` slate blue | `#f0b36e` **orange** | off-family entirely |

The orange `--accent: #f0b36e` is the loudest tell — it appears in notice borders and focus rings and belongs to no other page in the family.

The base colour matters most. `#101820` against `#080c14` reads as "grey office document" rather than "console", and a lighter base gives every gradient laid over it less headroom — the same bloom alpha reads weaker on a lighter canvas. This compounds the frozen-animation bug: even the static blooms show up less than they would on the family's darker base.

### 3. No shared chrome

Across all four pages:

| Component | JS ref | AI Features | CIS-CSM | CIS-VR |
|---|---|---|---|---|
| `sn-lnav` (learning header) | 0 | 0 | **0** | **0** |
| Footer sibling links | 0 | 4 | **0** | **0** |
| Left rail | 0 | 13 | 0 | 0 |
| Scroll-progress bar | 0 | 2 | 2 | 2 |
| Skip link | ✓ | ✓ | ✓ | ✓ |
| `:focus-visible` | ✓ | ✓ | ✓ | ✓ |

The two CIS pages are the only ones with **no navigation to their siblings at all**. A reader landing on CIS-VR has no way to discover the JS reference or the AI guide, which is why the set does not read as a product family even before colour is considered.

### 4. Different type stack

CIS pages use `"Segoe UI", Arial, sans-serif`; the JS reference uses `Inter`. Segoe UI is a Windows-first stack that falls back to Arial or the system default on macOS/Linux, so the pages do not even share a typeface on most readers' machines.

### 5. A debug control is live in production

Both pages ship `<div id="veil-slider-container" style="position:fixed; top:10px; right:10px; z-index:1000; ...">` — a transparency-tuning slider that is clearly a build-time aid for dialling in `.bg-veil`. It is fixed at `z-index: 1000`, above every content layer, and visible to every visitor on both pages.

It also happens to be evidence for root cause #1: the author was tuning the veil opacity with a slider against layers that never move.

---

## Source-of-truth problems (fix these first)

Deployment bugs, not styling ones. Any styling work done before fixing them will be lost.

### CIS-VR is not in git

```
$ git ls-files findtorontoevents.ca/CIS-CSM findtorontoevents.ca/CIS-VR
findtorontoevents.ca/CIS-CSM/index.html          ← tracked
                                                  ← CIS-VR: nothing
```

`findtorontoevents.ca/CIS-VR/index.html` is untracked, and the local file is a **completely different document** from what is deployed:

| | Local (untracked) | Live |
|---|---|---|
| Size | 19,764 bytes | 77,396 bytes |
| Colour scheme | `color-scheme: light` | `color-scheme: dark` |
| `--ink` | `#172b3a` dark-on-light | `#e6edf1` light-on-dark |
| `--paper` | `#f4f6f5` off-white | `#101820` grey-slate |

The live page exists only on the FTP server. If anyone deploys from the repo, **CIS-VR regresses to a small light-theme document**. Commit the live file as canonical before touching its styling.

### CIS-CSM local has drifted from live

```
$ md5sum findtorontoevents.ca/CIS-CSM/index.html   → 206315d1ce4c9be71d34525abface556
$ curl -s .../CIS-CSM/index.html | md5sum          → f0896a812c376103fbe8d61cd597361d
```

Local and live differ, and the local edit is uncommitted. Reconcile before styling, or the styling lands on whichever copy is not deployed.

---

## Suggested fix

Ordered so each step is verifiable on its own.

### Step 0 — Repair the source of truth

```bash
# Publish the live CIS-VR page as the canonical source
curl -s https://findtorontoevents.ca/servicenow/CIS-VR/index.html -o findtorontoevents.ca/CIS-VR/index.html
git add findtorontoevents.ca/CIS-VR/index.html
git commit -m "chore(cis-vr): commit the deployed page as canonical source"
```

Reconcile the CIS-CSM drift the same way. Do not proceed until `git status` is clean for both paths and local md5 equals live md5.

### Step 1 — Add the three missing `@keyframes` (both pages)

This is the actual fix for "the pages look plain" — the layers are already there and already positioned correctly. Three definitions, applied to **both** files:

```css
@keyframes scene-drift {
  from { transform: translate3d(-2%, 0, 0) scale(1); }
  to   { transform: translate3d(2%, 1%, 0) scale(1.05); }
}
@keyframes aurora-drift {
  from { transform: translate3d(-3%, -2%, 0) rotate(0deg) scale(1); }
  to   { transform: translate3d(3%, 2%, 0) rotate(7deg) scale(1.06); }
}
@keyframes orbit-drift {
  from { transform: translate3d(-1.5%, 0, 0) rotate(0deg); }
  50%  { transform: translate3d(1%, 1.5%, 0) rotate(5deg); }
  to   { transform: translate3d(0, -1%, 0) rotate(10deg); }
}
```

Durations and easings are already declared on the layers (`46s ease-in-out alternate`, `32s ease-in-out alternate`, `44s linear infinite`) — only the keyframes are missing, so no other CSS needs to change.

Both pages already have a `prefers-reduced-motion` block that correctly lists these three layers. Confirm it sets `animation: none`; do **not** add a second block.

### Step 2 — Remove the debug slider (careful: it is load-bearing)

Both pages ship a `z-index: 1000` opacity-tuning slider in production. Delete it — but **not before defining the variable it owns**, or the veil breaks.

The veil reads the custom property with no fallback:

```css
.bg-veil {
  background: rgba(0,0,0, var(--veil-opacity));   /* ← no fallback value */
}
```

and `--veil-opacity` is set in exactly one place — the slider's handler:

```js
root.style.setProperty('--veil-opacity', val);     /* only definition */
```

It is **never declared in `:root`**. So deleting the slider alone leaves `var(--veil-opacity)` undefined, the `rgba()` becomes an invalid color, and **the veil silently disappears** — the blooms go to full strength with nothing darkening them, and body text over them loses contrast. A naive "delete the debug div" ships a legibility regression that no overflow check would catch.

Correct order, both pages:

```css
/* 1. give the variable a home so the slider is no longer load-bearing */
:root { --veil-opacity: 0.4; }   /* matches the slider's current value */

/* 2. harden the rule against a missing value */
.bg-veil { background: rgba(0,0,0, var(--veil-opacity, 0.4)); }
```

```js
/* 3. only then remove the slider markup and its handler */
/*    #veil-slider-container + const slider = ... + update() + listener */
```

`0.4` is the value both pages already serve (`value="0.4"` in the markup and the `<span>` label), so this preserves current appearance exactly. The `var(--veil-opacity, 0.4)` fallback is belt-and-braces — with the `:root` declaration in place it should never fire, but it means a future partial edit cannot silently blank the veil again.

### Step 3 — Align the palette

Keep the CIS pages' existing token *names* (`--ink`, `--brand`, `--paper`, `--card`) so the change is nine lines and touches no component rule — the same technique that worked on the AI Features page. Only the values change:

```css
:root {
  color-scheme: dark;
  --ink:    #e6edf6;   /* was #e6edf1 — match family text */
  --muted:  #8b98ac;   /* was #aabac4 */
  --brand:  #62f5c7;   /* was #51c7ba — family accent */
  --brand-dark: #7fead0;
  --brand-soft: #0f2b2b;
  --accent: #7aa2ff;   /* was #f0b36e orange — off-family */
  --paper:  #080c14;   /* was #101820 — darker base = more gradient headroom */
  --card:   #0f1626;   /* was #18232c */
  --line:   rgba(255,255,255,0.08);
}
```

The base change from `#101820` to `#080c14` is the single highest-impact line here. It is what makes the page read as "console" rather than "document", and it gives the now-moving gradients enough contrast to actually show.

### Step 4 — Add shared chrome

Copy `nav.sn-lnav` and the footer sibling nav from the AI Features page, adding `aria-current="page"` on the matching link. This is what makes the four pages read as one product rather than four documents:

```html
<nav class="sn-lnav" aria-label="ServiceNow learning guides">
  <span class="sn-lnav-brand">ServiceNow<span class="sn-lnav-brand-dot">·</span>Learning</span>
  <span class="sn-lnav-links">
    <a href="/servicenow/javascript/index.html">JavaScript Reference</a>
    <a href="/servicenow/AIFeaturesOct2026/index.html">AI Features Guide</a>
    <a href="/servicenow/CIS-CSM/index.html" aria-current="page">CIS-CSM</a>
    <a href="/servicenow/CIS-VR/index.html">CIS-VR</a>
  </span>
</nav>
```

Then add the same four links to the footer nav so every page cross-links to every other.

### Step 5 — Font stack

```css
font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
```

Add the Google Fonts link for Inter to match the JS reference, or accept the system stack on both. Do not leave one page on Inter and three on Segoe UI.

---

## Verification

Extend the two existing scripts rather than writing new ones — `tools/verify_servicenow_es6_overflow.mjs` (local) and `tools/verify_servicenow_es6_live.mjs` (live) already sweep 390/768/1024/1280/1440 and gate on the document-level overflow invariant.

Add these checks to both:

```js
// 1. Overflow sweep (existing) — must stay 0 at every width

// 2. Animated layers must ACTUALLY animate, not merely declare animation
for (const cls of ['.bg-scene', '.bg-aurora', '.bg-orbit']) {
  const t0 = await page.evaluate(c => getComputedStyle(document.querySelector(c)).transform, cls);
  await page.waitForTimeout(1200);
  const t1 = await page.evaluate(c => getComputedStyle(document.querySelector(c)).transform, cls);
  if (t0 === t1) fail(`${cls} is static — missing @keyframes`);
}

// 3. Every animation name must resolve to a defined @keyframes
const orphans = await page.evaluate(() => {
  const defined = new Set([...document.querySelectorAll('style')]
    .flatMap(s => [...s.textContent.matchAll(/@keyframes\s+([\w-]+)/g)].map(m => m[1])));
  return [...document.querySelectorAll('*')]
    .filter(el => { const n = getComputedStyle(el).animationName; return n !== 'none' && !defined.has(n); })
    .map(el => el.className);
});
// orphans must be empty

// 4. No debug affordances in production
//    document.getElementById('veil-slider-container') === null

// 5. Family components present: sn-lnav, footer sibling links,
//    skip-link, focus-visible, prefers-reduced-motion

// 6. Palette matches family tokens (accent #62f5c7, base #080c14)
```

Check #3 is the one that catches the current bug, and it is worth adding to **all four** pages — the same missing-keyframes failure could land anywhere the background stack is duplicated. Check #2 is the runtime complement: it proves motion rather than inferring it from markup.

Deploy with a targeted FTP `STOR` — `deploy_main_site()` in `tools/deploy_to_ftp.py` does **not** recurse into `findtorontoevents.ca/servicenow/` or `findtorontoevents.ca/CIS-*`, which is the underlying reason edits to these pages repeatedly fail to go live. After deploying, confirm md5 parity and re-run the live script.

---

## Concurrency note

This document was re-measured because the pages changed underneath it. During the original investigation CIS-CSM reported 0 animated elements and a flat solid background; a parallel session then added the full five-layer stack to it — with the same missing `@keyframes`. CIS-VR's live size also moved 70,159 → 76,661 → 77,396 bytes across successive checks.

The diagnosis got *simpler* as a result: it started as two different problems and is now one problem on two pages. But the pages are actively being edited. **Coordinate with that session before applying Steps 0–5**, or the two efforts will clobber each other — which already happened once this session, when a hardcoded TOC numbering scheme landed on top of a CSS counter on the JS reference page and would have rendered every row as `01  1. Overview`.

---

## What I did not do

Investigation and this document only — no CSS was changed and nothing was deployed. Two reasons:

1. **CIS-VR is untracked in git and its live copy is 3.9× the local file.** Styling it before the source of truth is fixed means the work is lost on the next repo deploy.
2. **Another session is actively editing both pages.** Editing concurrently would clobber that work.

Steps 0 and the coordination are prerequisites, not optional. Once CIS-VR is committed and the other session is clear, the whole sequence is roughly an hour — and Step 1 alone (three `@keyframes` definitions) is the change that turns these pages from static to animated.
