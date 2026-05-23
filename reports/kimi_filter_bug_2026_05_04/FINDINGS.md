# Code Review Report: findtorontoevents.ca Event Filtering

**Date:** 2026-05-04
**File reviewed:** `TORONTOEVENTS_ANTIGRAVITY/index.html` (lines 3236–4600)
**Reviewers:** Race-Condition Specialist, Date/Time Specialist, React-DOM Specialist

---

## TL;DR — Your Three Bugs Explained

| Bug | Root Cause | Status |
|-----|-----------|--------|
| **"This Week" + "Next Month" both active** | `_wireThisMonthOverride` uses `stopImmediatePropagation()` in **capture phase**, which **swallows** the programmatic `thisMonthBtn.click()` that `_activateNextMonth` relies on. React stays on "This Week" while your `__nextMonthFilterActive__` flag becomes `true`. | **Confirmed — CRITICAL** |
| **"Next Month" shows wrong month / no events** | Same as above + 120 ms `setTimeout` fires against a partially-updated React DOM + no re-entry guard on `applyFilters()`. Multiple overlapping async passes corrupt the DOM state. | **Confirmed — CRITICAL / HIGH** |
| **"This Month" shows 2025 events** | The **2026-05-03 fix** already addressed the main cause (dropping the "All Dates + Ongoing On" cheat), but **secondary date-parsing bugs** remain: `__parseCardDisplayedDate__` wraps January cards to **2028** in February, and stale Nov/Dec cards survive in January because the wrap heuristic only checks `idx < now.getMonth()`. | **Partially Fixed — Remaining Issues HIGH** |

---

## Architecture Context (Why This Is So Complex)

Your `index.html` is a **~5,700-line imperative vanilla-JS shell** that overrides a Next.js React app's date-filter chip row. The vanilla JS:
- Injects a custom "Next Month" chip into React's chip row
- Intercepts clicks on React's "This Month" chip and rewrites the DOM
- Mutates card visibility, parent grid wrappers, and overlays date badges
- Runs `applyFilters()` from **7+ independent `setTimeout` / MutationObserver sources**

This architecture is inherently fragile because React does not expect external code to mutate its DOM tree. Every re-render risks wiping your mutations.

---

## CRITICAL Findings (Fix Immediately)

### 1. `stopImmediatePropagation()` Swallows Programmatic Clicks — The Dual-Filter Root Cause

**Location:** Lines 4376–4384, 4245–4256

**What happens:**
1. `_wireThisMonthOverride` installs a capture-phase listener on `document`.
2. When a user (or your code) clicks the "This Month" chip, it fires `e.stopImmediatePropagation()`.
3. It then tries to "re-dispatch" via `thisMonthBtn.click()` — but because the event was stopped, this second click **never reaches React**.
4. `_activateNextMonth` (line 4256) calls `thisMonthBtn.click()` to switch React to "This Month" before applying the Next Month filter. This click is **also swallowed**.
5. If React was already showing "This Week", it **stays** on "This Week" while `__nextMonthFilterActive__ = true`.
6. `applyFilters()` then hides everything that is NOT in next month — but React has already hidden everything not in "This Week". The intersection is empty or nearly empty.

**Fix:**
```javascript
// In _wireThisMonthOverride, at the TOP of the handler:
document.addEventListener('click', function (e) {
  if (!e.isTrusted) return;        // Ignore synthetic clicks from _activateNextMonth
  var btn = e.target && e.target.closest && e.target.closest('button');
  if (!btn) return;
  var label = (btn.textContent || '').trim();
  if (label === 'This Month') {
    e.preventDefault();
    e.stopImmediatePropagation();
    // ... rest of handler WITHOUT re-clicking thisMonthBtn synchronously
  }
}, true);
```

Also in `_activateNextMonth`, remove the `thisMonthBtn.click()` entirely and instead:
- Set React's filter state via URL param or direct React state manipulation if exposed, OR
- Simply set `__nextMonthFilterActive__ = true` and let `applyFilters()` do all the work without relying on React's chip.

**If you must keep the current architecture**, defer the programmatic click so it escapes the stopped propagation:
```javascript
// In _activateNextMonth:
setTimeout(function () {
  if (thisMonthBtn) thisMonthBtn.click();
}, 0);
window.__nextMonthFilterActive__ = true;
```

---

### 2. No Global Re-Entry Guard on `applyFilters()` — 7 Async Sources Race

**Location:** Lines 3416–3878

