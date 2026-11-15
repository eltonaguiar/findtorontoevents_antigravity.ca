# Asset Class Deep Dive: FOREX

**Source:** scratch-hippodraco research session  
**Date:** 2026-11-15T07:00Z  
**Status:** BLOCKED — Poor performance, drift alert active

## Current State

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| n (resolved) | 612 | ≥100 | PASS |
| WR | 32.19% | ≥50% | FAIL |
| PF | 0.6596 | ≥1.5 | FAIL |
| True 14d WR | ~5% | ≥50% | FAIL |
| Drift alert | KS_D = 6.6× critical | NOT active | BLOCKED |
| MDD | unknown | ≤20% | UNKNOWN |

## Strategies Identified in Repo

| Strategy | File | WR | PF | n | Status |
|----------|------|-----|-----|-----|--------|
| IG Contrarian Sentiment | `alpha_engine/forex_strategies.py` | SHORT 57% vs LONG 21% | unknown | unknown | 36pp spread |
| Carry Trade Momentum | `alpha_engine/forex_strategies.py` | unknown | unknown | unknown | unvalidated |
| Forex TSMOM 12m | `alpha_engine/forex_strategies.py` | unknown | unknown | unknown | unvalidated |
| Forex RSI-2 Mean Reversion | `alpha_engine/forex_strategies.py` | unknown | unknown | unknown | unvalidated |
| London Session Breakout | `alpha_engine/forex_strategies.py` | 62% | unknown | unknown | Kimi RoTC |
| MomentumEMA | blocked | unknown | unknown | unknown | blocked |
| Volume Spike Breakout | blocked | unknown | unknown | unknown | blocked |
| Forex Carry Momentum | blocked | unknown | unknown | unknown | blocked |
| Alpha Engine Fast | blocked | unknown | unknown | unknown | blocked |
| Multi-Asset | blocked | unknown | unknown | unknown | blocked |

## Key Issues

1. **Catastrophic PF**: 0.6596 — edge is negative after costs
2. **True WR ~5%**: Headline 32% is inflated
3. **Drift alert**: KS_D = 6.6× critical — regime shift detected
4. **Spread costs**: ~1-2 pips = ~4bp/side destroys micro-edges
5. **Multiple variants**: Many strategies tested, no DSR ≥ 0.5 survivor

## Recommended Next Steps

1. **DO NOT unblock FOREX** while drift alert is active
2. If unblocking: enforce allowlist at execution gate (not dead helper)
3. Test SHORT-axis bias (57% WR vs LONG 21%)
4. Model spread costs properly (4bp/side round-trip)
5. Apply multiple testing correction (many variants tested)
