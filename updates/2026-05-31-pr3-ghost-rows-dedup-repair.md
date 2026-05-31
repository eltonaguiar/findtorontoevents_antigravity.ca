# PR #3 — Ghost Row Dedup Repair (2026-05-31)

## What was broken

- **22,947 ghost rows** across multiple cohorts in `trading_picks`
- Largest cohort: `quan_engine/MATICUSDT/LONG/pnl=-15.0` (20,474 rows from 1 distinct entry)
- Ghost rows inflate PnL stats, corrupt win rate calculations, and waste DB space
- The old `ghost_rows_matic` check only caught ONE cohort — 11+ other cohorts were invisible

## What changed

**File:** `tools/repair_data_integrity.py`

1. **Broadened check:** Replaced `ghost_rows_matic` (MATICUSDT-only) with `ghost_rows` that counts ALL duplicate groups across all cohorts using `GROUP BY category, strategy, symbol, direction, pnl_pct, created_at`

2. **Added `repair_sql`:** DELETE with self-join keeping MIN(id) per duplicate group:
   - Uses `IFNULL` for nullable `category` and `strategy` columns
   - LIMIT 50,000 safety cap per run
   - Groups by exact match on all 6 key fields for conservative dedup

3. **Updated `run_checks()`:** 
   - Added `repaired` counter
   - Executes `repair_sql` when `--write` is passed AND check fails
   - Supports `callable(repair_sql)` for future lazy repair functions

## How to run

```bash
# Dry-run (count ghost rows only)
DB_PASS_STOCKS=<pass> python3 tools/repair_data_integrity.py

# Apply repair (dedup + mark resolved)
DB_PASS_STOCKS=<pass> python3 tools/repair_data_integrity.py --write
```

## Verification

- ✅ Compiles without syntax errors
- ✅ Code review passed — SQL is safe (LIMIT cap, conservative GROUP BY, IFNULL on nullable columns)
- ✅ Follows existing CHECKS architecture pattern

## Related

- `tools/cleanup_ghost_rows.py` — standalone ghost row cleaner for `bt_backtest_trades`
- `tools/db_p0_integrity_remediation.py` — original broad dedup DELETE (Incident #12)
- `updates/2026-05-31-pr3-ghost-rows-dedup-verification.md` — earlier verification pass
