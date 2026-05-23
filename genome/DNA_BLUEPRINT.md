# DNA EVOLUTION BLUEPRINT
## DARWIN ENGINE — Evolutionary Trading Intelligence

> A comprehensive DNA evolution system that breeds, mutates, and evolves trading strategies
> using genetic programming, quality-diversity search, ensemble coevolution, and meta-weight optimization.

---

## System Overview

The DARWIN ENGINE is a multi-engine DNA evolution platform that automatically generates,
backtests, and deploys trading strategies. Unlike traditional trading systems that rely on
human-designed indicators, DARWIN uses biological evolution principles to discover strategies
that no human would conceive.

### Evolution Engines

| Engine | Codename | What Evolves | DNA Representation |
|--------|----------|-------------|-------------------|
| Genetic Programming | **GENESIS** | Indicator formulas (expression trees) | GPNode trees with arithmetic/trig/comparison operators |
| MAP-Elites | **ATLAS** | Diverse strategy niches | Same as GP but archived across 5D behavior space |
| Audit Ensemble | **NEXUS** | Trust weights across 40+ systems | Float vector (softmax-normalized) |
| Ensemble Coevolution | **LEGION** | Voting teams of strategies | Team composition + weights + consensus rules |
| Classic DNA Engine | **HELIX** | Strategy parameters + combinations | StrategyDNA dataclass with CombinationLogic |

---

## Engine Deep Dives

### 1. GENESIS — Genetic Programming DNA Evolution

**File:** `genome/genetic_programmer.py` (978 lines)
**Output:** `genome/data/gp_active_picks.json`

#### DNA Structure
Each strategy's DNA is an **expression tree** with nodes:
- **Binary operators:** add, sub, mul, div, max, min, gt, lt
- **Unary operators:** neg, abs, sin, cos, tanh, log, sqrt, clip
- **Input features (26):** OHLCV + RSI(2,14) + EMA(9,21,50) + BB(20,2) + MACD + ATR + OBV + VWAP
- **Constants:** Random floats [-5, 5]

#### Evolution Process
```
Generation 0: 60 random expression trees
   |
   v Tournament Selection (k=5)
   v Crossover: Swap random subtrees between parents (70%)
   v Mutation: Replace random subtree with new random tree (15%)
   v Elitism: Top 10% carry forward unchanged
   |
Generation 15: Evolved strategies with novel indicators
```

#### Adaptive Mutation
When evolution stagnates (>3 generations without improvement):
- Mutation rate increases from 0.15 to 0.40
- Encourages exploration of new formula spaces
- Resets when improvement found

#### Hall of Fame Seeding
Previous evolution winners are stored in SQLite and seed future populations.
This creates cumulative improvement across runs.

#### Backtesting Performance (All-Time Best)

> **Note:** These are BACKTEST results (tested against historical price data). Forward-testing
> (live paper trading) is tracked separately and typically shows some decay vs backtest — this is
> normal. Forward results are the true measure of strategy quality.

| Strategy | Symbol | Win Rate | Sharpe | Performance Score | Notes |
|----------|--------|----------|--------|---------|-------|
| GPX_Gen15_246f61 | SOLUSDT | 69.0% | 39.96 | 0.785 | Run 1 champion |
| GPX_Gen14_fdc52b | SOLUSDT | 72.4% | 39.46 | 0.783 | High WR |
| GPX_Gen14_5a2dd0 | BTCUSDT | **76.2%** | 41.21 | 0.765 | Best single-symbol WR |
| GPM_Gen15_cfff58 | BTCUSDT | 66.7% | 31.01 | 0.734 | 5-symbol robust |

---

### 2. ATLAS — MAP-Elites Quality-Diversity DNA Evolution

**File:** `genome/mape_evolver.py` (617 lines)
**Output:** `genome/data/mape_active_picks.json`

#### Why Quality-Diversity?
Standard evolution converges to ONE optimal strategy. But markets are diverse — what works
in trending markets fails in ranging markets. ATLAS maintains an **archive** of the best
strategy for each behavioral niche.

#### 5D Behavioral Grid (675 cells)

| Dimension | Low (0) | High (1) | Grid Size |
|-----------|---------|----------|-----------|
| Trade Frequency | Swing (<0.5/day) | Scalper (>5/day) | 5 |
| Risk Profile | Conservative | Aggressive | 5 |
| Direction Bias | Short-biased | Long-biased | 3 |
| Regime Preference | Trending | Mean-reverting | 3 |
| Complexity | Simple (<20 nodes) | Complex (>40 nodes) | 3 |

