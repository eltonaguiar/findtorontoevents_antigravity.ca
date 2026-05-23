# Date/Time & Timezone Bug Analysis Report
## File: `/mnt/agents/repos/index.html`

---

## Finding 1: `__eventInNextMonth__` Month Computation — VERIFIED CORRECT

- **Severity**: LOW (documentation only)
- **Location**: Lines 4006–4010
- **Root Cause**: None — the logic is correct. `nextM = now.getMonth() + 1` yields the 0-indexed month of next month. `String(nextM + 1).padStart(2, '0')` correctly converts to 1-based month number. December rollover (`nextM = 12 → nextM = 0, nextY++`) is handled before the string formatting, so January of the next year produces `"01"`. The `new Date(nextY, nextM + 1, 0)` call correctly computes the last day of the target month because `new Date(year, month+1, 0)` returns the final day of `month`.
- **Fix Recommendation**: No code change needed. Consider adding an inline comment confirming the 0-index → 1-index conversion is intentional.
- **Affected Scenario**: N/A.

---

## Finding 2: `__parseCardDisplayedDate__` — Broken Wrap-Around Heuristic (HIGH)

- **Severity**: HIGH
- **Location**: Lines 4333–4336
- **Root Cause**: The heuristic `if (idx < now.getMonth()) year += 1` assumes that any displayed month numerically before the current month must belong to next year. This is wrong in two directions: (a) In January (`now.getMonth() == 0`), a November or December card (`idx` 10 or 11) does NOT satisfy `idx < 0`, so it stays in the current year — a stale Nov/Dec 2026 card in Jan 2027 is misread as 2027 instead of being dropped. (b) In February (`now.getMonth() == 1`), a January card (`idx == 0`) satisfies `0 < 1` and gets wrapped to **next** year (e.g., Jan 2027 → Jan 2028). A legitimate January 2027 event shown in February 2027 is therefore parsed as 2028-01-XX, which the "This Month" override (Feb 2027 window) will reject as non-overlapping, **hiding a currently-running event**.
- **Fix Recommendation**: Replace the single comparison with a centered delta check:
```javascript
var monthDelta = idx - now.getMonth();
if (monthDelta < -6) year += 1;       // card is >6 months behind → next year
else if (monthDelta > 6) year -= 1;   // card is >6 months ahead → previous year
```
Alternatively, always prefer `eventData.date` when available and treat parsed-display-date as a last-resort fallback with a large uncertainty margin.
- **Affected Scenario**: User clicks "This Month" on February 2; a multi-day event whose card still shows "JAN 15" (because React renders the first-occurrence date) is parsed as 2028-01-15 and hidden even though `eventData.end_date` says it runs through February.

---

## Finding 3: Past-Events Filter False-Negative from Parser Wrap Bug (MEDIUM)

- **Severity**: MEDIUM
- **Location**: Lines 3595–3633 (with root cause at 4321–4337)
- **Root Cause**: The user's specific scenario ("DEC 25 in January 2027 parsed as 2026-12-25") does **not** occur because `idx=11` is not `< now.getMonth()=0`, so the year stays 2027 and the parser returns **2027-12-25** (a future date). The stale card therefore **survives** the past filter (`2027-12-25 >= 2027-01-02`) instead of being dropped. This is a **false-negative** (past event shown), not a false-positive (future event hidden). However, the *reverse* wrap bug (Finding 2) does cause false-positives: a legitimate Jan 2027 event in Feb 2027 is parsed as Jan 2028, survives the past filter, but is then rejected by the "This Month" window overlap check (`2028-01-15` does not overlap February 2027).
- **Fix Recommendation**: Fix `__parseCardDisplayedDate__` per Finding 2. Additionally, make the past filter even more conservative when the fallback parser is used: if the parsed date is > 6 months in the future, treat it as unreliable and do NOT use it to keep a card visible.
- **Affected Scenario**: User clicks "This Month" in early February; a January-start ongoing event is dropped because its displayed date is mis-wrapped to the following year.

---

## Finding 4: `_renderNextMonthDateBadges` Uses Weak 8-Character Prefix Match (MEDIUM)

- **Severity**: MEDIUM
- **Location**: Lines 4138–4140
- **Root Cause**: The badge renderer uses `cardTitle.length >= 8` and `et.length >= 8` as guards for prefix matching, whereas `__eventInNextMonth__` (line 4054–4064) uses `_MIN_PARTIAL_NM = 20`. For titles between 8 and 19 characters, the badge logic permits prefix matches that the main filter rejects. Example: card "The Show" (8 chars) could match raw events "The Show Must Go On", "The Showcase", and "The Showdown", causing the wrong next-month date badge to be overlaid on an unrelated card.
- **Fix Recommendation**: Change both guards to `_MIN_PARTIAL_NM` (20):
```javascript
var matches = et === cardTitle ||
              (cardTitle.length >= _MIN_PARTIAL_NM && et.includes(snippet)) ||
              (et.length >= _MIN_PARTIAL_NM && cardTitle.includes(et.substring(0, _MIN_PARTIAL_NM)));
```
- **Affected Scenario**: User clicks "Next Month"; two distinct events share an 8-character prefix (e.g., "Toronto …") and the wrong JUN 5 badge is painted on a card that actually has no June occurrence.

