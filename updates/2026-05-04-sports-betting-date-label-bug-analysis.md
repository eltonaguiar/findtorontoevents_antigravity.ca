# Sports Betting Dashboard — Date Labeling Bug Analysis

**Date:** 2026-05-04  
**Issue:** Picks dated May 4 show with a non-TODAY label (blue "Later" badge) after midnight, instead of the green "TODAY" badge users expect.  
**Page:** `https://findtorontoevents.ca/live-monitor/sports-betting.html`  
**Files analyzed:** `live-monitor/sports-betting.html`, `live-monitor/sports-betting.js`, `live-monitor/api/sports_picks.php`

---

## 1. How Pick Date Labels Work

### 1.1 Client-Side: `fmtGameDate()` (lines ~1505–1529)

```javascript
function fmtGameDate(gd, ct) {
    var src = gd;
    if (!src && ct) {
        var utc = new Date(ct + (ct.indexOf('Z') < 0 && ct.indexOf('+') < 0 ? ' UTC' : ''));
        src = _estDateStr(utc);
    }
    if (!src) return '--';
    var parts = src.split('-');
    if (parts.length < 3) return src;
    var d = new Date(parseInt(parts[0]), parseInt(parts[1]) - 1, parseInt(parts[2]));
    var now = _estNow();
    var today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    var tomorrow = new Date(today); tomorrow.setDate(tomorrow.getDate() + 1);
    var yesterday = new Date(today); yesterday.setDate(yesterday.getDate() - 1);
    var label = d.toLocaleDateString('en-US', {weekday:'short', month:'short', day:'numeric'});
    if (d.getTime() === today.getTime()) label = 'TODAY';
    else if (d.getTime() === tomorrow.getTime()) label = 'TOMORROW';
    else if (d.getTime() === yesterday.getTime()) label = 'YESTERDAY';
    return label;
}
```

**How it works:**
1. Uses `game_date` from the API response as the primary source (`gd`)
2. Falls back to `commence_time` if `game_date` is empty — parses as UTC, then converts to EST via `_estDateStr()`
3. Parses the date string `"YYYY-MM-DD"` into a `Date` object: `new Date(year, month-1, day)` → **midnight LOCAL time**
4. Gets current time in EST via `_estNow()` → `_toEST(new Date())`
5. Creates `today` as midnight LOCAL time using EST-derived year/month/day components
6. Compares `d.getTime()` with `today.getTime()` using exact millisecond equality

### 1.2 Client-Side: `_toEST()` (lines 1483–1499)

```javascript
function _toEST(d) {
    var dt = (d instanceof Date) ? d : new Date(d);
    if (isNaN(dt.getTime())) return new Date();
    try {
        var parts = new Intl.DateTimeFormat('en-US', {
            timeZone: 'America/New_York',
            year: 'numeric', month: 'numeric', day: 'numeric',
            hour: 'numeric', minute: 'numeric', second: 'numeric', hour12: false
        }).formatToParts(dt);
        var p = {};
        for (var i = 0; i < parts.length; i++) { p[parts[i].type] = parts[i].value; }
        var hr = parseInt(p.hour, 10); if (hr === 24) hr = 0;
        return new Date(parseInt(p.year, 10), parseInt(p.month, 10) - 1, parseInt(p.day, 10), hr, parseInt(p.minute, 10), parseInt(p.second, 10));
    } catch (e) {
        return new Date(dt.toLocaleString('en-US', {timeZone: 'America/New_York'}));
    }
}
```

**How it works:**
1. Uses `Intl.DateTimeFormat` with `timeZone: 'America/New_York'` to extract numeric date/time components in EST/EDT
2. Constructs a new `Date` object: `new Date(year, month-1, day, hour, minute, second)` — **these EST/EDT components are interpreted as LOCAL time by the Date constructor**

### 1.3 CSS Badge Mapping

```javascript
var gdClass = gameDateLabel === 'TODAY' ? 'badge-green' 
            : gameDateLabel === 'TOMORROW' ? 'badge-yellow' 
            : 'badge-blue';
```

