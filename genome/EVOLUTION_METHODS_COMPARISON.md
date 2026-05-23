# Trading Strategy Evolution Methods — Comparison Guide

> **Location:** `genome/`
> **Last Updated:** 2026-03-09

This document compares the three evolution engines available in the genome system, helping you choose the right approach for your goals.

---

## Quick Comparison

| Dimension | **GP (genetic_programmer.py)** | **MAP-Elites (mape_evolver.py)** | **Ensemble (ensemble_evolver.py)** |
|-----------|-------------------------------|----------------------------------|-----------------------------------|
| **What evolves** | Indicator formulas (trees) | Individual strategies | Teams of strategies |
| **Search type** | Optimization | Illumination | Cooperative coevolution |
| **Goal** | Find best strategy | Map viable strategies | Find best teams |
| **Population** | One population | Behavior-space archive | Ensembles of teams |
| **Selection** | Tournament (fitness) | Random from archive | Tournament (ensemble fitness) |
| **Crossover** | Subtree swap | Not used directly | Member mixing |
| **Output** | 1-10 elite strategies | 50-200 diverse strategies | 5-10 elite ensembles |
| **Best for** | Novel indicators | Diverse alternatives | Robust combinations |

---

## 1. Genetic Programming (Standard)

**File:** `genome/genetic_programmer.py`

### What It Does
Evolves brand-new mathematical formulas for trading signals using expression trees.

### Strengths
- ✅ Discovers novel indicators not in textbooks
- ✅ Can find surprisingly simple effective formulas
- ✅ Pure numpy — fast, no pandas dependency
- ✅ Hall of Fame seeding for cumulative improvement

### Weaknesses
- ❌ Converges to local optima
- ❌ Misses diverse viable alternatives
- ❌ No concept of "this works for scalping, that for swinging"

### When to Use
- You want new indicator formulas
- You have a specific fitness target
- You want fast results (30 min cycles)

### Example Output
```
GPX_Gen15_246f61: mul(sub(ema_9, close), gt(rsi_2, 30))
Fitness: 0.785 | SOL | WR: 69%
```

---

## 2. MAP-Elites (Quality-Diversity)

**File:** `genome/mape_evolver.py`

### What It Does
Illuminates the behavior space, finding high-performing strategies across diverse niches (scalpers, swing traders, conservative, aggressive, etc.).

### Strengths
- ✅ Finds diverse strategy types automatically
- ✅ No convergence to single optimum
- ✅ Archive shows "map" of what works
- ✅ Can discover unexpected niches
- ✅ QD Score measures quality + diversity

### Weaknesses
- ❌ Slower than GP (more iterations needed)
- ❌ Archive can be sparse initially
- ❌ Requires tuning behavior dimensions

### When to Use
- You want alternatives to the "best" strategy
- You're exploring what types of strategies work
- You need strategies for different use cases
- You want to avoid overfitting to one style

### Example Output
```
Cell (4,1,2,0,1): Scalper, Aggressive, Long-biased, Trend
Strategy: MAPE_Init_a3f2d1 | Fitness: 0.62

Cell (0,4,1,2,0): Swing, Conservative, Balanced, MeanRev
Strategy: MAPE_Init_8b9c12 | Fitness: 0.58
```

### Coverage Metrics
- **Coverage %:** How much of behavior space is filled
- **QD Score:** Sum of all fitnesses (higher = better quality + diversity)

---

## 3. Ensemble Coevolution

**File:** `genome/ensemble_evolver.py`

### What It Does
Evolves teams of strategies that vote together, optimizing collective decision-making.

### Strengths
- ✅ Finds synergistic combinations
- ✅ Robust to individual strategy failures
- ✅ Multiple consensus mechanisms
- ✅ Can include "diversity specialists"
- ✅ Reduces overfitting through voting

### Weaknesses
- ❌ More complex to analyze
- ❌ Requires more computation per evaluation
- ❌ Ensemble size hyperparameter

### When to Use
- You want robust, production-ready systems
- You have multiple complementary strategies
- You want to reduce single-strategy risk
- You need explainable consensus decisions

### Example Output
```
Ensemble_G25_9fab91:
  Consensus: bayesian
  Members: 5
    - S1 (weight: 1.2, veto: no)
    - S2 (weight: 0.8, veto: yes)
    - S3 (weight: 1.0, veto: no)
    - S4 (weight: 1.5, veto: no)
    - S5 (weight: 0.9, veto: no)
  Fitness: 0.71
```