---

## Finding 5: `isMultiDayEvent()` UTC→Local Timezone Off-by-One (HIGH)

- **Severity**: HIGH
- **Location**: Lines 3242–3243
- **Root Cause**: `new Date("2026-05-04T00:00:00Z")` parses the string as **UTC** midnight, then `toDateString()` renders it in **local** time. In Toronto (EDT, UTC−4), this becomes May 3 at 8:00 PM, producing `"Sun May 03 2026"`. If the event's local start is May 4, the `start !== end` check may return `true` (multi-day) even when the event is truly single-day, or vice-versa. A single-day festival running midnight-to-midnight UTC therefore appears as a two-day event locally. Conversely, a true multi-day event could appear single-day if both UTC dates fall on the same local date after the shift.
- **Fix Recommendation**: Do not construct a Date object for ISO strings when only the calendar date is needed. Extract the date part directly:
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
- **Affected Scenario**: Any event with a UTC-midnight ISO timestamp viewed in a timezone west of UTC (e.g., all of the Americas). The multi-day toggle and related UI will miscategorize the event.

---

## Finding 6: Raw-Events Cache Uses UTC "Today" Against Local-Concept Event Dates (HIGH)

- **Severity**: HIGH
- **Location**: Line 94
- **Root Cause**: `_today = new Date().toISOString().slice(0, 10)` extracts the **UTC** calendar date. When local time is late evening (e.g., May 5 at 11:00 PM EDT = May 6 at 3:00 AM UTC), `_today` becomes `"2026-05-06"`. An event with `date: "2026-05-05"` is then filtered out as past (`"2026-05-05" < "2026-05-06"`) even though it is still the active local day. This silently drops legitimate same-day events from `__RAW_EVENTS__`, which means they never reach the DOM and are invisible to all downstream filters.
- **Fix Recommendation**: Use the local calendar date consistently:
```javascript
var _d = new Date();
var _today = _d.getFullYear() + '-' +
             String(_d.getMonth() + 1).padStart(2, '0') + '-' +
             String(_d.getDate()).padStart(2, '0');
```
- **Affected Scenario**: Any user browsing between 8:00 PM and 11:59 PM EDT (or equivalent offset in other western timezones). Events for the current local day are missing from the cache entirely.

---

## Finding 7: `__parseCardDisplayedDate__` Relies on `new Date()` for `now`, Risking Midnight Shift (LOW)

- **Severity**: LOW
- **Location**: Lines 4331–4336
- **Root Cause**: `__parseCardDisplayedDate__` calls `new Date()` to obtain `now.getFullYear()` and `now.getMonth()`. Because `applyFilters()` is long-running and loops over many cards, if the execution straddles local midnight, the first card might be parsed relative to Day N while the last card is parsed relative to Day N+1. In the worst case, a card with displayed month equal to the current month could be wrapped to next year for the first 999 cards but not the 1000th, producing inconsistent classification within a single filter pass.
- **Fix Recommendation**: Accept an optional `referenceDate` parameter, and have `applyFilters()` pass `__todayStart` (already computed at line 3418) so every card uses the same anchor:
```javascript
window.__parseCardDisplayedDate__ = function (card, refDate) {
  var now = refDate || new Date();
  // ... rest unchanged
};
// In applyFilters:
var _disp = window.__parseCardDisplayedDate__ &&
            window.__parseCardDisplayedDate__(card, __todayStart);
```
- **Affected Scenario**: Very rare — only if a filter run crosses midnight and the user has a large number of cards loaded.

---

## Summary Table

| # | Severity | Location | Bug | Primary Impact |
|---|----------|----------|-----|----------------|
| 1 | LOW | 4006–4010 | (None — verified correct) | — |
| 2 | HIGH | 4333–4336 | Wrap heuristic mis-classifies months before current month as next year, and Nov/Dec in Jan as current year | This Month override hides legitimate ongoing events; stale cards survive past filter |
| 3 | MEDIUM | 3595–3633 | Past filter accepts mis-parsed dates from #2 | False-negative: stale cards shown; false-positive: legitimate Jan events hidden in Feb |
| 4 | MEDIUM | 4138–4140 | 8-char prefix match instead of 20-char | Wrong date badge overlay on similarly-named events |
| 5 | HIGH | 3242–3243 | `new Date(iso).toDateString()` shifts UTC midnight to previous local day | Multi-day events mis-categorized; single-day events appear multi-day |
| 6 | HIGH | 94 | `_today` uses UTC date instead of local date | Events for current local day silently dropped from cache in evening hours |
| 7 | LOW | 4331–4336 | `new Date()` inside parser may shift at midnight | Inconsistent classification if filter run crosses midnight |

---

*Report generated from structured code review of event filtering logic.*
