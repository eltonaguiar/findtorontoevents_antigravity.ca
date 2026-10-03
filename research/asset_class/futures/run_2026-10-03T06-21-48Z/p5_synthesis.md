# Synthesis (P5)

## `futures_momentum_v1` — **NO_EDGE**

PF 3.5 meets the floor but WR 40% < 50%, MDD 33.5% > 20% and only 10 trades were observed; the simplified signal translation further reduces confidence.

**Engine votes:** cerebras: NO_EDGE, xai: NO_EDGE

## `futures_carry_v1` — **NO_EDGE**

PF 3.5 passes, yet WR 40% and MDD 33.5% violate Tier-2 thresholds and the backtest contains only 10 trades; signal parsing is still approximate.

**Engine votes:** cerebras: NO_EDGE, xai: NO_EDGE

## `futures_regime_switch_v1` — **NO_EDGE**

Despite PF 3.5, WR 40% and MDD 33.5% fall short, and the sample size is only 10 trades; the regime-switch logic relies on a simplified entry spec.

**Engine votes:** cerebras: NO_EDGE, xai: NO_EDGE

## `futures_vol_target_momentum_v1` — **NO_EDGE**

PF 3.5 is adequate but WR 40% and MDD 33.5% breach Tier-2 limits; only 10 trades were recorded, and the entry rule is a proxy rather than a faithful translation.

**Engine votes:** cerebras: NO_EDGE, xai: NO_EDGE

## `futures_pair_trend_v1` — **NO_EDGE**

PF 3.5 meets the floor, yet WR 40% and MDD 33.5% are outside acceptable ranges; the backtest contains just 10 trades and uses a simplified momentum proxy.

**Engine votes:** cerebras: NO_EDGE, xai: NO_EDGE

## `futures_carry_vol_dbc_v1` — **NO_EDGE**

PF 3.5 passes, but WR 40% and MDD 33.5% violate Tier-2 criteria; only 10 trades were generated and the carry signal is approximated via SMA crossovers.

**Engine votes:** cerebras: NO_EDGE, xai: NO_EDGE

## `futures_momentum_pdbc_v1` — **NO_EDGE**

PF 1.89 is below the 1.5 floor, WR 46.7% < 50%, MDD 35% > 20% and only 15 trades; the entry logic is a simplified momentum filter.

**Engine votes:** cerebras: NO_EDGE, xai: NO_EDGE

## `futures_regime_dba_v1` — **NO_EDGE**

PF 2.66 meets the PF threshold, but WR 64.7% is acceptable while MDD 15.9% is below 20%; however, the trade count is only 17 (<100) and the regime filter uses a coarse ISM PMI proxy, so evidence is insufficient.

**Engine votes:** cerebras: NO_EDGE, xai: NO_EDGE

## `futures_vol_target_uso_v1` — **NO_EDGE**

PF 1.67 meets PF floor, yet WR 14.3% is far below 50% and MDD 54.8% exceeds 20%; only 7 trades were observed, and the signal is a simplified momentum proxy.

**Engine votes:** cerebras: NO_EDGE, xai: NO_EDGE

## `futures_diagnostic_noedge_gsg_v1` — **NO_EDGE**

PF 2.22 passes, but WR 66.7% is acceptable while MDD 37.4% > 20% and trade count is 15; the entry rule is a simplified momentum/volatility filter, so no reliable edge is demonstrated.

**Engine votes:** cerebras: NO_EDGE, xai: NO_EDGE
