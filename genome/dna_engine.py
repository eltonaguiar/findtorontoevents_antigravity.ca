"""
DNA-Based Strategy Permutation Engine
=====================================
Genetic algorithm system for crypto trading strategy evolution and combination.

This module implements a biological-inspired approach to strategy optimization,
where each strategy has a unique DNA signature that can be combined, mutated,
and evolved to find winning combinations.
"""

import hashlib
import json
import random
import copy
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
import numpy as np

# Configure logging
import os as _os
_log_dir = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'logs')
_os.makedirs(_log_dir, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(_os.path.join(_log_dir, 'dna_engine.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('DNAEngine')


class CombinationLogic(Enum):
    """Logic types for combining multiple strategy signals."""
    AND = "and"                    # All strategies must agree
    OR = "or"                      # Any strategy can trigger
    MAJORITY = "majority"          # >50% agreement required
    WEIGHTED = "weighted"          # Confidence-weighted voting
    SEQUENTIAL = "sequential"      # Primary triggers, secondary confirms
    UNANIMOUS = "unanimous"        # 100% agreement (stricter than AND)
    CONSENSUS_75 = "consensus_75"  # 75% agreement required


class MarketRegime(Enum):
    """Market regime classifications for regime-aware optimization."""
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGING = "ranging"
    VOLATILE = "volatile"
    LOW_VOLATILITY = "low_volatility"
    BREAKOUT = "breakout"
    REVERSAL = "reversal"


class RiskProfile(Enum):
    """Risk profile classifications."""
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"
    DEGEN = "degen"


@dataclass
class StrategyDNA:
    """
    Represents the genetic signature of a trading strategy.
    
    Each strategy has a unique DNA that can be combined with others,
    mutated for optimization, and tracked through evolution history.
    """
    strategy_id: str
    name: str
    genes: Dict[str, Any] = field(default_factory=dict)
    mutation_history: List[Dict] = field(default_factory=list)
    parent_strategies: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    generation: int = 0
    dna_hash: str = field(default="")
    
    # Performance metadata
    symbol_specialization: Optional[str] = None  # e.g., "BTC", "ETH"
    regime_preferences: List[MarketRegime] = field(default_factory=list)
    
    def __post_init__(self):
        """Generate DNA hash if not provided."""
        if not self.dna_hash:
            self.dna_hash = self._compute_hash()
    
    def _compute_hash(self) -> str:
        """Compute unique hash for this DNA configuration."""
        hash_input = json.dumps({
            'strategy_id': self.strategy_id,
            'genes': self.genes,
            'generation': self.generation
        }, sort_keys=True)
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary representation."""
        return {
            'strategy_id': self.strategy_id,
            'name': self.name,
            'genes': self.genes,
            'mutation_history': self.mutation_history,
            'parent_strategies': self.parent_strategies,
            'created_at': self.created_at,
            'generation': self.generation,
            'dna_hash': self.dna_hash,
            'symbol_specialization': self.symbol_specialization,
            'regime_preferences': [r.value for r in self.regime_preferences]
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'StrategyDNA':
        """Create StrategyDNA from dictionary."""
        data = copy.deepcopy(data)
        data['regime_preferences'] = [
            MarketRegime(r) for r in data.get('regime_preferences', [])
        ]
        return cls(**data)
    
    def get_gene(self, key: str, default=None):
        """Safely get a gene value."""
        return self.genes.get(key, default)
    
    def set_gene(self, key: str, value: Any):
        """Set a gene value and recompute hash."""
        old_value = self.genes.get(key)
        self.genes[key] = value
        
        # Log mutation
        self.mutation_history.append({
            'timestamp': datetime.utcnow().isoformat(),
            'gene': key,
            'old_value': old_value,
            'new_value': value
        })
        
        # Recompute hash
        self.dna_hash = self._compute_hash()
    
    def is_compatible_with(self, other: 'StrategyDNA') -> bool:
        """Check if this DNA can be combined with another."""
        # Same timeframe is usually required for combination
        my_tf = self.genes.get('timeframe')
        other_tf = other.genes.get('timeframe')
        
        if my_tf and other_tf and my_tf != other_tf:
            return False
        
        # Check for conflicting risk profiles
        my_risk = self.genes.get('risk_profile')
        other_risk = other.genes.get('risk_profile')
        
        if my_risk == RiskProfile.DEGEN.value and other_risk == RiskProfile.CONSERVATIVE.value:
            return False
        
        return True


def adaptive_mutation_rate(generation: int, stagnation_count: int, base_rate: float = 0.02) -> float:
    """Adaptive mutation rate that ramps on stagnation and decays on progress.

    Ramps from base_rate up to 0.25 when stagnation_count > 5.
    Decays with 0.95^generation when not stagnating, floored at 0.005.
    """
    if stagnation_count > 5:
        return min(base_rate * (1 + 0.3 * stagnation_count), 0.25)
    return max(base_rate * 0.95 ** generation, 0.005)


@dataclass
class FitnessScore:
    """Comprehensive fitness metrics for strategy evaluation."""
    sharpe_ratio: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    max_drawdown: float = 0.0
    total_return: float = 0.0
    volatility: float = 0.0
    calmar_ratio: float = 0.0
    sortino_ratio: float = 0.0
    omega_ratio: float = 0.0
    
    # Composite scores
    overall_fitness: float = 0.0
    risk_adjusted_fitness: float = 0.0
    trade_count: int = 0

    def to_objectives(self):
        """Return 3-objective tuple for NSGA-II: (sharpe, abs_dd, wr_weighted).

        Used by pymoo NSGA-II for multi-objective optimization.
        """
        import math
        return (
            self.sharpe_ratio,
            abs(self.max_drawdown),
            self.win_rate * math.sqrt(max(self.trade_count, 1)),
        )

    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_backtest_results(cls, results: Dict) -> 'FitnessScore':
        """Create fitness score from backtest results."""
        fitness = cls(
            sharpe_ratio=results.get('sharpe_ratio', 0.0),
            win_rate=results.get('win_rate', 0.0),
            profit_factor=results.get('profit_factor', 0.0),
            max_drawdown=results.get('max_drawdown', 0.0),
            total_return=results.get('total_return', 0.0),
            volatility=results.get('volatility', 0.0),
            calmar_ratio=results.get('calmar_ratio', 0.0),
            sortino_ratio=results.get('sortino_ratio', 0.0),
            omega_ratio=results.get('omega_ratio', 0.0)
        )
        fitness._compute_composite_scores()
        return fitness
    
    def _compute_composite_scores(self):
        """Compute composite fitness scores from individual metrics."""
        # Overall fitness: weighted combination of key metrics
        weights = {
            'sharpe': 0.25,
            'win_rate': 0.20,
            'profit_factor': 0.20,
            'return': 0.20,
            'drawdown': 0.15  # Inverted (lower is better)
        }
        
        self.overall_fitness = (
            weights['sharpe'] * max(0, self.sharpe_ratio) +
            weights['win_rate'] * self.win_rate +
            weights['profit_factor'] * min(self.profit_factor / 3, 1.0) +
            weights['return'] * max(0, min(self.total_return / 2, 1.0)) +
            weights['drawdown'] * max(0, 1 - abs(self.max_drawdown))
        )
        
        # Risk-adjusted fitness: penalizes high drawdown and volatility
        risk_penalty = (abs(self.max_drawdown) * 0.5) + (self.volatility * 0.3)
        self.risk_adjusted_fitness = max(0, self.overall_fitness - risk_penalty)


class DNAPermutationEngine:
    """
    Core engine for DNA-based strategy permutation and evolution.
    
    Implements genetic algorithm operations including crossover, mutation,
    fitness evaluation, and population evolution.
    """
    
    # Valid gene values for mutation
    GENE_MUTATION_POOLS = {
        'timeframe': ['1m', '5m', '15m', '30m', '1h', '4h', '1d'],
        'risk_profile': ['conservative', 'moderate', 'aggressive', 'degen'],
        'entry_logic': [
            'golden_cross', 'breakout', 'mean_reversion', 'momentum',
            'support_bounce', 'resistance_break', 'volume_spike',
            'rsi_oversold', 'macd_crossover', 'funding_flip'
        ],
        'exit_logic': [
            'death_cross', 'take_profit', 'stop_loss', 'trailing_stop',
            'rsi_overbought', 'macd_crossunder', 'time_exit',
            'volatility_expansion', 'volume_divergence'
        ],
        'primary_indicator': [
            'EMA', 'SMA', 'RSI', 'MACD', 'Bollinger', 'VWAP',
            'ATR', 'Stochastic', 'Ichimoku', 'Volume_Profile'
        ],
        'secondary_indicator': [
            'None', 'RSI', 'MACD', 'Volume', 'ATR', 'Funding_Rate',
            'Open_Interest', 'Orderbook_Imbalance'
        ]
    }
    
    # Numeric gene ranges for mutation
    NUMERIC_GENE_RANGES = {
        'position_size': (0.01, 0.5),      # 1% to 50%
        'leverage': (1, 20),
        'take_profit_mult': (1.0, 5.0),
        'stop_loss_mult': (0.5, 3.0),
        'atr_period': (7, 21),
        'ema_fast': (5, 50),
        'ema_slow': (20, 200),
        'rsi_period': (7, 21),
        'rsi_overbought': (65, 85),
        'rsi_oversold': (15, 35)
    }
    
    def __init__(self, seed: Optional[int] = None):
        """
        Initialize the DNA Permutation Engine.
        
        Args:
            seed: Random seed for reproducibility
        """
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)
        
        self.combination_cache: Dict[str, StrategyDNA] = {}
        self.fitness_history: List[Dict] = []
        logger.info("DNA Permutation Engine initialized")
    
    def combine_dna(
        self,
        dna_list: List[StrategyDNA],
        combination_logic: CombinationLogic = CombinationLogic.WEIGHTED,
        offspring_name: Optional[str] = None
    ) -> StrategyDNA:
        """
        Create offspring DNA by combining parent strategies.
        
        Args:
            dna_list: List of parent StrategyDNA objects
            combination_logic: How to combine the strategies
            offspring_name: Name for the offspring strategy
            
        Returns:
            New StrategyDNA representing the combination
        """
        if not dna_list:
            raise ValueError("Must provide at least one parent DNA")
        
        if len(dna_list) == 1:
            return copy.deepcopy(dna_list[0])
        
        # Check compatibility
        for i, dna1 in enumerate(dna_list):
            for dna2 in dna_list[i+1:]:
                if not dna1.is_compatible_with(dna2):
                    logger.warning(
                        f"Incompatible DNA: {dna1.strategy_id} vs {dna2.strategy_id}"
                    )
        
        # Create offspring genes based on combination logic
        offspring_genes = self._merge_genes(dna_list, combination_logic)
        
        # Generate unique ID for combination
        parent_ids = sorted([d.strategy_id for d in dna_list])
        combo_str = f"{combination_logic.value}:{'+'.join(parent_ids)}"
        offspring_id = f"combo_{hashlib.md5(combo_str.encode()).hexdigest()[:12]}"
        
        if not offspring_name:
            parent_names = [d.name for d in dna_list[:3]]  # Limit to first 3
            offspring_name = f"Combo_{'+'.join(parent_names)}"
        
        offspring = StrategyDNA(
            strategy_id=offspring_id,
            name=offspring_name[:100],  # Limit length
            genes=offspring_genes,
            parent_strategies=parent_ids,
            generation=max(d.generation for d in dna_list) + 1
        )
        
        # Add combination metadata to genes
        offspring.genes['combination_logic'] = combination_logic.value
        offspring.genes['parent_count'] = len(dna_list)
        
        # Cache the result
        self.combination_cache[offspring.dna_hash] = offspring
        
        logger.info(
            f"Created offspring: {offspring_id} from {len(dna_list)} parents "
            f"using {combination_logic.value} logic"
        )
        
        return offspring
    
    def _merge_genes(
        self,
        dna_list: List[StrategyDNA],
        logic: CombinationLogic
    ) -> Dict[str, Any]:
        """Merge genes from multiple parent DNA based on combination logic."""
        merged = {}
        all_genes = set()
        for dna in dna_list:
            all_genes.update(dna.genes.keys())
        
        def _hashable(v):
            """Convert unhashable types (list, dict) to hashable for counting."""
            if isinstance(v, list):
                return tuple(v)
            if isinstance(v, dict):
                return tuple(sorted(v.items()))
            return v

        def _count_values(values):
            """Count occurrences of values, handling unhashable types."""
            counts = {}
            for v in values:
                key = _hashable(v)
                counts[key] = counts.get(key, 0) + 1
            return counts

        for gene_key in all_genes:
            values = [d.genes.get(gene_key) for d in dna_list if gene_key in d.genes]

            if not values:
                continue

            if logic == CombinationLogic.WEIGHTED:
                # Use most common value, weighted by parent fitness
                counts = _count_values(values)
                best_key = max(counts.items(), key=lambda x: x[1])[0]
                # Return original (unhashable) value, not the hashable key
                for v in values:
                    if _hashable(v) == best_key:
                        merged[gene_key] = v
                        break

            elif logic == CombinationLogic.AND:
                # All must agree, otherwise use most restrictive
                hashable_vals = [_hashable(v) for v in values]
                if len(set(hashable_vals)) == 1:
                    merged[gene_key] = values[0]
                else:
                    merged[gene_key] = self._select_most_conservative(gene_key, values)

            elif logic == CombinationLogic.OR:
                # Use most aggressive/lenient setting
                merged[gene_key] = self._select_most_aggressive(gene_key, values)

            elif logic == CombinationLogic.MAJORITY:
                # Use value that appears most frequently
                counts = _count_values(values)
                majority_threshold = len(values) / 2
                max_count = max(counts.values())
                if max_count > majority_threshold:
                    best_key = max(counts.items(), key=lambda x: x[1])[0]
                    for v in values:
                        if _hashable(v) == best_key:
                            merged[gene_key] = v
                            break
                else:
                    merged[gene_key] = values[0]  # Default to first
                    
            elif logic == CombinationLogic.SEQUENTIAL:
                # Primary strategy's value, but note secondary confirmations
                merged[gene_key] = values[0]
                if gene_key == 'entry_logic' and len(values) > 1:
                    merged['confirmation_logic'] = values[1:]
            else:
                # Default: use first parent's value
                merged[gene_key] = values[0]
        
        return merged
    
    def _select_most_conservative(self, gene_key: str, values: List[Any]) -> Any:
        """Select the most conservative value for a gene."""
        if gene_key == 'risk_profile':
            priority = {'conservative': 0, 'moderate': 1, 'aggressive': 2, 'degen': 3}
            return min(values, key=lambda x: priority.get(x, 99))
        elif gene_key == 'position_size':
            return min(values)
        elif gene_key == 'leverage':
            return min(values)
        else:
            return values[0]
    
    def _select_most_aggressive(self, gene_key: str, values: List[Any]) -> Any:
        """Select the most aggressive value for a gene."""
        if gene_key == 'risk_profile':
            priority = {'conservative': 0, 'moderate': 1, 'aggressive': 2, 'degen': 3}
            return max(values, key=lambda x: priority.get(x, -1))
        elif gene_key == 'position_size':
            return max(values)
        elif gene_key == 'leverage':
            return max(values)
        else:
            return values[0]
    
    # Entry direction pools for biased mutation
    LONG_ENTRIES = {"golden_cross", "breakout", "momentum", "support_bounce", "rsi_oversold", "macd_crossover"}
    SHORT_ENTRIES = {"death_cross", "resistance_break", "rsi_overbought", "volume_spike"}

    def mutate_dna(
        self,
        dna: StrategyDNA,
        mutation_rate: float = 0.1,
        mutation_strength: float = 0.3,
        bias: dict = None
    ) -> StrategyDNA:
        """
        Create a mutated copy of a strategy's DNA.
        
        Args:
            dna: Original StrategyDNA to mutate
            mutation_rate: Probability of mutating each gene (0-1)
            mutation_strength: How much to mutate numeric values (0-1)
            
        Returns:
            New mutated StrategyDNA
        """
        mutated = copy.deepcopy(dna)
        mutated.generation += 1
        mutated.parent_strategies = [dna.strategy_id]
        mutated.mutation_history = list(dna.mutation_history)
        
        mutations_applied = []
        
        for gene_key in list(mutated.genes.keys()):
            if random.random() > mutation_rate:
                continue
            
            old_value = mutated.genes[gene_key]
            
            # Apply appropriate mutation based on gene type
            if gene_key in self.GENE_MUTATION_POOLS:
                pool = list(self.GENE_MUTATION_POOLS[gene_key])
                if gene_key == "entry_logic" and bias:
                    direction = bias.get("entry_direction")
                    if direction == "long":
                        filtered = [e for e in pool if e in self.LONG_ENTRIES]
                        pool = filtered if filtered else pool
                    elif direction == "short":
                        filtered = [e for e in pool if e in self.SHORT_ENTRIES]
                        pool = filtered if filtered else pool
                new_value = random.choice(pool)
                mutated.genes[gene_key] = new_value
                
            elif gene_key in self.NUMERIC_GENE_RANGES:
                min_val, max_val = self.NUMERIC_GENE_RANGES[gene_key]
                
                if isinstance(old_value, (int, float)):
                    # Apply gaussian mutation
                    std = (max_val - min_val) * mutation_strength
                    if isinstance(old_value, int):
                        new_value = int(np.clip(
                            old_value + np.random.normal(0, std),
                            min_val, max_val
                        ))
                    else:
                        new_value = round(np.clip(
                            old_value + np.random.normal(0, std),
                            min_val, max_val
                        ), 4)
                    mutated.genes[gene_key] = new_value
            
            else:
                # Generic mutation: small random change
                if isinstance(old_value, (int, float)):
                    factor = 1 + np.random.normal(0, mutation_strength)
                    mutated.genes[gene_key] = old_value * factor
            
            # Record mutation
            mutations_applied.append({
                'gene': gene_key,
                'old': old_value,
                'new': mutated.genes.get(gene_key)
            })
        
        # Add new random genes occasionally (gene addition mutation)
        if random.random() < mutation_rate * 0.3:
            available_genes = set(self.NUMERIC_GENE_RANGES.keys()) - set(mutated.genes.keys())
            if available_genes:
                new_gene = random.choice(list(available_genes))
                min_val, max_val = self.NUMERIC_GENE_RANGES[new_gene]
                mutated.genes[new_gene] = round(random.uniform(min_val, max_val), 4)
                mutations_applied.append({
                    'gene': new_gene,
                    'old': None,
                    'new': mutated.genes[new_gene],
                    'type': 'addition'
                })
        
        # Recompute hash after mutations
        mutated.dna_hash = mutated._compute_hash()
        mutated.strategy_id = f"mut_{mutated.dna_hash[:12]}"
        mutated.name = f"Mutated_{dna.name[:50]}"
        
        if mutations_applied:
            logger.info(
                f"Applied {len(mutations_applied)} mutations to {dna.strategy_id}: "
                f"{[m['gene'] for m in mutations_applied]}"
            )
        
        return mutated
    
    def calculate_fitness(
        self,
        backtest_results: Dict[str, Any],
        regime: Optional[MarketRegime] = None,
        symbol: Optional[str] = None
    ) -> FitnessScore:
        """
        Calculate comprehensive fitness score from backtest results.
        
        Args:
            backtest_results: Dictionary containing backtest metrics
            regime: Current market regime (for regime-specific scoring)
            symbol: Trading symbol (for symbol-specific adjustments)
            
        Returns:
            FitnessScore object with composite metrics
        """
        fitness = FitnessScore.from_backtest_results(backtest_results)
        
        # Apply regime-specific adjustments
        if regime:
            fitness = self._apply_regime_adjustments(fitness, regime)
        
        # Apply symbol-specific adjustments
        if symbol:
            fitness = self._apply_symbol_adjustments(fitness, symbol)
        
        self.fitness_history.append({
            'timestamp': datetime.utcnow().isoformat(),
            'fitness': fitness.to_dict(),
            'regime': regime.value if regime else None,
            'symbol': symbol
        })
        
        return fitness
    
    def _apply_regime_adjustments(
        self,
        fitness: FitnessScore,
        regime: MarketRegime
    ) -> FitnessScore:
        """Adjust fitness scores based on market regime."""
        # Different regimes reward different characteristics
        regime_multipliers = {
            MarketRegime.TRENDING_UP: {
                'sharpe': 1.0, 'win_rate': 0.9, 'profit_factor': 1.1
            },
            MarketRegime.TRENDING_DOWN: {
                'sharpe': 1.0, 'win_rate': 0.8, 'profit_factor': 1.0
            },
            MarketRegime.RANGING: {
                'sharpe': 1.1, 'win_rate': 1.2, 'profit_factor': 1.0
            },
            MarketRegime.VOLATILE: {
                'sharpe': 1.2, 'win_rate': 0.8, 'profit_factor': 1.1
            },
            MarketRegime.LOW_VOLATILITY: {
                'sharpe': 0.9, 'win_rate': 1.1, 'profit_factor': 0.9
            }
        }
        
        multipliers = regime_multipliers.get(regime, {})
        
        adjusted = FitnessScore(
            sharpe_ratio=fitness.sharpe_ratio * multipliers.get('sharpe', 1.0),
            win_rate=fitness.win_rate * multipliers.get('win_rate', 1.0),
            profit_factor=fitness.profit_factor * multipliers.get('profit_factor', 1.0),
            max_drawdown=fitness.max_drawdown,
            total_return=fitness.total_return,
            volatility=fitness.volatility,
            calmar_ratio=fitness.calmar_ratio,
            sortino_ratio=fitness.sortino_ratio,
            omega_ratio=fitness.omega_ratio
        )
        adjusted._compute_composite_scores()
        
        return adjusted
    
    def _apply_symbol_adjustments(
        self,
        fitness: FitnessScore,
        symbol: str
    ) -> FitnessScore:
        """Apply symbol-specific fitness adjustments."""
        # Different symbols have different baseline expectations
        symbol_adjustments = {
            'BTC': {'sharpe_threshold': 1.5, 'dd_threshold': 0.20},
            'ETH': {'sharpe_threshold': 1.3, 'dd_threshold': 0.25},
            'SOL': {'sharpe_threshold': 1.2, 'dd_threshold': 0.30},
            'default': {'sharpe_threshold': 1.0, 'dd_threshold': 0.35}
        }
        
        base_symbol = symbol.replace('USDT', '').replace('USD', '')
        adj = symbol_adjustments.get(base_symbol, symbol_adjustments['default'])
        
        # Penalize if below symbol-specific thresholds
        if fitness.sharpe_ratio < adj['sharpe_threshold']:
            penalty = (adj['sharpe_threshold'] - fitness.sharpe_ratio) * 0.1
            fitness.overall_fitness = max(0, fitness.overall_fitness - penalty)
        
        if abs(fitness.max_drawdown) > adj['dd_threshold']:
            penalty = (abs(fitness.max_drawdown) - adj['dd_threshold']) * 0.2
            fitness.risk_adjusted_fitness = max(0, fitness.risk_adjusted_fitness - penalty)
        
        return fitness
    
    def evolve_population(
        self,
        population: List[Tuple[StrategyDNA, FitnessScore]],
        generations: int = 10,
        population_size: int = 50,
        elite_ratio: float = 0.1,
        crossover_rate: float = 0.7,
        mutation_rate: float = 0.1,
        fitness_threshold: float = 0.7
    ) -> Tuple[List[StrategyDNA], List[Dict]]:
        """
        Evolve a population of strategies using genetic algorithm.
        
        Args:
            population: Initial population as list of (DNA, FitnessScore) tuples
            generations: Number of generations to evolve
            population_size: Target population size
            elite_ratio: Percentage of top performers to preserve
            crossover_rate: Probability of crossover vs mutation
            mutation_rate: Mutation probability
            fitness_threshold: Stop if best fitness exceeds this
            
        Returns:
            Tuple of (final_population, evolution_history)
        """
        evolution_history = []
        current_pop = population.copy()
        
        logger.info(f"Starting evolution: {len(current_pop)} individuals, {generations} generations")
        
        for gen in range(generations):
            # Sort by fitness — filter out None fitness (new offspring not yet evaluated)
            current_pop = [
                (dna, fit if fit is not None else FitnessScore())
                for dna, fit in current_pop
            ]
            current_pop.sort(key=lambda x: x[1].overall_fitness, reverse=True)
            
            best_fitness = current_pop[0][1].overall_fitness
            avg_fitness = sum(f[1].overall_fitness for f in current_pop) / len(current_pop)
            
            evolution_history.append({
                'generation': gen,
                'best_fitness': best_fitness,
                'avg_fitness': avg_fitness,
                'population_size': len(current_pop),
                'best_strategy': current_pop[0][0].strategy_id
            })
            
            logger.info(
                f"Generation {gen}: Best={best_fitness:.4f}, Avg={avg_fitness:.4f}"
            )
            
            # Check termination condition
            if best_fitness >= fitness_threshold:
                logger.info(f"Fitness threshold reached at generation {gen}")
                break
            
            # Create next generation
            next_pop = []
            
            # Elitism: keep top performers
            elite_count = max(1, int(population_size * elite_ratio))
            next_pop.extend(current_pop[:elite_count])
            
            # Fill rest of population
            while len(next_pop) < population_size:
                if random.random() < crossover_rate and len(current_pop) >= 2:
                    # Crossover (combination)
                    parents = random.sample(current_pop[:max(10, len(current_pop)//2)], 2)
                    parent_dnas = [p[0] for p in parents]
                    
                    offspring = self.combine_dna(
                        parent_dnas,
                        combination_logic=random.choice(list(CombinationLogic))
                    )
                    # Will need fitness evaluation
                    next_pop.append((offspring, None))
                    
                else:
                    # Mutation
                    parent = random.choice(current_pop[:max(10, len(current_pop)//2)])
                    mutated = self.mutate_dna(
                        parent[0],
                        mutation_rate=mutation_rate
                    )
                    next_pop.append((mutated, None))
            
            current_pop = next_pop
        
        # Return final DNA list (fitness will need to be recalculated)
        final_population = [dna for dna, _ in current_pop]
        
        return final_population, evolution_history
    
    def generate_all_permutations(
        self,
        strategies: List[StrategyDNA],
        max_combo_size: int = 4,
        logic_types: Optional[List[CombinationLogic]] = None,
        filter_incompatible: bool = True
    ) -> List[StrategyDNA]:
        """
        Generate all possible strategy combinations (permutations).
        
        Args:
            strategies: Base strategies to combine
            max_combo_size: Maximum number of strategies per combination
            logic_types: Which combination logics to use (default: all)
            filter_incompatible: Skip incompatible combinations
            
        Returns:
            List of all combined StrategyDNA objects
        """
        from itertools import combinations
        
        if logic_types is None:
            logic_types = list(CombinationLogic)
        
        permutations = []
        
        # Generate combinations of different sizes
        for combo_size in range(2, min(max_combo_size + 1, len(strategies) + 1)):
            for strategy_combo in combinations(strategies, combo_size):
                # Check compatibility
                if filter_incompatible:
                    compatible = True
                    for i, s1 in enumerate(strategy_combo):
                        for s2 in strategy_combo[i+1:]:
                            if not s1.is_compatible_with(s2):
                                compatible = False
                                break
                        if not compatible:
                            break
                    
                    if not compatible:
                        continue
                
                # Create permutations with different logic types
                for logic in logic_types:
                    try:
                        offspring = self.combine_dna(
                            list(strategy_combo),
                            combination_logic=logic
                        )
                        permutations.append(offspring)
                    except Exception as e:
                        logger.warning(f"Failed to create combination: {e}")
        
        logger.info(f"Generated {len(permutations)} permutations from {len(strategies)} strategies")
        return permutations
    
    def detect_regime(self, price_data: List[float], volume_data: Optional[List[float]] = None) -> MarketRegime:
        """
        Detect current market regime from price and volume data.
        
        Args:
            price_data: List of price values
            volume_data: Optional list of volume values
            
        Returns:
            Detected MarketRegime
        """
        if len(price_data) < 20:
            return MarketRegime.RANGING
        
        prices = np.array(price_data)
        
        # Calculate returns
        returns = np.diff(prices) / prices[:-1]
        
        # Trend detection using linear regression
        x = np.arange(len(prices))
        slope = np.polyfit(x, prices, 1)[0]
        slope_normalized = slope / np.mean(prices) * len(prices)
        
        # Volatility (ATR-like)
        volatility = np.std(returns) * np.sqrt(252)  # Annualized
        
        # ADX-like trend strength (simplified)
        price_range = np.max(prices[-20:]) - np.min(prices[-20:])
        avg_price = np.mean(prices[-20:])
        trend_strength = price_range / avg_price if avg_price > 0 else 0
        
        # Regime classification
        if volatility > 0.8:
            if abs(slope_normalized) > 0.1:
                return MarketRegime.VOLATILE if slope_normalized > 0 else MarketRegime.VOLATILE
            return MarketRegime.VOLATILE
        
        if abs(slope_normalized) > 0.15:
            if slope_normalized > 0:
                return MarketRegime.TRENDING_UP
            else:
                return MarketRegime.TRENDING_DOWN
        
        if trend_strength < 0.05:
            return MarketRegime.RANGING
        
        if volatility < 0.2:
            return MarketRegime.LOW_VOLATILITY
        
        return MarketRegime.RANGING
    
    def export_permutations(self, permutations: List[StrategyDNA], filepath: str):
        """Export permutations to JSON file."""
        data = {
            'exported_at': datetime.utcnow().isoformat(),
            'count': len(permutations),
            'permutations': [p.to_dict() for p in permutations]
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Exported {len(permutations)} permutations to {filepath}")
    
    def import_permutations(self, filepath: str) -> List[StrategyDNA]:
        """Import permutations from JSON file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        permutations = [StrategyDNA.from_dict(p) for p in data['permutations']]
        logger.info(f"Imported {len(permutations)} permutations from {filepath}")
        return permutations


class IslandModel:
    """4-island model with ring-topology migration.

    Islands: bear (defensive), bull (momentum), range (mean-reversion), recent (ensemble/hybrid).
    Migration: ring topology bear->bull->range->recent->bear every N generations.
    """

    def __init__(self, seeds: dict, island_size: int = 15, engine: DNAPermutationEngine = None):
        self.engine = engine or DNAPermutationEngine()
        self.island_size = island_size
        self.islands = {}
        island_order = ["bear", "bull", "range", "recent"]
        for name in island_order:
            seed_pop = seeds.get(name, [])
            # Fill to target size by mutating seeds
            population = list(seed_pop)
            while len(population) < island_size:
                parent = random.choice(seed_pop) if seed_pop else population[0]
                mutant = self.engine.mutate_dna(parent, mutation_rate=0.3, mutation_strength=0.5)
                population.append(mutant)
            self.islands[name] = {
                "population": population[:island_size],
                "fitness_history": [],
                "stagnation_count": 0,
            }

    def migrate(self, n_migrants: int = 2):
        """Ring topology: bear->bull->range->recent->bear."""
        order = ["bear", "bull", "range", "recent"]
        emigrants = {}
        for name in order:
            pop = self.islands[name]["population"]
            # Top N strategies emigrate (assumes sorted by fitness)
            emigrants[name] = pop[:n_migrants]
        for i, name in enumerate(order):
            target = order[(i + 1) % len(order)]
            target_pop = self.islands[target]["population"]
            # Replace worst N with immigrants
            self.islands[target]["population"] = (
                emigrants[name] + target_pop[:-n_migrants]
            )


# Convenience functions for quick usage
def create_strategy_dna(
    name: str,
    timeframe: str = "1h",
    primary_indicator: str = "EMA",
    entry_logic: str = "golden_cross",
    exit_logic: str = "death_cross",
    risk_profile: str = "moderate",
    **additional_genes
) -> StrategyDNA:
    """Quick factory function to create a StrategyDNA."""
    
    genes = {
        'timeframe': timeframe,
        'primary_indicator': primary_indicator,
        'entry_logic': entry_logic,
        'exit_logic': exit_logic,
        'risk_profile': risk_profile,
        **additional_genes
    }
    
    # Generate ID from name
    strategy_id = f"strat_{hashlib.md5(name.encode()).hexdigest()[:12]}"
    
    return StrategyDNA(
        strategy_id=strategy_id,
        name=name,
        genes=genes
    )


if __name__ == "__main__":
    import argparse
    import os
    import sys

    parser = argparse.ArgumentParser(description="DNA Permutation Engine CLI")
    parser.add_argument("--mode", choices=["permute", "demo"], default="demo",
                        help="Operation mode: 'permute' loads seed strategies and generates combos, 'demo' runs example")
    parser.add_argument("--max-combo-size", type=int, default=4,
                        help="Maximum number of strategies per combination (default: 4)")
    parser.add_argument("--output-dir", type=str, default="results",
                        help="Directory to save permutation results (default: results)")
    args = parser.parse_args()

    if args.mode == "permute":
        # Load seed strategies -- handle both execution contexts
        try:
            from seed_strategies import get_all_island_seeds
        except ImportError:
            # Running as python -m genome.dna_engine from repo root
            from genome.seed_strategies import get_all_island_seeds

        engine = DNAPermutationEngine(seed=42)
        island_seeds = get_all_island_seeds()

        # Flatten all island seeds into one list
        all_seeds = []
        for island_name, seeds in island_seeds.items():
            all_seeds.extend(seeds)
            print(f"[INFO] Island '{island_name}': {len(seeds)} seed strategies")

        print(f"[INFO] Total seed strategies: {len(all_seeds)}")
        print(f"[INFO] Max combo size: {args.max_combo_size}")

        # Generate permutations
        permutations = engine.generate_all_permutations(all_seeds, max_combo_size=args.max_combo_size)
        print(f"[INFO] Generated {len(permutations)} strategy combinations")

        # Save results
        out_dir = args.output_dir
        os.makedirs(out_dir, exist_ok=True)
        output_path = os.path.join(out_dir, "permutations.json")
        engine.export_permutations(permutations, output_path)
        print(f"[OK] Saved permutations to {output_path}")

    else:
        # Demo mode (original example code)
        engine = DNAPermutationEngine(seed=42)

        strategy1 = create_strategy_dna(
            name="EMA Cross BTC", timeframe="1h", primary_indicator="EMA",
            entry_logic="golden_cross", ema_fast=20, ema_slow=50
        )
        strategy2 = create_strategy_dna(
            name="RSI Reversion", timeframe="1h", primary_indicator="RSI",
            entry_logic="rsi_oversold", rsi_period=14, rsi_oversold=30
        )
        strategy3 = create_strategy_dna(
            name="MACD Momentum", timeframe="1h", primary_indicator="MACD",
            entry_logic="macd_crossover"
        )

        print(f"Strategy 1: {strategy1.strategy_id} - {strategy1.dna_hash}")
        print(f"Strategy 2: {strategy2.strategy_id} - {strategy2.dna_hash}")
        print(f"Strategy 3: {strategy3.strategy_id} - {strategy3.dna_hash}")

        combo = engine.combine_dna(
            [strategy1, strategy2, strategy3],
            combination_logic=CombinationLogic.WEIGHTED
        )
        print(f"\nCombination: {combo.strategy_id}")
        print(f"Parents: {combo.parent_strategies}")
        print(f"Genes: {combo.genes}")

        mutated = engine.mutate_dna(strategy1, mutation_rate=0.5)
        print(f"\nMutated: {mutated.strategy_id}")
        print(f"Mutations: {len(mutated.mutation_history)}")

        all_strategies = [strategy1, strategy2, strategy3]
        perms = engine.generate_all_permutations(all_strategies, max_combo_size=3)
        print(f"\nTotal permutations: {len(perms)}")
