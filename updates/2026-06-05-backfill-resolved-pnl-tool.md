# Backfill resolved PnL on trading_picks

**Date:** 2026-06-05

## Problem

918 resolved `trading_picks` rows have `pnl_pct` NULL or zero despite `exit_price` set — breaks forward stats (e.g. inverse_ml ADA) and class WR/PF.

## Solution

`tools/backfill_resolved_pnl.py` recomputes PnL using the zero-safeguard formula. **`--apply` requires `ejaguiar1_backups` archive via `archive_table_slice` first.**

## Impact (dry-run 2026-06-05)

- Candidates: **918**
- Planned fixes: **823** (95 skipped — no exit_price)

## Usage

```bash
python3 tools/backfill_resolved_pnl.py --dry-run
python3 tools/backfill_resolved_pnl.py --apply --limit 100   # pilot batch
python3 tools/backfill_resolved_pnl.py --apply --strategy inverse_ml_enhanced_ADAUSDT_15m_D
```