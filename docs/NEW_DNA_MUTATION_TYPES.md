# New DNA Mutation Types - March 2026

> **Date:** March 9, 2026  
> **Status:** Production Ready  
> **Systems Added:** 2  
> **Total DNA Systems:** 5  

---

## Summary

We've expanded our DNA Evolution Engine with two powerful new mutation types that complement the existing Genetic Programming, MAP-Elites, and Ensemble systems.

| System | Type | Picks Generated | Status |
|--------|------|-----------------|--------|
| **NEAT Neural** | Topology Evolution | 8 | ✅ Active |
| **Hyperparameter DNA** | Self-Adaptive Parameters | 8 | ✅ Active |
| Genetic Programmer | Expression Trees | 50+ | ✅ Active |
| MAP-Elites | Quality-Diversity | 50+ | ✅ Active |
| Ensemble | Team Coevolution | 26 | ✅ Active |

---

## 1. NEAT Neural DNA Evolution

**File:** `genome/neat_neural_evolver.py`

### What It Does
Evolves **neural network topologies** (not just weights). Unlike fixed-architecture neural nets, this system discovers the optimal network structure through evolution.

### Key Innovations
- **Topology Evolution:** Networks start simple and complexify over generations
- **Species Protection:** Innovation is protected through speciation
- **Historical Markings:** Genes track their evolutionary history for proper crossover
- **Blending Crossover:** Combines networks with different structures intelligently

### Genome Structure
```python
@dataclass
class NeuralGenome:
    nodes: Dict[int, NeuralNode]      # Evolvable node types
    genes: List[NeuralGene]            # Connections with innovation IDs
    species_id: int                    # Speciation protection
    fitness: float
```

### Mutation Types
1. **Add Node:** Splits an existing connection, adds new neuron
2. **Add Connection:** Connects two previously unconnected nodes
3. **Weight Perturbation:** Gaussian noise on connection weights
4. **Enable/Disable:** Toggle connections on/off

### Current Picks (Sample)

| Strategy | Symbol | Direction | Fitness | Complexity | Nodes | Species |
|----------|--------|-----------|---------|------------|-------|---------|
| NEAT_Neural_001 | AVAX | LONG | 0.52 | 30 | 53 | 2 |
| NEAT_Neural_002 | SOL | SHORT | 0.74 | 30 | 37 | 5 |
| NEAT_Neural_003 | DOGE | LONG | 0.77 | 26 | 72 | 1 |

### Integration
- **Audit Dashboard:** `neat_neural` source added
- **Pick File:** `genome/data/neat_active_picks.json`
- **Database:** `genome/neat_evolver.db`

---

## 2. Hyperparameter DNA Evolution

**File:** `genome/hyperparameter_dna_evolver.py`

### What It Does
Evolves **strategy hyperparameters** (position sizes, thresholds, lookback periods) using self-adaptive mutation rates inspired by CMA-ES.

### Key Innovations
- **Self-Adaptive Rates:** Each parameter has its own mutation rate that evolves
- **Epigenetic Marks:** Tracks parameter importance (sensitivity to fitness)
- **Multi-Scale Search:** Small perturbations (90%) + large jumps (10%)
- **Blend Crossover:** Weighted average based on parent fitness

### Parameter Space (20 parameters)

| Category | Parameters |
|----------|------------|
| **Entry** | entry_threshold, confirmation_bars, volume_threshold |
| **Exit** | take_profit_atr_mult, stop_loss_atr_mult, trailing_activation, time_exit_bars |
| **Risk** | position_size_pct, max_positions, daily_loss_limit |
| **Filters** | trend_filter_lookback, trend_filter_threshold, volatility_filter |
| **Adaptive** | regime_sensitivity, market_impact_threshold |

### Genome Structure
```python
@dataclass
class HyperparameterDNA:
    params: Dict[str, Any]              # Parameter values
    mutation_rates: Dict[str, float]    # Self-adaptive rates
    epigenetic_marks: Dict[str, float]  # Importance scores
    fitness: float
```

### Current Picks (Sample)

| Strategy | Symbol | Direction | Fitness | TP (ATR) | SL (ATR) | Position Size |
|----------|--------|-----------|---------|----------|----------|---------------|
| HyperParam_001 | ETH | LONG | 0.62 | 3.2x | 1.8x | 4.2% |
| HyperParam_002 | BTC | SHORT | 0.74 | 4.5x | 2.1x | 6.8% |
| HyperParam_003 | SOL | LONG | 0.58 | 2.8x | 1.4x | 3.1% |

