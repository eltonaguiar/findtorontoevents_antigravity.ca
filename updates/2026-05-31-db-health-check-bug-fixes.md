# DB Health Check — Two Surgical Bug Fixes (Phase 11)

**Date:** 2026-05-31
**File touched:** `tools/db_health_check.py` (only)
**Branch:** `fix/db-health-check-direction-and-bloat-2026-05-31`

## Background

`tools/db_health_check.py` emits `audit_dashboard/data/db_health.json`, which
feeds the DB Health cards on `/audit` and the DO-NOT-TRADE banner. Two of its
Tier-1 checks were producing false RED tiers that hid real problems and made
the dashboard untrustworthy:

1. `check_pnl_integrity` — flagged ~33 % of `bt_backtest_trades` as
   pnl-mismatch, even when the stored value was correct, because the recomputed
   reference was long-only.
2. `check_open_bloat` — compared an `OPEN`-rows count to the **total**-table
   `information_schema.TABLE_ROWS` estimate, an apples-to-oranges ratio that
   triggered RED on healthy tables.

Investigation: kilo (CLI, 2026-05-31), confirmed by code-reading.

## Fix 1 — `check_pnl_integrity` is now direction-aware

**Before:**
```sql
ABS(pnl_pct - ((exit_price - entry_price) / entry_price * 100)) > 1
```
This formula matches **LONG** trades but inverts the sign for **SHORT** trades.
Roughly half of `bt_backtest_trades` rows are SHORT (CRYPTO perps, FOREX), so
their stored (negative-of-the-long-formula) pnl_pct always tripped the >1pp
threshold — producing a baseline ~33 % "mismatch" rate that had nothing to do
with data corruption.

**After:**
```sql
ABS(pnl_pct
    - (CASE WHEN UPPER(COALESCE(direction,'LONG')) IN ('SHORT','SELL') THEN -1 ELSE 1 END)
      * ((exit_price - entry_price) / entry_price * 100)
   ) > 1
```
The `direction` column already exists on `bt_backtest_trades` (used by
`tools/cleanup_ghost_rows.py` and the `idx_bt_asset` index). When direction is
SHORT/SELL the recomputed reference is flipped, so the integrity check measures
genuine corruption rather than long-only bias.

**Expected behaviour:** mismatch_pct drops from ~33 % (red) to <5 % (green) on
the same sample, and remaining mismatches are real (likely leveraged engines
whose stored pnl_pct includes leverage — a follow-up question, not corruption).

## Fix 2 — `check_open_bloat` compares totals to totals

**Before:** for each table (`bt_backtest_trades`, `trading_picks`) the suspect
flag was
```python
bloat = (open_count > info_schema_estimate * 10) or (info_schema_estimate > open_count * 10)
```
`open_count` is the count of `status='OPEN'` rows; `info_schema_estimate` is
the MySQL optimizer's estimate of **all** rows in the table. On a healthy
table the open-vs-total ratio is naturally orders of magnitude apart, so the
check fired RED unconditionally.

**After:** total-vs-total comparison:
```python
# bt_backtest_trades
bbt_total = SELECT COUNT(*) FROM bt_backtest_trades
bloat = (bbt_total > bbt_info * 10) or (bbt_info > bbt_total * 10)

# trading_picks (tp_total was already being fetched)
bloat = (tp_total > tp_info * 10) or (tp_info > tp_total * 10)
```
`open_count` is still emitted in the per-table block, but it no longer drives
the suspect flag. `bbt_total` is now also exposed in the JSON under
`bt_backtest_trades.total_count` for dashboard consumers.

**Expected behaviour:** the RED tier triggers only on a genuine
`COUNT(*) vs information_schema.TABLE_ROWS` discrepancy — i.e. a real
counting/ghost anomaly like the 2026-05-25 incident the check was designed
to catch — not on every healthy table.

## Scope

- One file: `tools/db_health_check.py`
- Two functions: `check_pnl_integrity`, `check_open_bloat`
- ~18 lines added / 6 removed
- `py_compile` clean
- No DB schema changes, no other consumers touched (dashboard JSON keys
  preserve backward compatibility)

## Verification

Live DB verification (run after merge):

```bash
python tools/db_health_check.py --check pnl_integrity --json
python tools/db_health_check.py --check open_bloat --json
```

Expectations:
- `pnl_integrity.mismatch_pct` <5 (green)
- `open_bloat.bt_backtest_trades.count_suspect` false on a healthy DB
- `open_bloat.trading_picks.count_suspect` false on a healthy DB

## Why this matters

Both checks gate the dashboard's DO-NOT-TRADE banner. While they were RED on
benign causes, real anomalies (e.g. the 29.2 M overcount incident) were lost
in the noise. After this fix the banner reflects actual integrity problems
only.
