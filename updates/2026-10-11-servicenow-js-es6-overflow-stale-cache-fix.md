# ServiceNow JavaScript Reference — ES6 Overflow + Stale Live Cache Fix

**Date:** 2026-10-11
**File:** [`findtorontoevents.ca/servicenow/javascript/index.html`](../findtorontoevents.ca/servicenow/javascript/index.html)
**Live URL:** https://findtorontoevents.ca/servicenow/javascript/index.html

## What was broken

Two distinct problems were reported by the user:

1. **Code overflow** — the ES6+ examples section used a multi-column CSS grid
   (`.api-grid` with `repeat(auto-fit, minmax(260px, 1fr))`). Long
   `Class.create()` / `Object.extendsObject` code blocks forced the grid items
   wider than their track, causing horizontal spill-over of the whole page.

2. **Stale live content** — the user kept seeing the *old* `Animal` / `Dog`
   inheritance example even after the local file had been rewritten. The live
   site was serving a **62,035-byte cached copy** while the local file on disk
   was **76,447 bytes** with the new content.

## What was changed

### 1. CSS overflow fixes (in the `<style>` block)

```css
/* Grid items must be allowed to shrink below their content width */
.concept, .api-card {
  min-width: 0; overflow: hidden;
}

/* Code blocks scroll internally instead of pushing the layout */
.api-card pre {
  overflow-x: auto; overflow-y: hidden;
  max-height: 320px;
}
.api-card code { white-space: pre; }

/* ES6 examples: single column so long Class.create() blocks have room */
.api-grid.es6-examples {
  grid-template-columns: 1fr;
}

/* Callout code blocks also scroll internally */
.danger pre, .warning pre, .notice pre, .flow pre, .success pre,
.anti pre, .good pre {
  overflow-x: auto; white-space: pre;
}
```

### 2. Content replacement

The old "Quick Examples" cards (Arrow + Template + Destructuring, Optional
Chaining + Nullish, and the `Animal`/`Dog` `Class.create()` inheritance demo)
were replaced with **5 production-grade ServiceNow examples** under the heading
**"Production-Grade ServiceNow Examples"**:

1. GlideRecord + Destructuring + Template Literals (Business Rule)
2. GlideAjax + Arrow Functions + Optional Chaining (Client Script)
3. Map + Set — Deduplicate Callers from Incidents (Script Include)
4. Rest Parameters + Nullish Coalescing — Dynamic Query Builder (Script Include)
5. Safe Property Access — Avoid NPE on Reference Fields (Business Rule)

### 3. Deployment

The `deploy_main_site()` helper in [`tools/deploy_to_ftp.py`](../tools/deploy_to_ftp.py)
only uploads the **root** `index.html`, `.htaccess`, `events.json`, and
`next/_next/` — it does **not** recurse into `findtorontoevents.ca/servicenow/`.
The page was therefore re-uploaded with a targeted `ftplib` `STOR` to:

```
findtorontoevents.ca/servicenow/javascript/index.html
```

Remote size after upload: **76,447 bytes** (matches local).

## How it was verified

### Local file (`file://`) — Playwright

Script: [`tools/verify_servicenow_es6_overflow.mjs`](../tools/verify_servicenow_es6_overflow.mjs)

```
[Heading] "Production-Grade ServiceNow Examples" count = 1
[ES6 Grid] count = 1, cards = 5
[Old code] Animal present = false, Dog present = false
[ES6 Grid] scrollWidth=900, clientWidth=900, overflow=false
[Card 1 pre] scrollWidth=866, clientWidth=866, overflow=false
[Card 2 pre] scrollWidth=866, clientWidth=866, overflow=false
[Card 3 pre] scrollWidth=866, clientWidth=866, overflow=false
[Card 4 pre] scrollWidth=866, clientWidth=866, overflow=false
[Card 5 pre] scrollWidth=866, clientWidth=866, overflow=false
[Body] horizontal overflow = false
[Page errors] none
RESULT: PASS
```

### Live URL — Playwright

Script: [`tools/verify_servicenow_es6_live.mjs`](../tools/verify_servicenow_es6_live.mjs)

```
[HTTP] status=200
[Heading] "Production-Grade ServiceNow Examples" count = 1
[ES6 Grid] count = 1, cards = 5
[Old code] Animal present = false, Dog present = false
[ES6 Grid] scrollWidth=900, clientWidth=900, overflow=false
[Card 1 pre] scrollWidth=866, clientWidth=866, overflow=false
[Card 2 pre] scrollWidth=866, clientWidth=866, overflow=false
[Card 3 pre] scrollWidth=866, clientWidth=866, overflow=false
[Card 4 pre] scrollWidth=866, clientWidth=866, overflow=false
[Card 5 pre] scrollWidth=866, clientWidth=866, overflow=false
[Body] horizontal overflow = false
[Page errors] none
RESULT: PASS
```

### Live content diff (before → after re-upload)

| Metric | Before (stale) | After (fixed) |
|---|---|---|
| Size | 62,035 bytes | 76,447 bytes |
| `Animal` matches | 6 (old code block) | 2 (compat table only) |
| New heading | 0 | 1 |
| `es6-examples` class | 0 | 2 |

## Root cause

The FTP host (`ftps2.50webs.com`) was serving a **stale cached copy** of the
page. The earlier upload had not landed (or was overwritten by a later stale
write). A targeted re-upload of the single file corrected the remote copy, and
the live URL now serves the correct 76,447-byte version.

## Follow-up recommendation

`deploy_main_site()` should be extended to recurse the full
`findtorontoevents.ca/` subtree (or at least the `servicenow/` directory) so
future edits to this page are deployed by the standard deploy path rather than
requiring a manual targeted upload.
