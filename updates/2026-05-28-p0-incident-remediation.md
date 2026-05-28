# P0 Incident Remediation — 2026-05-28

## Three incidents resolved

### #1: WON rows re-labeled (0 remaining)
- **Issue**: WON status with negative/non-positive PnL (logical contradiction)
- **Fix**: All WON rows re-labeled to TP_HIT (positive PnL) or LOST (non-positive PnL)
- **Result**: 0 WON rows with pnl<=0, 0 WON total
- **Status**: ✅ RESOLVED

### #2: Ghost duplicate rows deduped (2,563 removed)
- **Issue**: 2,563 duplicate rows via (symbol, direction, entry_price, created_at) match
- **Fix**: Two-pass approach:
  - Pass 1: Deleted 2,195 rows using `=` join (missed NULL-entry_price rows)
  - Pass 2: Deleted 368 rows using `<=>` (NULL-safe) join to catch NULL matches
- **Result**: 0 duplicate groups, table reduced from 46,639 → 44,076 rows
- **Root cause**: `GROUP BY asset_class` bug in `tools/db_p0_integrity_remediation.py` (column `asset_class` doesn't exist, should be `category`). Fixed.
- **Status**: ✅ RESOLVED

### #3: FOREX pnl < -100% clamped (0 remaining)
- **Issue**: 5 FOREX rows with pnl_pct < -100%
- **Fix**: Already clamped to -100 in previous remediation session
- **Result**: 0 FOREX rows with pnl < -100%
- **Status**: ✅ RESOLVED

## Files changed
- `tools/db_p0_integrity_remediation.py`: Fixed `asset_class` → `category` in DELETE subquery GROUP BY clause (line 79)
- `tools/standardize_statuses.py`: New script — PnL-based status standardization across all non-canonical statuses

## P1 Follow-up: Full Status Standardization (2026-05-28)
- **Issue**: 974 rows across 8 non-canonical statuses (WIN, WON, LOSS, closed, CLOSED_SL, CLOSED_TP, SIGNAL, FLAT, STALE)
- **Fix**: PnL-based relabeling to canonical statuses (TP_HIT, SL_HIT, LOST, EXPIRED, TIME_EXIT)
- **Script**: `tools/standardize_statuses.py`
- **Result**: 0 non-canonical statuses remain. Final distribution:
  - TIME_EXIT: 27,799 | ACTIVE: 5,228 | TP_HIT: 3,394 | LOST: 3,305 | OPEN: 3,082 | SL_HIT: 1,174 | EXPIRED: 599
- **Status**: ✅ RESOLVED
