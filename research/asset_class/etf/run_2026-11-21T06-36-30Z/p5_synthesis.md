# Synthesis (P5)

## `etf_carry_yield_v1` — **MIXED**

Backtest shows PF=77.12, WR=80%, MDD=17% - attractive but only 5 trades (n=5) far below the 100-trade floor; cross-test independence is good but the entry signal is simplified, so more data and a faithful-signal translation are needed.

**Engine votes:** cerebras: MIXED

## `etf_spread_arbitrage_v1` — **MIXED**

PF=1.97, WR=61.5%, MDD=19.7% meets the floor on PF/WR/MDD but only 13 trades; still below the 100-trade requirement and uses a simplified SMA crossover proxy, so edge is uncertain pending longer history.

**Engine votes:** cerebras: MIXED

## `etf_cross_asset_momentum_v1` — **MIXED**

Identical backtest stats to the carry-yield model (PF=77.12, WR=80%, MDD=17%, n=5) - promising performance but trade count is too low and signal translation is approximate, requiring more observations.

**Engine votes:** cerebras: MIXED

## `etf_value_momentum_combo_v1` — **MIXED**

Same backtest results (PF=77.12, WR=80%, MDD=17%, n=5) as other momentum variants; insufficient trade frequency and simplified entry logic prevent a confident GO decision.

**Engine votes:** cerebras: MIXED

## `etf_diagnostic_momentum_v1` — **MIXED**

Backtest shows PF=77.12, WR=80%, MDD=17% but only 5 trades; the strategy's simplistic rule and lack of a faithful signal parser mean more data is required before production.

**Engine votes:** cerebras: MIXED
