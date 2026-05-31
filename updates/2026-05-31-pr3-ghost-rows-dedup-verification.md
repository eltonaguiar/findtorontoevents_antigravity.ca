# PR3: Ghost Rows Deduplication Verification

**Date:** 2026-05-31
**Branch:** `fix/pr3-ghost-rows-dedup-verification`
**Severity:** P0 — historical ghost-row cohorts contaminated performance stats
**Incident addressed:** `56,559 ghost rows in trading_picks (top cohort: 20,474 identical MATICUSDT entries)`

## What Was Broken

The incidents inventory reported a P0 ghost-row issue attributed to `trading_picks`, describing 12 large duplicate cohorts such as `CRYPTO/quan_engine/MATICUSDT/LONG/pnl=-15.0` and MEMECOIN `meta_strategy` variants.

On inspection, the currently committed health-check detector (`tools/db_health_check.py`) and cleanup runner (`tools/cleanup_ghost_rows.py`) primarily target `bt_backtest_trades` constant-PnL duplicate cohorts. The `trading_picks` table does not have an `asset_class` column; it uses `category`.

## What Was Checked

1. Directly inspected the live `trading_picks` schema.
2. Queried current `trading_picks` duplicate cohorts using the incident-style grouping:
   - `category`
   - `strategy`
   - `symbol`
   - `direction`
   - `ROUND(pnl_pct, 4)`
   - `COUNT(DISTINCT entry_price) < 5`
   - `COUNT(*) > 1000`
3. Ran the guarded ghost cleanup runner in dry-run mode:
   - `python3 tools/cleanup_ghost_rows.py --min-size 1000 --output tools/ghost_cleanup_report_current.json`

## Current State

The current live database returned **zero active `trading_picks` ghost cohorts** under the incident definition.

The guarded cleanup runner also returned **zero active known ghost cohorts**:

```text
Found 0 active ghost cohorts.
Found 0 ghost cohorts
No ghost cohorts found. Nothing to do.
```

## What Changed

No destructive database cleanup was required in this session because the target cohorts are already absent.

No code change was needed for `tools/cleanup_ghost_rows.py` because it already provides:

- dry-run default behavior
- `--execute` opt-in deletion
- `--yes` confirmation bypass only when explicitly requested
- delete safety caps
- batch deletion
- known cohort targeting
- JSON report output

## Verification

Verified with:

```bash
python3 tools/cleanup_ghost_rows.py --min-size 1000 --output tools/ghost_cleanup_report_current.json
```

Result: clean; zero active ghost cohorts found.

## Follow-Up Recommendation

The incident should be updated from `OPEN` to `RESOLVED` or `STALE_VERIFIED_CLEAN` in the incident tracker. Its affected component should be reviewed because the committed detector scans `bt_backtest_trades`, while the incident title names `trading_picks`.

If the issue reappears, use the existing guarded runner instead of ad-hoc SQL deletes:

```bash
python3 tools/cleanup_ghost_rows.py --min-size 1000
python3 tools/cleanup_ghost_rows.py --execute --limit 1000
```
