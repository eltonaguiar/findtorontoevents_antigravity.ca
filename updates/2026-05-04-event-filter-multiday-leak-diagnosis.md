# Multi-Day Event Filter Leak Diagnosis
**Date:** 2026-05-04  
**File:** `TORONTOEVENTS_ANTIGRAVITY/index.html` (~4845 lines)  
**Status:** Diagnosis complete — patches ready

---

## Executive Summary

Multi-day and recurring events are bypassing all three date-window filters (Tomorrow, This Week, This Month) on findtorontoevents.ca. Two root causes account for all observed leaks:

1. **UTC `_today` in cache bootstrap** (line 117) causes `eventData = null` cascading failures
2. **`isMultiDay` defaults to `false` when `eventData` is null** (line 3588) → multi-day filter completely skipped

These combine to form a **two-stage leak chain** that explains every user-reported misbehavior. Below are the detailed root causes, the exact code at fault, and the surgical fixes.

---

## Bug 1 — P0 CRITICAL: UTC `_today` in Cache Bootstrap

**Location:** Line 117, inside the `loadEventsText()` IIFE

**Current broken code:**
```javascript
var _today = new Date().toISOString().slice(0, 10);
```

**Why it's broken:**  
`toISOString()` returns **UTC time**. Toronto is UTC-4 (EDT) or UTC-5 (EST). From 8pm–midnight local time, `_today` is already "tomorrow" UTC. The filter:
```javascript
return _ed.substring(0, 10) >= _today || _end.substring(0, 10) >= _today;
```
Then drops events whose **both** `_ed` and `_end` are before tomorrow-UTC — i.e., all single-day events for the current Toronto date get excluded from `window.__RAW_EVENTS__` during evening hours.

**Cascading effects:**  
When an event is missing from `__RAW_EVENTS__`:
- `eventData` becomes `null` at `applyFilters()` time (lookup fails)
- `isMultiDay` defaults to `false` → **Bug 2 activates** (multi-day filter bypassed)
- Past-filter falls back to `__parseCardDisplayedDate__` → year-ambiguous "MAY 23" zombies can survive
- This Month override misclassifies cards without eventData

**Fix:** Use local date parts instead of UTC:
```javascript
var _now = new Date();
var _today = _now.getFullYear() + '-' +
  String(_now.getMonth() + 1).padStart(2, '0') + '-' +
  String(_now.getDate()).padStart(2, '0');
```

**Blast radius:** 1 line changed, no other code paths affected. The `_today` variable is only used in this one filter closure.

---

## Bug 2 — P0 CRITICAL: isMultiDay Defaults to false When eventData is null

**Location:** Line 3588, inside `applyFilters()`

**Current broken code:**
```javascript
// Multi-day filter
if (!showMultiDayEvents) {
    const isMultiDay = eventData ? isMultiDayEvent(eventData) : false;
    if (isMultiDay) {
        // ... active-today exception logic
    }
}
```

**Why it's broken:**  
When `eventData` is `null` (because the event was dropped from `__RAW_EVENTS__` by Bug 1, or for any other reason like data feed mismatch), `isMultiDay` defaults to `false` and the **entire multi-day filter block is skipped**. The event shows regardless of the `showMultiDayEvents` toggle.

This means:
- Any card rendered by React that doesn't have matching data in `__RAW_EVENTS__` completely bypasses the multi-day gate
- Combined with Bug 1, this affects ALL evening users who see events from today's date
- The `isMultiDayEvent()` function is **never called** for these cards, so even events with explicit `is_multi_day: true` flags slip through

**Fix:** When `eventData` is null, try to detect multi-day status from the card's DOM content:
```javascript
const isMultiDay = eventData ? isMultiDayEvent(eventData) :
    card ? _detectMultiDayFromCard(card) : false;
```

Where `_detectMultiDayFromCard` is a new helper that checks:
1. The card already has a `.multi-day-indicator` badge (indicating a previous run flagged it)
2. The card title contains multi-day keywords
3. The card shows a date range (e.g., "MAY 3–5" pattern)

