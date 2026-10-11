# Why CIS-CSM and CIS-VR look plain — diagnosis and beautification plan

**Date:** 2026-10-11
**Pages:** https://findtorontoevents.ca/servicenow/CIS-CSM/ · https://findtorontoevents.ca/servicenow/CIS-VR/
**Files:** [`findtorontoevents.ca/CIS-CSM/index.html`](../findtorontoevents.ca/CIS-CSM/index.html) · [`findtorontoevents.ca/CIS-VR/index.html`](../findtorontoevents.ca/CIS-VR/index.html)

All numbers below are measured from the live pages with Playwright at 1440×900, not inferred from the markup.

---

## TL;DR

| | CIS-CSM | CIS-VR | JS reference | AI Features |
|---|---|---|---|---|
| Animated elements | **0** | 3 *(all dead — see bug)* | 0 | 4 |
| `position: fixed` bg layers | **0** | 5 | 0 | 7 |
| Body background | **flat solid `#101820`** | 2 gradients | 2 gradients | 5 gradients |
| Accent hue | `#51c7ba` | `#51c7ba` | `#62f5c7` | `#62f5c7` |
| Base hue | `#101820` | `#101820` | `#080c14` | `#080c14` |
| Font | Segoe UI | Segoe UI | Inter | system stack |
| Horizontal overflow | 0px | 0px | 0px | 0px |

Two different problems, not one:

1. **CIS-CSM is genuinely bare** — a flat solid background, zero layers, zero motion.
2. **CIS-VR already has the background stack, but it is frozen.** It animates three layers whose `@keyframes` were never copied in.

Neither is a bug in the sense of "broken rendering" — both are `overflowPx: 0` with no page errors. They look plain because they were built as standalone one-off documents and never brought into the family that the other two pages now share.

---

## Root cause

### 1. Different palette family

The two rebuilt pages share one token set. The CIS pages use an entirely separate one:

| Token role | Family (JS / AI) | CIS pages | Difference |
|---|---|---|---|
| Accent | `#62f5c7` bright teal-green | `#51c7ba` muted sea-green | noticeably duller, lower chroma |
| Base | `#080c14` near-black navy | `#101820` grey-slate | ~12% lighter, flatter |
| Panel | `#0f1626` | `#18232c` | lighter, less depth |
| Secondary | `#7aa2ff` slate blue | `#f0b36e` **orange** | off-family entirely |

The orange `--accent: #f0b36e` is the loudest tell. It appears in notice borders and focus rings, and it belongs to no other page in the family.

The base colour matters most. `#101820` against `#080c14` reads as "grey office document" rather than "console", and a lighter base also means every gradient laid over it has less headroom — the same bloom alpha reads weaker on a lighter canvas.

### 2. No background layers on CIS-CSM

`body` declares `background: var(--paper)` and nothing else. Playwright reports **0 fixed elements and 0 animated elements** on the whole page. There is no grain, no veil, no gradient — it is a single flat colour behind every card.

### 3. CIS-VR: the layers exist, the animations are dead

This is the actual bug, and it is worth separating from the styling work because it is a straightforward copy-paste failure.

CIS-VR declares three layers and animates them:

```
.bg-scene  { animation: scene-drift  46s ... }   ← @keyframes scene-drift  NOT DEFINED
.bg-aurora { animation: aurora-drift 32s ... }   ← @keyframes aurora-drift NOT DEFINED
.bg-orbit  { animation: orbit-drift  44s ... }   ← @keyframes orbit-drift  NOT DEFINED
```

Only `@keyframes progress-grow` was copied across. Measured:

```
t=0    : {"bg-scene":"none","bg-aurora":"none","bg-orbit":"none"}
t=2.5s : {"bg-scene":"none","bg-aurora":"none","bg-orbit":"none"}
actually animating: NONE — all dead
```

`transform` is `none` at both samples. So CIS-VR has the *appearance* of the family's background stack in the markup, but the reader sees three static gradient blobs. `prefers-reduced-motion` is declared, and it correctly lists the layers — which makes the missing keyframes look like an incomplete paste rather than an intentional choice.

### 4. No shared chrome

Across all four pages:

| Component | JS ref | AI Features | CIS-CSM | CIS-VR |
|---|---|---|---|---|
| `sn-lnav` (learning header) | 0 | 0 | 0 | 0 |
| `footer-nav` (sibling links) | 0 | 4 | 0 | 0 |
| Left rail | 0 | 13 | 0 | 0 |
| Scroll-progress bar | 0 | 2 | 0 | 2 |
| Skip link | ✓ | ✓ | ✓ | ✓ |
| `:focus-visible` | ✓ | ✓ | ✓ | ✓ |

