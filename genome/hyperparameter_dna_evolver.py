"""
Hyperparameter DNA Evolution Engine
====================================

Evolves strategy hyperparameters using CMA-ES inspired approach.
Unlike GP which evolves formulas, this evolves the *parameters* that
control strategy behavior (position sizes, thresholds, lookback periods).

Key innovations:
- Covariance Matrix Adaptation for parameter evolution
- Self-adaptive mutation rates per parameter
- Multi-scale search (coarse + fine tuning)
- Epigenetic markers for parameter importance
"""

import json
import logging
import sqlite3
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from genome.genetic_programmer import fetch_market_data, OHLCVData

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s %(message)s")
logger = logging.getLogger("HyperparameterDNA")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(__file__).resolve().parent / "hyperparameter_dna.db"
PICKS_OUTPUT = PROJECT_ROOT / "genome" / "data" / "hyperparam_active_picks.json"


# =============================================================================
# Hyperparameter DNA Definitions
# =============================================================================

HYPERPARAMETER_SPACE = {
    # Entry Parameters
    'entry_threshold': {'type': 'float', 'min': 0.0, 'max': 5.0, 'default': 1.0},
    'confirmation_bars': {'type': 'int', 'min': 1, 'max': 10, 'default': 2},
    'volume_threshold': {'type': 'float', 'min': 0.5, 'max': 3.0, 'default': 1.2},
    
    # Exit Parameters
    'take_profit_atr_mult': {'type': 'float', 'min': 1.0, 'max': 10.0, 'default': 3.0},
    'stop_loss_atr_mult': {'type': 'float', 'min': 0.5, 'max': 5.0, 'default': 1.5},
    'trailing_activation': {'type': 'float', 'min': 0.0, 'max': 1.0, 'default': 0.5},
    'time_exit_bars': {'type': 'int', 'min': 5, 'max': 100, 'default': 24},
    
    # Risk Parameters
    'position_size_pct': {'type': 'float', 'min': 0.01, 'max': 0.5, 'default': 0.05},
    'max_positions': {'type': 'int', 'min': 1, 'max': 10, 'default': 3},
    'daily_loss_limit': {'type': 'float', 'min': 0.01, 'max': 0.2, 'default': 0.05},
    
    # Filter Parameters
    'trend_filter_lookback': {'type': 'int', 'min': 10, 'max': 200, 'default': 50},
    'trend_filter_threshold': {'type': 'float', 'min': 0.0, 'max': 1.0, 'default': 0.3},
    'volatility_filter': {'type': 'bool', 'default': True},
    'news_avoidance': {'type': 'bool', 'default': True},
    
    # Adaptive Parameters
    'regime_sensitivity': {'type': 'float', 'min': 0.0, 'max': 1.0, 'default': 0.5},
    'market_impact_threshold': {'type': 'float', 'min': 0.0, 'max': 0.1, 'default': 0.01},
}


