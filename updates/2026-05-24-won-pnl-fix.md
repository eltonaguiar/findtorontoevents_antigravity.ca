# WON PnL Contradiction Fix — 2026-05-24

## Problem
`audit_dashboard/data/db_health.json` reported:
- 2,531 picks with status `WON` had average PnL of **-41.13%**
- 9 out of 2,531 "WON" picks had explicitly negative PnL
- This is logically impossible — a won trade should have positive PnL

## Root Cause

Two bugs contributed to this contradiction:

### Bug 1: Direction-agnostic PnL formula in `_resolve_claude_gainer_ml_pick`
**File:** `alpha_engine/outcome_resolver.py` line 1656

The function `_resolve_claude_gainer_ml_pick` used a LONG-only PnL formula:
```python
pnl_pct = round((exit_price - entry) / entry * 100, 2)  # WRONG for SHORT
```

This meant SHORT positions that hit TP (exit_price < entry, which is profitable for SHORTs) would get a **negative** PnL because `(97 - 100) / 100 = -3%` instead of the correct `(100 - 97) / 100 = +3%`.

The function already had `is_short` computed for TP/SL comparison but did not use it for PnL calculation.

### Bug 2: No sign-coherence guard in `backfill_local_sources.py`
**File:** `audit_trail/backfill_local_sources.py` lines 208-227

The backfill script set `status = "WON"` based purely on `exit_reason` (TP_HIT, etc.) without checking whether the PnL was actually positive. This allowed contradictory data (WON status + negative PnL) to be written to the database.

Note: `audit_trail/mysql_client.py` already had this guard in `mysql_close_trade` (lines 637-648), but `backfill_local_sources.py` did not mirror it.

## What Was Fixed

### Fix 1: Direction-aware PnL in `_resolve_claude_gainer_ml_pick`
**File:** `alpha_engine/outcome_resolver.py` line 1656

Changed from:
```python
pnl_pct = round((exit_price - entry) / entry * 100, 2)
```

To:
```python
if is_short:
    pnl_pct = round((entry - exit_price) / entry * 100, 2)
else:
    pnl_pct = round((exit_price - entry) / entry * 100, 2)
```

This ensures SHORT positions get positive PnL when exit_price < entry (price fell, short profits).

### Fix 2: Sign-coherence guard in `backfill_local_sources.py`
**File:** `audit_trail/backfill_local_sources.py`

Added a guard that checks PnL sign against status before writing to DB:
- If status is WON/TP_HIT but PnL < 0 → change status to LOST
- If status is LOST/SL_HIT but PnL > 0 → change status to WON

This mirrors the existing guard in `mysql_client.py:mysql_close_trade`.

## New Files

### `tools/test_won_pnl_contradiction.py`
Unit tests validating:
- PnL formula correctness for LONG and SHORT positions
- SHORT at TP yields positive PnL
- SHORT at SL yields negative PnL
- `classify_outcome` returns WON only for positive PnL
- `_resolve_claude_gainer_ml_pick` uses direction-aware PnL
- Fuzz test: 5000 randomized cases for WON/LOST invariant

### `tools/audit_won_picks.py`
DB audit tool that:
- Queries `trading_picks` for rows where `status='WON' AND pnl_pct < 0`
- Reports count, details, and breakdowns by exit_reason and direction
- Optionally corrects status from WON to LOST (`--correct` flag)
- Supports `--dry-run` for preview without execution

## Verification

Run tests:
```bash
python tools/test_won_pnl_contradiction.py
```

Expected: All 12 tests pass.

Run audit:
```bash
python tools/audit_won_picks.py
```

## Impact on Existing Data

The 9 existing rows in the DB with `status='WON' AND pnl_pct < 0` were written by `backfill_local_sources.py` before this fix. They need manual correction. Use:
```bash
python tools/audit_won_picks.py --correct
```

Future picks resolved by `_resolve_claude_gainer_ml_pick` and backfilled by `backfill_local_sources.py` will have coherent status/PnL.

## Files Changed
- `alpha_engine/outcome_resolver.py` — fixed PnL formula in `_resolve_claude_gainer_ml_pick`
- `audit_trail/backfill_local_sources.py` — added sign-coherence guard

## Files Created
- `tools/test_won_pnl_contradiction.py` — unit tests
- `tools/audit_won_picks.py` — DB audit tool
- `updates/2026-05-24-won-pnl-fix.md` — this file
