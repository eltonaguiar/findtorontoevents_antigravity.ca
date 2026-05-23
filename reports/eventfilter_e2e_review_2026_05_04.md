# Event Filter Pipeline — End-to-End Review (2026-05-04)

**Method:** 5-agent swarm dispatched against `TORONTOEVENTS_ANTIGRAVITY/index.html` (~5800 lines) + supporting scripts. 4 specialists actually ran (race-condition / datetime-timezone / react-dom / event-surface-engineer); coordinator-synthesizer step was skipped by the dispatcher (this doc IS the synthesis). Engine coverage: cerebras only (nous flaked, dispatcher was supposed to fan to 5 engines but only ran 2). Single-engine output — treat findings as candidates needing cross-validation, not consensus.

**Inputs:**
- `swarm_runs/eventfilter_review_2026_05_04/race_condition_specialist/cerebras.json.raw.txt`
- `swarm_runs/eventfilter_review_2026_05_04/datetime_timezone_specialist/cerebras.json.raw.txt`
- `swarm_runs/eventfilter_review_2026_05_04/react_dom_specialist/cerebras.json.raw.txt`
- `swarm_runs/eventfilter_review_2026_05_04/event_surface_engineer/cerebras.json.raw.txt`

---

## TL;DR — top 12 findings ranked by ship-priority

