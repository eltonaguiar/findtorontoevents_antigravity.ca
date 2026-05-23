# Date Filter Bug Fix — "This Month" and "Next Month"

**Date:** 2026-05-04  
**Branch:** `copilot/fix-month-filter-issues`  
**Reported:** User observed "This Month" showing 2025 events and events labelled with other months' dates; "Next Month" showing "MAY xx" labels instead of "JUN xx".

---

## Root Cause Analysis

### Bug A — "This Month" shows zombie 2025 events (same-month year ambiguity)

**Evidence from `next/events.json` (11 290 events total):**

| Event title | `date` field |
|---|---|
| Declaration of the Understory | `2025-05-23T12:00:00Z` |
| Bathed in Strange Light | `2025-05-23T12:00:00Z` |

Both are 2025 shows that were never removed from the feed.

**How they slip through the filter chain:**

The fetch interceptor (line 94-98 of `index.html`) pre-filters `window.__RAW_EVENTS__` to only events with `start_date >= today` (2026-05-04). The 2025-05-23 events are **excluded** from `__RAW_EVENTS__`. However, the same interceptor returns the **unfiltered** JSON text to React, so React still renders cards for these events.

When `applyFilters()` runs under "This Month" mode:

1. `eventData = null` — the card title lookup against `__RAW_EVENTS__` finds nothing.
2. Past-events fallback calls `__parseCardDisplayedDate__(card)`.
3. The parser reads `"MAY 23"` from the card header → month index = 4 (May).  
   The wrap-around guard only activates when `idx < now.getMonth()` i.e. `4 < 4` → **false** → year is assigned as **2026** (not 2025).
4. Parsed date = `2026-05-23`.
5. Past filter: `'2026-05-23' >= '2026-05-04'` → **passes** (looks like a future event).
6. This Month window `['2026-05-04', '2026-05-31']`: `'2026-05-23'` is inside → **card shown** ❌

The 2025-05-23 zombie appears as a current May 2026 event.

---

### Bug B — "This Month" hides 80 multi-day events still actively running

**Evidence:**

```
$ python3 -c "
import json
from datetime import datetime
with open('next/events.json') as f: events = json.load(f)
today = '2026-05-04'
running = [e for e in events
           if str(e.get('date',''))[:10] < today
           and str(e.get('end_date') or e.get('endDate') or e.get('date',''))[:10] >= today]
print(len(running), 'multi-day still-running events')
for e in running[:8]:
    print(' ', e['date'][:10], '->', (e.get('end_date') or '')[:10], e.get('title','')[:55])
"

80 multi-day still-running events
  2025-12-03 -> 2026-05-17  & Juliet
  2026-01-01 -> 2026-12-31  Toronto History Museums Free Admission
  2026-01-01 -> 2026-05-31  The Wedding Party: A Dinner Theatre Escape Room
  2026-01-06 -> 2026-05-20  Free Concert Series – Canadian Opera Company
  2026-01-16 -> 2026-05-08  21C Music Festival
  2026-02-01 -> 2026-08-31  Building Black AMORPHIA: Spiritual Starships
  2026-02-12 -> 2026-05-15  Toronto Union Presents A Kind Of Order
  2026-02-21 -> 2026-12-19  Toronto Comedy All Stars at Comedy Bar
```

The old pre-filter only checked `start_date >= today`. Events like "& Juliet" (opens 2025-12-03, closes 2026-05-17) had `start < today` and were removed from `__RAW_EVENTS__`. This caused `eventData = null` for these cards. `__parseCardDisplayedDate__("DEC 3")` assigned year 2026 (Dec index 11 ≥ May index 4 → no year-wrap → 2026). The This Month window check then rejected `'2026-12-03' <= '2026-05-31'` → card hidden even though the show is running through May 17.

---

### Bug C — "Next Month" shows "MAY xx" labels (React date label not hidden)

When "Next Month" is active, `_renderNextMonthDateBadges()` overlays a "JUN x" badge on each card and tries to hide the React date element via `visibility: hidden`. The hiding logic was:

```js
if (/^([A-Z]{3})\s*\n?\s*(\d{1,2})\b/i.test(_t) && _t.length <= 12) {
```

The `_t.length <= 12` constraint was designed to target narrow date-only spans, but React's EventCard can render the date container with day-of-week or year appended (e.g. `"MAY 8 Wednesday"` = 15 chars, `"MAY 8\n2026"` in a compact view = 9–12 chars, `"MAY 08, 2026"` = 12 chars but tighter marginal cases). Anything exceeding 12 characters silently skipped the hide step — so the original "MAY 8" label remained visible beside or behind the opaque "JUN 8" badge overlay.

---

## Fixes Applied

### Fix 1 — `__RAW_EVENTS__` pre-filter: also retain currently-running events (`end_date >= today`)

