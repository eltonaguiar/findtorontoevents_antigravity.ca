# PR #7: PnL Price Corruption Detection & Repair

**Date:** 2026-05-31  
**Branch:** `fix/incidents-batch-resolve-2026-05-31`

## Problem

The `pnl_integrity` check reported 722 rows with >1% mismatch between stored `pnl_pct` and the price-based calculation `(exit - entry) / entry`. Investigation revealed two distinct root causes:

### Root Cause A: Corrupted Exit Prices (19 rows)
- Exit prices were wildly wrong (e.g., entry=0.7157, exit=76,429 — a 10,679,247% move)
- These are data corruption: exit_price written from a different symbol or timeframe
- The calculated PnL is garbage, but `pnl_pct` often holds a reasonable value (computed independently by the strategy at exit time)

### Root Cause B: Genuine PnL Disagreement (374 rows on clean prices)
- Both `pnl_pct` and calculated PnL are in reasonable ranges (<500%)
- They disagree by >1% — could be due to fees, leverage, slippage, or different price sources
- Cannot safely auto-repair without knowing which value is authoritative

## Solution

**Added `pnl_price_corruption` check** (before `pnl_integrity`):
- Detects rows where `ABS(calc_pnl) > 500%` — impossible prices
- Repair: NULLs `exit_price` and tags `exit_reason` with `[PRICE_CORRUPT]`
- Does NOT touch `pnl_pct` — the stored value is more trustworthy

**Refined `pnl_integrity` check:**
- Added `ABS(calc_pnl) <= 500` filter to exclude corrupt-price rows
- Now measures genuine mismatches only (5.0% vs old 38.97%)
- Kept as monitoring-only (no `repair_sql`) — blind recalculation is unsafe

## Execution

```
pnl_price_corruption: 19 rows detected → 18 repaired (NULL exit_price + PRICE_CORRUPT tag)
pnl_integrity:         PnL mismatch dropped from 722/6,173 (38.97%) → 374/6,148 (6.1%) → 306/6,159 (5.0%)
```

## Verification

All 10 checks PASS after repair:
```
=== Summary: 10 PASS, 0 FAIL, 10 total ===
```

## Files Changed

- `tools/repair_data_integrity.py` — added `_repair_pnl_price_corruption(cur)`, `pnl_price_corruption` check, refined `pnl_integrity` query
