# PR7: Fix WON/LOST Status Labels in MySQL + Dedup Tool Enhancement

**Date:** 2026-05-27
**Branch:** `fix/pr7-ghost-rows-and-won-relabel`
**Severity:** P0 (WON rows showing avg pnl -41.1%) + P0 (56,559 ghost rows)

## Problem

1. **2,531 rows tagged status='WON' have avg pnl_pct = -41.13%.** Every WR/PF calculation using status is wrong.
2. **56,559 ghost rows** in trading_picks (20,474 identical MATICUSDT entries from quan_engine).
3. The existing `mysql_dedup_fix.py` handles dedup + confidence scale but doesn't fix status labels.

## Changes

### File: `tools/mysql_dedup_fix.py`
- **Added `step_fix_won_labels()`** function:
  - `status='WON' AND pnl_pct <= 0` → `status='LOST'`
  - `status='LOST' AND pnl_pct > 0` → `status='WON'`
- Wired as Step 3 in the pipeline (after dedup, before UNIQUE index)
- Dry-run by default, included in existing `--apply` flag

## Impact Analysis

- **WR calculations:** All downstream WR stats will become accurate. Currently, "WON" includes ~2,531 losers.
- **PF calculations:** Profit Factor will no longer count losing trades as wins.
- **Risk:** LOW — relabeling is based on pnl_pct sign (the ground truth). No data is deleted.
- **Ghost rows:** The existing dedup step handles these — no changes needed.

## Verification
1. Run `python tools/mysql_dedup_fix.py` (dry-run) — should show WON/LOST contradictions
2. Run with `--apply` to fix
3. Verify: `SELECT COUNT(*) FROM trading_picks WHERE status='WON' AND pnl_pct <= 0` should return 0
4. Check `/audit/` — aggregate WR/PF stats should shift (likely downward for some classes)
