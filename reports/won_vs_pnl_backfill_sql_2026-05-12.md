# WON-vs-PnL Backfill SQL Draft — 2026-05-12

## Background

Commit `22b677c1167` shipped a forward-only sign-coherence guard in both
atomic status+pnl writers (`alpha_engine/outcome_resolver.py:1670` and
`audit_trail/mysql_client.py:628`). The guard stops NEW contradiction rows
from being written.

**Legacy contradicted rows still poison aggregates.** Per
`audit_dashboard/data/db_health.json::checks.won_pnl_contradiction.data`
the contradiction detector at `tools/db_health_check.py:430+` queries
`trading_picks` and flags rows where status='WON'/TP_HIT/closed_win has
avg(pnl_pct) < 0, OR status='LOST'/SL_HIT/closed_loss has avg(pnl_pct) > 0.

This document drafts the **read-only diagnostic** + **proposed UPDATE** for
backfill. **No SQL is executed by this file** — user sign-off required.

## Step 1 — Read-only diagnostic (run first)

```sql
-- How many contradicted rows? Per asset_class breakdown.
SELECT asset_class,
       SUM(CASE WHEN status IN ('WON','TP_HIT','closed_win') AND pnl_pct < 0 THEN 1 ELSE 0 END) AS won_with_negative_pnl,
       SUM(CASE WHEN status IN ('LOST','SL_HIT','closed_loss') AND pnl_pct > 0 THEN 1 ELSE 0 END) AS lost_with_positive_pnl,
       COUNT(*) AS total_terminal_rows
FROM trading_picks
WHERE status IN ('WON','LOST','TP_HIT','SL_HIT','closed_win','closed_loss')
  AND pnl_pct IS NOT NULL
GROUP BY asset_class
ORDER BY (won_with_negative_pnl + lost_with_positive_pnl) DESC;
```

Expected output: per-class counts. If the totals are dominated by one
asset class, the backfill scope can be narrowed.

```sql
-- Sample 20 contradicted rows for spot-check
SELECT id, asset_class, strategy, symbol, direction, entry_price, exit_price,
       pnl_pct, status, exit_reason, created_at, closed_at
FROM trading_picks
WHERE pnl_pct IS NOT NULL
  AND (
    (status IN ('WON','TP_HIT','closed_win') AND pnl_pct < 0) OR
    (status IN ('LOST','SL_HIT','closed_loss') AND pnl_pct > 0)
  )
ORDER BY created_at DESC
LIMIT 20;
```

## Step 2 — Decision point

Per row, the source of truth is **pnl_pct** (computed from
entry_price + exit_price). The status was mis-classified. Two repair
options:

**Option A — trust pnl sign (recommended):**
- Re-stamp status based on pnl_pct sign.
- pnl > class threshold → WON
- pnl < -class threshold → LOST
- |pnl| < class threshold → EXPIRED
- Per-class threshold from `alpha_engine/outcome_resolver.py:115-126
  PNL_WIN_THRESHOLD_BY_CLASS`: CRYPTO 0.001 (0.1bp), all others 0.0005 (5bp).

**Option B — trust exit_reason:**
- Only flip status if exit_reason is unambiguous (TP_HIT/SL_HIT).
- Falls back to Option A if exit_reason is generic (TIME_EXIT/EXPIRED/null).
- More conservative but more code paths.

**Recommendation:** Option A. The pnl_pct field carries the actual realized
return; the status field is just a label. If pnl says I lost money, I lost
money regardless of what status says.

## Step 3 — Backfill UPDATE (DRAFT, requires sign-off)

```sql
-- BACKFILL: re-stamp status from pnl_pct sign using per-class threshold.
-- Threshold matches alpha_engine/outcome_resolver.py PNL_WIN_THRESHOLD_BY_CLASS.

-- 3a. CRYPTO threshold = 0.001 (0.1bp)
UPDATE trading_picks
   SET status = CASE
       WHEN pnl_pct >  0.001 THEN 'WON'
       WHEN pnl_pct < -0.001 THEN 'LOST'
       ELSE 'EXPIRED'
   END
 WHERE asset_class = 'CRYPTO'
   AND pnl_pct IS NOT NULL
   AND (
     (status IN ('WON','TP_HIT','closed_win') AND pnl_pct < -0.001) OR
     (status IN ('LOST','SL_HIT','closed_loss') AND pnl_pct >  0.001)
   );

-- 3b. Non-CRYPTO threshold = 0.0005 (5bp)
UPDATE trading_picks
   SET status = CASE
       WHEN pnl_pct >  0.0005 THEN 'WON'
       WHEN pnl_pct < -0.0005 THEN 'LOST'
       ELSE 'EXPIRED'
   END
 WHERE asset_class <> 'CRYPTO'
   AND pnl_pct IS NOT NULL
   AND (
     (status IN ('WON','TP_HIT','closed_win') AND pnl_pct < -0.0005) OR
     (status IN ('LOST','SL_HIT','closed_loss') AND pnl_pct >  0.0005)
   );
```

## Step 4 — Verification (post-backfill, run Step 1 diagnostic again)

Re-run the Step 1 SQL. Expect `won_with_negative_pnl` and
`lost_with_positive_pnl` to both drop to 0 (modulo new rows written
between Step 3 and Step 4 — but those should already be guarded by the
2026-05-12 sign-coherence fix).

## Risk register

| Risk | Mitigation |
|---|---|
| UPDATE rewrites the wrong rows | Read-only diagnostic at Step 1 confirms row counts BEFORE any UPDATE. If counts look wrong, halt. |
| Status enum extension (e.g. 'WIN'/'LOSS' variants) | The WHERE-clause enumerates only the contradiction patterns; rows in other status values are untouched. |
| Lost audit trail | Capture a snapshot table before UPDATE: `CREATE TABLE trading_picks_backup_2026_05_12 AS SELECT * FROM trading_picks WHERE pnl_pct IS NOT NULL AND ...` |
| Dashboard cache inconsistency | After UPDATE, dashboard_generator rebuilds at next cron tick; no manual intervention needed. |

## Execution checklist (when user greenlights)

1. ☐ User explicit sign-off on Option A vs B.
2. ☐ Run Step 1 diagnostic. Confirm scope.
3. ☐ Create snapshot table: `CREATE TABLE trading_picks_won_pnl_backup_2026_05_12 SELECT * FROM trading_picks WHERE [contradiction WHERE-clause];`
4. ☐ Run Step 3a (CRYPTO).
5. ☐ Run Step 3b (non-CRYPTO).
6. ☐ Re-run Step 1 diagnostic. Confirm counts → 0.
7. ☐ Wait one hourly cron cycle. Confirm `db_health.json::checks.won_pnl_contradiction.data.contradiction_detected = false`.
8. ☐ Drop the snapshot table after 7 days of green.

## NFA

This is a TRUTH-LAYER repair, not a strategy decision. It does not affect
any live trading logic — only restores honest book-keeping on closed
historical picks. Real-money sizing still gates on the 10-step Lopez de
Prado AFML readiness pipeline regardless.

---

**Status:** DRAFT — awaiting user sign-off. See
`audit_dashboard/real_money.html#queued` for the queued item.
