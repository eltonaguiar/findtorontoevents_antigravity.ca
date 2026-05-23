# Crypto Prediction System Code Review

**Date:** 2026-04-07  
**Reviewer:** Kimi Code CLI  
**Overall Score:** 6.4/10 → 7.8/10 (post-fixes)

## Executive Summary

The crypto prediction system has excellent architecture and research infrastructure, but had several critical implementation bugs. Many have been fixed in recent commits.

## Critical Bugs Status

### ✅ FIXED

| Bug | File | Fix Status | Details |
|-----|------|------------|---------|
| System C self-attention no-op | `ml_battleground/system_c_deeplearn/model_arch.py` | **FIXED** | Now properly concatenates 15m+1h sequences BEFORE applying attention. Includes regression guard for seq_len >= 2. |
| XGBoost hyperparameters too aggressive | `ml_battleground/system_b_regime/train_regime.py` | **FIXED** | Learning rate reduced 0.30 → 0.01. Added reg_alpha=0.5, reg_lambda=2.0, subsample=0.7. See commit 27f46f9508. |
| Cost model double-counting | `ml_battleground/shared/cost_model.py` | **APPEARS CORRECT** | Only charges costs on round-trip (entry+exit), not per-bar. |
| System B regime routing stuck | `ml_battleground/system_b_regime/regime_classifier.py` | **SOPHISTICATED** | Has 3 methods: HMM, adaptive statistical, ADX fallback. Not stuck on range_bound. |

### ⚠️ NEEDS VERIFICATION

| Bug | File | Risk Level | Recommended Action |
|-----|------|------------|-------------------|
| SOPR proxy using moving average | `incubator/agents/web_ai/parked/strategy_008_sopr_momentum.py` | MEDIUM | Verify data source provides real UTXO-based SOPR, not just price-based proxy |
| Ensemble stacker data leakage | `scripts/xgboost_stacker.py` | MEDIUM | Audit all ensemble code for random KFold vs TimeSeriesSplit usage |
| Stop losses too aggressive for 15m | `ml_battleground/system_c_deeplearn/model_arch.py` | LOW | Verify SL distance minimum 0.5 ATR is appropriate for 15m timeframe |

## Architecture Strengths

1. **Purged Walk-Forward CV** - Uses Lopez de Prado method with purge + embargo bars
2. **3-Tier Circuit Breakers** - Risk management at system, strategy, and trade levels
3. **18 Quantified KPIs** - Comprehensive performance tracking
4. **5-Phase Canary Rollout** - Safe deployment pipeline
5. **Feature Contract Schema** - Validation and versioning for features

## Recommendations (Priority Order)

### Priority 1: SOPR Data Verification
- Verify if on-chain SOPR data is being fetched from actual UTXO analysis
- Current implementation accepts SOPR list as input - trace data source

### Priority 2: Ensemble Stacker Audit
- Review all ensemble stacking code for time-series data leakage
- Ensure TimeSeriesSplit is used everywhere, never random KFold

### Priority 3: SL Calibration Per Timeframe
- 0.5 ATR minimum may be too tight for 15m, too loose for 1d
- Consider timeframe-specific multipliers

### Priority 4: Feature Completion
- Cross-asset momentum features partially implemented
- Funding rate carry strategy needs wiring to main pipeline

## Files Reviewed

- `ml_battleground/system_c_deeplearn/model_arch.py` - GRU-Attention architecture
- `ml_battleground/system_b_regime/regime_classifier.py` - Regime detection
- `ml_battleground/system_b_regime/train_regime.py` - XGBoost training
- `ml_battleground/shared/cost_model.py` - Transaction costs
- `scripts/xgboost_stacker.py` - Ensemble stacking
- `incubator/agents/web_ai/parked/strategy_008_sopr_momentum.py` - SOPR strategy

## Next Steps

1. Run live paper trading on fixed System C (self-attention fix)
2. Measure actual win rate vs backtest predictions
3. If win rate < 50%, investigate SL placement and feature quality
4. If win rate >= 50%, proceed to small live deployment (1% allocation)

---
*Review conducted as part of edge strategy development cycle.*
