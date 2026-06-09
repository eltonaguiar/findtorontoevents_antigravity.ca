# CRYPTO Null PnL Backfill Constraint Fix

## Problem
The `tools/backfill_resolved_pnl.py` script failed with `pymysql.err.OperationalError: (3819, "Check constraint 'chk_pnl_sign_coherence' is violated.")` when attempting to backfill missing PnL values for CRYPTO trades. This was due to inconsistent `status` labels (e.g., `LOST`) for trades with recomputed positive PnL values.

## Changes
1.  **Refined `_recompute()`**: Updated the function to return `None` if the recomputed PnL would violate the `chk_pnl_sign_coherence` constraint (e.g., `WON` status with negative PnL or `LOST` status with positive PnL).
2.  **SQL `UPDATE` Safeguard**: Modified the SQL `UPDATE` statement in `tools/backfill_resolved_pnl.py` to include the `chk_pnl_sign_coherence` conditions in the `WHERE` clause, ensuring the database rejects any invalid updates.
3.  **NULL Handling**: Refined the `WHERE` clause to correctly handle `NULL` `pnl_pct` values, allowing the backfill to proceed for all valid candidates.

## Verification
- Ran `tools/backfill_resolved_pnl.py --apply --skip-backup`.
- 790 rows were successfully updated without constraint violations.
- Verified `n_resolved` for CRYPTO increased from 176 to 262 in `audit_dashboard/data/money_ready_verdict.json`.