### Integration
- **Audit Dashboard:** `hyperparam_dna` source added
- **Pick File:** `genome/data/hyperparam_active_picks.json`
- **Database:** `genome/hyperparameter_dna.db`

---

## DNA Mutation Type Comparison

| Aspect | GP | MAP-Elites | Ensemble | NEAT Neural | Hyperparam DNA |
|--------|-----|------------|----------|-------------|----------------|
| **Evolves** | Formulas | Strategies | Teams | Network Topologies | Parameters |
| **Genome** | Expression Tree | Behavior Cell | Member List | Nodes + Edges | Parameter Vector |
| **Mutation** | Subtree swap | Archive placement | Member mixing | Add node/edge | Self-adaptive perturb |
| **Crossover** | Subtree exchange | N/A | Member blending | Historical marking | Weighted blend |
| **Key Strength** | Novel indicators | Diverse alternatives | Robust voting | Discovers architectures | Fine-tunes parameters |
| **Best For** | New signals | Multi-strategy portfolios | Production systems | Complex patterns | Optimizing known strategies |

---

## Audit Dashboard Integration

All new DNA systems are integrated into the audit dashboard:

```python
# audit_trail/dashboard_generator.py JSON_PICK_SOURCES
("neat_neural",     "genome/data/neat_active_picks.json",      None),
("hyperparam_dna",  "genome/data/hyperparam_active_picks.json", None),
```

### Pick Format
All DNA picks include:
- `symbol`, `direction`, `confidence`
- `strategy` name
- `source_system` for tracking
- `fitness` score
- `timestamp`
- System-specific metadata (complexity, generation, etc.)

---

## Usage

### Generate New Picks
```bash
# Run specific DNA evolution
python genome/neat_neural_evolver.py
python genome/hyperparameter_dna_evolver.py

# Generate all DNA picks
python genome/generate_dna_picks.py
```

### Query DNA Picks
```bash
# View NEAT picks
cat genome/data/neat_active_picks.json | jq '.picks[:3]'

# View Hyperparameter picks  
cat genome/data/hyperparam_active_picks.json | jq '.picks[:3]'
```

### Backtest DNA Strategy
```python
from genome.neat_neural_evolver import NeuralGenome, NEATEvolutionEngine

# Load from hall of fame
engine = NEATEvolutionEngine()
winners = engine.run_evolution(generations=15)
```

---

## Performance Tracking

### Metrics Captured

| Metric | NEAT | Hyperparam |
|--------|------|------------|
| Fitness | ✅ | ✅ |
| Generation | ✅ | ✅ |
| Complexity | ✅ (# genes) | N/A |
| Species | ✅ | N/A |
| Parameters | N/A | ✅ (20 params) |
| Epigenetics | N/A | ✅ (importance) |

### Validation
All DNA systems track:
- Backtest fitness (pre-computed)
- Live forward performance (via audit trail)
- Win rate comparison (backtest vs live)

---

## Future DNA Mutation Types (Roadmap)

### Q2 2026
1. **Multi-Objective NSGA-II** - Pareto frontier for Sharpe/DD/WR
2. **Adversarial Coevolution** - Strategies vs market maker agents
3. **Meta-Learning DNA** - Learns to learn across market regimes

### Q3 2026
4. **Attention Mechanism Evolution** - Evolves transformer-style attention patterns
5. **Graph Neural Evolution** - For multi-asset correlation trading
6. **Quantum-Inspired DNA** - Superposition of strategy states

---

## Files Created

| File | Purpose | Lines |
|------|---------|-------|
| `genome/neat_neural_evolver.py` | NEAT topology evolution | 607 |
| `genome/hyperparameter_dna_evolver.py` | Self-adaptive parameter evolution | 582 |
| `genome/generate_dna_picks.py` | Pick generation script | 122 |
| `docs/NEW_DNA_MUTATION_TYPES.md` | This documentation | - |

---

## Success Metrics

| Metric | Target | Current |
|--------|--------|---------|
| DNA Systems | 5+ | 5 ✅ |
| Active Picks | 100+ | 140+ ✅ |
| Audit Integration | 100% | 100% ✅ |
| Documentation | Complete | Complete ✅ |

---

**Contact:** Trading Systems Team  
**Last Updated:** March 9, 2026  
**Next Review:** After 100 live trades tracked
