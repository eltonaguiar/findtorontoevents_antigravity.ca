# Asset Class Deep Dive: ETF

**Source:** scratch-hippodraco research session  
**Date:** 2026-11-15T07:00Z  
**Status:** INSUFFICIENT_DATA — n=45, WR=2.22%, PF=0.0216

## Current State

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| n (resolved) | 45 | ≥100 | FAIL |
| WR | 2.22% | ≥50% | FAIL |
| PF | 0.0216 | ≥1.5 | FAIL |
| Historical PF | ~1.24 | ≥1.5 | FAIL |
| Historical WR | ~55% | ≥50% | PASS (historical only) |
| WF consistency | 100% (historical) | N/A | PASS (historical) |
| OOS WR | 75% (historical) | ≥50% | PASS (historical) |
| Decay | +23% (historical) | positive | PASS (historical) |

## Strategies Identified in Repo

| Strategy | File | WR | PF | n | Status |
|----------|------|-----|-----|-----|--------|
| etf_sector_rotation | `alpha_engine/etf_strategies.py` | unknown | unknown | unknown | unvalidated |
| etf_sector_rotation_bl | `alpha_engine/etf_strategies.py` | unknown | unknown | unknown | unvalidated |
| etf_dual_momentum | `alpha_engine/etf_strategies.py` | unknown | unknown | unknown | unvalidated |
| etf_economic | `alpha_engine/etf_strategies.py` | unknown | unknown | unknown | unvalidated |
| etf_relative_strength | `alpha_engine/etf_strategies.py` | unknown | unknown | unknown | unvalidated |
| FreshPicks DNA | `alpha_engine/antigravity_strategies.py` | 95% | 1.61 | unknown | unverified |

## Key Issues

1. **n=45**: Far below 100 floor
2. **PF=0.0216**: Catastrophically low (current snapshot)
3. **WR=2.22%**: Nearly all trades are losses
4. **SPY miscategorized**: SPY sometimes classified as equity instead of ETF
5. **97.8% zero-PnL**: Historical snapshot showed most ETF picks at 0%
6. **Expense ratio not modeled**: ETFs have ongoing cost drag

## Recommended Next Steps

1. Fix classifier: SPY not miscategorized as equity
2. Expand ETF universe (XLF, XLE, XLK, XLV, XLI, XLB, XLP, XLU, XLRE, XLC, EFA, EEM, AGG, TLT)
3. Model expense ratio drag in PnL calculation
4. Backtest sector rotation strategy with walk-forward
5. Accumulate n≥100 before any edge claim
