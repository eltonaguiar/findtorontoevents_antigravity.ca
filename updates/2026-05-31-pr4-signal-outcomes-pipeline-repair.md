# PR #4 — Signal Outcomes Pipeline Freshness Repair (2026-05-31)

## What was broken

- `at_signal_outcomes` table was **82 days stale** — last write 2026-03-10
- The old check only verified `COUNT(*) > 1000` but didn't detect staleness
- Dashboard analytics, edge calculators, and audit tools depend on `at_signal_outcomes` for signal-to-outcome tracking
- Root cause: `paper_trading/mysql_sync.py` stopped syncing (paper.db not updated)

## What changed

**File:** `tools/repair_data_integrity.py`

1. **Improved staleness detection:** Check now queries `MAX(created_at) > NOW() - INTERVAL 7 DAY` and requires both `cnt > 1000` AND `fresh=1` to pass

2. **Added `_repair_signal_outcomes(cur)` callable repair:**
   - `TRUNCATE TABLE at_signal_outcomes` — clears stale data
   - `INSERT INTO ... SELECT FROM trading_picks` — rebuilds from source of truth
   - Status mapping: `TP_HIT/WON/CLOSED_TP → TP_HIT`, `SL_HIT/LOST/CLOSED_SL → SL_HIT`, `EXPIRED + pnl>0 → WIN`, `EXPIRED + pnl<=0 → LOSS`
   - Filters: closed picks with non-null symbol and closed_at only
   - Returns total rows inserted

3. **Updated callable API:** `run_checks()` now passes `cur` to callable repair functions, which execute their own SQL and return rowcount. Backward-compatible — no existing callables were broken.

## How to run

```bash
# Dry-run (check staleness only)
DB_PASS_STOCKS=<pass> python3 tools/repair_data_integrity.py

# Apply repair (truncate + rebuild from trading_picks)
DB_PASS_STOCKS=<pass> python3 tools/repair_data_integrity.py --write
```

## Verification

- ✅ Compiles without syntax errors
- ✅ Code review passed — TRUNCATE gated behind FAIL + --write, status mapping correct, null handling defensive
- ✅ Follows existing CHECKS + repair_sql architecture (extended for callable repairs)

## Related

- `paper_trading/mysql_sync.py` — original sync from paper.db (needs paper.db to be up-to-date)
- `audit_trail/backfill_local_sources.py` — local source backfill
- `updates/2026-05-31-pr4-signal-outcomes-pipeline-verification.md` — earlier verification pass