**Total cells:** 5 x 5 x 3 x 3 x 3 = **675 unique niches**

#### Key Metrics
- **Coverage %:** How much of the behavior space has been explored
- **QD Score:** Sum of all fitnesses across archive (quality + diversity)
- **Max Fitness:** Best single strategy found

#### First Run Results (2026-03-09)
- Archive Coverage: 5.2% (35 cells filled of 675)
- QD Score: 0.467
- Best Fitness: 0.745
- Diversity: 15 trend-following, 18 mean-reversion, 2 hybrid

---

### 3. NEXUS — Audit Ensemble Meta-Weight DNA Evolution

**File:** `genome/audit_ensemble_evolver.py` (335 lines)
**Output:** `genome/data/ae_active_picks.json`

#### Unique Approach
Instead of evolving strategies, NEXUS evolves **how much to trust each existing system**.
The genome is a weight vector across 40+ audit sources, softmax-normalized.

#### DNA Structure
```
Genome: [w1, w2, w3, ..., w40]  (logit space)
   |
   v Softmax normalization
   |
Weights: [0.05, 0.12, 0.03, ..., 0.01]  (sum = 1.0)
```

#### Fitness Components
1. **Weighted signal strength** — per-symbol ensemble consensus
2. **Diversity reward** — penalizes over-concentration on few sources
3. **Entropy bonus** — encourages broad weight distribution

#### Sources Aggregated
40+ systems including: alpha_engine, battleground, mercury2, ml_battleground (6 sub-systems),
breakout_arena (3 approaches), crypto_signal_engine, coinglass, rl_agent, genome, predictions,
regime_terminal, riseoftheclaw, quan_engine, and more.

#### First Run Results (2026-03-09)
- Best Fitness: 4.95
- 4 consensus picks generated (BTC, ETH, DOGE, SOL — all LONG)
- Top weighted sources: quan_engine, genome, genetic_programmer

---

### 4. LEGION — Ensemble Coevolution DNA Evolution

**File:** `genome/ensemble_evolver.py` (833 lines)
**Output:** `genome/data/ensemble_active_picks.json`

#### Team-Level DNA Evolution
Instead of evolving one strategy, LEGION evolves **teams** of 3-8 strategies that vote together.
A mediocre strategy might be valuable if it provides unique perspective.

#### What the DNA Encodes
| Gene | Description |
|------|-------------|
| Member Selection | Which strategies are in the team |
| Voting Weights | How much influence each member has |
| Consensus Type | majority, weighted, unanimous, cascade, bayesian |
| Veto Powers | Can certain members block decisions |
| Participation Threshold | Min % that must vote |

#### Consensus Mechanisms
- **Majority:** Simple weighted vote
- **Weighted:** Confidence x weight voting
- **Unanimous:** All must agree (high-confidence only)
- **Cascade:** Primary voters decide, secondary confirm
- **Bayesian:** Log-odds belief combination

#### First Run Results (2026-03-09)
- Top ensemble: weighted consensus, 4 members, fitness 0.507
- Key members: GP_Gen1_cd5490 (weight 1.93), GPBonus_MomentumZScore (weight 1.56)

---

### 5. HELIX — Classic DNA Engine (Original)

**File:** `genome/dna_engine.py` (1074 lines)
**Output:** Various via `genome/picks_generator.py`

#### Legacy DNA System
The original evolution engine that optimizes strategy parameters (not formulas).

| Component | Description |
|-----------|-------------|
| StrategyDNA | Dataclass with entry/exit/risk genes |
| CombinationLogic | AND, OR, MAJORITY, WEIGHTED, SEQUENTIAL, UNANIMOUS, CONSENSUS_75 |
| MarketRegime | BULL, BEAR, SIDEWAYS, HIGH_VOL detection |
| IslandModel | Parallel populations with migration |

#### Key Differences from New Engines

| Feature | HELIX (Classic) | GENESIS (GP) | ATLAS (MAP-E) | LEGION (Ensemble) |
|---------|----------------|--------------|---------------|-------------------|
| DNA type | Parameters | Expression trees | Expression trees | Team composition |
| Evolution | Parameter tuning | Formula invention | Niche filling | Team building |
| Output | 1 optimal config | Novel indicators | Diverse archive | Voting teams |
| Diversity | Single optimum | Limited | Guaranteed | Moderate |

---

## Paper Trading Portfolios

