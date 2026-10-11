# OVERFLOWFIX.MD — ServiceNow JS reference page: code overflow

**Page:** https://findtorontoevents.ca/servicenow/javascript/index.html (`#best-practices`, ES6 examples, anti-patterns)
**Source:** [`findtorontoevents.ca/servicenow/javascript/index.html`](findtorontoevents.ca/servicenow/javascript/index.html)
**Date:** 2026-10-11
**Status:** Both bugs fixed, deployed and verified on the live URL (2026-10-11).
Live also carries a footer menu linking all four ServiceNow guides and a reading-progress
bar; the viewport sweep confirms neither reintroduces overflow.

The report was *"code is overflowing"* next to the `Animal`/`Dog` inheritance example:

```js
var Animal = Class.create();
Animal.prototype = { initialize: function(name) { this.name = name; }, ... };
var Dog = Class.create();
Dog.prototype = Object.extendsObject(Animal, { bark: ..., type: 'Dog' });
```

That example has two separate problems behind it — a **stale deployment** and a **real CSS
layout bug**. A third, still-unfixed overflow exists further down the same page.

---

## Bug 1 — Old `Animal`/`Dog` build still being served (FIXED)

The live server was returning a **62,035-byte** old build that still contained the
"Quick Examples" 3-card grid (including `Class + Inheritance (Script Include)`), while the
file on disk was **76,447 bytes** with that grid replaced by 5 single-column examples.

Re-verified independently during review:

| Check | Result |
|---|---|
| `curl` live before redeploy | 62,035 bytes, old `Animal`/`Dog` card present |
| `curl` live after redeploy (`last-modified: Sun, 11 Oct 2026 06:06:41 GMT`) | 76,447 bytes, `md5` **identical** to local file |
| `node tools/verify_servicenow_es6_live.mjs` | `RESULT: PASS` (exit 0) |

Fix applied by targeted FTP `STOR` of the single file — `deploy_main_site()` in
[`tools/deploy_to_ftp.py`](tools/deploy_to_ftp.py) only uploads root `index.html`,
`.htaccess`, `events.json`, `ai-assistant.js`, `last_update.json` and `next/_next/`, so
**nothing under `findtorontoevents.ca/servicenow/` is covered by the standard deploy path.**
That deploy gap is the real root cause of "I changed it but the site didn't change" — it was
not a browser/CDN cache.

The CSS half of that fix (already in the source file):

```css
.concept, .api-card { min-width: 0; overflow: hidden; }   /* grid items may shrink */
.api-card pre { overflow-x: auto; overflow-y: hidden; }   /* code scrolls, doesn't push layout */
.api-grid.es6-examples { grid-template-columns: 1fr; }    /* long Class.create() blocks get full width */
```

---

## Bug 2 — `.anti` / `.good` comparison cards overflowed below 1024px (**FIXED**)

### Measured (Playwright, live URL, fresh `?cb=` cache-buster)

| Viewport | `documentElement.scrollWidth` vs `clientWidth` | Overflow |
|---|---|---|
| 390 px (phone) | 485 vs 390 | **+95 px** |
| 768 px (tablet) | 912 vs 768 | **+144 px** |
| 1024 / 1280 / 1440 px | equal | 0 |

Every overflowing element is inside `<section id="anti-patterns">`: `DIV.anti`,
`DIV.good`, their `h4` and their `pre`. Local `file://` render of the source file gives the
identical numbers, so it is a CSS bug, not a deploy artifact.

### Root cause

[`index.html` lines 250–261](findtorontoevents.ca/servicenow/javascript/index.html):

```css
.comparison { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin: 16px 0; }
@media (max-width: 720px) { .comparison { grid-template-columns: 1fr; } }
.anti, .good { border-radius: var(--radius); padding: 14px 16px; border: 1px solid var(--panel-border); }
.anti pre, .good pre { ...; overflow-x: auto; white-space: pre; }
```

Grid items have `min-width: auto`, so a track cannot shrink below the item's
**min-content size** — the longest unbroken `pre` line inside it. `overflow-x: auto` on the
`pre` gives the `pre` a zero *automatic minimum size*, but it does **not** stop its
min-content width from propagating up through the `.anti`/`.good` block to the grid track.
The track is then sized to the code line instead of the container.

Instrumented chain at 390 px (container is only 342 px wide):

```
PRE        w=427  overflow-x:auto
DIV.anti   w=461  min-width:auto          ← item refuses to shrink
DIV.comparison w=342  gridTemplateColumns="460.531px"  ← track blown out to 460px
SECTION / ARTICLE / MAIN  w=342, scrollWidth=461
BODY       w=390  scrollWidth=485         ← page scrolls sideways
```

`.api-card` does not have this problem because it carries `min-width: 0; overflow: hidden`.
`.anti` / `.good` were never given the same treatment.

### Fix

```css
/* 1. Let the grid tracks shrink: fixed 1fr fractions, not content-driven minimums */
.comparison { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 14px; margin: 16px 0; }
@media (max-width: 720px) { .comparison { grid-template-columns: minmax(0, 1fr); } }

/* 2. And let the items themselves shrink below min-content */
.anti, .good { min-width: 0; }
```

