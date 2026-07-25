# Synthesis (P5)

## `equity_ts_momentum_v1` — **MIXED**

Backtest shows very high PF (55.79) and 100% win rate, but only 4 trades over the 5-year window, far below the 100-trade minimum, making the result statistically unreliable. The signal is a simplified SMA crossover, not the true spec, so longer history and faithful signal parsing are needed.

**Engine votes:** cerebras: MIXED

## `equity_vol_target_v1` — **MIXED**

Identical performance to the momentum ETF (PF 55.79, WR 100%) yet only 4 trades, which is insufficient for robust inference. Simplified signal translation further limits confidence; more data required before deployment.

**Engine votes:** cerebras: MIXED

## `equity_carry_pair_v1` — **MIXED**

Meets PF (5.24), WR (66.7%) and MDD (19.3%) thresholds, but the backtest contains only 6 trades, well under the 100-trade floor. The simplified SMA-crossover proxy may misrepresent the intended carry-based entry, so a longer history and faithful signal are needed.

**Engine votes:** cerebras: MIXED

## `equity_hmm_momentum_v1` — **NO_EDGE**

While PF (100.64) and WR (100%) are impressive, MDD (22.8%) exceeds the 20% limit and the strategy executed only 3 trades, far below the required sample size. Combined with the simplified signal, there is no reliable edge to endorse.

**Engine votes:** cerebras: NO_EDGE

## `equity_bab_pair_v1` — **MIXED**

PF (5.24), WR (66.7%) and MDD (19.3%) satisfy Tier-2 thresholds, but the backtest comprises only 6 trades, insufficient for statistical confidence. The entry logic is currently approximated by an SMA crossover, so longer data and accurate signal parsing are needed.

**Engine votes:** cerebras: MIXED
