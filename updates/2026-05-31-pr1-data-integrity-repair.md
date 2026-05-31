# PR #1 Data Integrity Repair — PnL/Status Sign Coherence

**Date:** 2026-05-31

## What was broken

The incidents dashboard flagged critical trading data integrity issues in `trading_picks`:

- Positive terminal statuses (`WON`, `TP_HIT`, `closed_win`) could contain negative `pnl_pct` values.
- Negative terminal statuses (`LOST`, `SL_HIT`, `closed_loss`) could contain positive `pnl_pct` values.
- Historical FOREX rows had previously shown impossible `pnl_pct < -100` artifacts.
- No database-level guard existed to prevent future status/PnL sign drift.

These issues made status-based win/loss reporting unreliable and caused `/audit/incidents.html` to continue surfacing P0 data-integrity incidents.

## What changed

Added `tools/repair_data_integrity.py`, a guarded repair tool that:

1. Runs in dry-run mode by default.
2. Clamps `trading_picks` FOREX rows where `category='FOREX'` and `pnl_pct < -100` to `-100`.
3. Repairs sign-coherence contradictions by relabeling terminal statuses from the `pnl_pct` sign:
   - `pnl_pct < 0` → `LOST`
   - `pnl_pct > 0` → `WON`
4. Adds MySQL check constraint `chk_pnl_sign_coherence` to prevent future contradictory terminal status/PnL rows, with a small ±0.01 tolerance for zero/rounding artifacts.
5. Stamps repaired rows with an explanatory `exit_reason` suffix and updates `updated_at`.

## Live repair applied

The tool was run against the live `ejaguiar1_stocks.trading_picks` table:

- First apply pass:
  - FOREX clamp: `0` rows needed repair.
  - Positive-status/negative-PnL contradictions: `23` rows fixed.
  - Initial strict constraint add failed because `3` negative-status/positive-PnL rows remained.
- Second apply pass after widening repair coverage:
  - Remaining status/PnL contradictions: `3` rows fixed.
  - `chk_pnl_sign_coherence` constraint added successfully.

## Verification

Verification commands:

```bash
python3 tools/repair_data_integrity.py
python3 - <<'PY'
import os, pymysql
conn = pymysql.connect(host='mysql.50webs.com', user='ejaguiar1_stocks', password=os.environ.get('DB_PASS_STOCKS',''), database='ejaguiar1_stocks', connect_timeout=15, charset='utf8mb4')
cur = conn.cursor()
cur.execute("""
SELECT COUNT(*)
FROM trading_picks
WHERE (status IN ('WON','TP_HIT','closed_win') AND pnl_pct < 0)
   OR (status IN ('LOST','SL_HIT','closed_loss') AND pnl_pct > 0)
""")
print('remaining_sign_coherence_violations=', cur.fetchone()[0])
conn.close()
PY
```

Results:

- Dry-run after repair: `0` affected rows.
- Direct SQL verification: `remaining_sign_coherence_violations=0`.
- Constraint add status: `FIXED`.

## Notes

This fix intentionally does not run broad destructive cleanup. Ghost-row deduplication and historical PnL recomputation remain separate PRs because they require heavier sampling/deletion controls and different rollback planning.
