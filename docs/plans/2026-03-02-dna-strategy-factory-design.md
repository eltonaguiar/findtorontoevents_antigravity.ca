# DNA Strategy Factory + Progressive Promotion Pipeline

**Date**: 2026-03-02
**Status**: Approved

## Problem

- 627 baby/incubator strategies exist but most have zero forward-test data
- DNA combiner ran 623 permutations, all stuck on probation (3-6 trades each)
- Proven winners (RSI-2, Keltner, Carter Squeeze) aren't systematically tested across all crypto pairs/timeframes
- No progressive promotion pipeline from paper-tracking to Discord master picks

## Solution

Three parallel workstreams:

### Part A: Combo DNA Bundles (8 new strategies)

Combine statistically proven signals using the DNA engine's combination logic:

| # | Name | Components | Logic | Hypothesis |
|---|------|-----------|-------|-----------|
| 1 | RSI2_FearGreed_Confluence | Connors RSI-2 + F&G ≤20 | AND | Buy only when mean-reversion AND macro fear align |
| 2 | Keltner_RSI2_DoubleBottom | Keltner MR + RSI-2 | SEQUENTIAL | Keltner triggers, RSI-2 confirms oversold |
| 3 | Carter_Keltner_VolSqueeze | TTM Squeeze + Keltner MR | WEIGHTED | Vol compression→expansion with MR filter |
| 4 | Levine_Momentum_FG | Levine Adaptive + F&G contrarian | MAJORITY | Adaptive momentum + macro sentiment |
| 5 | ConsecDown_Bollinger_Trap | Consecutive Down RSI + Bollinger MR | AND | 3+ red candles + BB touch |
| 6 | BTCDom_RSI2_Rotation | BTC Dominance + RSI-2 | SEQUENTIAL | Macro rotation timing + precise entry |
| 7 | TripleMR_Confluence | RSI-2 + Keltner + Bollinger | CONSENSUS_75 | 3 MR signals, 75% must agree |
| 8 | FearGreed_Carter_Breakout | F&G extreme + TTM Squeeze | SEQUENTIAL | Buy fear + wait for squeeze breakout |

### Part B: Asset-Timeframe Expansion Matrix

Top 8 proven strategies × 7 pairs × 3 timeframes = up to 168 cells:

- **Pairs**: BTCUSDT, ETHUSDT, SOLUSDT, AVAXUSDT, DOGEUSDT, LINKUSDT, ATOMUSDT
- **Timeframes**: 1h, 4h, 1d
- **Strategies**: connors_rsi2, keltner_mean_reversion, carter_squeeze_breakout, levine_adaptive_lookback, consecutive_down_rsi, bollinger_mean_reversion, rsi2_bb_squeeze, fear_greed_contrarian

Each cell gets registered as a separate StrategyDNA with `symbol_specialization` and timeframe gene set.

### Part C: Progressive Promotion Pipeline

```
INCUBATOR → SANDBOX → FRESH_PICKS → DNA_MASTER
```

| Tier | Criteria | Discord Channel | Auto-Demote If |
|------|----------|-----------------|----------------|
| INCUBATOR | New strategy, < 10 trades | (none, silent tracking) | — |
| SANDBOX | 10+ forward trades | #sandbox | WR drops < 40% over 20 trades |
| FRESH_PICKS | 20+ trades, WR ≥ 50%, Sharpe ≥ 0.5 | #fresh-picks | WR < 45% or Sharpe < 0.3 rolling |
| DNA_MASTER | 30+ trades, WR ≥ 55%, Sharpe ≥ 1.5 | #dna-master-picks | WR < 50% or Sharpe < 1.0 rolling |

Promotions and demotions trigger Discord notifications.

## Files

| File | Action | Purpose |
|------|--------|---------|
| `genome/dna_strategy_factory.py` | NEW | Creates combo bundles + expansion matrix, registers into pipeline |
| `genome/progressive_promotion.py` | NEW | Tier promotion/demotion engine with Discord hooks |
| `cross_aggregation/dna_master_tracker.py` | UPDATE | Add tier field + promotion check integration |
| `cross_aggregation/discord_notify.py` | UPDATE | Add tier-specific routing (sandbox/fresh/master) |
| `.github/workflows/dna_strategy_pipeline.yml` | UPDATE | Run factory on schedule + promotion checks |

## Data Flow

```
dna_strategy_factory.py
  ├─ Creates 8 combo StrategyDNA objects (Part A)
  ├─ Creates 168 expansion StrategyDNA objects (Part B)
  └─ Registers all in battleground/data/bundle_babies.db

dna_strategy_pipeline.yml (every 4 hours)
  ├─ Runs genome/evolve_strategies.py (existing)
  ├─ Runs genome/generate_picks.py (existing)
  ├─ Runs genome/dna_strategy_factory.py --check-signals (new)
  │   └─ For each registered strategy: check if signal fires on latest data
  │       └─ If fires: record trade in bundle_trades table
  └─ Runs genome/progressive_promotion.py --evaluate (new)
      └─ For each strategy: count forward trades, calculate metrics
          ├─ Promote if criteria met → Discord notification
          └─ Demote if criteria breached → Discord warning
```

## Key Design Decisions

1. **Each asset-timeframe cell is a separate StrategyDNA** — not one strategy tested on many pairs. This lets the promotion pipeline track "RSI-2 on BTC 1H" independently from "RSI-2 on ETH 4H".

2. **Combo strategies use the existing CombinationLogic enum** — no new logic types needed, just new combinations of proven parents.

3. **Progressive tiers use a rolling window** — not lifetime stats. A strategy that was great but decayed gets demoted. A strategy that started slow but improved gets promoted.

4. **Factory is idempotent** — running it twice doesn't create duplicates. It checks by strategy_id hash before inserting.
