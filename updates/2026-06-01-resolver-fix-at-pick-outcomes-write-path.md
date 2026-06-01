# Resolver Fix: at_pick_outcomes Write Path & Health Check Crash

**Date:** 2026-06-01  
**Branch:** `fix/resolver-write-path-0601`  
**Files Changed:**
- `audit_trail/universal_pick_resolver.py`
- `tools/check_resolver_health.py`

## What Was Broken

### Bug 1: `at_pick_outcomes` MySQL write path silently failing (0 records)
**Root cause:** Three bugs in `_write_outcomes_to_mysql()`:

1. **Syntax error:** `with conn.cursor() as cur: for pick in resolved_picks:` was on the same line — `for` was incorrectly inside the `with` block without proper indentation, causing a syntax error on Python >= 3.12.

2. **Wrong INSERT columns:** The `UPSERT_SQL` was inserting columns that don't exist in `at_pick_outcomes`:
   - Old columns: `direction, source_system, entry_price, take_profit, stop_loss, exit_price, outcome, opened_at, closed_at` — NONE of these exist in the table.
   - Fixed to match actual schema: `pick_id, symbol, strategy, asset_class, status, resolution_method, pnl_pct, resolved_at, resolver_version`

3. **Empty env var fallback:** `AUDIT_DB_USER` defaulted to `""` when not set. The MySQL connection would use empty string as user, causing silent auth failure. Fixed to default to `"ejaguiar1_stocks"`.

### Bug 2: `check_resolver_health.py` crashing on missing column
**Root cause:** The `check_stale_by_asset_class()` function queried `asset_class` column on `trading_picks`, but the column is named `category` in that table. Renamed function to `check_stale_by_category()` and updated query to use `category`.

## Verification

- ✅ Both files pass `py_compile`
- ✅ Health check runs without crashing (GREEN on 3/4 checks, YELLOW on stale picks — expected)
- ✅ Test INSERT into `at_pick_outcomes` with corrected schema round-trips successfully (0→1 record, verified via SELECT)
- ✅ All 3 live URLs return HTTP 200: audit dashboard, ai-tournament, dashboard_data.json
