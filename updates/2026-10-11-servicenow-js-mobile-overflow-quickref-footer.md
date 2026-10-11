# ServiceNow JS reference — mobile overflow fix, Quick Reference redeploy, footer menu

**Date:** 2026-10-11
**File:** [`findtorontoevents.ca/servicenow/javascript/index.html`](../findtorontoevents.ca/servicenow/javascript/index.html)
**Live URL:** https://findtorontoevents.ca/servicenow/javascript/index.html
**Overflow write-up:** [`OVERFLOWFIX.MD`](../OVERFLOWFIX.MD) (root cause analysis + measured evidence)

## What was broken

1. **Mobile/tablet horizontal overflow.** The page scrolled sideways at 390px (+95px) and
   768px (+144px). Desktop (≥1024px) was clean, which is why the existing verify scripts —
   both hard-coded to a 1280px viewport — reported PASS while phones saw a broken page.
   Culprit: every `.anti`/`.good` comparison card in `#anti-patterns`.
2. **Quick Reference missing 2 of 3 patterns on live.** The local file had been expanded to
   `FindUpdate` + `GetById` + `Count`, but the edit landed *after* the earlier upload, so
   live still served only `FindUpdate`.
3. **No navigation between the ServiceNow guides** — the page was an island.

## What was changed

### 1. CSS — grid tracks could no longer be blown out by a code line

```css
/* minmax(0,1fr) so tracks cannot be blown out by a long code line's min-content */
.comparison { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 14px; margin: 16px 0; }
@media (max-width: 720px) { .comparison { grid-template-columns: minmax(0, 1fr); } }
.anti, .good { ...; min-width: 0; }
```

Grid items default to `min-width: auto`, so a `1fr` track refused to shrink below the
longest unbroken `pre` line (measured: a 460px track inside a 342px container). Long code
lines now scroll **inside** their `pre` (`overflow-x: auto`) instead of dragging the page.

### 2. Verify scripts — viewport sweep + correct invariant

- [`tools/verify_servicenow_es6_overflow.mjs`](../tools/verify_servicenow_es6_overflow.mjs) (`file://`)
- [`tools/verify_servicenow_es6_live.mjs`](../tools/verify_servicenow_es6_live.mjs) (live URL)

Both now sweep 390/768/1024/1280/1440px and gate on the **document-level** invariant
(`documentElement.scrollWidth <= clientWidth + 2`). The old
`pre.scrollWidth === pre.clientWidth` assertion was demoted to informational output —
a `pre` scrolling its own content is correct behavior, not a defect.

The live script additionally asserts the Quick Reference ships 3 patterns and that every
footer link resolves HTTP 200.

### 3. Footer nav

```html
<nav class="footer-nav" aria-label="ServiceNow guides">
  <a href="/servicenow/javascript/" class="current">JavaScript Reference</a>
  <a href="/servicenow/AIFeaturesOct2026/">AI Features — Oct 2026</a>
  <a href="/servicenow/CIS-CSM/">CIS-CSM Study Briefing</a>
  <a href="/servicenow/CIS-VR/">CIS-VR Study Briefing</a>
  <a href="/">findtorontoevents.ca</a>
</nav>
```

Pills with `flex-wrap` so they wrap rather than overflow on narrow viewports (the sweep
confirms overflowPx stays 0).

### 4. Reading-progress bar

```html
<div class="scroll-progress" id="scroll-progress" aria-hidden="true"></div>
```

Fixed-position 2px gradient bar driven by `transform: scaleX(ratio)` inside a
`requestAnimationFrame`-throttled passive scroll handler. `transform` (not `width`) means no
layout work per frame, and `position: fixed` takes it out of flow so it cannot contribute to
`scrollWidth` — the sweep still reports overflowPx 0 at every viewport. Hidden entirely under
`prefers-reduced-motion: reduce`, which also disables the page's transitions and smooth scroll.

**Already present, so left alone:** TOC scroll-spy highlighting (`nav.toc a.active`, styled at
line 137) and the "Copied!" copy-button feedback were already implemented — no change needed.

## How it was verified

Pre-deploy control run of the live script **failed as expected** (proves the new check
catches the regression it now guards):

```
[QuickRef] patterns = ["FindUpdate.pattern"]          → FAIL (1 patterns)
[Sweep 390px]  overflowPx=95  culprits=[anti-patterns > DIV.anti, ...]
[Sweep 768px]  overflowPx=144 culprits=[anti-patterns > DIV.good, ...]
RESULT: FAIL (exit 1)
```

Post-deploy run:

```
[QuickRef] patterns = ["FindUpdate.pattern","GetById.pattern","Count.pattern"]   → PASS
[Footer] 5 links; /servicenow/javascript/ /AIFeaturesOct2026/ /CIS-CSM/ /CIS-VR/ / → all 200
[Progress] count=1 position=fixed transform start=scaleX(0) mid=scaleX(0.520283) end=scaleX(1) moves=true  → PASS
[Sweep 390px]  overflowPx=0  culprits=none
[Sweep 768px]  overflowPx=0  culprits=none
[Sweep 1024px] overflowPx=0  culprits=none
[Sweep 1280px] overflowPx=0  culprits=none
[Sweep 1440px] overflowPx=0  culprits=none
[Page errors] none
RESULT: PASS (exit 0)
```

Live and local md5 identical: 81,185 bytes after the progress-bar addition.

**Test gotcha:** `html { scroll-behavior: smooth }` makes `window.scrollTo()` animate, so a
progress-bar check that samples 120ms after scrolling read `scaleX(0.019)` and falsely failed.
Fixed by setting `document.documentElement.style.scrollBehavior = 'auto'` inside the measurement
before scrolling — a test-harness fix, not an assertion change.

## Deployment

Targeted FTP `STOR` to `findtorontoevents.ca/servicenow/javascript/index.html` —
`deploy_main_site()` in [`tools/deploy_to_ftp.py`](../tools/deploy_to_ftp.py) does not cover
`findtorontoevents.ca/servicenow/`, which is the underlying reason two of these changes
("done" locally) were not actually live. Re-run `node tools/verify_servicenow_es6_live.mjs`
after any future edit to this page.