**File:** `TORONTOEVENTS_ANTIGRAVITY/index.html` lines 93-99

Old filter logic (start-only):
```js
var _today = new Date().toISOString().slice(0, 10);
events = events.filter(function(e) {
  var _ed = e.date || e.start_date || e.startDate || "";
  return !_ed || _ed >= _today;
});
```

New filter logic (start OR still-running):
```js
var _today = new Date().toISOString().slice(0, 10);
events = events.filter(function(e) {
  var _ed = String(e.date || e.start_date || e.startDate || '');
  if (!_ed) return true;
  var _end = String(e.end_date || e.endDate || _ed);
  return _ed.substring(0, 10) >= _today || _end.substring(0, 10) >= _today;
});
```

**Effect:** 80 multi-day running events are now included in `__RAW_EVENTS__`. `applyFilters()` finds `eventData` for them; the This Month overlap gate (`eStart ≤ monthEnd && eEnd ≥ today`) correctly shows them. The 2025-05-23 zombie events (both `start` and `end` = `2025-05-23 < today`) remain excluded — addressed separately by Fix 2.

**Pool size change:** `__RAW_EVENTS__` grows from ~6 806 to ~6 886 events (+80).

---

### Fix 2 — "This Month" mode: hide cards with no `eventData` when `__RAW_EVENTS__` is loaded

**File:** `TORONTOEVENTS_ANTIGRAVITY/index.html` — "This Month" fallback block

Old (unconditional display-parse fallback):
```js
if (!_eStartTM) {
  var _disp = window.__parseCardDisplayedDate__ && window.__parseCardDisplayedDate__(card);
  if (_disp) { _eStartTM = _disp; _eEndTM = _disp; }
}
```

New (hide when reference data confirms event is not in feed):
```js
if (!_eStartTM) {
  if (!eventData && window.__RAW_EVENTS__) {
    // __RAW_EVENTS__ loaded but event absent → past/zombie card; year-ambiguous.
    shouldShow = false;
  } else {
    var _disp = window.__parseCardDisplayedDate__ && window.__parseCardDisplayedDate__(card);
    if (_disp) { _eStartTM = _disp; _eEndTM = _disp; }
  }
}
```

**Logic:** If `__RAW_EVENTS__` is loaded and the event is absent from it, the event has a `start_date < today` (the pre-filter excluded it). We cannot reliably determine its year from display text (the same-month wrap-around bug). We hide it. The guard `window.__RAW_EVENTS__` ensures the pre-fetch race window (page just loaded) falls back to the old behaviour and doesn't blank the grid.

**What remains visible:** Any event with `eventData` (i.e. start ≥ today **or** end ≥ today after Fix 1) continues to be evaluated normally by the overlap gate.

---

### Fix 3 — Next Month badge: increase React date-element length limit from 12 → 30

**File:** `TORONTOEVENTS_ANTIGRAVITY/index.html` line ~4240

Old:
```js
if (/^([A-Z]{3})\s*\n?\s*(\d{1,2})\b/i.test(_t) && _t.length <= 12) {
```

New:
```js
if (/^([A-Z]{3})\s*\n?\s*(\d{1,2})\b/i.test(_t) && _t.length <= 30) {
```

**Why 30:** covers all observed React EventCard date renders including day-of-week (`"MAY 8 Wednesday"` = 15 chars) and date-plus-year (`"MAY 08, 2026"` = 12 chars). The regex anchor `^([A-Z]{3})…` already ensures the element STARTS with a month abbreviation, so false-positive hiding of long description paragraphs is not a concern.

---

## Verification

### Unit tests — all pass unchanged

```
$ node --test tests/event_date_filters.unit.test.js

✔ getNextMonthWindow: May 1 2026 → June 1..30 2026
✔ getNextMonthWindow: Dec 15 2026 → Jan 1..31 2027 (year wrap)
... (23 tests)
ℹ pass 23 / fail 0
```

### Data verification

```
Events in next/events.json:
  Total:                      11 290
  Future (start >= 2026-05-04):  6 806
  Multi-day still running:          80   ← added to __RAW_EVENTS__ by Fix 1
  Past-only (both dates < today):  4 404  ← excluded (includes 2025-05-23 zombies)
```

---

## Impact Summary

| Symptom | Root cause | Fix |
|---|---|---|
| "This Month" shows 2025-05-23 zombie events | Same-month display text is year-ambiguous; event absent from `__RAW_EVENTS__` | Fix 2: hide cards without `eventData` when feed is loaded |
| "This Month" hides long-running shows (& Juliet, museums, etc.) | `end_date` not considered in `__RAW_EVENTS__` pre-filter | Fix 1: retain events where `end_date >= today` |
| "Next Month" shows "MAY xx" labels instead of "JUN xx" | `_t.length <= 12` check skipped hiding for React date elements > 12 chars | Fix 3: raise limit to 30 |
