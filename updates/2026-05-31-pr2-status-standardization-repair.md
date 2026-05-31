# PR #2: Status Standardization Repair (2026-05-31)

## What was broken
607 non-canonical statuses in `trading_picks` (`CLOSED_SL`, `CLOSED_TP`, `WON`, `FLAT`, etc.) causing inconsistent portfolio calculations and incorrect win-rate reporting.

## What was changed
Added three components to `tools/repair_data_integrity.py`:

### 1. `_CANONICAL_STATUSES` frozenset
Mirrors `tools/standardize_statuses.py` — `TP_HIT`, `SL_HIT`, `LOST`, `EXPIRED`, `TIME_EXIT`, `ACTIVE`, `OPEN`.

### 2. `_STATUS_MAPPINGS` (11 rules)
- **WON/WIN** → `TP_HIT` (pnl>0) / `LOST` (pnl≤0)
- **LOSS** → `LOST` (pnl<0) / `TP_HIT` (pnl≥0)
- **CLOSED_SL** → `SL_HIT` (unconditional)
- **CLOSED_TP** → `TP_HIT` (unconditional)
- **FLAT** → `TIME_EXIT`, **SIGNAL/STALE** → `EXPIRED`

### 3. `_repair_status_standardization(cur)` callable
- **Pre-loop**: Fixes rows already tagged with `STATUS_STANDARDIZED` in `exit_reason` but where status wasn't actually corrected (race condition edge case — 35 rows)
- **Main loop**: Standardizes remaining non-canonical rows with `exit_reason NOT LIKE '%STATUS_STANDARDIZED%'` idempotency guard
- Tags all corrected rows with `STATUS_STANDARDIZED` in `exit_reason` for audit trail

### 4. `status_standardization` check in CHECKS
Counts rows with non-canonical status via `COUNT(*) WHERE status NOT IN (canonical_set)`.

## Execution results
| Pass | Rows detected | Rows repaired |
|------|---------------|---------------|
| 1st  | 794           | 759           |
| 2nd  | 35            | 35            |
| **Total** | **794** | **794** |

## Post-repair verification
- `status_standardization`: **PASS** (0 non-canonical rows)
- `won_status_contradiction`: **PASS** (0 WON rows with negative PnL)
