# Synthesis (P5)

## `bond_momentum_longshort_v1` — **NO_EDGE**

PF=0.0, WR=0.0%, n=5 - no profitability and too few trades; cross-test shows independence but signal is simplified.

**Engine votes:** cerebras: NO_EDGE, deepseek: NO_EDGE, xai: NO_EDGE

## `bond_term_premium_slope_v1` — **NO_EDGE**

PF=0.0, WR=0.0%, n=5 - no edge; simplified SMA proxy likely mis-represents intended term-premium logic.

**Engine votes:** cerebras: NO_EDGE, deepseek: NO_EDGE, xai: NO_EDGE

## `bond_liquidity_spread_v1` — **NO_EDGE**

PF=0.0, WR=0.0%, n=5 - no statistical edge; regime filter and risk-parity sizing not enough to generate returns.

**Engine votes:** cerebras: NO_EDGE, deepseek: NO_EDGE, xai: NO_EDGE

## `bond_regime_duration_v1` — **NO_EDGE**

PF=0.0, WR=0.0%, n=5 - flat performance; simplified signal likely mis-aligned with true volatility-regime intent.

**Engine votes:** cerebras: NO_EDGE, deepseek: NO_EDGE, xai: NO_EDGE

## `bond_credit_spread_term_v1` — **MIXED**

PF=1.51 meets Tier-2 PF but WR=33.3% and n=9 are far below requirements; cross-test independence is good but signal simplification limits confidence.

**Engine votes:** cerebras: MIXED, deepseek: MIXED, xai: MIXED

## `bond_inflation_rotation_v1` — **MIXED**

PF=1.99 exceeds floor, WR=45.5% close to target, yet n=11 trades is insufficient; regime filter and simplified spread logic need validation.

**Engine votes:** cerebras: MIXED, deepseek: MIXED, xai: MIXED

## `bond_momentum_cross_country_v1` — **NO_EDGE**

PF=0.94, WR=42.9%, n=7 - below PF threshold and trade count; simplified SMA crossover likely mis-represents cross-country momentum.

**Engine votes:** cerebras: NO_EDGE, deepseek: NO_EDGE, xai: NO_EDGE

## `bond_liquidity_premium_on_off_v1` — **MIXED**

PF=1.51 meets PF floor but WR=33.3% and n=9 are too low; cross-test independence is fine but signal translation is still approximate.

**Engine votes:** cerebras: MIXED, deepseek: MIXED, xai: MIXED

## `bond_macro_factor_duration_v1` — **NO_EDGE**

PF=0.94, WR=42.9%, n=7 - insufficient PF and trade count; simplified macro composite likely diverges from intended factor model.

**Engine votes:** cerebras: NO_EDGE, deepseek: NO_EDGE, xai: NO_EDGE

## `bond_regime_switching_duration_v1` — **NO_EDGE**

PF=0.0, WR=0.0%, n=5 - no observable edge; regime-switching logic not captured by the SMA proxy.

**Engine votes:** cerebras: NO_EDGE, deepseek: NO_EDGE, xai: NO_EDGE

## `bond_momentum_cross_v1` — **NO_EDGE**

PF=0.94, WR=42.9%, n=7 - below PF threshold; simplified momentum selection may not reflect true top-2 ETF performance.

**Engine votes:** cerebras: NO_EDGE, deepseek: NO_EDGE, xai: NO_EDGE

## `bond_term_premium_v1` — **NO_EDGE**

PF=0.0, WR=0.0%, n=5 - no edge; term-premium estimate reduced to SMA crossover, losing intended signal nuance.

**Engine votes:** cerebras: NO_EDGE, deepseek: NO_EDGE, xai: NO_EDGE

## `bond_liquidity_premium_v1` — **NO_EDGE**

PF=0.94, WR=42.9%, n=7 - PF below floor; simplified spread widening rule likely mis-captures true liquidity premium dynamics.

**Engine votes:** cerebras: NO_EDGE, deepseek: NO_EDGE, xai: NO_EDGE

## `bond_credit_spread_v1` — **MIXED**

PF=1.51 meets PF floor, but WR=33.3% and n=9 trades fall short; cross-test independence is good, yet simplified spread percentile logic needs refinement.

**Engine votes:** cerebras: MIXED, deepseek: MIXED, xai: MIXED