**What happens:** `applyFilters()` can be invoked from 7+ independent sources with **no mutex**:
- 120 ms timeout (Next Month activate)
- 120 ms timeout (Next Month deactivate)
- 180 ms timeout (This Month last-day shortcut)
- 200 ms timeout (This Month normal path)
- 500 ms MutationObserver debounce
- 800 ms capture-click debounce
- 0 ms loop-guard bail-out

When they overlap, the second pass counts against a DOM already mutated by the first pass. The loop-guard can bail incorrectly, and `shownCount`/`hiddenCount` become nonsensical.

**Fix:** Add a global re-entry guard:
```javascript
function applyFilters() {
  if (window.__applyFiltersRunning__) return;
  window.__applyFiltersRunning__ = true;
  try {
    // ... existing body ...
  } finally {
    window.__applyFiltersRunning__ = false;
  }
}
```

And consolidate all scheduling into one cancellable helper:
```javascript
function scheduleApplyFilters(delay) {
  clearTimeout(window._filterTimeout);
  window._filterTimeout = setTimeout(function () {
    safeApply();
  }, delay);
}
```

---

### 3. `_injectNextMonthChip` Fragile to React Row Restructure

**Location:** Lines 4275–4302

**What happens:** The guard `existing.previousElementSibling === thisMonthBtn` assumes the Next Month chip is **immediately after** "This Month". If React adds any new chip (e.g., "Ongoing"), the guard fails, the chip is removed and re-inserted in the wrong position.

**Fix:** Replace strict sibling check with a "still in the same row" check:
```javascript
function _injectNextMonthChip() {
  var thisMonthBtn = _findReactChipByText('This Month');
  if (!thisMonthBtn) return false;
  var chipRow = thisMonthBtn.closest('[class*="chip-row"], [role="tablist"]');
  var existing = document.getElementById('next-month-chip');
  if (existing && chipRow && chipRow.contains(existing)) {
    _setNextMonthChipClass(existing, !!window.__nextMonthFilterActive__);
    return true;
  }
  if (existing && existing.parentNode) existing.parentNode.removeChild(existing);
  // ... create and insert after thisMonthBtn ...
}
```

---

## HIGH Findings (Fix Soon)

### 4. `__parseCardDisplayedDate__` Wrap-Around Bug

**Location:** Lines 4333–4336

**What happens:** `if (idx < now.getMonth()) year += 1` breaks in two directions:
- **January** (`now.getMonth() == 0`): November/December cards (`idx` 10, 11) do NOT satisfy `idx < 0`, so they stay in **current year**. A stale Dec 2026 card in Jan 2027 is parsed as 2027-12-XX (future) and survives the past filter.
- **February** (`now.getMonth() == 1`): January cards (`idx == 0`) satisfy `0 < 1` and get wrapped to **next year** (Jan 2027 → Jan 2028). A legitimate Jan 2027 event running through February is parsed as 2028-01-XX, which the "This Month" overlap check rejects, **hiding a valid ongoing event**.

**Fix:** Use a centered delta:
```javascript
var monthDelta = idx - now.getMonth();
if (monthDelta < -6) year += 1;
else if (monthDelta > 6) year -= 1;
```

---

### 5. `isMultiDayEvent()` UTC→Local Off-by-One

**Location:** Lines 3242–3243

**What happens:** `new Date("2026-05-04T00:00:00Z").toDateString()` parses UTC midnight, then converts to Toronto local time (EDT, UTC−4) → "Sun May 03 2026 8:00 PM". A single-day event appears multi-day, and vice-versa.

**Fix:** Extract YYYY-MM-DD strings directly without constructing Date objects:
```javascript
function isoDateStringToYMD(iso) {
  if (typeof iso !== 'string') return null;
  var m = iso.match(/^\d{4}-\d{2}-\d{2}/);
  return m ? m[0] : null;
}
// In isMultiDayEvent:
const start = isoDateStringToYMD(event.date);
const end = isoDateStringToYMD(event.end_date || event.endDate);
return start && end && start !== end;
```

---

### 6. Raw-Events Cache Uses UTC "Today" — Drops Evening Events

**Location:** Line 94

**What happens:** `_today = new Date().toISOString().slice(0, 10)` is **UTC**. At 11:00 PM EDT (= 3:00 AM UTC next day), `_today` becomes tomorrow's date. Events for the current local day are silently dropped from `window.__RAW_EVENTS__`.

