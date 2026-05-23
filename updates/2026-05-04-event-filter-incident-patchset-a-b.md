# 2026-05-04 - Event filter incident Patch Sets A+B

## What was broken

- The event-filter pipeline had race/state risks in `TORONTOEVENTS_ANTIGRAVITY/index.html`:
  - `applyFilters()` could silently drop a requested re-run when the mutex was already held.
  - Sibling chip deactivation accepted synthetic clicks and could desync Next Month state.
  - `__parseCardDisplayedDate__` used one-sided year wrapping and misclassified boundary months.
  - This Month interceptor stopped propagation too aggressively, causing React/state sync risk.

## What changed

### Patch Set A (lower blast radius)

1. `applyFilters()` now queues one deferred pass when called while running.
2. `__parseCardDisplayedDate__` now uses centered month-delta year wrap:
   - `monthDelta < -6 => next year`
   - `monthDelta > 6 => previous year`
3. Sibling-chip deactivator now ignores non-trusted clicks with `if (!e.isTrusted) return;`.

### Patch Set B (isolated event-propagation slice)

4. This Month capture handler no longer calls `stopPropagation()` / `stopImmediatePropagation()`, allowing React delegated click flow to continue while preserving custom override logic.

## Baseline and evidence artifacts

- Baseline remote suite run before edits:
  - `VERIFY_REMOTE=1 npx playwright test --config=playwright.filters.config.ts --reporter=list`
- Artifact bundle captured:
  - `tmp/eventfilter_baseline_2026_05_04/`
  - Includes per-chip screenshots and JSON snapshots.
  - Hidden persistence trace: `tmp/eventfilter_baseline_2026_05_04/hidden_persistence_trace.json`

## Verification after code changes

1. Attempted HTML syntax gate:
   - `node tools/check_syntax.js TORONTOEVENTS_ANTIGRAVITY/index.html`
   - Result: tool missing in this repo (`MODULE_NOT_FOUND`).
2. Local JS error smoke:
   - `python tools/serve_local.py`
   - `npx playwright test tests/no_js_errors.spec.ts --project="Desktop Chrome"`
   - Result: known local chunk 404 limitation in this workspace (test fails before runtime assertions).
3. Remote filter suite (post-fix):
   - `VERIFY_REMOTE=1 npx playwright test --config=playwright.filters.config.ts --reporter=list`
   - Result: 8/8 pass; known Next Month 4-card leak remains at same threshold.
4. Lints:
   - `ReadLints` on edited files: no new lint errors.

## Deploy

- Deployed homepage to 50webs mirrors:
  - `python tmp/deploy_homepage.py`
  - Uploaded:
    - `findtorontoevents.ca/index.html`
    - `tdotevent.ca/index.html`
- Deployed GoDaddy mirror homepage:
  - Uploaded `torontoevent.net/index.html` using FTP env credentials.

## Post-deploy verification

- Verified live markers present on all three domains:
  - `__applyFiltersQueued__`
  - `monthDelta`
  - `if (!e.isTrusted) return;`
- Hash/size check:
  - `https://findtorontoevents.ca/` -> sha `b5de38a807a8`, bytes `340938`
  - `https://tdotevent.ca/` -> sha `b5de38a807a8`, bytes `340938`
  - `https://torontoevent.net/` -> sha `3de024444ee7`, bytes `341392` (content markers confirmed)