| Label | Badge Color | User Perception |
|-------|------------|-----------------|
| TODAY | Green (`badge-green`) | "Today" |
| TOMORROW | Yellow (`badge-yellow`) | "Tomorrow" |
| Anything else (e.g., "Sun, May 4") | Blue (`badge-blue`) | **"Later"** |

> **There is no literal "Later" label in the codebase.** The user's "Later" refers to picks that fall through to the `badge-blue` class — i.e., picks whose `fmtGameDate` returns a formatted date string instead of "TODAY" or "TOMORROW".

---

## 2. Server-Side: `sports_action_today()` (PHP)

```php
function sports_action_today($mysqli) {
    $sport = isset($_GET['sport']) ? $_GET['sport'] : 'all';
    // ...
    $dr = $mysqli->query("SELECT MAX(pick_date) AS d FROM lm_sports_daily_picks");
    $pickDate = date('Y-m-d');  // ⚠️ Server timezone, may not be EST
    if ($dr && ($drow = $dr->fetch_assoc()) && $drow['d'] !== null && $drow['d'] !== '') {
        $pickDate = $drow['d'];  // Uses MAX(pick_date) from DB if available
    }
    $where = "pick_date = '" . $mysqli->real_escape_string($pickDate) . "'";
    // ...
    $r = $mysqli->query("SELECT * FROM lm_sports_daily_picks WHERE " . $where . " ORDER BY ev_pct DESC");
    // Returns rows with: game_date, commence_time, etc.
}
```