Or more simply, when `eventData` is null and `showMultiDayEvents` is false, **conservatively hide multi-day-looking cards**:

```javascript
const isMultiDay = eventData ? isMultiDayEvent(eventData) :
    (card ? _looksMultiDayFromCard(card) : false);
```

**Minimum viable fix (lowest risk):** Add a fallback so that when `eventData` is null, the card's existing `.multi-day-indicator` DOM badge is used as evidence:
```javascript
const isMultiDay = eventData ? isMultiDayEvent(eventData) :
    (card && card.querySelector('.multi-day-indicator') ? true : false);
```

---

## Bug 3 — P1 HIGH: Window Filters Don't Suppress Active-Today Exception

**Location:** Lines 3607–3665, inside `applyFilters()` multi-day block

**Current broken code (conceptual):**
```javascript
// Only Today/Tomorrow suppress the active-today exception
var _discreteDayActive = false;
if (_todayBtn && (...active...)) _discreteDayActive = true;
if (_tmrwBtn && (...active...)) _discreteDayActive = true;

// This Week / This Month / Next Month set _anyDateFilterActive but NOT _discreteDayActive
if (_wkBtn && (...active...)) _anyDateFilterActive = true;
if (_tmBtn && (...active...)) _anyDateFilterActive = true;

if (!_activeToday || _discreteDayActive) {
    shouldShow = false;  // Only fires for Today/Tomorrow
}

// Only blocks >31 day exhibitions
if (_anyDateFilterActive && _isLongDuration) {
    shouldShow = false;
}
```

**Why it's broken:**  
When "This Week" or "This Month" is active:
- `_discreteDayActive` remains `false` (only Today/Tomorrow trigger it)
- `_anyDateFilterActive` becomes `true`
- The active-today exception fires: if today falls within the event's [start, end], the event is shown
- The `_isLongDuration` guard only blocks events lasting >31 days
- **Events lasting 2–31 days leak through** (e.g., a 3-day festival, a week-long conference)

Example: "Speed Dating Weekend" running May 2–4:
- isMultiDayEvent → true (title has "Weekend")
- `_activeToday` = true (May 4 is within May 2–4)
- `_discreteDayActive` = false (This Week is active, not Today/Tomorrow)
- `_isLongDuration` = false (2 days)
- **shouldShow stays true** → event leaks through This Week filter

**Fix:** Extend `_discreteDayActive` to also cover window filters (This Week / This Month / Next Month), because **any date-window filter** should suppress the active-today exception — user intent for window filters is "events happening within this window", not "exhibitions that happen to overlap today":

```javascript
// Before: only Today/Tomorrow suppressed
// After: ALL date-window filters suppress the active-today exception
var _discreteDayActive = false;
if (_todayBtn && (...active...)) _discreteDayActive = true;
if (_tmrwBtn && (...active...)) _discreteDayActive = true;
if (_wkBtn && (...active...)) _discreteDayActive = true;    // NEW
if (_tmBtn && (...active...)) _discreteDayActive = true;     // NEW
if (window.__nextMonthFilterActive__) _discreteDayActive = true;  // NEW
if (window.__thisMonthOverrideActive__) _discreteDayActive = true; // NEW
```

Then remove the `_isLongDuration` check since it's no longer needed — ALL multi-day events are hidden under date-window filters when `showMultiDayEvents` is off.

---

## Bug 4 — P1 MEDIUM: Redundant DOM Queries + Unused Top-Level Chip State Variables

**Location:** Lines 3472–3479 (top) vs lines 3619–3630 (inner multi-day block)

**Current code:**
At the TOP of `applyFilters` (lines 3472–3479), chip states are queried once:
```javascript
_todayChipActive = !!(_btnTodayChip && ...);
_tomorrowChipActive = !!(_btnTomorrowChip && ...);
_thisWeekChipActive = !!(_btnThisWeekChip && ...);
_thisMonthChipActive = !!(_btnThisMonthChip && ...);
```

