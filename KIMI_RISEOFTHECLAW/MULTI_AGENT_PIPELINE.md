# Multi-Agent Strategy Development Pipeline

## Overview
Continuous strategy generation, variation, and testing system using parallel sub-agents.

## Pipeline Stages

### Stage 1: Strategy Generation (Continuous)
**Agents**: Multiple creative strategy brainstormers
- Generate novel strategy concepts
- Research new sources
- Find edge cases and niches

**Output**: Raw strategy ideas → Queue for Stage 2

### Stage 2: Strategy Variation (Parallel)
**Agents**: Variation generators
For each base strategy, create variations:
- Timeframe variations (1m, 5m, 15m, 1h, 4h, Daily)
- Asset-specific versions (BTC, ETH, SPY, QQQ, etc.)
- Parameter sweeps (RSI 14 vs 21 vs 30)
- Indicator substitutions (EMA vs SMA vs WMA)
- Entry/exit rule modifications

**Example**:
```
Base: RSI Mean Reversion
├── RSI_14_MeanRev
├── RSI_21_MeanRev
├── RSI_30_MeanRev
├── RSI_MeanRev_BTC
├── RSI_MeanRev_ETH
├── RSI_MeanRev_SPY
├── RSI_MeanRev_5m
├── RSI_MeanRev_1h
└── Stoch_MeanRev (indicator swap)
```

**Output**: 10-50 variations per base strategy → Queue for Stage 3

### Stage 3: Backtesting (Parallel)
**Agents**: Backtest runners
For each strategy variation:
- Run 5-year backtest (2020-2025)
- Calculate: Sharpe, Sortino, Max DD, Win Rate, Profit Factor
- Test on multiple assets
- Walk-forward analysis
- Out-of-sample validation

**Output**: Backtest results → Queue for Stage 4

### Stage 4: Filtering & Ranking
**Agents**: Strategy evaluators
Filter criteria:
- Sharpe > 1.0
- Max DD < 30%
- Win Rate > 50%
- Profit Factor > 1.5
- Consistent across assets
- Robust to parameter changes

Rank by:
- Risk-adjusted returns
- Consistency
- Robustness
- Ease of implementation

**Output**: Top 100 strategies → Queue for Stage 5

### Stage 5: Live Paper Trading
**Agents**: Live trading executors
Deploy top strategies:
- $10,000 paper capital each
- Real market data
- 15-minute updates
- Track real-time P&L

**Output**: Live performance data → Feedback to Stage 1

## Continuous Improvement Loop

```
┌─────────────────┐
│  Live Results   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│  New Research   │────▶│  Strategy Gen   │
│  (News/Papers)  │     │  (Brainstorm)   │
└─────────────────┘     └────────┬────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │  Variations     │
                        │  (10-50x)       │
                        └────────┬────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │  Backtesting    │
                        │  (5-year)       │
                        └────────┬────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │  Filtering      │
                        │  (Top 100)      │
                        └────────┬────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │  Live Trading   │
                        │  (Paper)        │
                        └─────────────────┘
```

## Agent Deployment Schedule

### Continuous Agents (Always Running)
- 2x Strategy Brainstormers
- 4x Variation Generators
- 8x Backtest Runners
- 2x Live Trading Executors

### On-Demand Agents (Triggered by Queue)
- Strategy Evaluators (when backtests complete)
- Performance Analyzers (daily)
- Research Scouts (weekly new sources)

## Target Throughput

| Stage | Input | Output | Time |
|-------|-------|--------|------|
| Generate | - | 10 strategies/day | Continuous |
| Vary | 10 base | 300 variations/day | 2 hours |
| Backtest | 300 variants | 300 results | 4 hours |
| Filter | 300 results | Top 10/day | 30 min |
| Live | 10 new | Performance data | Ongoing |

**Monthly Target**: 300 strategies → 90 top strategies → 30 live strategies

## Quality Gates

### Gate 1: Variation Worthiness
- Must have logical edge
- Must be implementable
- Must have clear rules

### Gate 2: Backtest Worthiness
- Minimum 100 trades in backtest
- Must work on multiple assets
- Must survive parameter changes

### Gate 3: Live Worthiness
- Sharpe > 1.0 in backtest
- Max DD < 30%
- Positive expectancy

### Gate 4: Production Worthiness
- 30 days live with positive returns
- Consistent performance
- Robust to market changes

## Strategy Database Schema

```json
{
  "strategy_id": "unique_id",
  "name": "Strategy Name",
  "version": "1.0",
  "parent_strategy": "parent_id or null",
  "variation_type": "timeframe|asset|parameter|indicator",
  
  "logic": {
    "entry_rules": ["rule1", "rule2"],
    "exit_rules": ["rule1", "rule2"],
    "indicators": [{"name": "RSI", "period": 14}],
    "timeframe": "1h",
    "asset_class": "crypto"
  },
  
  "risk": {
    "stop_loss": "2%",
    "take_profit": "6%",
    "position_size": "2% equity",
    "max_positions": 5
  },
  
  "backtest": {
    "period": "2020-01-01 to 2025-01-01",
    "sharpe": 1.45,
    "max_dd": 18.5,
    "win_rate": 58.3,
    "profit_factor": 1.78,
    "total_return": 245.0,
    "trades": 450
  },
  
  "live": {
    "start_date": "2026-02-16",
    "starting_value": 10000,
    "current_value": 10500,
    "return": 5.0,
    "status": "ACTIVE"
  },
  
  "source": {
    "type": "brainstorm|research|variation",
    "agent": "agent_id",
    "timestamp": "2026-02-16T09:00:00Z"
  }
}
```

## Success Metrics

- **Volume**: 500+ strategies in database
- **Quality**: 100+ strategies with Sharpe > 1.0
- **Live Performance**: Top 20 strategies beating buy-and-hold
- **Robustness**: Strategies work across multiple assets
- **Innovation**: 20% novel strategies not found in literature

## Current Status

| Pipeline Stage | Active Agents | Queue Size | Output Rate |
|----------------|---------------|------------|-------------|
| Research | 3 | - | 10/day |
| Brainstorm | 1 | 5 ideas | 10/day |
| Variation | 0 | 0 | - |
| Backtest | 0 | 0 | - |
| Live | 0 | 0 | - |

**Next Actions**:
1. Wait for current sub-agents to return
2. Process results into strategy database
3. Deploy variation generators
4. Start backtesting pipeline
5. Launch live trading with top strategies
