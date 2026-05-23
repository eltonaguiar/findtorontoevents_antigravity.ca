# Zero-PnL Backfill SQL Draft — 2026-05-12

User audit 2026-05-12 cites **69% of resolved trades have zero PnL**.
This is the second-largest truth-layer corruption alongside the
WON-vs-PnL contradiction (draft at `reports/won_vs_pnl_backfill_sql_2026-05-12.md`).

## Hypotheses for zero-PnL rows

Per memory + investigator findings:
1. Resolver wrote `status=WON|LOST` but `exit_price` is NULL/0 → pnl_pct computed from (NULL − entry)/entry = 0.
2. Auto-expired rows where `exit_reason` is generic (TIME_EXIT/EXPIRED) and exit_price was filled at entry_price → pnl_pct = exact 0.
3. lm_signals expire-cron skips the resolver (per F10 evidence-graded final).
4. Synthetic / template rows (already partially covered by ghost-row triple-block commit 597819d79c7).

## Step 1 — Read-only diagnostic

```sql
-- Counts per category
SELECT
  asset_class,
  COUNT(*) AS total_terminal,
  SUM(CASE WHEN pnl_pct = 0 THEN 1 ELSE 0 END) AS zero_pnl_count,
  SUM(CASE WHEN pnl_pct = 0 AND (exit_price IS NULL OR exit_price = 0) THEN 1 ELSE 0 END) AS zero_pnl_null_exit,
  SUM(CASE WHEN pnl_pct = 0 AND exit_price = entry_price THEN 1 ELSE 0 END) AS zero_pnl_exit_eq_entry,
  SUM(CASE WHEN pnl_pct = 0 AND exit_price IS NOT NULL AND exit_price <> entry_price AND exit_price > 0 THEN 1 ELSE 0 END) AS zero_pnl_other
FROM trading_picks
WHERE status IN ('WON','LOST','TP_HIT','SL_HIT','EXPIRED','closed_win','closed_loss')
  AND pnl_pct IS NOT NULL
GROUP BY asset_class
ORDER BY total_terminal DESC;
```

Per-strategy variant (top 20 strategies by zero-pnl count):
```sql
SELECT strategy,
       COUNT(*) AS n,
       SUM(CASE WHEN pnl_pct = 0 THEN 1 ELSE 0 END) AS zero_pnl,
       ROUND(100.0 * SUM(CASE WHEN pnl_pct = 0 THEN 1 ELSE 0 END) / COUNT(*), 2) AS zero_pnl_pct
FROM trading_picks
WHERE status IN ('WON','LOST','TP_HIT','SL_HIT','EXPIRED','closed_win','closed_loss')
  AND pnl_pct IS NOT NULL
GROUP BY strategy
HAVING zero_pnl > 100
ORDER BY zero_pnl DESC
LIMIT 20;
```

## Step 2 — Decision

Per row, 4 options:

**Option A — Re-compute from entry/exit if both present:**
```sql
UPDATE trading_picks
   SET pnl_pct = CASE
       WHEN direction IN ('LONG','BUY') THEN (exit_price - entry_price) / entry_price * 100
       WHEN direction IN ('SHORT','SELL') THEN (entry_price - exit_price) / entry_price * 100
       ELSE pnl_pct
   END
 WHERE pnl_pct = 0
   AND entry_price IS NOT NULL AND entry_price > 0
   AND exit_price IS NOT NULL AND exit_price > 0
   AND exit_price <> entry_price;
```

**Option B — Demote rows with NULL/0 exit_price to a non-terminal status
(needs separate column or audit-flag):**
```sql
-- Tag for re-resolution by outcome_resolver
UPDATE trading_picks
   SET status = 'PENDING_REOLVE',
       exit_reason = CONCAT('zero_pnl_demoted_', COALESCE(exit_reason, 'none'))
 WHERE pnl_pct = 0
   AND status IN ('WON','LOST','TP_HIT','SL_HIT','closed_win','closed_loss')
   AND (exit_price IS NULL OR exit_price = 0);
```
**Risk:** 'PENDING_REOLVE' is a new enum value; ensure outcome_resolver
recognizes it. If not supported, use status='OPEN' (let resolver pick up).

**Option C — Quarantine zero-pnl rows from dashboard aggregates** (no DB
write):
Add a filter in `audit_trail/dashboard_generator.py::_is_historical_blocked_pick`:
```python
# Zero-PnL noise filter (2026-05-12)
try:
    if float(pick.get("pnl_pct", 0) or 0) == 0:
        # Exclude only zero-pnl terminal rows; OPEN/ACTIVE zero is fine
        if str(pick.get("status", "")).upper() in ("WON","LOST","TP_HIT","SL_HIT","WIN","LOSS"):
            return True
except (ValueError, TypeError):
    pass
```
**Pro:** no DB write; reversible; instant impact on /audit metrics.
**Con:** leaves the rows in the DB; future audits still see them.

**Option D — DELETE the zero-pnl rows** — most aggressive; lose audit
trail. NOT recommended without snapshot.

## Recommended sequence

1. Run Step 1 diagnostic — confirm scope per class + per strategy.
2. **Ship Option C first** (read-side filter, no DB write, immediate UI
   impact). Single commit to dashboard_generator.py + the filter helper
   already exists.
3. Run Step 2 Option A (recompute from entry/exit). This catches the
   "writer dropped pnl computation" subset that has good prices but
   zero pnl_pct.
4. After Option A, re-run Step 1 diagnostic. If significant zero_pnl_null_exit
   remains (rows with no exit_price), ship Option B (demote to re-resolution).
5. Skip Option D entirely; the audit trail matters more than DB cleanliness.

## Verification

After each step, re-pull `audit_dashboard/data/db_health.json::checks.outcome_coverage`
and `pnl_integrity`. Expected:
- `raw_resolved_pct` either steady or improving (Option A adds resolved PnL where it was 0)
- `pnl_integrity.mismatch_pct` drops as recomputed values match (exit-entry)/entry math

## Sizing

| Step | Effort | Risk |
|---|---|---|
| Step 1 diagnostic | 5 min (read-only) | None |
| Option C (filter) | 30 min code + commit | Low (reversible) |
| Option A (recompute) | 15 min SQL + verification | Low (math is mechanical) |
| Option B (demote) | 30 min + outcome_resolver check | Medium (enum changes) |

## NFA

This is truth-layer repair, not a strategy change. Real-money sizing
remains gated on the 10-step Lopez de Prado AFML readiness pipeline
regardless.

## Status

**DRAFT** — awaiting user sign-off on Option A SQL execution. Option C
is a single-commit change I can ship now if user approves.

## Refs

- User audit 2026-05-12 (69% zero-pnl finding)
- `reports/won_vs_pnl_backfill_sql_2026-05-12.md` (sibling draft)
- `audit_trail/dashboard_generator.py::_is_historical_blocked_pick`
- `tools/db_health_check.py::check_pnl_integrity` (current detector)