But in the multi-day inner block (lines 3619–3630), the DOM is **re-queried for every card**:
```javascript
var _todayBtn = _findReactChipByText('🔥 Today');
var _tmrwBtn = _findReactChipByText('Tomorrow');
var _wkBtn = _findReactChipByText('This Week');
var _tmBtn = _findReactChipByText('This Month');
```

**Why it's broken:**  
- Wastes O(N×M) DOM queries (N cards × M chip lookups)
- The top-level variables `_todayChipActive`, `_tomorrowChipActive`, `_thisWeekChipActive`, `_thisMonthChipActive` are computed but **never used** later in the function
- The inner block's re-queries could produce different results (e.g., if React re-renders between queries)

**Fix:** Reuse the top-level variables directly in the multi-day block instead of re-querying:
```javascript
var _discreteDayActive = false;
if (_todayChipActive) _discreteDayActive = true;
if (_tomorrowChipActive) _discreteDayActive = true;
if (_thisWeekChipActive) _discreteDayActive = true;    // NEW
if (_thisMonthChipActive) _discreteDayActive = true;    // NEW
if (window.__nextMonthFilterActive__) _discreteDayActive = true;  // NEW
if (window.__thisMonthOverrideActive__) _discreteDayActive = true; // NEW
```

This also fixes Bug 3 in the same pass.

---

## Bug 5 — P2 LOW: isMultiDayEvent Keyword Matching Over-Fires

**Location:** Lines 3283–3285

**Current code:**
```javascript
const multiDayKeywords = ['festival', 'week', 'weekend', 'days', 'exhibition', 'exhibit', 'runs until', 'through'];
return multiDayKeywords.some(keyword => title.includes(keyword));
```

**Why it's problematic:**  
- `'days'` matches "30 Days of Night" (movie screening, single day)
- `'week'` matches "This Week in Toronto" (newsletter, not multi-day)
- `'festival'` matches "Toronto Festival of Beer" even if it's a single-day tasting event
- These false positives cause events to enter the multi-day filter path when they shouldn't

**Fix (low priority):** Add a guard: only apply keyword matching when the event has no explicit `end_date`:
```javascript
// Only keyword-match when there's no explicit end_date to check
if (event.end_date || event.endDate) return false; // already checked above
const title = (event.title || '').toLowerCase();
const multiDayKeywords = ['festival', 'weekend', 'exhibition', 'exhibit', 'runs until', 'through'];
// Removed: 'week', 'days' — too many false positives
return multiDayKeywords.some(keyword => title.includes(keyword));
```

---

## Bug 6 — P2 LOW: isMultiDayEvent UTC Date Parse for toDateString()

**Location:** Lines 3274–3275

**Current code:**
```javascript
const start = new Date(event.date).toDateString();
const end = new Date(event.end_date || event.endDate).toDateString();
return start !== end;
```

**Why it's bug-prone:**  
`new Date("2026-05-05")` parses as **UTC midnight**. In Toronto (UTC-4), `new Date("2026-05-05")` is May 4 at 8pm local. `.toDateString()` returns "Mon May 04 2026" for that local time, not "Tue May 05 2026". This means two dates that are genuinely different calendar days could return the same `.toDateString()` at the right timezone offset, causing missed multi-day detection.

For Toronto EDT (UTC-4), `new Date("2026-05-05").toDateString()` = "Mon May 04 2026" — WRONG! It should be "Tue May 05 2026".

**Fix:** Compare date strings directly without constructing Date objects:
```javascript
if (event.end_date || event.endDate) {
    const startYMD = String(event.date).substring(0, 10);
    const endYMD = String(event.end_date || event.endDate).substring(0, 10);
    return startYMD !== endYMD;
}
```

---

## Complete Leak Chain (How Bugs 1+2 Interact)

