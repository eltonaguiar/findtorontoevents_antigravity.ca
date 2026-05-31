# Plan: Repair 44 pnl_status_mismatch rows (freebuff DB health 2026-05-31)

## Background
Freebuff DB health audit 2026-05-31 surfaced:
- `pnl_sign_flip` = 0 (PASS)
- FOREX clamp = 0 (PASS)
- `pnl_status_mismatch` = **44 FAIL** (new since prior check; likely from CI outcome-resolver run between checks)

## Verified state (dry-run)
`DB_PASS_STOCKS=*** python3 tools/repair_data_integrity.py` (no --apply) confirms:
- FOREX PnL Clamp: 0 SKIPPED
- Status/PnL Contradiction: **44 DRY_RUN**
- CHECK constraint: skip (separate path)

Mismatch SQL (from `repair_pnl_contradictions`):
```sql
(status IN ('WON','TP_HIT','closed_win') AND pnl_pct < 0)
OR (status IN ('LOST','SL_HIT','closed_loss') AND pnl_pct > 0)
```

## Plan
1. BACKUP all 44 rows from `ejaguiar1_stocks.trading_picks` → `ejaguiar1_backups.trading_picks_pre_freebuff_pnl_status_mismatch_20260531` (full-row INSERT...SELECT).
2. Capture per-row sample (id, ticker, category, status, pnl_pct, exit_reason) into AFTER report.
3. Apply: `DB_PASS_STOCKS=*** python3 tools/repair_data_integrity.py --apply`.
   - Note: script runs all three repair tasks. FOREX clamp = 0 (no-op); CHECK constraint attempt is benign (ALREADY_EXISTS expected).
4. Verify: re-run dry-run, expect Status/PnL Contradiction = 0.
5. Spot-check 5 row IDs post-apply (status flipped + exit_reason ends with " (REPAIRED_PNL_CONTRADICTION)").

## Abort conditions
- If pre-apply count > 44 (drift since dry-run), abort and re-investigate.
- If backup table INSERT row count != 44, abort.
