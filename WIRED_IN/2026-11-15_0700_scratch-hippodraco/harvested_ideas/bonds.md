# Asset Class Deep Dive: BOND

**Source:** scratch-hippodraco research session  
**Date:** 2026-11-15T07:00Z  
**Status:** INSUFFICIENT_DATA — n=1, structurally blocked

## Current State

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| n (resolved) | 1 | ≥100 | FAIL |
| WR | 0.0% | ≥50% | FAIL |
| PF | 0.0 | ≥1.5 | FAIL |
| Verdict | INSUFFICIENT_DATA | N/A | FAIL |

## Strategies Identified in Repo

| Strategy | File | WR | PF | n | Status |
|----------|------|-----|-----|-----|--------|
| bond_strategies.py | `alpha_engine/bond_strategies.py` | unknown | unknown | 1 | unvalidated |
| bond_strategies.py (variant) | `alpha_engine/bond_strategies.py` | unknown | unknown | unknown | unvalidated |

## Key Issues

1. **n=1**: Single trade — statistically meaningless
2. **No FRED API key**: `fred_data_fetcher.py` exists but key not configured
3. **Price-only PnL**: Bond ETF PnL ignores distributions/dividends
4. **Scope unclear**: Bond ETFs vs true bonds not decided
5. **Blocked**: In `BLOCKED_ASSET_CLASSES` in `quality_gate.py`

## Recommended Next Steps

1. Set FRED_API_KEY in repo secrets to unblock BOND scanner
2. Decide scope: bond ETFs (model distributions) vs true bonds
3. Model expense ratios and dividend distributions
4. Benchmark against TLT/IEF/AGG total return
5. Accumulate n≥100 before any edge claim