Each DNA evolution engine has a dedicated paper trading portfolio starting at $10,000:

| Portfolio | Engine | Status | Initial Capital |
|-----------|--------|--------|----------------|
| GENESIS Portfolio | Genetic Programming | Active | $10,000 |
| ATLAS Portfolio | MAP-Elites | Active | $10,000 |
| NEXUS Portfolio | Audit Ensemble | Active | $10,000 |
| LEGION Portfolio | Ensemble Coevolution | Active | $10,000 |
| DARWIN CONSENSUS | Cross-engine agreement | Active | $10,000 |
| PHOENIX Portfolio | Failure-Specific Evolution | Active | $10,000 |

### Position Management
- Max 5 positions per portfolio
- Position size: 20% of capital
- Take Profit: 5% | Stop Loss: 2.5%
- Tracked in: `genome/darwin_portfolios.db`

---

## Architecture

```
genome/
  |-- genetic_programmer.py      # GENESIS engine (978 lines)
  |-- mape_evolver.py            # ATLAS engine (617 lines)
  |-- audit_ensemble_evolver.py  # NEXUS engine (335 lines)
  |-- ensemble_evolver.py        # LEGION engine (833 lines)
  |-- failure_evolver.py           # PHOENIX failure-specific DNA evolution
  |-- dna_engine.py              # HELIX classic engine (1074 lines)
  |-- universal_evolver.py       # Orchestrates all engines
  |-- darwin_portfolio_tracker.py # Paper trading portfolios
  |-- dna_backtester.py          # Walk-forward backtesting
  |-- dna_strategy_factory.py    # DNA combo definitions
  |-- quality_engine.py          # Hedge fund-grade scoring
  |-- signal_validator.py        # Pre-trade validation
  |-- picks_generator.py         # Final picks output
  |-- progressive_promotion.py   # Tier promotion pipeline
  |-- strategy_registry.py       # Central SQLite registry
  |-- bayesian_optimizer.py      # TPE hyperparameter search
  |-- universal_strategy_finder.py # Multi-symbol patterns
  |-- evidence_based_strategies.py # Academic strategies
  |-- data/
      |-- gp_active_picks.json        # GENESIS picks
      |-- mape_active_picks.json      # ATLAS picks
      |-- ae_active_picks.json        # NEXUS picks
      |-- ensemble_active_picks.json  # LEGION picks
      |-- universal_picks.json        # All engines merged
      |-- darwin_portfolios.json      # Portfolio tracker data
```

---

## Running the System

```bash
# Run individual DNA evolution engines
python genome/genetic_programmer.py --pop 60 --gens 15 --symbols BTCUSDT,ETHUSDT,SOLUSDT
python genome/mape_evolver.py --iterations 3000 --symbols BTCUSDT,ETHUSDT,SOLUSDT
python genome/audit_ensemble_evolver.py --pop 50 --gens 20
python genome/ensemble_evolver.py --pop 40 --gens 25

# Run universal evolution (all engines)
python genome/universal_evolver.py --mode all
python genome/universal_evolver.py --mode all --quick  # Fast test run

# Update paper trading portfolios
python genome/darwin_portfolio_tracker.py

# Classic DNA engine
python genome/dna_engine.py
python genome/evolve_strategies.py
```

---

## Forward Testing vs Backtesting

### Backtesting (Historical)
- 750 hourly candles from Binance via ccxt
- Walk-forward validation in DNA backtester
- Commission-aware (0.1% per trade)
- TP/SL/TIME/SIGNAL exit conditions

### Forward Testing (Live Paper)
- Real-time prices from Binance
- Paper portfolios track each engine separately
- P/L updated every run cycle
- No lookahead bias — picks generated before price moves

### Performance Tracking
| Metric | Backtest | Forward Test |
|--------|----------|-------------|
| Win Rate | From historical trades | From paper portfolio closes |
| Sharpe Ratio | Calculated from backtest returns | Rolling from live returns |
| Max Drawdown | Peak-to-trough in backtest | Peak-to-trough in portfolio value |
| Avg Holding Time | Bars between entry/exit | Real time between open/close |
| P/L | Simulated | Paper trading (unrealized + realized) |

---

## Total Codebase: 19,250+ lines across 36 modules
## Evolution Engines: 5 (GENESIS, ATLAS, NEXUS, LEGION, HELIX)
## Strategies Evolved: 200+ unique DNA combinations
## Systems Aggregated: 40+ audit sources
## Asset Focus: Crypto (primary), Stocks/Forex (future expansion)
