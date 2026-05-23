# Mutation Lab — Hourly Strategy Evolution Pipeline

## Date: 2026-03-09
## Status: Approved

## Overview
Hourly pipeline that identifies top-performing and worst-losing strategies, generates 50 mutations across 5 strategies, backtests extensively, and promotes winners into the audit dashboard as live picks.

## Architecture: Multi-Stage Pipeline

```
Stage 1: SCOUT (2 min)
  → Query audit DB + JSON sources for top-15 winners & bottom-15 losers
  → Fetch current Binance prices for live pick generation
  → Output: mutation_targets.json

Stage 2: MUTATE + BACKTEST (parallel, 8-12 min)
  → Job A: Winner Amplification (20% — 10 mutations)
  → Job B: Loser Inversion + Pure Flip (30% — 15 mutations)
  → Job C: Loser Fix + Crossbreed (40% — 20 mutations) + Live Picks (10% — 5 mutations)
  → Each backtests on BTC/ETH/SOL × 750 bars

Stage 3: PROMOTE (2 min)
  → Merge results, apply quality gates
  → Generate live picks from winning mutations against current market data
  → Register in strategy_registry.db
  → Write genome/data/mutation_lab_picks.json
  → Git commit + push → dashboard auto-ingests
```

## 5 Mutation Strategies

| # | Strategy | Budget | Source | Technique |
|---|----------|--------|--------|-----------|
| C1 | Loser Fix | 30% (15) | Bottom 15 losers | Perturb params ±20-40%, keep direction |
| C2 | Loser Invert | 20% (10) | Bottom 15 losers | Flip BUY↔SELL, swap TP/SL logic |
| A | Winner Amplify | 20% (10) | Top 15 winners | Small perturbations ±10-15%, tighten risk |
| B | Pure Flip | 10% (5) | Bottom 5 worst (WR<30%) | Direct signal inversion, no param changes |
| X | Crossbreed | 10% (5) | 1 winner + 1 loser | Winner entry + loser inverted exit |

## Live Picks Analysis (Stage 3 addition)
After backtesting, winning mutations are run against **current market data** to generate actionable live picks:
1. Fetch latest 300 bars from Binance for each symbol
2. Run each promoted mutation's signal logic on current data
3. If signal fires → generate live pick with entry_price = current price, TP/SL from ATR
4. Enrich with live Binance price for unrealized PnL tracking
5. Include backtest stats (WR, Sharpe, PF) for dashboard scoring

## Quality Gates

### Pre-filter (before backtest)
- TP > SL (reward > risk)
- TP/SL ratio >= 1.2
- No degenerate genes (RSI period > 0, MA length > 1)
- DNA hash not duplicate of existing strategy

### Post-backtest (for promotion)
- win_rate >= 50%
- sharpe_ratio >= 1.0
- profit_factor >= 1.2
- num_trades >= 30
- max_drawdown <= 15%
- avg_trade > 0 (positive expectancy)
- Profitable on >= 2 of 3 symbols

## Backtest Configuration
- Data: Real Binance klines (750 bars, 1h)
- Symbols: BTCUSDT, ETHUSDT, SOLUSDT
- Capital: $10,000 per mutation
- Position: 10% of equity per trade
- Commission: 0.1% per side
- Slippage: 0.05% per side
- Max hold: 15 bars

## Output Format (mutation_lab_picks.json)
```json
{
  "system": "mutation_lab",
  "generated_at": "2026-03-09T20:00:00Z",
  "total_picks": 8,
  "mutation_stats": {
    "total_mutations": 50,
    "passed_prefilter": 42,
    "passed_backtest": 12,
    "promoted": 8,
    "live_signals": 5
  },
  "picks": [{
    "symbol": "BTCUSDT",
    "direction": "LONG",
    "entry_price": 67250.00,
    "take_profit": 68500.00,
    "stop_loss": 66800.00,
    "confidence": 0.72,
    "strategy": "C1_fix_macd_divergence_v3",
    "source_system": "mutation_lab",
    "trust_tier": "SANDBOX",
    "mutation_type": "loser_fix",
    "parent_strategy": "macd_divergence_hunter",
    "win_rate": 0.58,
    "sharpe_ratio": 1.84,
    "profit_factor": 1.45,
    "total_trades": 42,
    "max_drawdown_pct": 8.2,
    "tp_pct": 0.045,
    "sl_pct": 0.025,
    "timestamp": "2026-03-09T20:00:00Z"
  }]
}
```

## Files
| File | Purpose |
|------|---------|
| genome/mutation_lab/__init__.py | Package |
| genome/mutation_lab/scout.py | Stage 1: target identification |
| genome/mutation_lab/backtester.py | Shared backtest engine |
| genome/mutation_lab/mutator_amplify.py | Strategy A: winner amplification |
| genome/mutation_lab/mutator_invert.py | Strategy B+C2: flip + inversion |
| genome/mutation_lab/mutator_hybrid.py | Strategy C1+X: fix + crossbreed |
| genome/mutation_lab/promoter.py | Stage 3: quality gates + live picks |
| genome/mutation_lab/db_wrapper.py | Thin DB abstraction |
| genome/mutation_lab/schemas.py | JSON validation |
| .github/workflows/mutation-lab.yml | Hourly workflow |
| tests/mutation_lab/ | Unit tests |

## Dashboard Integration
- Dashboard generator already scans genome/data/*.json
- Add entry to JSON_PICK_SOURCES in audit_trail/dashboard_generator.py
- All picks start as SANDBOX tier (0.25x weight)
- Promotion to PROVEN after 50+ forward trades with WR>55%

## Risk Mitigations
- Matrix parallelism prevents timeout
- JSON schema validation between stages
- DB wrapper insulates from schema changes
- Pre-filter reduces wasted backtest compute
- Artifact gzip keeps payloads small