**Fix:** Use local date:
```javascript
var _d = new Date();
var _today = _d.getFullYear() + '-' +
             String(_d.getMonth() + 1).padStart(2, '0') + '-' +
             String(_d.getDate()).padStart(2, '0');
```

---

### 7. `display: none` on `.group` Parent Vulnerable to React Reconciliation

**Location:** Lines 3738–3742

**What happens:** `applyFilters()` sets `gridItem.style.display = 'none'` on the parent wrapper. React can overwrite this inline style on re-render, causing hidden cards to reappear.

**Fix:** Use a CSS class instead of inline style:
```css
/* In injected stylesheet */
.group.event-group-hidden { display: none !important; }
```
```javascript
// In applyFilters:
if (shouldShow) {
  gridItem.classList.remove('event-group-hidden');
} else {
  gridItem.classList.add('event-group-hidden');
}
```

---

### 8. MutationObserver Debounce Too Short for Lazy-Load Batches

**Location:** Lines 4511–4534

**What happens:** The 500 ms debounce fires while React is still inserting cards in waves. The loop-guard sees only the first wave, counts 50 hidden cards, and **prematurely disables the "This Month" override** before the rest of the batch arrives.

**Fix:** Extend debounce to **1200 ms** and reset it on each new mutation:
```javascript
function scheduleSafeApply() {
  clearTimeout(window._filterTimeout);
  window._filterTimeout = setTimeout(function () {
    safeApply();
    hideSkeletons && hideSkeletons();
  }, 1200);
}
```

---

## MEDIUM Findings

### 9. `_renderNextMonthDateBadges` Uses Weak 8-Character Prefix Match

**Location:** Lines 4138–4140

**What happens:** The badge renderer uses `cardTitle.length >= 8` instead of the `_MIN_PARTIAL_NM = 20` used by the main filter. For titles between 8–19 characters, prefix collisions are likely, causing wrong "JUN 5" badges on unrelated cards.

**Fix:** Change guards to 20 characters:
```javascript
var matches = et === cardTitle ||
              (cardTitle.length >= 20 && et.includes(snippet)) ||
              (et.length >= 20 && cardTitle.includes(et.substring(0, 20)));
```

---

### 10. React Can Erase `visibility: hidden` on Date Labels

**Location:** Lines 4207–4226

**What happens:** `_renderNextMonthDateBadges` hides React's intrinsic date label with `node.style.visibility = 'hidden'`. React reconciliation may overwrite this, showing both the original label and the badge.

**Fix:** Make the badge overlay fully opaque so it physically covers the label, or use a CSS `!important` rule injected by vanilla JS that React won't overwrite.

---

## Recommended Fix Priority

### Immediate (Deploy Today)
1. **Add `if (!e.isTrusted) return;`** at the top of `_wireThisMonthOverride` (line 4376) — this alone prevents the dual-filter bug.
2. **Add `window.__applyFiltersRunning__` mutex** at the top of `applyFilters()`.
3. **Fix UTC "today" bug** in the raw-events cache (line 94).
4. **Fix `__parseCardDisplayedDate__` wrap heuristic** (lines 4333–4336).

### This Week
5. **Consolidate all `applyFilters` scheduling** into a single `scheduleApplyFilters(delay)` helper.
6. **Fix `isMultiDayEvent()` timezone bug** (lines 3242–3243).
7. **Strengthen `_injectNextMonthChip` guard** against React row changes.
8. **Switch `.group` inline style to CSS class**.
9. **Extend MutationObserver debounce** to 1200 ms.

### Next Sprint
10. **Refactor the entire imperative filter architecture** to use React props/context instead of DOM mutation. The current approach will keep accumulating bugs as React evolves.

---

## Affected User Scenarios

| Scenario | Bug | Result |
|----------|-----|--------|
| User clicks "This Week", then "Next Month" | Finding 1 | Both appear active; grid is empty or nearly empty |
| User clicks "Next Month" on a slow device | Findings 1 + 2 + 4 | Grid shows wrong month, counter is wrong, or cards flash |
| User clicks "This Month" on Feb 2 | Finding 4 | Legitimate Jan events that run through Feb are hidden |
| User browses at 10:30 PM EDT | Finding 6 | Today's events are missing entirely |
| User clicks "This Month" on last day of month | Findings 1 + 2 | Today chip gets styled inactive but React still shows "This Month" state incorrectly |
| User scrolls on "This Month" filter | Finding 8 | Override disables itself prematurely, showing all dates |

---

*End of Report*
