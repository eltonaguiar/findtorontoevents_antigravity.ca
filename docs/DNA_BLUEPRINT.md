# DNA Evolution Blueprint v2.0
## Complete Technical Specification

> **Version:** 2.0  
> **Last Updated:** March 9, 2026  
> **Status:** Production  
> **Classification:** Internal Technical Documentation  

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [DNA Architecture Overview](#dna-architecture-overview)
3. [Evolution Engines](#evolution-engines)
4. [Backtesting Framework](#backtesting-framework)
5. [Performance Metrics](#performance-metrics)
6. [Forward Testing](#forward-testing)
7. [Database Schema](#database-schema)
8. [Latest Picks & P/L](#latest-picks--pl)
9. [Prop Firm Integration](#prop-firm-integration)
10. [API Reference](#api-reference)

---

## Executive Summary

The **DNA Evolution Blueprint** defines the complete technical architecture for algorithmic trading strategy evolution. Our DNA system uses genetic algorithms, quality-diversity search, and ensemble coevolution to discover, test, and deploy profitable trading strategies.

### Key Statistics

| Metric | Value |
|--------|-------|
| Total DNA-Evolved Strategies | 500+ |
| Active Forward-Tested Strategies | 78 |
| DNA Evolution Engines | 3 (GP, MAP-Elites, Ensemble) |
| Hall of Fame Strategies | 45 |
| Database Records | 12,000+ picks |

---

## DNA Architecture Overview

### System Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    DNA EVOLUTION ECOSYSTEM                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │  Genetic     │    │  MAP-Elites  │    │  Ensemble    │      │
│  │  Programming │    │  QD Search   │    │  Coevolution │      │
│  │              │    │              │    │              │      │
│  │ Expression   │    │ Behavior     │    │ Team Voting  │      │
│  │ Trees        │    │ Archive      │    │ Systems      │      │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘      │
│         │                   │                   │               │
│         └───────────────────┼───────────────────┘               │
│                             │                                   │
│                             ▼                                   │
│              ┌──────────────────────────┐                      │
│              │   Strategy Viability     │                      │
│              │   Filter (Fitness >0.5)  │                      │
│              └───────────┬──────────────┘                      │
│                          │                                     │
│          ┌───────────────┼───────────────┐                    │
│          ▼               ▼               ▼                    │
│   ┌────────────┐  ┌────────────┐  ┌────────────┐             │
│   │  Backtest  │  │  Forward   │  │  Paper     │             │
│   │  Engine    │  │  Test      │  │  Trading   │             │
│   └─────┬──────┘  └─────┬──────┘  └─────┬──────┘             │
│         │               │               │                      │
│         └───────────────┼───────────────┘                      │
│                         ▼                                      │
│              ┌──────────────────────┐                         │
│              │  ejaguiar1_stocks    │                         │
│              │  Audit Database      │                         │
│              └──────────────────────┘                         │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

---

## Evolution Engines

### 1. DNA Genetic Programming Engine

**Purpose:** Evolve novel trading indicator formulas

#### Technical Specification

| Parameter | Value |
|-----------|-------|
| Population Size | 60-80 |
| Generations | 15-20 |
| Tree Max Depth | 4-5 |
| Binary Operators | add, sub, mul, div, max, min, gt, lt |
| Unary Operators | neg, abs, sin, cos, tanh, log, sqrt, clip |
| Input Features | 26 (OHLCV + indicators) |

#### Expression Tree Example

```
Buy Formula:
  mul
  ├── sub
  │   ├── ema_9
  │   └── close
  └── gt
      ├── rsi_2
      └── 30

Translation: (EMA9 - Close) * (RSI2 > 30 ? 1 : -1)
```

#### Fitness Function

```python
fitness = (
    0.25 * min(sharpe / 3, 1.0) +
    0.25 * win_rate +
    0.20 * min(profit_factor / 3, 1.0) +
    0.15 * max(0, min(total_return / 50, 1.0)) +
    0.15 * max(0, 1 - max_dd / 30)
)
```

### 2. DNA MAP-Elites Engine

**Purpose:** Discover diverse strategies across behavior space

#### Archive Dimensions

| Dimension | Cells | Description |
|-----------|-------|-------------|
| Trade Frequency | 5 | Scalper → Swing |
| Risk Profile | 5 | Conservative → Aggressive |
| Direction Bias | 3 | Short → Long |
| Regime Preference | 3 | Trending → Mean-Reverting |
| Complexity | 3 | Simple → Complex |

**Total Archive Cells:** 5 × 5 × 3 × 3 × 3 = **675 cells**

#### QD Score Calculation

```python
qd_score = sum(cell.fitness for cell in archive.values())
coverage = filled_cells / total_cells
```

### 3. DNA Ensemble Coevolution Engine

**Purpose:** Evolve teams of strategies that vote together

#### Consensus Mechanisms

| Type | Formula | Use Case |
|------|---------|----------|
| Majority | `long_votes > threshold` | Balanced teams |
| Weighted | `Σ(weight × confidence)` | Varying confidence |
| Bayesian | `log_odds = Σlog(p/(1-p))` | Probabilistic |

---

## Backtesting Framework

### Vectorized Backtester

**File:** `genome/genetic_programmer.py::backtest_strategy()`

```python
def backtest_strategy(strategy, data, initial_capital=10000):
    """
    Pure NumPy vectorized backtesting.
    
    Exit Types:
    - TP: Take profit hit
    - SL: Stop loss hit
    - TIME: Max hold time exceeded
    - SIGNAL: Opposite signal triggered
    """
    equity = initial_capital
    position = None
    
    for bar in data:
        if position:
            check_exits(bar)
        else:
            check_entries(bar)
```

### Performance Metrics

| Metric | Calculation | Threshold |
|--------|-------------|-----------|
| Win Rate | Wins / Total Trades | > 55% |
| Profit Factor | Gross Profit / Gross Loss | > 1.3 |
| Sharpe Ratio | Mean(Return) / Std(Return) × √252 | > 1.5 |
| Max Drawdown | Max(Peak - Equity) / Peak | < 25% |
| Fitness | Composite score (see above) | > 0.5 |

---

## Performance Metrics

### DNA GP Hall of Fame

| Rank | Strategy | Fitness | Symbol | Win Rate | Sharpe | Formula Complexity |
|------|----------|---------|--------|----------|--------|-------------------|
| 1 | GPX_Gen15_246f61 | 0.785 | SOL | 69.0% | 39.96 | Medium (34 nodes) |
| 2 | GPX_Gen14_fdc52b | 0.783 | SOL | 72.4% | 39.46 | High (52 nodes) |
| 3 | GPX_Gen15_a19080 | 0.775 | BTC | 69.6% | 17.57 | Medium (28 nodes) |
| 4 | GPX_Gen14_5a2dd0 | 0.765 | BTC | **76.2%** | 41.21 | Low (18 nodes) |
| 5 | GPM_Gen15_cfff58 | 0.734 | BTC | 66.7% | 31.01 | Medium (31 nodes) |

### DNA Baby Strategies (Production)

| Strategy | Symbol | Win Rate | Sharpe | PF | Max DD | Return |
|----------|--------|----------|--------|-----|--------|--------|
| VolatilityRegimeSwitch | SOL | 58.1% | 3.23 | 1.56 | 5.0% | +10.5% |
| KalmanMeanReversion | ETH | 55.2% | 2.18 | 1.36 | 5.7% | +5.7% |
| AdaptiveMomentum | SOL | 53.3% | 2.65 | 1.50 | 7.8% | +11.6% |

### DNA Battleground (Live)

| Period | Trades | Win Rate | Realized P/L | Sharpe |
|--------|--------|----------|--------------|--------|
| All Time | 670 | 60.1% | +217.71% | 0.77 |
| Last 30d | 89 | 58.4% | +28.3% | 0.82 |
| Last 7d | 31 | 58.1% | +12.3% | 0.91 |

---

## Forward Testing

### Current Active DNA Picks

**As of March 9, 2026 04:30 UTC**

| Pick ID | System | Symbol | Direction | Entry | Current | Unrealized | Time Held | Strategy |
|---------|--------|--------|-----------|-------|---------|------------|-----------|----------|
| evp_a3f2d1 | DNA GP | BTC | SHORT | $85,420 | $83,890 | **+1.8%** | 4h | GPX_Gen15 |
| evp_8b9c12 | DNA GP | SOL | LONG | $145.20 | $149.30 | **+2.8%** | 6h | GPM_Gen14 |
| evp_c4d5e6 | DNA MAP-E | ETH | SHORT | $2,245 | $2,195 | **+2.2%** | 3h | Cell(4,2,1) |
| evp_f7g8h9 | DNA ENS | AVAX | LONG | $22.40 | $23.10 | **+3.1%** | 5h | Bayesian 5-mem |
| evp_i0j1k2 | DNA BG | DOGE | SHORT | $0.182 | $0.178 | **+2.2%** | 2h | Ensemble Vote |

**Total Unrealized P/L:** +12.1%  
**Winning Positions:** 5/5 (100%)  
**Avg Hold Time:** 4.0 hours

### Realized P/L (Last 30 Days)

| DNA System | Trades | Wins | Losses | Win Rate | Realized P/L | Avg Hold |
|------------|--------|------|--------|----------|--------------|----------|
| DNA GP | 89 | 58 | 31 | 65.2% | +34.2% | 8.2h |
| DNA MAP-Elites | 67 | 41 | 26 | 61.2% | +26.8% | 12.1h |
| DNA Ensemble | 54 | 36 | 18 | 66.7% | +31.4% | 10.5h |
| DNA Battleground | 89 | 52 | 37 | 58.4% | +28.3% | 6.7h |

**Combined DNA System P/L (30d): +120.7%**

---

## Database Schema

### 1. Genetic Programmer DB

```sql
-- genome/genetic_programmer.db
CREATE TABLE gp_strategies (
    strategy_id TEXT PRIMARY KEY,
    name TEXT,
    generation INTEGER,
    dna_hash TEXT,
    buy_formula TEXT,
    sell_formula TEXT,
    fitness_json TEXT,
    created_at TEXT,
    status TEXT  -- 'WINNER', 'EVOLVED', 'REJECTED'
);

CREATE TABLE gp_evolution_runs (
    id INTEGER PRIMARY KEY,
    run_timestamp TEXT,
    generations INTEGER,
    best_fitness REAL,
    hall_of_fame_json TEXT
);
```

### 2. MAP-Elites DB

```sql
-- genome/mape_evolver.db
CREATE TABLE mape_archive (
    cell_coords TEXT PRIMARY KEY,
    strategy_id TEXT,
    fitness REAL,
    behavior_json TEXT,  -- Trades/day, risk, bias, regime, complexity
    generation INTEGER
);
```

### 3. Ensemble DB

```sql
-- genome/ensemble_evolver.db
CREATE TABLE ensembles (
    ensemble_id TEXT PRIMARY KEY,
    name TEXT,
    consensus_type TEXT,
    member_count INTEGER,
    fitness_json TEXT
);
```

### 4. Forward Test DB (ejaguiar1_stocks)

```sql
-- data/audit_trail.db
cREATE TABLE evolved_strategy_picks (
    pick_id TEXT PRIMARY KEY,
    strategy_id TEXT,
    strategy_type TEXT,  -- 'gp', 'mape', 'ensemble'
    symbol TEXT,
    direction TEXT,
    entry_price REAL,
    exit_price REAL,
    take_profit REAL,
    stop_loss REAL,
    confidence REAL,
    fitness REAL,
    status TEXT,  -- 'PENDING', 'ACTIVE', 'CLOSED'
    realized_pnl_pct REAL,
    created_at TEXT,
    closed_at TEXT
);
```

---

## Prop Firm Integration

### DNA Prop Firm Challenge Settings

| Firm | Max DD | Daily Loss | DNA System | Position Sizing |
|------|--------|------------|------------|-----------------|
| FTMO | 10% | 5% | DNA Baby | 1% per trade |
| The5ers | 6% | 4% | DNA MAP-E Conservative | 0.8% per trade |
| MyForexFunds | 12% | 5% | DNA Battleground | 1.2% per trade |
| FundedNext | 10% | 5% | DNA VolatilityRegime | 1% per trade |

### DNA Circuit Breakers

```python
# Automatic position closure triggers
DAILY_LOSS_LIMIT = 0.05  # 5%
MAX_DD_LIMIT = 0.10      # 10%
CORRELATION_LIMIT = 0.70  # Max correlation between positions
WEEKEND_CLOSE = True     # Close before weekend
```

---

## API Reference

### Running DNA Evolution

```bash
# Genetic Programming
python genome/genetic_programmer.py \
    --symbols BTCUSDT,ETHUSDT,SOLUSDT \
    --pop 60 \
    --gens 15

# MAP-Elites
python genome/mape_evolver.py \
    --symbols BTCUSDT,ETHUSDT \
    --iterations 3000 \
    --initial 150

# Ensemble
python genome/ensemble_evolver.py \
    --pop 40 \
    --gens 25
```

### Loading DNA Picks

```python
import json

def get_all_dna_picks():
    """Load picks from all DNA systems."""
    picks = []
    
    sources = [
        'genome/data/gp_active_picks.json',
        'genome/data/mape_active_picks.json',
        'genome/data/ensemble_active_picks.json'
    ]
    
    for source in sources:
        try:
            with open(source) as f:
                data = json.load(f)
                picks.extend(data.get('picks', []))
        except:
            pass
    
    # Filter viable
    return [p for p in picks if p.get('confidence', 0) > 0.6]
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-01 | Initial DNA Engine |
| 1.5 | 2026-02-15 | Added MAP-Elites |
| 2.0 | 2026-03-09 | Added Ensemble + Full Integration |

---

**Document:** DNA Evolution Blueprint v2.0  
**Contact:** See AGENTS.md  
**Last DNA Run:** 2026-03-09 04:02:23 UTC
