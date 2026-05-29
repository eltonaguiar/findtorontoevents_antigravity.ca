# EAGLE Session — signal_outcomes Refresh (P1-03)
**Date**: 2026-05-27 10:47 EST
**Branch**: `main`
**Commit**: `cb5173e68`

---

## Problem
`at_signal_outcomes` table was **82 days stale** (last entry 2026-03-05, 121 rows). The `db_freshness.json` showed **RED** at 115,782 minutes stale. This blocked forward validation signal tracking and ensemble consensus scoring.

## Root Cause
`audit_trail/backfill_local_sources.py::load_json_picks()` only inserted into `at_local_picks`. Closed JSON picks (67K+ rows across 12+ systems) were never written to `at_signal_outcomes`. Only SQLite sources (which produce ~121 outcomes) populated the table.

The `outcome-resolver.yml` Mirror step (INC #10) calls this script daily, but the JSON→outcomes gap meant the table stayed empty regardless of how often it ran.

## Fix
Modified `load_json_picks()`:
- Return type changed from `int` → `(int, int)` (picks count, outcomes count)
- For every closed JSON pick with status ≠ OPEN, calls `insert_outcome()` with:
  - Outcome mapped from `exit_reason` (TP_HIT, SL_HIT, EXPIRED) or falls back to status
  - `opened_at` = signal timestamp, `closed_at` = exit timestamp
- Caller in `main()` updated to unpack tuple and accumulate both counts

## Verification
- **Before**: 121 outcomes, latest 2026-03-05 (82 days stale, RED)
- **After**: 2,131 outcomes, latest 2026-05-27 14:44 UTC (40 min stale, GREEN)
- `db_freshness.json`: signal_outcomes → GREEN, 40.6 min, 28 resolved today

## Files Changed
- `audit_trail/backfill_local_sources.py` — +73/−32 lines

## Also Dispatched
- Outcome Resolver workflow via `gh workflow run` — completed successfully (run #26517953586)
