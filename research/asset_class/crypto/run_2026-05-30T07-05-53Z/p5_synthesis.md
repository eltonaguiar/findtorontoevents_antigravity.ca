# Synthesis (P5)

## `crypto_cross_mom_v1` — **NO_EDGE**

Backtest shows PF=2.86 but only 5 trades, MDD=37.1% >20% and WR=60% with a simplified signal; trade count far below Tier-2 floor (n≥100).

**Engine votes:** cerebras: NO_EDGE, deepseek: NO_EDGE, xai: NO_EDGE

## `crypto_ts_mom_v1` — **NO_EDGE**

Same metrics as other candidates (PF=2.86, n=5, MDD=37.1%); insufficient trade history and high drawdown prevent confidence.

**Engine votes:** cerebras: NO_EDGE, deepseek: NO_EDGE, xai: NO_EDGE

## `crypto_vol_target_v1` — **NO_EDGE**

PF looks attractive but only 5 trades, MDD exceeds Tier-2 limit and signal translation is simplified; not enough evidence of robust edge.

**Engine votes:** cerebras: NO_EDGE, deepseek: NO_EDGE, xai: NO_EDGE

## `crypto_regime_switch_v1` — **NO_EDGE**

Metrics identical to others with n=5 and MDD=37.1%; trade count too low for reliable inference.

**Engine votes:** cerebras: NO_EDGE, deepseek: NO_EDGE, xai: NO_EDGE

## `crypto_pairs_trade_v1` — **NO_EDGE**

Backtest PF=2.86 based on only 5 trades; high drawdown and simplified signal mean edge is unproven.

**Engine votes:** cerebras: NO_EDGE, deepseek: NO_EDGE, xai: NO_EDGE

## `crypto_momentum_cross_v1` — **NO_EDGE**

Despite PF=2.86, the sample contains only 5 trades and MDD=37.1% >20%; signal parsing is approximate, so no actionable edge.

**Engine votes:** cerebras: NO_EDGE, deepseek: NO_EDGE, xai: NO_EDGE

## `crypto_carry_funding_v1` — **NO_EDGE**

Same backtest numbers with n=5; drawdown too large and signal not faithfully implemented, so edge is not established.

**Engine votes:** cerebras: NO_EDGE, deepseek: NO_EDGE, xai: NO_EDGE

## `crypto_vol_target_btc_v1` — **NO_EDGE**

PF=2.86 derived from only 5 trades; MDD exceeds Tier-2 threshold and the entry logic is simplified, lacking confidence.

**Engine votes:** cerebras: NO_EDGE, deepseek: NO_EDGE, xai: NO_EDGE

## `crypto_pairs_meanrev_v1` — **NO_EDGE**

Only 5 trades, high MDD, and simplified signal translation; insufficient evidence of a repeatable edge.

**Engine votes:** cerebras: NO_EDGE, deepseek: NO_EDGE, xai: NO_EDGE

## `crypto_ml_boost_v1` — **NO_EDGE**

Backtest shows PF=2.86 but with n=5 and MDD=37.1%; the model-driven signal is not yet faithfully parsed, so no reliable edge.

**Engine votes:** cerebras: NO_EDGE, deepseek: NO_EDGE, xai: NO_EDGE

## `crypto_diagnostic_noedge_v1` — **NO_EDGE**

Designed as a baseline; only 5 trades and high drawdown; clearly no edge.

**Engine votes:** cerebras: NO_EDGE, deepseek: NO_EDGE, xai: NO_EDGE

## `crypto_momentum_btc_v1` — **NO_EDGE**

Metrics identical to other candidates with insufficient trade count; cannot endorse.

**Engine votes:** cerebras: NO_EDGE, deepseek: NO_EDGE, xai: NO_EDGE

## `crypto_vol_target_eth_v1` — **NO_EDGE**

PF=0.86 and MDD=61.6% with only 5 trades; fails Tier-2 floor on both performance and trade volume.

**Engine votes:** cerebras: NO_EDGE, deepseek: NO_EDGE, xai: NO_EDGE

## `crypto_pairs_btc_eth_v1` — **NO_EDGE**

Same backtest numbers (PF=2.86, n=5, MDD=37.1%); insufficient evidence of a robust strategy.

**Engine votes:** cerebras: NO_EDGE, deepseek: NO_EDGE, xai: NO_EDGE

## `crypto_regime_switch_btc_v1` — **NO_EDGE**

Only 5 trades, high drawdown; simplified SMA crossover signal not yet faithfully implemented.

**Engine votes:** cerebras: NO_EDGE, deepseek: NO_EDGE, xai: NO_EDGE

## `crypto_cross_momentum_multi_v1` — **NO_EDGE**

Backtest PF=2.86 based on 5 trades; MDD exceeds Tier-2 limit and signal translation is approximate, so no actionable edge.

**Engine votes:** cerebras: NO_EDGE, deepseek: NO_EDGE, xai: NO_EDGE