| # | Severity | Where | Bug | Owner persona |
|---|---|---|---|---|
| 1 | **CRITICAL** | `index.html:4412-4428` (`__parseCardDisplayedDate__`) | Year-wrap heuristic still one-sided: Jan/DEC card on Jan 5 returns 2026-12-25 instead of 2025-12-25. **STILL PRESENT** despite Kimi flag earlier. | datetime-timezone-specialist |
| 2 | **CRITICAL** | `index.html:14-19, 125` (boot/cache) | `__RAW_EVENTS__` loads full 11,290 rows; ~40% are past events that inflate payload + cause O(N×M) filter latency >2s on Tomorrow click. | event-surface-engineer |
| 3 | **CRITICAL** | `index.html:3500-3514` (title-match loop) | No title index — every card runs `__RAW_EVENTS__.filter(_matchPredicate)` = 50 × 11,290 string comparisons per chip click → CPU spike. | event-surface-engineer |
| 4 | **CRITICAL** | `index.html:4467-4543` (This-Month capture listener) + `:4551-4561` (Sibling deactivator) | Programmatic click on "This Month" via `_activateNextMonth` unintentionally fires the sibling deactivator → `__nextMonthFilterActive__` flips false, leaving impossible UI state. | race-condition-specialist |
| 5 | **CRITICAL** | `index.html:3803-3819` (`gridItem.classList.add('event-group-hidden')`) | React reconciliation overwrites `className` on the wrapper, removing `event-group-hidden` → hidden cards reappear after scroll. | react-dom-specialist |
| 6 | **HIGH** | `index.html:3517-3522` (multi-day overlap check) | UTC ISO timestamps compared against local YMD string. After 20:00 EDT, today's events surface as "tomorrow" because UTC has already rolled over. | datetime-timezone-specialist |
| 7 | **HIGH** | `index.html:3447-3461` (mutex) | `applyFilters` mutex (PR #753) silently DROPS calls with no retry queue. Newly-injected lazy-loaded cards can miss filtering pass. | race-condition-specialist |
| 8 | **HIGH** | `index.html:96-108` (boot guard) | Fallback cache-warm path is documented in comments but NOT IMPLEMENTED. CDN outage → blank UI. | event-surface-engineer |
| 9 | **HIGH** | `index.html:2542-2555` (chip observer) | Re-injection of Next-Month chip can re-fire its own MutationObserver → infinite loop until 250ms debounce kicks in. | react-dom-specialist |
| 10 | **HIGH** | feed drift | `/events.json` = 11,290 events vs `/next/events.json` = 6,909 events. Title-lookup misses on the difference cause `eventData=null` fallback. | event-surface-engineer (data-quality-auditor) |
| 11 | **MEDIUM** | `index.html:3592, 3667, 3737` (date field reads) | Inconsistent `end_date` vs `endDate` field names — multi-day events with `endDate` only get dropped from window filters. | event-surface-engineer |
| 12 | **MEDIUM** | `index.html:4473-4479, 4485-4492` (rapid-click race) | 200ms timer of first click overwrites flag set by second click — "This Month → Tomorrow → This Month" within 200ms produces stale flag. | race-condition-specialist |

---

## SHIP-TODAY (4 fixes, P0+P1, low blast radius)

### 1. Year-wrap heuristic — centered delta (CRITICAL)

`TORONTOEVENTS_ANTIGRAVITY/index.html:4412-4428`. Replace one-sided `if (idx < now.getMonth()) year += 1` with centered delta:

```js
const delta = monthIdx - now.getMonth();
const year = delta < -6 ? now.getFullYear() - 1
           : delta >  6 ? now.getFullYear() + 1
           :              now.getFullYear();
```

Handles Dec→Jan boundary correctly. **Same fix Kimi flagged on 2026-05-04 that didn't fully land.** Test: assert "DEC 25" parsed in early January returns last year, not next.

### 2. UTC `_today` → local YMD (HIGH)

`index.html:3517-3522` and any `new Date().toISOString().slice(0,10)`. Replace with local-date helper:

```js
function _localTodayYMD() {
  const d = new Date();
  return d.getFullYear() + '-' + String(d.getMonth()+1).padStart(2,'0') + '-' + String(d.getDate()).padStart(2,'0');
}
```

Already partially in main per PR #753 but the multi-day overlap check at `:3517` still uses `__todayStart` constructed via `Date()` which is local — but the comparison is against ISO `event.date.substring(0,10)` which IS UTC-derived. After 20:00 EDT this misclassifies. Test: mock 23:00 EDT (03:00 UTC next day) and confirm today = local-23h day, not UTC-tomorrow.

### 3. applyFilters mutex retry queue (HIGH)

`index.html:3447-3461`. Replace silent early-return with queued retry:

```js
if (window.__applyFiltersRunning__) {
  window.__applyFiltersQueued__ = true;
  return;
}
window.__applyFiltersRunning__ = true;
try { /* existing body */ }
finally {
  window.__applyFiltersRunning__ = false;
  if (window.__applyFiltersQueued__) {
    window.__applyFiltersQueued__ = false;
    setTimeout(applyFilters, 0);
  }
}
```

Test: rapid-click 5 chips within 100ms; assert final DOM matches the LAST clicked chip's filter, not the first.

### 4. e.isTrusted guard on sibling-chip deactivator (CRITICAL)

`index.html:4551-4561`. The sibling deactivator that flips `__nextMonthFilterActive__` to false runs on ANY click event — including synthetic clicks from `_activateNextMonth`'s programmatic `thisMonthBtn.click()`. Add the same `isTrusted` guard PR #753 added to `_wireThisMonthOverride`:

```js
if (!e.isTrusted) return;
```

Test: rapid-fire `_activateNextMonth()` from JS console; assert `__nextMonthFilterActive__` stays true.

---

## THIS WEEK (4 fixes, MEDIUM-HIGH)

### 5. Replace `gridItem.classList.add` with React-safe hide (CRITICAL but blast-radius wider)

Cerebras's recommendation: instead of `classList.add('event-group-hidden')` on the React-owned wrapper, inject a higher-specificity CSS rule into `<head>` and toggle a non-Tailwind class that React doesn't manage. Or better: wrap the `<EventsGrid>` in a static `<div id="grid-root">` and query that. This is bigger surgery — needs careful staging.

### 6. Field-name normalizer (MEDIUM)

```js
function normalize(e) {
  e.end_date = e.end_date || e.endDate;
  e.start_date = e.start_date || e.startDate || e.date;
  return e;
}
```
Run on every `__RAW_EVENTS__` row at boot. Fixes the multi-day-disappears-on-window-filter bug.

### 7. Cache-warm fallback path (HIGH)

`index.html:96-108` — implement what the comment promises. On fetch error, read `localStorage.getItem('eventsCache')`, show "stale data" badge, schedule retry.

### 8. Title index Map (CRITICAL — performance)

After `__RAW_EVENTS__` is set, build `Map<normalizedTitle, Event[]>`. Replace per-card `.filter` with `titleIndex.get(...)`. Cerebras estimates this brings `applyFilters` from >2s to <300ms.

---

## NEXT SPRINT (4 fixes, MEDIUM-LOW)

9. Schema validation on raw feed load (drop malformed rows; log).
10. Future-only endpoint (`/events.future.json`) + boot fetch.
11. Periodic re-fetch at 00:05 local (long-session midnight rollover).
12. Recurrence dedup via short-title hash (currently `_MIN_PARTIAL_MATCH_LEN=20` excludes "Yoga", "Jazz" etc.).

---

## What's NOT in scope of this review

- The minified React bundle `afe53b3593ec888c.js` itself — observable only via console; can't audit source. `event-surface-engineer` flagged 2 findings inferred from console behavior (feed drift + duplicate fetches) but cannot verify code-level claims.
- The audit dashboard at `/audit` — separate codebase under `audit_dashboard/`. Not in this pass.

---

## Engine health note

Subagent's dispatch instruction was 5 engines per specialist (deepseek/xai/nous/cerebras/kimi). Actual run produced only **cerebras + nous** outputs per specialist; **nous returned empty** in all 4 specialists (consistent with our earlier observation that nous Hermes-4 flakes on long prompts ~10-15% of calls). Effective coverage: **single-engine (cerebras) per specialist**. Findings should be treated as candidates needing a follow-up cross-validation pass with deepseek + xai before committing P0 fixes blindly.

The dispatcher subagent also stopped before running the coordinator-synthesizer step, which is why this doc is hand-synthesized. To produce a higher-confidence ranked plan, re-run with explicit engine selection and verify the coordinator step lands.

## Recommended next-3 fix PRs (in order)

1. **`fix(homepage): __parseCardDisplayedDate__ centered-delta year wrap`** — closes the Kimi-flagged bug that didn't fully land. Smallest blast radius; biggest correctness win.
2. **`fix(homepage): isTrusted guard on sibling-chip deactivator`** — closes the sibling-deactivator-fires-on-synthetic-click bug. Mirrors PR #753 pattern. Tiny diff.
3. **`fix(homepage): applyFilters mutex retry queue`** — replaces silent drop with one-shot retry. Surfaces edge-case timing bugs that the current early-return masks.

🤖 Synthesized from 4 cerebras specialist outputs (race-condition, datetime-timezone, react-dom, event-surface-engineer) + cross-reference to existing session work (PRs #746–#770 + Kimi audit + cursor reports). Single-engine coverage; cross-validate with deepseek/xai before committing P0 fixes.
