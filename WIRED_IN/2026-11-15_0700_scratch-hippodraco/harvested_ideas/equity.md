# Asset Class Deep Dive: EQUITY (US Stocks)

**Source:** scratch-hippodraco research session  
**Date:** 2026-11-15T07:00Z  
**Status:** HIGH PRIORITY — Best current candidate

## Current State

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| n (resolved) | 250 | ≥100 | PASS |
| WR | 59.2% | ≥50% | PASS |
| PF | 0.9392 | ≥1.5 | FAIL |
| MDD | 33.04% | ≤20% | FAIL |
| Sharpe | ~0.9 | ≥1.0 | FAIL |
| Bootstrap CI | crosses zero | excludes zero | FAIL |
| DSR | not computed | ≥0.95 | UNKNOWN |
| SPA p-value | not computed | ≤0.10 | UNKNOWN |
| Cost model | 10bps hardcoded | real costs | PARTIAL |
| OOS validation | none | required | FAIL |
| Multiple testing | not corrected | required | FAIL |

## Strategies Identified in Repo

| Strategy | File | WR | PF | n | Status |
|----------|------|-----|-----|-----|--------|
| connors_rsi2_pullback | `alpha_engine/equity_strategies.py` | 75.7% | 4.84 | 78 | n<100 |
| stocks_rsi2_pullback | `alpha_engine/equity_strategies.py` | ~60% | ~1.0 | ~250 | best candidate |
| donchian-stock-breakout | `alpha_engine/equity_strategies.py` | 78.6% | unknown | 14 | n too small |
| rs-breakout-scout | `alpha_engine/equity_strategies.py` | 81.3% | unknown | 32 | n too small |
| growth_stock_screener | `alpha_engine/equity_strategies.py` | unknown | unknown | 2 | n too small |
| vwap-reversion-scout | `alpha_engine/equity_strategies.py` | unknown | 3.74 | 15 | n too small |
| mtf-align-scout | `alpha_engine/equity_strategies.py` | unknown | 1.50 | 19 | n too small |
| gap-and-go-stocks | `alpha_engine/equity_strategies.py` | unknown | unknown | 1 | n too small |

## Key Issues

1. **n=250 borderline**: Just above 100 minimum but needs more for statistical power
2. **PF=0.9392**: Below 1.5 threshold — costs not fully modeled
3. **MDD=33.04%**: Well above 20% limit
4. **No walk-forward**: All backtests in-sample
5. **No multiple testing correction**: 27+ parameter combos tested without correction
6. **Single-source concentration**: 100% alpha_engine

## Recommended Next Steps

1. Fix PnL calculation (use exit_price not current_price)
2. Apply full cost model (10bps round-trip)
3. Run walk-forward with embargo
4. Apply DSR with correct nb_trials
5. Run SPA/White's Reality Check
6. Run bootstrap CI on mean excess return
7. Test regime splits (bull/bear/sideways)
8. Run shuffle control (permuted prices)