Long code lines then scroll **inside** the `pre` (which already has `overflow-x: auto`)
instead of dragging the whole page sideways. Content is unchanged.

This patch **has been applied** to [lines 250–257](findtorontoevents.ca/servicenow/javascript/index.html)
and uploaded — see Deployment status below.

### Verified fix result (live URL, `tools/verify_servicenow_es6_live.mjs`)

```
[Sweep 390px]  overflowPx=95 → 0   culprits=none
[Sweep 768px]  overflowPx=144 → 0  culprits=none
[Sweep 1024px] overflowPx=0        culprits=none
[Sweep 1280px] overflowPx=0        culprits=none
[Sweep 1440px] overflowPx=0        culprits=none
RESULT: PASS (exit 0)
```

Pre-deploy control run of the same script exited 1 with `overflowPx=95` at 390px
and `144` at 768px, so the sweep is proven to catch the regression it now guards.

No page content is lost: `pre` blocks keep horizontal scrolling, which is the intended
behavior for code.

---

## Verification method (use this, it matters)

**Correct invariant:** the *document* must not scroll sideways —

```js
document.documentElement.scrollWidth <= document.documentElement.clientWidth + 2
```

measured at **390, 768, 1024, 1280, 1440 px**, on both the `file://` source and the live URL.

**Wrong invariant:** `pre.scrollWidth === pre.clientWidth`. A code block whose content is
wider than its box *should* report `scrollWidth > clientWidth` — that means it scrolls
correctly. Asserting equality flags correct behavior as a failure (and, at only 1280 px,
misses Bug 2 entirely — that is why both existing verify scripts PASS while the page still
overflows on phones).

Both scripts now implement this sweep:
[`tools/verify_servicenow_es6_overflow.mjs`](tools/verify_servicenow_es6_overflow.mjs) (`file://`
source) and [`tools/verify_servicenow_es6_live.mjs`](tools/verify_servicenow_es6_live.mjs) (live URL,
also asserts the Quick Reference ships all 3 patterns, that all footer links resolve, and that
the progress bar tracks scroll). They gate on the document-level invariant; the old per-`pre`
equality check is retained as informational output only.

**Gotcha found while adding the progress-bar check:** the page sets `html { scroll-behavior: smooth }`,
so `window.scrollTo()` animates. A test that scrolls and samples 120ms later reads the bar mid-animation
(`scaleX(0.019)` instead of `1`) and reports a false failure. Disable smooth scroll inside the
measurement (`document.documentElement.style.scrollBehavior = 'auto'`) first.

---

## Deployment status (check before declaring done)

| Artifact | Local | Live |
|---|---|---|
| `servicenow/javascript/index.html` | **79,380 bytes** (md5 `4104da01…`) | **79,380 bytes** (md5 `4104da01…`) — identical |
| Quick Reference: `FindUpdate` + `GetById` + `Count` | present (3 code-cards) | present (`[QuickRef] PASS (3 patterns)`) |
| Footer nav (JS / AI Features / CIS-CSM / CIS-VR / home) | present (5 links) | present, all 5 resolve HTTP 200 |
| Reading-progress bar (`#scroll-progress`) | present, `position: fixed` | present, `scaleX(0)→0.52→1` |
| Mobile sweep 390/768/1024/1280/1440 | PASS | PASS |
| File size | 81,185 bytes | 81,185 bytes (md5 identical) |

Deployed 2026-10-11 via targeted FTP `STOR` to
`findtorontoevents.ca/servicenow/javascript/index.html` (the standard
`deploy_main_site()` path does not cover `servicenow/`). Note the Quick Reference
expansion had originally been written *after* the earlier 06:06:41 upload and was
live-missing until this second upload — re-run the live verify script after any
future edit to this page.

---

## Appendix — `JSON.parse` / `JSON.stringify` over GlideAjax

**Does `JSON.parse` work whether you receive an object or a string?**
No. `JSON.parse` accepts **only a string**. Anything else is first coerced with
`ToString`, so `JSON.parse(someObject)` becomes `JSON.parse("[object Object]")` and throws
`SyntaxError` (and `JSON.parse(null)` quietly returns `null`, which looks like success but
isn't a parse). On the client you must type-check first:

```js
ga.getXMLAnswer(function (answer) {
    var data = (typeof answer === 'string') ? JSON.parse(answer) : answer;
});
```

In practice with GlideAjax you will always get a string — `getXMLAnswer` returns the
`answer` attribute of the XML envelope, a string by construction.

**Does the Script Include have to stringify its return value, even when it's an object?**
Yes — **when the call travels over GlideAjax.** The XML envelope can only carry text, so a
returned object is coerced by the platform and arrives as `"[object Object]"`, which no
longer parses. Stringify on the server:

```js
// server — Script Include
getCallerInfo: function () {
    return JSON.stringify({ name: gr.getDisplayValue('name'), vip: true });  // ← stringify here
}
```

```js
// client — caller
ga.getXMLAnswer(function (answer) {
    var info = JSON.parse(answer);   // ← parse here
});
```

Two exceptions where you should **not** stringify: calling the Script Include directly from
other server-side code (`new MyScriptInclude().getCallerInfo()`), where a real object is
returned as-is; and when you deliberately return a plain scalar (`count.toString()`), which
needs no parsing on the client.