```
User clicks "Tomorrow" filter chip
         │
         ▼
React shows cards with start_date = tomorrow (including multi-day 3-day festival starting tomorrow)
         │
         ▼
applyFilters() runs
         │
    ┌────┴────┐
    │          │
    ▼          ▼
[lookup eventData in __RAW_EVENTS__]
    │
    ├─ FOUND → isMultiDay = isMultiDayEvent(eventData) → correct behavior
    │
    └─ NULL (Bug 1: UTC _today dropped today's events from cache)
            │
            ▼
       isMultiDay = false   ← Bug 2: defaults to false, skips entire multi-day block
            │
            ▼
       shouldShow stays true → EVENT LEAKS through Tomorrow filter
```

For This Week / This Month:
```
User clicks "This Week" filter
         │
         ▼
React shows cards (its own internal filtering)
         │
         ▼
applyFilters() runs
         │
         ▼
Multi-day filter: isMultiDay = true (eventData found, event IS multi-day)
         │
         ▼
_activeToday = true (today falls within event range)
         │
         ▼
_discreteDayActive = false (Bug 3: This Week doesn't trigger it)
         │
         ▼
_isLongDuration = false (event is only 5 days)
         │
         ▼
shouldShow stays true → EVENT LEAKS through This Week filter
```

---

## Proposed Fix Order (Ship Order)

| Priority | Bug | Lines | Δ | Risk |
|----------|-----|-------|---|------|
| **P0** | Bug 1: UTC `_today` → local date parts | ~117 | +5/-1 | Low |
| **P0** | Bug 2: isMultiDay fallback when eventData null | ~3588 | +6/-1 | Low |
| **P1** | Bug 3+4: Extend _discreteDayActive + reuse top vars | ~3607-3665 | +5/-10 | Low |
| **P2** | Bug 5: Tighten keyword matching | ~3283-3285 | +2/-1 | Low |
| **P2** | Bug 6: String-compare dates in isMultiDayEvent | ~3274-3275 | +2/-2 | Very Low |

---

## Testing Verification

After applying P0+P1 fixes, verify:

1. **UTC evening test:** Mock `Date` to 10pm EDT (UTC-4 → next day UTC). Verify events for current Toronto date appear in the grid.
2. **Tomorrow filter + multi-day:** Click "Tomorrow". Assert no multi-day events appear without enabling the multi-day toggle.
3. **This Week filter + multi-day:** Click "This Week". Assert no multi-day events appear without the toggle.
4. **This Month filter + multi-day:** Click "This Month". Assert no exhibitions (>31 day) or multi-day (2-31 day) events appear without the toggle.
5. **Multi-day toggle ON:** Enable the multi-day toggle. Verify multi-day events DO appear under all filters (regression check).
6. **Console check:** Run `[...document.querySelectorAll('[class*="glass-panel"]:not(.animate-pulse)')].filter(c => c.querySelector('.multi-day-indicator') && !c.classList.contains('event-card-hidden')).length` — should be 0 when multi-day toggle is OFF and any date-window filter is active.

---

## Deployment Notes

- Edit only `TORONTOEVENTS_ANTIGRAVITY/index.html`
- Deploy via `tmp/deploy_homepage.py` to:
  - 50webs: `findtorontoevents.ca/index.html` + `tdotevent.ca/index.html`
  - GoDaddy: `torontoevent.net/index.html`
- Verify all 3 domains post-deploy
- Playwright test: `tests/playwright/test_event_date_filters.spec.ts`

---

## References

- Prior report: `reports/eventfilter_e2e_review_2026_05_04.md`
- Prior investigation: `reports/findtorontoevents_filter_bugs_2026_05_04.md`
- Incident plan: `C:/Users/zerou/.cursor/plans/events-swarm-incident-plan_91d51306.plan.md`
- PR #753: `_wireThisMonthOverride` isTrusted guard
- PR #751: cache bootstrap end_date filter
- PR #770: multi-day Today/Tomorrow fix