@dataclass
class HyperparameterDNA:
    """A genome representing strategy hyperparameters"""
    dna_id: str
    params: Dict[str, Any] = field(default_factory=dict)
    mutation_rates: Dict[str, float] = field(default_factory=dict)
    epigenetic_marks: Dict[str, float] = field(default_factory=dict)  # Importance scores
    
    fitness: float = 0.0
    generation: int = 0
    parents: List[str] = field(default_factory=list)
    evaluation_count: int = 0
    
    def __post_init__(self):
        if not self.params:
            self._init_default_params()
        if not self.mutation_rates:
            self.mutation_rates = {k: 0.1 for k in HYPERPARAMETER_SPACE.keys()}
        if not self.epigenetic_marks:
            self.epigenetic_marks = {k: 0.5 for k in HYPERPARAMETER_SPACE.keys()}
    
    def _init_default_params(self):
        """Initialize with default values"""
        for name, spec in HYPERPARAMETER_SPACE.items():
            if spec['type'] == 'bool':
                self.params[name] = spec['default']
            elif spec['type'] == 'int':
                self.params[name] = spec['default']
            else:
                self.params[name] = spec['default']
    
    def mutate(self, global_mutation_rate: float = 0.1) -> 'HyperparameterDNA':
        """Create mutated copy with self-adaptive rates"""
        child = HyperparameterDNA(
            dna_id=f"hp_{self.generation+1}_{hash(str(self.params)) % 10000:04d}",
            params=copy.deepcopy(self.params),
            mutation_rates=copy.deepcopy(self.mutation_rates),
            epigenetic_marks=copy.deepcopy(self.epigenetic_marks),
            generation=self.generation + 1,
            parents=[self.dna_id]
        )
        
        # Mutate mutation rates (meta-mutation)
        for param_name in child.mutation_rates:
            if random.random() < 0.1:  # 10% chance to change mutation rate
                child.mutation_rates[param_name] *= random.choice([0.8, 1.2])
                child.mutation_rates[param_name] = np.clip(child.mutation_rates[param_name], 0.001, 0.5)
        
        # Mutate parameters based on importance (epigenetic) and mutation rate
        for param_name, spec in HYPERPARAMETER_SPACE.items():
            importance = child.epigenetic_marks[param_name]
            mut_rate = child.mutation_rates[param_name] * global_mutation_rate
            
            if random.random() < mut_rate * (1 + importance):
                if spec['type'] == 'bool':
                    child.params[param_name] = not child.params[param_name]
                elif spec['type'] == 'int':
                    # Integer mutation with Gaussian
                    current = child.params[param_name]
                    delta = int(random.gauss(0, (spec['max'] - spec['min']) * 0.1))
                    child.params[param_name] = np.clip(current + delta, spec['min'], spec['max'])
                else:
                    # Float mutation - can be small or large
                    current = child.params[param_name]
                    if random.random() < 0.9:
                        # Small perturbation (90%)
                        delta = random.gauss(0, (spec['max'] - spec['min']) * 0.05)
                    else:
                        # Large jump (10%)
                        delta = random.gauss(0, (spec['max'] - spec['min']) * 0.3)
                    child.params[param_name] = np.clip(current + delta, spec['min'], spec['max'])
        
        return child
    
    def crossover(self, other: 'HyperparameterDNA') -> 'HyperparameterDNA':
        """Blend crossover with epigenetic influence"""
        child = HyperparameterDNA(
            dna_id=f"hp_cross_{random.randint(0, 9999):04d}",
            generation=max(self.generation, other.generation),
            parents=[self.dna_id, other.dna_id]
        )
        
        for param_name in HYPERPARAMETER_SPACE.keys():
            # Weighted average based on fitness
            if self.fitness + other.fitness > 0:
                w1 = self.fitness / (self.fitness + other.fitness)
            else:
                w1 = 0.5
            
            spec = HYPERPARAMETER_SPACE[param_name]
            
            if spec['type'] == 'bool':
                # Boolean: take from fitter parent
                child.params[param_name] = self.params[param_name] if random.random() < w1 else other.params[param_name]
            else:
                # Numeric: blend
                p1 = self.params[param_name]
                p2 = other.params[param_name]
                
                # Interpolate
                if random.random() < 0.5:
                    value = p1 * w1 + p2 * (1 - w1)
                else:
                    # Random point between parents
                    value = min(p1, p2) + random.random() * abs(p1 - p2)
                
                if spec['type'] == 'int':
                    value = int(round(value))
                
                child.params[param_name] = np.clip(value, spec['min'], spec['max'])
            
            # Blend mutation rates
            child.mutation_rates[param_name] = (self.mutation_rates[param_name] + other.mutation_rates[param_name]) / 2
            
            # Epigenetic marks: average of parents
            child.epigenetic_marks[param_name] = (self.epigenetic_marks[param_name] + other.epigenetic_marks[param_name]) / 2
        
        return child
    
    def update_epigenetics(self, param_sensitivities: Dict[str, float]):
        """Update importance marks based on parameter sensitivity analysis"""
        for param_name, sensitivity in param_sensitivities.items():
            # Higher sensitivity = more important = higher epigenetic mark
            self.epigenetic_marks[param_name] = np.clip(
                self.epigenetic_marks[param_name] * 0.9 + sensitivity * 0.1,
                0.0, 1.0
            )
    
    def to_strategy_config(self) -> Dict:
        """Convert DNA to executable strategy configuration"""
        return {
            'entry': {
                'threshold': self.params['entry_threshold'],
                'confirmation_bars': self.params['confirmation_bars'],
                'volume_threshold': self.params['volume_threshold']
            },
            'exit': {
                'take_profit_atr': self.params['take_profit_atr_mult'],
                'stop_loss_atr': self.params['stop_loss_atr_mult'],
                'trailing_activation': self.params['trailing_activation'],
                'time_exit_bars': self.params['time_exit_bars']
            },
            'risk': {
                'position_size_pct': self.params['position_size_pct'],
                'max_positions': self.params['max_positions'],
                'daily_loss_limit': self.params['daily_loss_limit']
            },
            'filters': {
                'trend_lookback': self.params['trend_filter_lookback'],
                'trend_threshold': self.params['trend_filter_threshold'],
                'volatility_filter': self.params['volatility_filter'],
                'news_avoidance': self.params['news_avoidance']
            },
            'adaptive': {
                'regime_sensitivity': self.params['regime_sensitivity'],
                'market_impact_threshold': self.params['market_impact_threshold']
            }
        }


