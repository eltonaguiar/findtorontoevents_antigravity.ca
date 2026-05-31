# Phase 8 — Group B Backfill + Refresh Re-dispatch (RESULT)
Date: 2026-05-31
Agent: peer_claude (Opus 4.7)

## TASK 1 — Group B Backfill

### Pre-state
- Verified count of NULL pnl_pct with populated entry+exit prices: **162**
- All 162 had `status='LOST'` (resolver bug — math computes positive but label says LOST).

### Backup
- Table: `ejaguiar1_backups.trading_picks_pre_phase8_group_b_20260531`
- Rows snapshotted: **162**
- Schema built from `INFORMATION_SCHEMA.COLUMNS` (CREATE TABLE LIKE failed due to named CHECK constraint collision `chk_pnl_sign_coherence`).

### CHECK constraint discovered
`chk_pnl_sign_coherence` on `trading_picks`:
```
((status IN ('WON','TP_HIT','closed_win') AND pnl_pct >= -0.01)
 OR (status IN ('LOST','SL_HIT','closed_loss') AND pnl_pct <= 0.01)
 OR status NOT IN ('WON','TP_HIT','closed_win','LOST','SL_HIT','closed_loss'))
```
A naive `UPDATE pnl_pct` would violate the constraint because all 162 rows compute positive PnL but currently have `status='LOST'`. We had to relabel status atomically per row.

### Backfill execution (atomic per row)
Formula: `pnl_pct = (exit_price - entry_price) / entry_price * 100 * sign(direction)` where SHORT = -1, else +1.

| Bucket | Count | Action |
|---|---|---|
| pnl > 0.01 (mislabel) | **162** | UPDATE status='WON', exit_reason='RECONCILED_POSITIVE_PNL', pnl_pct=<computed> |
| pnl < -0.01 | 0 | n/a |
| ~0 pnl | 0 | n/a |

- Errors: **0**
- Remaining NULL pnl_pct with prices: **0** (verified post-commit)

### Spot-check (5 rows)
| id | status | exit_reason | pnl_pct |
|---|---|---|---|
| connors_rsi2::SI=F::2026-03-12 | WON | RECONCILED_POSITIVE_PNL | 0.2381 |
| copy_hl_lb_None::AEROUSDT::2026-04-18_1943 | WON | RECONCILED_POSITIVE_PNL | 9.8650 |
| ema_stack_momentum::CL=F::2026-03-11 | WON | RECONCILED_POSITIVE_PNL | 8.0000 |
| ema_stack_momentum::TLT::2026-03-11 | WON | RECONCILED_POSITIVE_PNL | 0.1310 |
| hyperopt_connors_rsi2::SI=F::2026-03-12 | WON | RECONCILED_POSITIVE_PNL | 0.2381 |

### Status verdict impact
- 162 picks flipped LOST -> WON. This **raises win-counts** across affected strategies/classes when pf_registry is re-derived.
- Concentrated in COMMODITY (CL=F, SI=F), BOND (TLT), CRYPTO copy_hl/AERO. Per-class WR/PF will shift; expect EQUITY/COMMODITY/BOND class-health snapshots to improve modestly when the next refresh emits.
- Relabel log written to `/tmp/phase8_relabel_log.txt` (162 ids).

### Rollback path
`UPDATE ejaguiar1_stocks.trading_picks t JOIN ejaguiar1_backups.trading_picks_pre_phase8_group_b_20260531 b ON t.id=b.id SET t.pnl_pct=b.pnl_pct, t.status=b.status, t.exit_reason=b.exit_reason`

## TASK 2 — Refresh workflow re-dispatch

- Stuck run `26704679535` (Unified Audit Dashboard, queued since 05:50Z) -> **cancelled** 2026-05-31T05:58Z.
- Dispatched fresh: `gh workflow run "Unified Audit Dashboard"` -> new run id **26704818902** (status: pending at 05:58:18Z).
- Workflow list confirms only one queued run remains.

## Open follow-ups
- Group A (131 rows) still untouched (needs Binance/yfinance exit_price refetch — not in scope).
- Resolver bug producing LOST-with-positive-pnl is upstream of `trading_picks` writer; should be tracked as P0 (see Phase 7 forensic). Recommend adding `chk_pnl_sign_coherence` enforcement at the resolver layer to prevent recurrence.
- Verify pf_registry.json + money_ready_verdict.json regenerate cleanly after run 26704818902 completes.
