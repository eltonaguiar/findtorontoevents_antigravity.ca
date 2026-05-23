# EQUITY 3Y Validation Audit — 2026-05-19

## Summary

Attempted to extend EQUITY edge validation to 3Y window per Ring-2.6-1T recommendation. Found that the MySQL DB only contains EQUITY resolved picks going back to 2026-02-17 (~3 months, not 3 years).

## MySQL Query Results (post-dedup: 41,360 rows)

```sql
SELECT COUNT(*) as n,
  ROUND(SUM(CASE WHEN status IN ('WIN','WON','TP_HIT','CLOSED_TP') THEN 1 ELSE 0 END)/COUNT(*),4) as wr,
  ROUND(SUM(CASE WHEN status IN ('WIN','WON','TP_HIT','CLOSED_TP') AND pnl_pct IS NOT NULL THEN pnl_pct ELSE 0 END)
        /NULLIF(ABS(SUM(CASE WHEN status IN ('LOSS','LOST','SL_HIT','CLOSED_SL') AND pnl_pct IS NOT NULL THEN pnl_pct ELSE 0 END)),0),3) as pf,
  ROUND(AVG(CASE WHEN pnl_pct IS NOT NULL THEN pnl_pct END),4) as avg_pnl,
  MIN(created_at), MAX(created_at)
FROM trading_picks 
WHERE category='equity' AND status IN (...)
AND created_at >= DATE_SUB(NOW(), INTERVAL 3 YEAR)
```

| Window | n | WR | PF | avg_pnl | Date range |
|--------|---|----|----|---------|------------|
| 3Y | 65 | 49.2% | 0.760 | -0.18% | 2026-02-17 → 2026-05-18 |
| ALL-TIME | 65 | 49.2% | 0.760 | -0.18% | 2026-02-17 → 2026-05-18 |

**The 3Y window IS the all-time window.** The DB has no EQUITY resolved picks before 2026-02-17.

## Diagnosis

The DB started tracking EQUITY picks in February 2026 (system was primarily CRYPTO/COMMODITY earlier). The Ring-2.6-1T recommendation to use a 3Y MySQL window assumed historical data exists — it does not.

Ring's prior estimate of ~207 picks at 3Y was based on an extrapolation that didn't account for the system's actual launch date for EQUITY coverage.

## NW t-stat Assessment

With n=65, WR=49.2%:
- **NW t-stat**: `(0.492 - 0.5) * sqrt(65) / (0.492 * 0.508)^0.5` ≈ -0.13 → p ≈ 0.55 → **FAIL** (same as prior 1Y assessment)
- **DSR**: At n=65 with SR near 0 → DSR would also FAIL
- **PF=0.760 < 1.0**: System is net-negative on equity, not just sub-threshold

## Root Cause of Sub-threshold EQUITY Performance

The 65 resolved picks show WR=49.2% (just below 50%) and PF=0.760 (net negative). This is worse than the prior local assessment (WR=52.7% from `asset_class_health`). Possible causes:
1. The local `asset_class_health` uses post-noise-filter data; MySQL has all picks including noisy ones
2. The 65 MySQL picks include strategies that are now blocked/filtered out
3. Small n=65 → high variance

## Path to n≥100 for EQUITY Validation

Since we only have 3 months of EQUITY data, there is no 3Y shortcut. Options:

| Option | n | ETA | Notes |
|--------|---|-----|-------|
| Organic accumulation | ~65 + ~22/month | Aug 2026 | At current rate, n≥100 by ~Aug 2026 |
| Unblock equity sources | ~65 + more | sooner | Depend on which sources are blocked |
| Run walk-forward on existing 65 | 65 | now | Too few for 3-window harness (need n≥30/window) |
| Accept n=65 with NW Newey-West correction | 65 | now | NW t-stat p=0.55 → can't reject null |

**Recommended:** Accept n=65 as insufficient and flag as PENDING_MORE_DATA with target n=100 by Aug 2026. Do NOT run statistical validation on n=65 (too few windows, NW fails).

## Status Update for run_equity_edge_test.py

The script was designed for closed_picks.json. Extension to MySQL is possible but the data constraint is real — n=65 all-time. No amount of window-extension helps.

**Action**: Update the equity validation script to pull from MySQL but label result as `INSUFFICIENT_DATA` (n<100) and report next milestone.

## H-021 Pre-registration Note

Separately completed: pre-registered H-021 window 3 criteria in hypothesis_registry.json to prevent goal-post moving before 2026-05-26 re-run.