### Consensus Types
| Type | Best When |
|------|-----------|
| Majority | Balanced ensemble, no clear leaders |
| Weighted | Members have varying confidence |
| Unanimous | Need high certainty (fewer trades) |
| Cascade | Have primary/secondary distinction |
| Bayesian | Want probabilistic aggregation |

---

## Choosing the Right Engine

### Decision Tree

```
Do you need novel indicator formulas?
├── YES → Use GP (genetic_programmer.py)
│
Do you need diverse strategy alternatives?
├── YES → Use MAP-Elites (mape_evolver.py)
│
Do you have strategies to combine?
├── YES → Use Ensemble (ensemble_evolver.py)
│
Want maximum robustness?
└── Use ALL THREE and take consensus
```

### Recommended Workflows

#### Workflow 1: Exploration → Refinement
1. Run **MAP-Elites** to discover diverse strategy types
2. Take top performers from each behavioral niche
3. Feed into **Ensemble** evolution as seed members
4. Output: Robust ensemble covering multiple styles

#### Workflow 2: Formula Discovery → Production
1. Run **GP** to evolve novel indicator formulas
2. Validate best formulas individually
3. Combine winners into **Ensemble** for production
4. Output: Novel indicators + robust voting system

#### Workflow 3: Full Pipeline
1. **MAP-Elites** → Discover diverse base strategies
2. **GP** → Evolve novel indicators using diverse seeds
3. **Ensemble** → Combine everything into voting teams
4. Output: Maximum diversity + novelty + robustness

---

## Integration with Audit System

All three engines output to the audit dashboard:

| Engine | Output File | Dashboard Source |
|--------|-------------|------------------|
| GP | `genome/data/gp_active_picks.json` | `genetic_programmer` |
| MAP-Elites | `genome/data/mape_active_picks.json` | `mape_evolver` |
| Ensemble | `genome/data/ensemble_active_picks.json` | `ensemble_evolver` |

### Cross-System Consensus

You can look for consensus across evolution methods:
- GP says LONG + MAP-Elites says LONG + Ensemble says LONG = High confidence
- Disagreement = Market uncertainty or regime transition

---

## Performance Expectations

| Metric | GP | MAP-Elites | Ensemble |
|--------|-----|------------|----------|
| Runtime (typical) | 5-10 min | 15-30 min | 10-20 min |
| Iterations | 15-20 gens | 3000 iters | 25 gens |
| Evaluations | 800-1600 | 3200 | 1000 |
| Output size | 10-20 | 50-200 | 5-10 |
| Best fitness | 0.70-0.80 | 0.60-0.75 | 0.65-0.75 |
| Diversity | Low | High | Medium |

---

## Future Extensions

### Potential Additions
1. **NEAT** — Evolve neural network topologies
2. **CMA-ES** — Covariance matrix adaptation for continuous parameters
3. **HyperNEAT** — Evolve indirect encodings (genomes → networks)
4. **Multi-Objective NSGA-II** — Pareto frontier for Sharpe vs DD vs WR
5. **Competitive Coevolution** — Strategies evolve against each other in arena

### Hybrid Approaches
- MAP-Elites + GP: Use archive to seed GP with diverse starting points
- Ensemble + MAP-Elites: Build ensembles from diverse archive cells
- GP + Ensemble: Evolve formulas specifically for ensemble diversity

---

## Technical Notes

### Pure NumPy
All three engines use pure numpy (no pandas) for:
- Python 3.14 compatibility
- Maximum performance
- Minimal dependencies

### Shared Components
- `fetch_market_data()` — Binance data via ccxt
- `compute_features()` — Technical indicators
- `backtest_strategy()` — Vectorized backtesting
- `GPStrategy` — Common strategy data structure

### Databases
| Engine | Database | Tables |
|--------|----------|--------|
| GP | `genetic_programmer.db` | gp_strategies, gp_evolution_runs |
| MAP-Elites | `mape_evolver.db` | mape_archive, mape_runs |
| Ensemble | `ensemble_evolver.db` | ensembles, ensemble_runs |

---

## Conclusion

These three engines provide complementary capabilities:

- **GP** = Formula innovation
- **MAP-Elites** = Diversity exploration  
- **Ensemble** = Robust combination

Use them individually for specific goals, or combine for maximum effect.