The two CIS pages are the only ones with **no navigation to their siblings at all**. A reader landing on CIS-VR has no way to discover the JS reference or the AI guide — which is why the set does not read as a product family even before you look at colour.

### 5. Different type stack

CIS pages use `"Segoe UI", Arial, sans-serif`; the JS reference uses `Inter`. Segoe UI is a Windows-first stack that renders as Arial or system-default on macOS/Linux, so the two pages do not even share a typeface on most readers' machines.

---

## Source-of-truth problems (fix these first)

Found while investigating. These are deployment bugs, not styling ones, and any styling work done before fixing them will be lost.

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

The live page exists only on the FTP server. If anyone deploys from the repo, **CIS-VR will regress to a small light-theme document**. Commit the live file as the canonical source before touching its styling.

### CIS-CSM local has drifted from live

Local and live differ, and the local edit is uncommitted. Reconcile before styling, or the styling will land on whichever copy is not deployed.

### CIS-VR was mid-edit during this investigation

Its live size moved 70,159 → 76,661 → **77,396 bytes** across successive checks during this investigation, and the file gained `bg-aurora` / `bg-orbit` / `bg-scene` / `bg-veil` in that window. Another session is actively working on this page *right now*. **Coordinate before editing**, or the two efforts will clobber each other — the same collision already happened on the JS reference page, where a hardcoded TOC numbering landed on top of a CSS counter and would have rendered `01  1. Overview`.

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

Reconcile the CIS-CSM local/live drift the same way. Do not proceed until `git status` is clean for both paths and local md5 equals live md5.

### Step 1 — Align the palette

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

The base change from `#101820` to `#080c14` is the single highest-impact line. It is what makes the pages read as "console" rather than "document", and it gives the gradient layers below enough contrast to actually show.

### Step 2 — Add the background stack

This is the direct answer to "make it more beautified with a dynamic background". Five layers, all CSS-only, no canvas, no JS, no network requests:

```html
<div class="bg-scene"  aria-hidden="true"></div>
<div class="bg-aurora" aria-hidden="true"></div>
<div class="bg-orbit"  aria-hidden="true"></div>
<div class="bg-grain"  aria-hidden="true"></div>
<div class="bg-veil"   aria-hidden="true"></div>
```

```css
.bg-scene, .bg-aurora, .bg-orbit, .bg-grain { position: fixed; inset: 0; pointer-events: none; }

/* base wash — slow, barely perceptible */
.bg-scene {
  z-index: 0; inset: -12%;
  background:
    radial-gradient(46% 50% at 18% 12%, rgba(98,245,199,.10) 0%, transparent 68%),
    radial-gradient(42% 46% at 84% 20%, rgba(122,162,255,.09) 0%, transparent 66%);
  filter: blur(90px) saturate(.95);
  animation: scene-drift 46s ease-in-out infinite alternate;
}

/* main blooms */
.bg-aurora {
  z-index: 0; inset: -25%;
  background:
    radial-gradient(42% 46% at 18% 22%, rgba(98,245,199,.16) 0%, transparent 66%),
    radial-gradient(40% 44% at 82% 18%, rgba(122,162,255,.15) 0%, transparent 64%),
    radial-gradient(46% 50% at 62% 78%, rgba(98,245,199,.07) 0%, transparent 68%);
  filter: blur(82px) saturate(1.05) brightness(.8);
  animation: aurora-drift 32s ease-in-out infinite alternate;
}

/* fine line texture, screen-blended */
.bg-orbit {
  z-index: 0; inset: -12%;
  background:
    repeating-linear-gradient(125deg,
      rgba(255,255,255,0) 0 18px,
      rgba(122,162,255,.025) 18px 19px,
      rgba(255,255,255,0) 19px 44px);
  mix-blend-mode: screen; opacity: .34;
  animation: orbit-drift 44s linear infinite;
}

/* texture */
.bg-grain {
  z-index: 1; opacity: .03;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='240' height='240'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.82' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
}

/* darkening veil — sits ABOVE the blooms, BELOW content.
   This is what keeps body text legible over the animation. */
.bg-veil {
  position: fixed; inset: 0; z-index: 1; pointer-events: none;
  background: linear-gradient(180deg, rgba(8,12,20,.34) 0%, rgba(8,12,20,.52) 55%, rgba(8,12,20,.70) 100%);
}

/* content clears the ambient layers */
body > .page, body > header, body > main, body > footer { position: relative; z-index: 2; }
```