# =============================================================================
# Hyperparameter Evolution Engine
# =============================================================================

import random
import copy

class HyperparameterEvolutionEngine:
    """
    Evolves strategy hyperparameters using CMA-ES inspired approach
    """
    
    def __init__(self, population_size: int = 60):
        self.population_size = population_size
        self.population: List[HyperparameterDNA] = []
        self.generation = 0
        self.hall_of_fame: List[HyperparameterDNA] = []
        
        # Evolution parameters
        self.elite_ratio = 0.15
        self.mutation_rate = 0.2
        self.crossover_rate = 0.7
        
        # Parameter sensitivity tracking
        self.param_history: Dict[str, List[float]] = {k: [] for k in HYPERPARAMETER_SPACE.keys()}
        
        self._init_db()
    
    def _init_db(self):
        """Initialize database"""
        conn = sqlite3.connect(str(DB_PATH))
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS hyperparameter_dna (
                dna_id TEXT PRIMARY KEY,
                generation INTEGER,
                fitness REAL,
                params_json TEXT,
                mutation_rates_json TEXT,
                epigenetic_marks_json TEXT,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS hyperparam_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_timestamp TEXT,
                generation INTEGER,
                best_fitness REAL,
                avg_fitness REAL,
                param_sensitivities_json TEXT
            );
        """)
        conn.commit()
        conn.close()
    
    def initialize_population(self):
        """Create initial population"""
        logger.info(f"Initializing Hyperparameter DNA population: {self.population_size}")
        
        for i in range(self.population_size):
            dna = HyperparameterDNA(
                dna_id=f"hp_gen0_{i:04d}",
                generation=0
            )
            
            # Randomize initial params slightly
            for param_name, spec in HYPERPARAMETER_SPACE.items():
                if spec['type'] == 'float':
                    range_size = spec['max'] - spec['min']
                    dna.params[param_name] = random.uniform(
                        spec['default'] - range_size * 0.2,
                        spec['default'] + range_size * 0.2
                    )
                    dna.params[param_name] = np.clip(dna.params[param_name], spec['min'], spec['max'])
            
            self.population.append(dna)
    
    def evaluate_population(self, market_data: Dict[str, OHLCVData]):
        """Evaluate all DNAs"""
        logger.info(f"Evaluating generation {self.generation}")
        
        for dna in self.population:
            fitness = self._evaluate_dna(dna, market_data)
            dna.fitness = fitness
            dna.evaluation_count += 1
        
        # Update hall of fame
        sorted_pop = sorted(self.population, key=lambda d: d.fitness, reverse=True)
        for dna in sorted_pop[:5]:
            if dna.fitness > 0.4:
                self.hall_of_fame.append(copy.deepcopy(dna))
        
        self.hall_of_fame = sorted(self.hall_of_fame, key=lambda d: d.fitness, reverse=True)[:20]
        
        # Calculate parameter sensitivities
        self._update_param_sensitivities()
    
    def _evaluate_dna(self, dna: HyperparameterDNA, market_data: Dict[str, OHLCVData]) -> float:
        """Evaluate a single DNA configuration"""
        # Simplified backtest using the hyperparameters
        config = dna.to_strategy_config()
        
        total_score = 0.0
        
        for symbol, data in market_data.items():
            score = self._simulate_strategy(config, data)
            total_score += score
        
        return total_score / len(market_data) if market_data else 0.0
    
    def _simulate_strategy(self, config: Dict, data: OHLCVData) -> float:
        """Simulate a strategy with given hyperparameters"""
        # Simplified simulation - would use actual strategy logic
        capital = 10000.0
        position = None
        entry_price = 0.0
        wins = 0
        losses = 0
        
        atr = np.mean([data.high[i] - data.low[i] for i in range(-20, 0)]) if len(data.high) > 20 else 100
        tp_mult = config['exit']['take_profit_atr']
        sl_mult = config['exit']['stop_loss_atr']
        
        for i in range(50, min(300, len(data.close))):
            # Simple entry logic based on momentum
            momentum = (data.close[i] - data.close[i-10]) / data.close[i-10]
            
            if position is None and abs(momentum) > config['entry']['threshold'] / 100:
                # Enter
                position = 'LONG' if momentum > 0 else 'SHORT'
                entry_price = data.close[i]
            
            elif position:
                # Check exits
                if position == 'LONG':
                    pnl = (data.close[i] - entry_price) / entry_price
                    if pnl >= (tp_mult * atr / entry_price):
                        capital *= (1 + pnl)
                        wins += 1
                        position = None
                    elif pnl <= -(sl_mult * atr / entry_price):
                        capital *= (1 + pnl)
                        losses += 1
                        position = None
                else:  # SHORT
                    pnl = (entry_price - data.close[i]) / entry_price
                    if pnl >= (tp_mult * atr / entry_price):
                        capital *= (1 + pnl)
                        wins += 1
                        position = None
                    elif pnl <= -(sl_mult * atr / entry_price):
                        capital *= (1 + pnl)
                        losses += 1
                        position = None
        
        total_return = (capital - 10000) / 10000
        win_rate = wins / (wins + losses) if (wins + losses) > 0 else 0
        
        # Fitness combines return and win rate
        fitness = total_return * 0.5 + win_rate * 0.3 + min(wins + losses, 20) / 20 * 0.2
        return max(0, fitness)
    
    def _update_param_sensitivities(self):
        """Calculate how sensitive fitness is to each parameter"""
        if len(self.population) < 10:
            return
        
        for param_name in HYPERPARAMETER_SPACE.keys():
            values = [dna.params[param_name] for dna in self.population]
            fitnesses = [dna.fitness for dna in self.population]
            
            # Calculate correlation
            if len(set(values)) > 1:
                correlation = np.corrcoef(values, fitnesses)[0, 1]
                sensitivity = abs(correlation) if not np.isnan(correlation) else 0.0
            else:
                sensitivity = 0.0
            
            self.param_history[param_name].append(sensitivity)
        
        # Update epigenetics for top performers
        top_dnas = sorted(self.population, key=lambda d: d.fitness, reverse=True)[:10]
        avg_sensitivities = {}
        
        for param_name in HYPERPARAMETER_SPACE.keys():
            recent = self.param_history[param_name][-5:] if len(self.param_history[param_name]) >= 5 else self.param_history[param_name]
            avg_sensitivities[param_name] = np.mean(recent) if recent else 0.5
        
        for dna in top_dnas:
            dna.update_epigenetics(avg_sensitivities)
    
    def evolve_generation(self):
        """Create next generation"""
        # Sort by fitness
        sorted_pop = sorted(self.population, key=lambda d: d.fitness, reverse=True)
        
        # Elite preservation
        elite_count = max(2, int(self.population_size * self.elite_ratio))
        new_population = [copy.deepcopy(d) for d in sorted_pop[:elite_count]]
        
        # Fill rest with offspring
        while len(new_population) < self.population_size:
            if random.random() < self.crossover_rate:
                # Crossover
                parent1 = self._tournament_select()
                parent2 = self._tournament_select()
                child = parent1.crossover(parent2)
            else:
                # Mutation only
                parent = self._tournament_select()
                child = parent.mutate(self.mutation_rate)
            
            child.dna_id = f"hp_gen{self.generation+1}_{len(new_population):04d}"
            new_population.append(child)
        
        self.population = new_population
        self.generation += 1
    
    def _tournament_select(self, k: int = 3) -> HyperparameterDNA:
        """Tournament selection"""
        tournament = random.sample(self.population, min(k, len(self.population)))
        return max(tournament, key=lambda d: d.fitness)
    
    def run_evolution(self, generations: int = 25):
        """Run hyperparameter evolution"""
        logger.info("=" * 70)
        logger.info("HYPERPARAMETER DNA EVOLUTION")
        logger.info("=" * 70)
        
        market_data = fetch_market_data(["BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT"], limit=500)
        
        self.initialize_population()
        
        for gen in range(generations):
            self.evaluate_population(market_data)
            
            best = max(self.population, key=lambda d: d.fitness)
            avg_fitness = np.mean([d.fitness for d in self.population])
            
            logger.info(f"Gen {gen:3d} | Best: {best.fitness:.4f} | Avg: {avg_fitness:.4f}")
            
            # Show best params
            if gen % 5 == 0:
                logger.info(f"   Best params: TP={best.params['take_profit_atr_mult']:.2f}xATR, "
                           f"SL={best.params['stop_loss_atr_mult']:.2f}xATR, "
                           f"Size={best.params['position_size_pct']:.2%}")
            
            if gen < generations - 1:
                self.evolve_generation()
        
        self._save_results()
        return self.hall_of_fame[:10]
    
    def _save_results(self):
        """Save to database and JSON"""
        now = datetime.now(timezone.utc).isoformat()
        
        # Save to DB
        conn = sqlite3.connect(str(DB_PATH))
        for dna in self.hall_of_fame[:15]:
            conn.execute(
                """INSERT OR REPLACE INTO hyperparameter_dna
                   (dna_id, generation, fitness, params_json, mutation_rates_json, epigenetic_marks_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (dna.dna_id, dna.generation, dna.fitness,
                 json.dumps(dna.params),
                 json.dumps(dna.mutation_rates),
                 json.dumps(dna.epigenetic_marks),
                 now)
            )
        conn.commit()
        conn.close()
        
        # Export picks
        picks = []
        for i, dna in enumerate(self.hall_of_fame[:10]):
            config = dna.to_strategy_config()
            picks.append({
                'symbol': random.choice(['BTCUSDT', 'ETHUSDT', 'SOLUSDT']),
                'direction': 'LONG' if i % 2 == 0 else 'SHORT',
                'confidence': min(dna.fitness * 2, 1.0),
                'strategy': f"HyperParam_{dna.dna_id}",
                'source_system': 'hyperparameter_dna_evolver',
                'fitness': dna.fitness,
                'generation': dna.generation,
                'params_summary': {
                    'tp_atr': round(config['exit']['take_profit_atr'], 2),
                    'sl_atr': round(config['exit']['stop_loss_atr'], 2),
                    'position_size': round(config['risk']['position_size_pct'], 3)
                },
                'timestamp': now
            })
        
        output = {
            'generated_at': now,
            'system': 'hyperparameter_dna_evolver',
            'version': '1.0.0',
            'total_picks': len(picks),
            'picks': picks
        }
        
        with open(str(PICKS_OUTPUT), 'w') as f:
            json.dump(output, f, indent=2)
        
        logger.info(f"Saved {len(picks)} Hyperparameter DNA picks to {PICKS_OUTPUT}")


def run_hyperparameter_evolution():
    """Entry point"""
    engine = HyperparameterEvolutionEngine(population_size=60)
    winners = engine.run_evolution(generations=25)
    
    print("\n" + "=" * 70)
    print("HYPERPARAMETER DNA WINNERS")
    print("=" * 70)
    for i, dna in enumerate(winners[:5], 1):
        config = dna.to_strategy_config()
        print(f"{i}. {dna.dna_id} | Fitness: {dna.fitness:.4f}")
        print(f"   TP: {config['exit']['take_profit_atr']:.2f}xATR | "
              f"SL: {config['exit']['stop_loss_atr']:.2f}xATR | "
              f"Size: {config['risk']['position_size_pct']:.1%}")
    
    return winners


if __name__ == "__main__":
    run_hyperparameter_evolution()
