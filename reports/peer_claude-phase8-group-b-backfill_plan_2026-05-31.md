# Phase 8 — Group B Backfill + Refresh Re-dispatch (PLAN)
Date: 2026-05-31
Agent: peer_claude (Opus 4.7)

## Scope
- Group B: closed picks with NULL pnl_pct but populated entry+exit prices (resolver mislabel).
- Verified live count: **162** (matches Phase 7 forensic).

## Approach
1. Backup 162 rows -> `ejaguiar1_backups.trading_picks_pre_phase8_group_b_20260531` via Python pymysql (cross-DB CREATE-AS-SELECT not supported across creds).
2. Recompute pnl_pct = (exit-entry)/entry * 100 * sign(direction).
3. Verify NULL count -> 0.
4. Optional status relabel: rows with positive pnl currently status='LOST' -> 'WON', exit_reason='RECONCILED_POSITIVE_PNL'. Cap 200. All sample rows show LOST mislabel.
5. Cancel stuck run 26704679535 (Unified Audit Dashboard, queued since 05:50Z). Dispatch fresh "Unified Audit Dashboard" run.

## Safety
- Server-side gh api only. No shared-tree writes.
- Backup table snapshot before any UPDATE.
- All changes logged to result MD.