**Copy the `@keyframes` too.** This is precisely the failure CIS-VR already has — the layers were pasted without their animations:

```css
@keyframes scene-drift  { from { transform: translate3d(-2%,0,0) scale(1); } to { transform: translate3d(2%,1%,0) scale(1.05); } }
@keyframes aurora-drift { from { transform: translate3d(-3%,-2%,0) rotate(0deg) scale(1); } to { transform: translate3d(3%,2%,0) rotate(7deg) scale(1.06); } }
@keyframes orbit-drift  { from { transform: translate3d(-1.5%,0,0) rotate(0deg); } 50% { transform: translate3d(1%,1.5%,0) rotate(5deg); } to { transform: translate3d(0,-1%,0) rotate(10deg); } }

@media (prefers-reduced-motion: reduce) {
  .bg-scene, .bg-aurora, .bg-orbit { animation: none; }
}
```

Add the reduced-motion rule in the same edit as the layers. Both CIS pages already have a `prefers-reduced-motion` block — extend it, do not add a second one.

### Step 3 — Fix the frozen CIS-VR layers

For CIS-VR specifically, this is a two-minute repair: copy the three missing `@keyframes` definitions in. Verify with the transform-sample check:

```js
// transform must differ between two samples 2.5s apart
const t0 = await page.evaluate(() => getComputedStyle(document.querySelector('.bg-aurora')).transform);
await page.waitForTimeout(2500);
const t1 = await page.evaluate(() => getComputedStyle(document.querySelector('.bg-aurora')).transform);
console.log('animating:', t0 !== t1);
```

A grep for `animation:` alone is **not** sufficient proof — CIS-VR currently passes that check while being completely static. The keyframes must exist by name.

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

Then add the same four links to the footer nav so every page in the family cross-links to every other page.

### Step 5 — Font stack

```css
font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
```

Add the Google Fonts link for Inter to match the JS reference, or accept the system stack on both. Do not leave one page on Inter and three on Segoe UI.

---

## Verification

Extend the two existing scripts rather than writing new ones — `tools/verify_servicenow_es6_overflow.mjs` (local) and `tools/verify_servicenow_es6_live.mjs` (live) already sweep 390/768/1024/1280/1440 and gate on the document-level invariant.

Add to both:

```js
// 1. Overflow sweep (existing) — must stay 0 at every width
// 2. Animated layers must ACTUALLY animate, not merely declare animation
for (const cls of ['.bg-scene', '.bg-aurora', '.bg-orbit']) {
  const t0 = await page.evaluate(c => getComputedStyle(document.querySelector(c)).transform, cls);
  await page.waitForTimeout(1200);
  const t1 = await page.evaluate(c => getComputedStyle(document.querySelector(c)).transform, cls);
  if (t0 === t1) fail(`${cls} is static — missing @keyframes`);
}

// 3. Every animation: name must resolve to a defined @keyframes
const orphans = await page.evaluate(() => {
  const defined = new Set([...document.querySelectorAll('style')]
    .flatMap(s => [...s.textContent.matchAll(/@keyframes\s+([\w-]+)/g)].map(m => m[1])));
  return [...document.querySelectorAll('*')]
    .filter(el => { const n = getComputedStyle(el).animationName; return n !== 'none' && !defined.has(n); })
    .map(el => el.className);
});
// orphans must be empty

// 4. Family components present
//    sn-lnav, footer-nav, skip-link, focus-visible, prefers-reduced-motion

// 5. Palette matches family tokens (accent #62f5c7, base #080c14)
```

Check #3 is the one that would have caught the current CIS-VR bug. It is cheap and worth adding to all four pages.

Deploy with a targeted FTP `STOR` — `deploy_main_site()` in `tools/deploy_to_ftp.py` does **not** recurse into `findtorontoevents.ca/servicenow/` or `findtorontoevents.ca/CIS-*`, which is the underlying reason edits to these pages repeatedly fail to go live. After deploying, confirm md5 parity and re-run the live script.

---

## What I did not do

Investigation and this document only — no CSS was changed and nothing was deployed. Two reasons:

1. **CIS-VR is untracked in git and its live copy is 3.9× the local file.** Styling it before the source of truth is fixed means the work would be lost on the next repo deploy.
2. **Another session is actively editing CIS-VR right now** — its live size changed mid-investigation. Editing concurrently would clobber that work, which has already happened once this session on the JS reference page.

Steps 0 and the coordination are prerequisites, not optional. Once CIS-VR is committed and the other session is clear, Steps 1–5 are roughly an hour of work with a verification script that catches the specific failure mode already present on the page.
