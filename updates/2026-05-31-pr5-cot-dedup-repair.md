# PR #5 — COT Dedup Reconciliation Repair

**Date:** 2026-05-31
**Branch:** `fix/incidents-batch-resolve-2026-05-31`
**Incidents addressed:** #4 (COT paper pilot over-emission), #16 (Ring DSR=1.0 vs BLOCKED reconciliation)

## Problem

COT (Commitments of Traders) strategies count the same weekly CFTC release as ~100 separate trades, inflating n from ~5 to 101. This produces misleading DSR=1.0/WR=86.5% claims that contradict the post-dedup reality (WR 5%/PF 0.12 on n=20).

**Root cause:** The `cot_positioning` and `multi_asset_cot` emitters re-emit the same CFTC release across multiple scan cycles without deduplication at write time.

## Fix

Added a `cot_dedup` check + callable `repair_sql` to `tools/repair_data_integrity.py`:

### Check (`cot_dedup`)
- Counts duplicate COT picks grouped by `(symbol, strategy, direction, YEARWEEK(created_at, 1))`
- Filters to `_COT_DEDUP_STRATS`: `multi_asset_cot`, `cot_positioning`, `cftc_cot_commercial_signal`, `multi_asset_copytrader`
- Pass condition: 0 duplicate groups

### Repair (`_repair_cot_dedup`)
- Creates temporary table with `MIN(id)` per dedup key group
- DELETE self-join removing all but the earliest pick per `(symbol, strategy, direction, release_week)`
- `LIMIT 50000` safety cap
- `DROP TEMPORARY TABLE IF EXISTS` before CREATE to prevent stale data on re-calls

### Dedup Key
Matches `audit_trail/dashboard_generator.py` `_dedup_cot_over_emission()`:
```
(symbol, strategy, direction, YEARWEEK(created_at, 1))
```
First occurrence per CFTC release week wins (sorted by `MIN(id)`).

## Changes

| File | Change |
|------|--------|
| `tools/repair_data_integrity.py` | Added `_COT_DEDUP_STRATS` frozenset, `cot_dedup` check, `_repair_cot_dedup(cur)` callable repair |

## To Execute

```bash
DB_PASS_STOCKS=<pass> python3 tools/repair_data_integrity.py --write
```

The `cot_dedup` check will report duplicate COT rows, and `--write` will delete them keeping the earliest pick per release week.

## Verification

- ✅ Compiles without syntax errors
- ✅ Code-reviewed: parameterized queries, temp table lifecycle, redundant WHERE clause removed
- ✅ Dedup key consistent with `audit_trail/quality_gates.py` `COT_DEDUP_SYSTEMS` and `dashboard_generator.py` `_dedup_cot_over_emission()`
