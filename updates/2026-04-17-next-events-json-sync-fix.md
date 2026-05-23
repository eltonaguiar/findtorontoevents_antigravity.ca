# Fix: Sync next/events.json — Restore 3,351 Events to Frontend

**Date**: 2026-04-17  
**Author**: Antigravity AI  
**Status**: Verified ✅

## What Was Broken

The live site at `findtorontoevents.ca` was showing **0 April 17, 2026 events** (and barely any events at all). The frontend loads event data from `/next/events.json`, which had been reduced to a single test event (798 bytes) instead of the full 3,351-event dataset.

## Root Cause

1. **`next/events.json` was out of sync with `events.json`**: The file contained only a single test event:
   ```json
   [{"id":"test-event-2026-04-17","title":"Test Event April 17 2026",...}]
   ```
2. **The most recent manual fix** (commit `7079b7069e` — "fix: dating scraper uses end-of-day UTC") updated `events.json` (115K+ line changes) but did **not** update `next/events.json`.
3. **The frontend's fallback chain did not trigger**: The fetch interceptor in `index.html` tries `/next/events.json` first. Since the file was valid JSON (just a 1-element array), the fallback to `/events.json` never activated.
4. **The automated scraper** (`scrape_and_sync_events.py`, lines 259–263) normally keeps both files in sync, but the manual commit bypassed it.

## What Was Changed

### 1. `next/events.json` — Re-synced from `events.json`
- **Before**: 798 bytes, 1 test event
- **After**: Full dataset (3,351 events, 54 of which are for April 17, 2026)

### 2. `.github/workflows/scrape-events.yml` — Added sync verification step
- New step: **"Verify next/events.json is in sync with events.json"**
- Compares event counts between the two files after each scraper run
- Auto-fixes by copying `events.json` → `next/events.json` if the next file is missing >10% of events or has fewer than 100 events
- Prevents this class of desynchronization from recurring

## How It Was Verified

```
$ python check_events.py
Root events.json: 3351 total events
Apr 17 events in root: 54

next/events.json: 3351 events  (after fix)
April 17: 54 events            (after fix)
```

## Frontend Data Flow Reference

```
index.html fetch interceptor → tries in order:
  1. /next/events.json  ← PRIMARY (was broken, now fixed)
  2. /events.json        ← fallback
  3. /data/events.json   ← fallback
  4. GitHub raw URL       ← last resort
```
