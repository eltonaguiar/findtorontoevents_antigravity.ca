# Synthesis (P5)

## `commodity_ts_momentum_gold_v1` — **NO_EDGE**

PF=10.68 but only 4 trades (n<30); insufficient sample size to trust edge, and signal is simplified.

**Engine votes:** cerebras: NO_EDGE, deepseek: NO_EDGE

## `commodity_cross_sectional_momentum_v1` — **NO_EDGE**

PF=10.68 with n=4 trades; trade count far below Tier-2 floor, making the backtest unreliable.

**Engine votes:** cerebras: NO_EDGE, deepseek: NO_EDGE

## `commodity_carry_value_gold_silver_v1` — **NO_EDGE**

PF=10.68 but only 4 trades; n too low for robust inference despite attractive metrics.

**Engine votes:** cerebras: NO_EDGE, deepseek: NO_EDGE

## `commodity_energy_momentum_carry_v1` — **NO_EDGE**

PF=2.25, WR=58.3% but only 12 trades; n<100 violates Tier-2 floor, so edge is not credible.

**Engine votes:** cerebras: NO_EDGE, deepseek: MIXED

## `commodity_agri_momentum_value_v1` — **NO_EDGE**

PF=2.66, WR=64.7% yet only 17 trades; insufficient history to validate performance.

**Engine votes:** cerebras: NO_EDGE, deepseek: MIXED

## `commodity_ts_momentum_v1` — **NO_EDGE**

PF=10.68 with n=4 trades; trade count far below required threshold, making the result speculative.

**Engine votes:** cerebras: NO_EDGE, deepseek: NO_EDGE

## `commodity_carry_gold_v1` — **NO_EDGE**

PF=10.68 but only 4 trades; n too low for reliable edge assessment.

**Engine votes:** cerebras: NO_EDGE, deepseek: NO_EDGE

## `commodity_value_agriculture_v1` — **NO_EDGE**

PF=2.66, WR=64.7% yet only 17 trades; fails the n≥100 requirement.

**Engine votes:** cerebras: NO_EDGE, deepseek: MIXED

## `commodity_momentum_cross_sectional_v1` — **NO_EDGE**

PF=10.68 with n=4 trades; insufficient sample size despite strong backtest numbers.

**Engine votes:** cerebras: NO_EDGE, deepseek: NO_EDGE

## `commodity_carry_momentum_combined_v1` — **NO_EDGE**

PF=10.68 but only 4 trades; n below Tier-2 floor, so edge cannot be confirmed.

**Engine votes:** cerebras: NO_EDGE, deepseek: NO_EDGE
