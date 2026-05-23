# Homepage "Last updated: Jan 27" — stale metadata.json

**Date:** 2026-05-21  
**Surface:** https://findtorontoevents.ca/ (React events grid header)

## What was broken

The visible line **"Last updated: Jan 27, 3:38 PM EST • 1,084 events"** comes from live **`metadata.json`**, not from `TORONTOEVENTS_ANTIGRAVITY/index.html`. The React chunk loads `/metadata.json` (and fallbacks) for `lastUpdated` and `totalEvents`.

Live file was stuck at:

- `lastUpdated`: `2026-01-27T20:38:47.018Z`
- `totalEvents`: `1084`

Meanwhile `next/events.json` and `last_update.json` were current (~13k events, May 20 scrape). **Scrape events** and **deploy-fte-events-json** updated events data but never regenerated or FTP-uploaded `metadata.json`.

## Fix

1. **`tools/scrape_and_sync_events.py`** — after each scrape, `write_events_metadata()` writes `metadata.json` and `next/metadata.json` using `last_update.json` timestamp (or max event `lastUpdated`).
2. **`tools/regenerate_events_metadata.py`** — one-off regen from existing `next/events.json` without a full scrape.
3. **`.github/workflows/scrape-events.yml`** — validate and commit `metadata.json` / `next/metadata.json`.
4. **`.github/workflows/deploy-fte-events-json.yml`** — trigger on metadata paths; FTP upload to `/findtorontoevents.ca/metadata.json` and `/findtorontoevents.ca/next/metadata.json`.

## Intermittent Jan 27 without Ctrl+F5 (2026-05-21 follow-up)

React `useEventsMetadata` uses **Promise.any()** across four URLs. Stale **309-byte** files at `/data/metadata.json` and `/TORONTOEVENTS_ANTIGRAVITY/metadata.json` (Jan 27) often **won the race** against fresh `/metadata.json` (796 bytes) — normal refresh showed Jan 27; hard refresh sometimes reordered winners.

**Additional fixes:**
- Deploy `metadata.json` to `/data/` and `/TORONTOEVENTS_ANTIGRAVITY/` on FTP.
- `write_events_metadata()` mirrors to `data/` and `TORONTOEVENTS_ANTIGRAVITY/` in repo.
- `TORONTOEVENTS_ANTIGRAVITY/index.html`: `[metadata-cache]` coalesces fetches to `/metadata.json` and `/next/metadata.json` only (`cache: no-store`).

Deploy **index.html** via `deploy-fte-index.yml` after the metadata-cache script change.

## Verify

```bash
python3 tools/regenerate_events_metadata.py
curl -sL "https://findtorontoevents.ca/data/metadata.json" | python3 -m json.tool
curl -sL "https://findtorontoevents.ca/TORONTOEVENTS_ANTIGRAVITY/metadata.json" | python3 -m json.tool
```

All four paths should show `lastUpdated` ≥ May 2026 and `totalEvents` ~13298. Console should log `✅ [metadata-cache] Loaded metadata from /metadata.json`.
