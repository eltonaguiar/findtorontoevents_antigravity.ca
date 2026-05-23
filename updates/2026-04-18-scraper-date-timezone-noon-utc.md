# Fix: Scraper Date Timezone — Use Noon UTC for Date-Only Values

**Date:** 2026-04-18  
**Branch:** `fix/scraper-date-timezone-noon-utc`

## What Was Broken

Events on findtorontoevents.ca were appearing on the **wrong calendar day** when viewed in the EST/EDT timezone. For example, events for April 17, 2026 were showing up under April 16 instead.

### Root Cause

When scrapers parse a date string without a time component (e.g., "April 17, 2026" or "2026-04-17"), Python's `datetime.strptime()` defaults to **midnight** (00:00:00). The scrapers then appended `"Z"` to make it UTC:

```
"2026-04-17" → datetime(2026, 4, 17, 0, 0, 0) → "2026-04-17T00:00:00Z"
```

The frontend uses `Intl.DateTimeFormat("en-CA", {timeZone: "America/Toronto"})` to convert UTC timestamps to local dates. Midnight UTC in Toronto's timezone is:

- **EDT (UTC-4):** April 16 at 8:00 PM — **previous day**
- **EST (UTC-5):** April 16 at 7:00 PM — **previous day**

So an event meant for April 17 was displayed as an April 16 event.

### Impact

Any scraper producing date-only timestamps with `T00:00:00Z` (or `T23:59:00Z`) caused events to land on the wrong date in the frontend's "Today" filter and date grouping.

## What Was Changed

### 1. `tools/scrapers/base_scraper.py` — `parse_date()` method
- All date-only formats now produce **noon UTC** (`T12:00:00Z`) instead of midnight
- Noon UTC (8:00 AM EDT / 7:00 AM EST) is always the same calendar day in Toronto
- This is the base method used by many scrapers as a fallback

### 2. `tools/scrapers/blogto_scraper.py` — `_parse_blogto_date()`
- ISO date-only handler: `T00:00:00Z` → `T12:00:00Z`
- (Spelled-month handler was already using noon UTC)

### 3. `tools/scrapers/harbourfront_scraper.py` — `_parse_hc_date()`
- ISO date-only handler: `T00:00:00Z` → `T12:00:00Z`
- (Spelled-month/no-year handlers were already using noon UTC)

### 4. `tools/scrapers/major_venues_scraper.py` — `_iso()`
- ISO date-only handler: `T00:00:00Z` → `T12:00:00Z`
- (Spelled-month/no-year handlers were already using noon UTC)

### 5. `tools/scrapers/meetup_scraper.py` — `_parse_meetup_date()`
- ISO date-only handler: `T00:00:00Z` → `T12:00:00Z`

### 6. `tools/scrapers/nowtoronto_scraper.py` — `_parse_now_date()`
- ISO date-only handler: `T00:00:00Z` → `T12:00:00Z`

### 7. `tools/scrapers/tpl_scraper.py` — `_iso()`
- ISO date-only handler: `T00:00:00Z` → `T12:00:00Z`
- Spelled-month handlers: added `.replace(hour=12, minute=0, second=0)`
- No-year handlers: added `hour=12, minute=0, second=0` to `.replace()`

### 8. `tools/scrapers/torontocom_scraper.py` — `_parse_tc_date()`
- ISO date-only handler: `T00:00:00Z` → `T12:00:00Z`
- Spelled-month handlers: added `.replace(hour=12, minute=0, second=0)`
- No-year handlers: added `hour=12, minute=0, second=0` to `.replace()`

### 9. `tools/scrapers/eventbrite_scraper.py` — `_parse_event_card()`
- Start date date-only: `T00:00:00Z` → `T12:00:00Z`
- End date date-only: `T23:59:59Z` → `T12:00:00Z` (consistency)

### 10. `tools/scrapers/dating_events_scraper.py` — `_normalize_date()`
- ISO date-only: `T23:59:00Z` → `T12:00:00Z`
- Date-only strptime parse: `hour=23, minute=59` → `hour=12, minute=0`

### 11. `tools/scrapers/unified_scraper.py` — safety net `fix_midnight_utc()`
- Already present from earlier commit on this branch
- Catches any scraper that still emits `T00:00:00Z` for date-only values
- Belt-and-suspenders protection at the pipeline level

## How It Was Verified

- All 11 modified files pass `py_compile` syntax checks
- `grep -rn 'T00:00:00Z' tools/scrapers/` returns only the safety net code in `unified_scraper.py` — no more date-parsing code emits midnight UTC
- `grep -rn 'T23:59' tools/scrapers/` returns zero results — no more end-of-day UTC
- The fix pattern (T12:00:00Z for date-only values) was already proven in production by scrapers that had independently fixed this same issue

## Data Migration

### `tools/patch_midnight_utc_events.py` — one-time data fix
- Patches existing events in `events.json` and `next/events.json`
- Converts `T00:00:00Z` → `T12:00:00Z` on `date`, `end_date`, and `endDate` fields
- This fixes the immediate live-site issue without waiting for the next scraper run
