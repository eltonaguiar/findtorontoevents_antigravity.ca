# Audit Dashboard Compound Return Fix — 2026-05-23

## Problem

The audit dashboard at `findtorontoevents.ca/audit` was showing absurd compound return metrics:
- **Compound Return (EW): +1,122,354.53%** — completely unrealistic for any portfolio
- **Purged EW Compound: +3,909,501,741.94%** (3.9 billion %) — from clean_metrics

## Root Cause

Two separate issues:

### 1. Client-side compound (template.html) — 500% cap, no ceiling
- `compoundEwCappedPct(closedPicks, 500)` used a **500% per-trade cap** vs server's **2%**
- No hard ceiling was applied, allowing exponential blow-up across thousands of trades
- Affected: summary card when filters active, and all per-asset-class cards

**Math:** With N=10,000 trades and 500% cap, even a tiny mean of 0.1% per trade compounds to:
`(1.001)^10000 ≈ 22,026` → 2,202,500% return. The 500% cap was so loose it was effectively no cap.

### 2. Server-side purged compound (stats_cleaner.py) — no cap at all
- `_compound_pct_ew_chronological(purged, None)` — `None` means **uncapped**
- Single outlier trades with +8,559% PnL (like the CADJPY data error) blew up the product

## Fix

### template.html (3 changes)
1. **Line 5129:** Changed `compoundEwCappedPct(closedPicks, 500)` → `compoundEwCappedPct(closedPicks, 2)` with ±9999% hard ceiling
2. **Line 6366:** Same fix for per-asset-class compound cards
3. **Tooltips:** Updated all references from "±500% cap" to "±2% cap, ±9999% hard ceiling"

### stats_cleaner.py (1 change)
- **Line 143:** Changed `_compound_pct_ew_chronological(purged, None)` → `_compound_pct_ew_chronological(purged, max_abs_pct=2.0)`

Both changes align with `dashboard_generator.py` line 14505 which already uses `_MAX_PNL_COMPOUND = 2`.

## Impact

| Metric | Before | After |
|--------|--------|-------|
| Compound Return (EW) — filtered | +1,122,354.53% | Realistic value (capped at 9999%) |
| Purged EW Compound | +3,909,501,741.94% | Realistic value (±2% per trade) |
| Per-asset-class compound | Same absurd pattern | Same fix applied |
