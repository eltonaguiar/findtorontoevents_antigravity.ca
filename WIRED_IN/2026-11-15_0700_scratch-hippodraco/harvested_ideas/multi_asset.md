# Asset Class Deep Dive: MULTI_ASSET

**Source:** scratch-hippodraco research session  
**Date:** 2026-11-15T07:00Z  
**Status:** EXPLORATORY — No dedicated multi-asset strategies in production

## Current State

Multi-asset strategies exist in the repo but none are production-ready:

| Strategy | File | Status |
|----------|------|--------|
| Bundle-Optimized Portfolios | `alpha_engine/antigravity_strategies.py` | 8 bundles, unvalidated |
| Sentinel Fund Strategy | `alpha_engine/sentinel_fund_strategy.py` | Unvalidated |
| Quantum Fusion System | `alpha_engine/quantum_fusion_backtester.py` | Unvalidated |
| Meta-Strategy Permutation | `alpha_engine/meta_strategy_permutation_engine.py` | Unvalidated |
| DARWIN Engine | `alpha_engine/anti_overfit_gate.py` | 9 engines, up to 90.5% WR (claimed) |
| FreshPicks DNA | `alpha_engine/fresh_picks_dna_strategy.py` | 95% WR claimed |

## Key Issues

1. **No production multi-asset strategy**: All multi-asset strategies are unvalidated prototypes
2. **DARWIN engine results suspect**: 30+ runs, up to 90.5% WR / Sharpe 97, but direction oscillates run-to-run (regime transition signature)
3. **No cross-asset correlation model**: No covariance matrix for multi-asset portfolio construction
4. **No regime-aware allocation**: No dynamic allocation based on market regime
5. **No cost model for multi-asset**: Different asset classes have different cost structures

## Recommended Next Steps

1. Build multi-asset portfolio optimizer (HRP, risk parity)
2. Implement regime-aware asset allocation
3. Add cross-asset correlation matrix
4. Model different cost structures per asset class
5. Test multi-asset walk-forward with OOS validation
