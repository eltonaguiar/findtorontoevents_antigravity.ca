# Synthesis (P5)

## `forex_momentum_uup_v1` — **NO_EDGE**

Backtest PF=1.61 and WR=56.7% look promising, but only 30 trades were observed and the signal is a simplified SMA crossover rather than the true momentum/volatility rule, making the result unreliable.

**Engine votes:** cerebras: NO_EDGE

## `forex_value_momentum_combo_fxA_v1` — **NO_EDGE**

PF=0.7, WR=41.7% and Sharpe negative already fail Tier-2; with just 12 trades and a placeholder SMA crossover signal, there is no credible edge.

**Engine votes:** cerebras: NO_EDGE

## `forex_regime_conditional_hybrid_fxA_v1` — **NO_EDGE**

Identical performance to the previous FXA candidate (PF=0.7, WR=41.7%, n=12) and suffers from the same simplified-signal issue, so no actionable edge.

**Engine votes:** cerebras: NO_EDGE

## `forex_dollar_carry_uup_v1` — **NO_EDGE**

PF=1.61 and WR=56.7% meet the PF/WR thresholds but only 30 trades were recorded; the entry logic is currently reduced to an SMA crossover, so the backtest is not trustworthy enough for deployment.

**Engine votes:** cerebras: NO_EDGE

## `forex_risk_parity_multi_etf_v1` — **NO_EDGE**

While PF=1.61, WR=56.7% look decent, the strategy has only 30 trades and the entry is a placeholder SMA crossover rather than the intended multi-ETF risk-parity construction, leaving the edge unverified.

**Engine votes:** cerebras: NO_EDGE
