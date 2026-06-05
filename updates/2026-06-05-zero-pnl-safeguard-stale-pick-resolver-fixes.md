# Fix: Zero-PnL Safeguard + Stale Pick Resolver Table-Awareness

**Date:** 2026-06-05
**Files changed:**
- `audit_trail/universal_pick_resolver.py`
- `tools/resolve_stale_open_picks.py`
- `tools/pick_hold_windows.py`
- `tools/test_resolver_health.py`

## Fix 1: Zero-PnL Bug in `universal_pick_resolver.py`

### Problem
1,034 picks in `at_pick_outcomes` had `pnl_pct = 0` but `status IN ('WON','LOST')`. This happened when TP or SL was hit extremely close to the entry price, causing `round(..., 2)` to collapse the true PnL to exactly `0.0`. A 0% PnL on a "WON" or "LOST" record breaks analytics and looks like a data-quality bug.

### Root Cause
PnL was computed inline in three places (`check_tp_sl`, `_check_tp_sl_intrabar`, and the TIME_EXPIRY path) using `round(..., 2)`. For trades where the exit price was only fractionally different from entry, the rounded value became `0.0`.

### Change
Added a centralized `_compute_pnl(entry, exit_price, direction)` helper that:
1. Computes the standard PnL with `round(..., 2)`.
2. If the rounded result is exactly `0.0` but the unrounded formula is non-zero, logs a `[ZERO-PNL-SAFEGUARD]` warning and returns the unrounded fallback value.
3. Replaced all inline PnL computations in `check_tp_sl`, `_check_tp_sl_intrabar`, and the TIME_EXPIRY path with calls to `_compute_pnl`.

### Verification
- Syntax-checked with `py_compile`.
- Confirmed only one `pnl = round(...)` remains in the file (inside `_compute_pnl`).

## Fix 2: Batch-Resolve Stale OPEN Picks in `resolve_stale_open_picks.py`

### Problem
~7,400 stale OPEN picks existed in `at_raw_picks` (`status='OPEN'`, `recorded_at < NOW() - INTERVAL 30 DAY`). The existing `resolve_stale_open_picks.py` only targeted `trading_picks`, used `TIME_EXIT`/`TIME_EXIT_MAX_HOLD` status values, and had a dry-run infinite-loop bug.

### Changes
1. **Table-awareness:** Added `--table` CLI argument (`at_raw_picks` | `trading_picks`, default `at_raw_picks`). A `_TABLE_CONFIG` dict maps each table to its correct columns and resolution values:
   - `at_raw_picks`: queries `status='OPEN'`, uses `recorded_at` / `asset_class`, resolves to `ABANDONED` / `STALE_TIMEOUT`
   - `trading_picks`: queries `status IN ('OPEN','ACTIVE')`, uses `created_at` / `category`, resolves to `TIME_EXIT` / `TIME_EXIT_MAX_HOLD`

2. **ENUM safety for `at_raw_picks`:** `at_raw_picks.status` is an ENUM that historically did not include `ABANDONED`. Added `_ensure_abandoned_enum()` which checks `information_schema.COLUMNS` and auto-runs `ALTER TABLE ... MODIFY COLUMN status ENUM(...,'ABANDONED')` when needed. If the ALTER fails (permissions), it falls back to `status='EXPIRED'` and logs a loud warning.

3. **Dry-run pagination fix:** In dry-run mode, after processing a batch with stale picks, `scan_offset` now advances by `len(picks)` instead of resetting to `0`. Previously, dry-run would infinitely re-fetch the same batch because no rows were actually deleted.

4. **`pick_hold_windows.py`:** Added `recorded_at` as a third fallback timestamp in `pick_age_hours()`, so `at_raw_picks` rows are correctly aged.

5. **Tests:** Fixed stale `test_hold_hours_mapping` expectation (`FOREX` hold window is `72h`, not `120h`). Added `_hold_hours_for` alias so the tests can find the helper.

### Verification
- Syntax-checked with `py_compile`.
- `pytest tools/test_resolver_health.py -k TestResolveStaleOpenPicks` → **4/4 passed**.

## Recommendations
1. **Run a one-time backfill** on the 1,034 existing `at_pick_outcomes` rows with `pnl_pct = 0` and `status IN ('WON','LOST')` to recompute their true PnL from `(exit_price, entry_price, direction)`.
2. **Schedule `resolve_stale_open_picks.py --execute --max-batches 50`** against `at_raw_picks` to drain the ~7,400 stale OPEN backlog.
3. **Monitor `[ZERO-PNL-SAFEGUARD]` warnings** in the universal resolver logs over the next few days to confirm the safeguard is catching edge cases and not firing excessively.