**How it works:**
1. Tries to use `MAX(pick_date)` from `lm_sports_daily_picks` table as the pick date
2. Falls back to `date('Y-m-d')` (PHP server's local time) if no rows exist
3. Filters picks by `pick_date = '$pickDate'`
4. Returns `game_date` and `commence_time` fields to the client

### 3. Potential Root Causes

#### 3.1 🟡 **Timezone Mismatch in `_toEST` → `fmtGameDate` chain** (Most Likely)

The `_toEST` function extracts EST/EDT date components but the `Date` constructor interprets them as **local** time:

```
Browser timezone: EDT (UTC-4)
Current time: May 4, 2026 00:05 EDT

_toEST(new Date()):
  → Intl.DateTimeFormat extracts: year=2026, month=5, day=4, hour=0, minute=5, second=0
  → new Date(2026, 4, 4, 0, 5, 0) = May 4 00:05 LOCAL = May 4 04:05 UTC ✓

today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  → new Date(2026, 4, 4) = May 4 00:00 LOCAL = May 4 04:00 UTC ✓

d = new Date(2026, 4, 4) = May 4 00:00 LOCAL = May 4 04:00 UTC ✓
d.getTime() === today.getTime() → TRUE → "TODAY" ✓
```

**On EDT browsers, this normally works because EST date = local date.** However:

**Scenario where it breaks — non-EDT browser:**
```
Browser timezone: PDT (UTC-7)
Current time: May 3, 2026 21:05 PDT (= May 4 00:05 EDT)

_toEST(new Date()):
  → Intl.DateTimeFormat extracts: year=2026, month=5, day=4, hour=0, minute=5, second=0 (EDT!)
  → new Date(2026, 4, 4, 0, 5, 0) = May 4 00:05 PDT = May 4 07:05 UTC

today = new Date(2026, 4, 4) = May 4 00:00 PDT = May 4 07:00 UTC

d = new Date(2026, 4, 4) = May 4 00:00 PDT = May 4 07:00 UTC
d.getTime() === today.getTime() → TRUE → "TODAY"
```

**Actually, even on PDT, both `today` and `d` use the same `new Date(year, month, day)` pattern at local midnight, so they still match.** The timezone mismatch is indirectly "cancelled out" because both dates are constructed the same way.

#### 3.2 🔴 **`commence_time` Timezone Offset Bug** (Confirmed Bug)

```javascript
var utc = new Date(ct + (ct.indexOf('Z') < 0 && ct.indexOf('+') < 0 ? ' UTC' : ''));
```

**The check only looks for `Z` and `+` in the timestamp.** Timezone offsets with `-` (like `-04:00`, `-05:00`) are NOT detected:

| commence_time value | `indexOf('+')` | `indexOf('Z')` | Appends " UTC"? | Result |
|---------------------|:---:|:---:|:---:|---|
| `2026-05-04T19:00:00Z` | -1 | 0 | No | Correct |
| `2026-05-04T19:00:00+00:00` | ≥0 | -1 | No | Correct |
| `2026-05-04T19:00:00-04:00` | **-1** | **-1** | **YES** | `"2026-05-04T19:00:00-04:00 UTC"` — **INVALID** |
| `2026-05-04T19:00:00` (no tz) | -1 | -1 | Yes | Correct (assumed UTC) |

When the string is invalid, `new Date(invalid)` returns `Invalid Date`. Then `_toEST` catches this:
```javascript
if (isNaN(dt.getTime())) return new Date();  // Returns current time
```

This would make `_estDateStr` return **today's date** regardless of the actual game date, causing a pick to show as TODAY when it shouldn't be, or vice versa depending on timing.

#### 3.3 🟡 **PHP Server Timezone Fallback**

```php
$pickDate = date('Y-m-d');  // Uses SERVER timezone, which may be UTC
```

If the server is UTC and the `lm_sports_daily_picks` table happens to be empty:
- At midnight EDT (4 AM UTC): `date('Y-m-d')` = `"2026-05-05"` (next day!)
- This would query for May 5 picks, missing May 4 picks entirely

However, this is mitigated by the `MAX(pick_date)` query which normally returns the correct date.

#### 3.4 🟡 **Fragile Exact-Millisecond Date Comparison**

```javascript
if (d.getTime() === today.getTime()) label = 'TODAY';
```

This uses **exact millisecond equality**. Both `d` and `today` are constructed as `new Date(y, m, d)` creating midnight objects. As long as:
1. Both use the same `year/month/day` values
2. Both are constructed via `new Date(year, month, day)` (midnight, no time components)

...they will have identical millisecond timestamps. This is fragile and would break if either date had sub-millisecond precision differences or was constructed differently.

#### 3.5 🟡 **Two Different "Today" Calculations in the HTML File**

The `live-monitor/sports-betting.html` file contains **two separate** "today" calculations:

1. **`fmtGameDate()`** (line ~1521): Uses `_estNow()` → `_toEST(new Date())` → `new Date(estYear, estMonth, estDay)` 
2. **Event filter logic** (line ~1523 in the diff): Uses `__todayStart` which is `new Date(now.getFullYear(), now.getMonth(), now.getDate())` where `now = new Date()` (NOT adjusted to EST)

These could disagree under certain timezone conditions. However, the event filter code is for a different section of the site (the events homepage), not the sports betting dashboard.

---

## 4. Summary of Findings

### Primary Suspect: `commence_time` Timezone Offset Bug (Section 3.2)

The most concrete bug found is in how `commence_time` strings with negative UTC offsets (like `-04:00`) are handled. The check `ct.indexOf('+') < 0` fails to detect `-` timezone offsets, causing `" UTC"` to be incorrectly appended, producing an invalid date string.

**When this triggers:**
- If `game_date` is empty/null in the API response
- AND `commence_time` has an explicit timezone offset with `-` (e.g., `-04:00`, `-05:00`)
- Then `_toEST` falls back to `new Date()` (current time)
- The pick gets today's date as its label, which could be WRONG

**The interplay with the midnight complaint:**
If a May 4 pick has `commence_time = "2026-05-04T19:00:00-04:00"` and `game_date` is null:
1. `fmtGameDate(null, "2026-05-04T19:00:00-04:00")` is called
2. The timezone detection fails → `"2026-05-04T19:00:00-04:00 UTC"` (invalid)
3. `new Date(invalid)` → Invalid Date
4. `_toEST` returns `new Date()` = now
5. `_estDateStr` returns today's date
6. If called right at midnight when today JUST changed to May 5, the label becomes May 5 instead of May 4

This would explain: picks that should be "TODAY May 4" getting a May 5 label (or vice versa) right around midnight.

### Secondary Concern: No Defensive Normalization

The code relies on `game_date` being a clean `"YYYY-MM-DD"` string. If the database returns `"2026-05-04 00:00:00"` or other formats, `split('-')` still produces correct results (`parseInt` stops at first non-digit), but this is luck rather than by design.

---

## 5. Recommended Fixes

### Fix 1: Repair `commence_time` Timezone Detection (Critical)

```javascript
// BEFORE (buggy):
var utc = new Date(ct + (ct.indexOf('Z') < 0 && ct.indexOf('+') < 0 ? ' UTC' : ''));

// AFTER (fixed):
var hasTz = ct.indexOf('Z') >= 0 || ct.indexOf('+') >= 0 || (ct.length >= 19 && (ct[ct.length-6] === '+' || ct[ct.length-6] === '-'));
var utc = new Date(ct + (hasTz ? '' : ' UTC'));
```

Or more robustly, use a regex:
```javascript
var hasTz = /[+-]\d{2}:\d{2}$/.test(ct) || ct.endsWith('Z');
```

### Fix 2: Use Date-Normalized Comparison Instead of Millisecond Equality (Defensive)

```javascript
// BEFORE (fragile):
if (d.getTime() === today.getTime()) label = 'TODAY';

// AFTER (robust):
var dStr = d.getFullYear() + '-' + ('0'+(d.getMonth()+1)).slice(-2) + '-' + ('0'+d.getDate()).slice(-2);
var todayStr = today.getFullYear() + '-' + ('0'+(today.getMonth()+1)).slice(-2) + '-' + ('0'+today.getDate()).slice(-2);
if (dStr === todayStr) label = 'TODAY';
```

### Fix 3: Add `commence_time` Parsing Fallback Safety

```javascript
if (!src && ct) {
    try {
        var utc = new Date(ct + (hasTz(ct) ? '' : ' UTC'));
        if (isNaN(utc.getTime())) throw new Error('Invalid date');
        src = _estDateStr(utc);
    } catch(e) {
        // Keep src as undefined/null; will fall through to '--'
        console.warn('[fmtGameDate] Could not parse commence_time:', ct);
    }
}
```

---

## 6. Files Requiring Changes

| File | Lines | Change |
|------|-------|--------|
| `live-monitor/sports-betting.html` | ~1513–1515 | Fix commence_time timezone detection |
| `live-monitor/sports-betting.html` | ~1522–1523 | Switch from millisecond comparison to date-string comparison |

---

## 7. Verification Plan

1. **Unit test the fixed `fmtGameDate`** with various `commence_time` formats:
   - `"2026-05-04T19:00:00-04:00"` (EDT offset — the bug case)
   - `"2026-05-04T19:00:00Z"` (UTC)
   - `"2026-05-04T19:00:00+00:00"` (UTC with + offset)
   - `"2026-05-04"` (date-only via `game_date`)
2. **Test at midnight boundary** — simulate `_estNow()` returning midnight and verify labels
3. **Cross-browser test** on non-EDT timezone browser settings
4. **Manual verification** on the live page after deployment

---

## 8. Implementation Status (Applied)

The following fixes have now been applied in `live-monitor/sports-betting.html`:

1. Added `_hasExplicitTZ(str)` regex helper to correctly detect `Z`, `+HH:MM`, and `-HH:MM` suffixes.
2. Updated both `fmtTime()` and `fmtGameDate()` commence-time parsing to use `_hasExplicitTZ` instead of checking only `'+'`.
3. Changed `_toEST()` invalid-input behavior from `return new Date()` to `return null` to avoid masking bad input as "now".
4. Added `_estDateStr()` null/invalid guard (`return ''`) before reading date parts.
5. Switched `fmtGameDate()` comparisons from exact millisecond equality to normalized `YYYY-MM-DD` key comparison (`dKey`, `todayKey`, `tomorrowKey`, `yesterdayKey`).

### Verification Run

- `node tests/sports_date_bucketing_regression.js` -> PASS
- `npx playwright test tests/sports_betting_js_errors.spec.js --project="Desktop Chrome"` -> 4 passed, 1 failed
  - Remaining failure is `Pick History tab populates with at least one day` (`body.ok === false`), which is pre-existing API behavior and not introduced by the date-bucketing patch.

### Notes

- The workspace rule references `tools/check_syntax.js`, but that file is not present in this repository, so that static validator could not be run.
