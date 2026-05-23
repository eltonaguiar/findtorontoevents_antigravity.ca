#!/usr/bin/env python3
"""
Enhanced DNA Genome Engine - Phase 1 Implementation
7 Chromosome Groups with Multi-Objective Optimization
"""

import json
import hashlib
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
from copy import deepcopy


@dataclass
class EnhancedGenome:
    """
    Enhanced genome with 7 chromosome groups.
    """
    # Core chromosome groups (4 original)
    entry_genes: Dict = field(default_factory=dict)
    exit_genes: Dict = field(default_factory=dict)
    risk_genes: Dict = field(default_factory=dict)
    meta_genes: Dict = field(default_factory=dict)
    
    # NEW: Extended chromosome groups (3 new)
    data_quality_genes: Dict = field(default_factory=dict)
    regime_adaptation_genes: Dict = field(default_factory=dict)
    portfolio_fit_genes: Dict = field(default_factory=dict)
    
    # Evolution tracking
    generation: int = 0
    fitness_score: float = 0.0
    dna_hash: str = ""
    parent_hashes: List[str] = field(default_factory=list)
    mutation_history: List[Dict] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.dna_hash:
            self.dna_hash = self._calculate_hash()
    
    def _calculate_hash(self) -> str:
        """Calculate unique hash for this genome."""
        data = json.dumps({
            'entry': self.entry_genes,
            'exit': self.exit_genes,
            'risk': self.risk_genes,
            'meta': self.meta_genes,
            'data_quality': self.data_quality_genes,
            'regime': self.regime_adaptation_genes,
            'portfolio': self.portfolio_fit_genes
        }, sort_keys=True)
        return hashlib.md5(data.encode()).hexdigest()[:16]
    
    def to_dict(self) -> Dict:
        return {
            'entry_genes': self.entry_genes,
            'exit_genes': self.exit_genes,
            'risk_genes': self.risk_genes,
            'meta_genes': self.meta_genes,
            'data_quality_genes': self.data_quality_genes,
            'regime_adaptation_genes': self.regime_adaptation_genes,
            'portfolio_fit_genes': self.portfolio_fit_genes,
            'generation': self.generation,
            'fitness_score': self.fitness_score,
            'dna_hash': self.dna_hash,
            'parent_hashes': self.parent_hashes,
            'mutation_history': self.mutation_history
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'EnhancedGenome':
        return cls(
            entry_genes=data.get('entry_genes', {}),
            exit_genes=data.get('exit_genes', {}),
            risk_genes=data.get('risk_genes', {}),
            meta_genes=data.get('meta_genes', {}),
            data_quality_genes=data.get('data_quality_genes', {}),
            regime_adaptation_genes=data.get('regime_adaptation_genes', {}),
            portfolio_fit_genes=data.get('portfolio_fit_genes', {}),
            generation=data.get('generation', 0),
            fitness_score=data.get('fitness_score', 0.0),
            dna_hash=data.get('dna_hash', ''),
            parent_hashes=data.get('parent_hashes', []),
            mutation_history=data.get('mutation_history', [])
        )


class EnhancedDNAEngine:
    """
    Enhanced DNA Engine with 200 generations and multi-objective optimization.
    """
    
    # Fitness weights for multi-objective optimization
    FITNESS_WEIGHTS = {
        'sharpe': 0.30,
        'max_drawdown': 0.25,  # Lower is better, so we invert
        'profit_factor': 0.20,
        'win_rate': 0.15,
        'statistical_significance': 0.10
    }
    
    def __init__(self, 
                 population_size: int = 100,
                 max_generations: int = 200,  # Increased from 50
                 mutation_rate: float = 0.10,
                 crossover_rate: float = 0.70):
        
        self.population_size = population_size
        self.max_generations = max_generations
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        
        self.population: List[EnhancedGenome] = []
        self.generation = 0
        self.best_genome: Optional[EnhancedGenome] = None
        self.fitness_history: List[Dict] = []
    
    def create_random_genome(self) -> EnhancedGenome:
        """Create a random genome with all 7 chromosome groups."""
        return EnhancedGenome(
            entry_genes={
                'indicator_type': random.choice(['weighted_vote', 'consensus', 'cascade']),
                'threshold': round(random.uniform(0.5, 0.8), 2),
                'confirmation_rules': {
                    'require_volume': random.choice([True, False]),
                    'min_confluence': random.randint(2, 4)
                },
                'multi_timeframe_alignment': random.choice([True, False])
            },
            exit_genes={
                'tp_mode': random.choice(['adaptive_atr', 'fixed_percent', 'trailing']),
                'sl_mode': random.choice(['volatility_adjusted', 'fixed', 'atr_based']),
                'trailing_activation': round(random.uniform(0.3, 0.7), 2),
                'partial_tp_levels': random.sample([1.0, 1.5, 2.0, 2.5, 3.0], k=random.randint(2, 4))
            },
            risk_genes={
                'position_sizing': random.choice(['kelly_fraction', 'fixed_percent', 'volatility_targeting']),
                'kelly_fraction': round(random.uniform(0.15, 0.50), 2),
                'max_portfolio_risk': round(random.uniform(0.01, 0.03), 3),
                'correlation_limit': round(random.uniform(0.6, 0.8), 2),
                'drawdown_circuit_breaker': round(random.uniform(0.08, 0.15), 2)
            },
            meta_genes={
                'regime_preference': random.sample(['bull', 'bear', 'sideways', 'high_vol', 'low_vol'], 
                                                   k=random.randint(1, 3)),
                'decay_factor': round(random.uniform(0.90, 0.98), 3),
                'confidence_threshold': round(random.uniform(0.60, 0.75), 2)
            },
            # NEW: Data Quality Genes
            data_quality_genes={
                'source_reliability_weights': {
                    'binance': round(random.uniform(0.9, 1.0), 2),
                    'okx': round(random.uniform(0.8, 0.95), 2),
                    'bybit': round(random.uniform(0.8, 0.95), 2),
                    'coingecko': round(random.uniform(0.7, 0.85), 2)
                },
                'minimum_data_freshness_hours': random.randint(1, 4),
                'feature_importance_threshold': round(random.uniform(0.005, 0.02), 3),
                'data_quality_filter': random.choice(['strict', 'moderate', 'relaxed'])
            },
            # NEW: Regime Adaptation Genes
            regime_adaptation_genes={
                'volatility_sensitivity': round(random.uniform(0.6, 1.0), 2),
                'trend_strength_requirement': round(random.uniform(0.3, 0.6), 2),
                'market_cap_preference': random.choice(['large', 'mid', 'small', 'mixed']),
                'regime_switch_threshold': round(random.uniform(0.15, 0.30), 2),
                'adaptive_lookback': random.choice([20, 50, 100, 200])
            },
            # NEW: Portfolio Fit Genes
            portfolio_fit_genes={
                'maximum_sector_concentration': round(random.uniform(0.20, 0.40), 2),
                'correlation_penalty': round(random.uniform(0.3, 0.7), 2),
                'diversification_score': round(random.uniform(0.6, 0.9), 2),
                'position_correlation_limit': round(random.uniform(0.5, 0.7), 2),
                'portfolio_heat_limit': round(random.uniform(0.5, 0.8), 2)
            }
        )
    
    def initialize_population(self):
        """Create initial random population."""
        self.population = [
            self.create_random_genome()
            for _ in range(self.population_size)
        ]
        print(f"Initialized population of {self.population_size} genomes")
    
    def calculate_fitness(self, 
                         backtest_results: Dict,
                         statistical_tests: Dict) -> float:
        """
        Multi-objective fitness calculation.
        
        Combines: Sharpe, Max DD, Profit Factor, Win Rate, Statistical Significance
        """
        # Normalize each component to 0-1 scale
        sharpe_score = min(backtest_results.get('sharpe', 0) / 3.0, 1.0)
        
        # Max DD: lower is better, so invert
        max_dd = backtest_results.get('max_drawdown', 1.0)
        dd_score = max(0, 1.0 - max_dd / 0.30)  # 30% DD = 0 score
        
        pf_score = min(backtest_results.get('profit_factor', 0) / 3.0, 1.0)
        wr_score = backtest_results.get('win_rate', 0)
        
        # Statistical significance
        stat_score = statistical_tests.get('confidence', 0)
        
        # Weighted combination
        fitness = (
            self.FITNESS_WEIGHTS['sharpe'] * sharpe_score +
            self.FITNESS_WEIGHTS['max_drawdown'] * dd_score +
            self.FITNESS_WEIGHTS['profit_factor'] * pf_score +
            self.FITNESS_WEIGHTS['win_rate'] * wr_score +
            self.FITNESS_WEIGHTS['statistical_significance'] * stat_score
        )
        
        return fitness
    
    def select_parents(self) -> Tuple[EnhancedGenome, EnhancedGenome]:
        """Tournament selection for parents."""
        tournament_size = 3
        
        def tournament():
            contestants = random.sample(self.population, tournament_size)
            return max(contestants, key=lambda g: g.fitness_score)
        
        return tournament(), tournament()
    
    def crossover(self, 
                  parent1: EnhancedGenome, 
                  parent2: EnhancedGenome) -> Tuple[EnhancedGenome, EnhancedGenome]:
        """Perform crossover between two parents."""
        if random.random() > self.crossover_rate:
            return parent1, parent2
        
        child1 = deepcopy(parent1)
        child2 = deepcopy(parent2)
        
        # Crossover each chromosome group
        for gene_key in ['entry_genes', 'exit_genes', 'risk_genes', 'meta_genes',
                        'data_quality_genes', 'regime_adaptation_genes', 'portfolio_fit_genes']:
            if random.random() < 0.5:
                # Swap genes
                temp = getattr(child1, gene_key)
                setattr(child1, gene_key, getattr(child2, gene_key))
                setattr(child2, gene_key, temp)
        
        # Update parent hashes
        child1.parent_hashes = [parent1.dna_hash, parent2.dna_hash]
        child2.parent_hashes = [parent1.dna_hash, parent2.dna_hash]
        
        child1.generation = self.generation
        child2.generation = self.generation
        
        # Recalculate hashes
        child1.dna_hash = child1._calculate_hash()
        child2.dna_hash = child2._calculate_hash()
        
        return child1, child2
    
    def mutate(self, genome: EnhancedGenome) -> EnhancedGenome:
        """Apply mutations to genome."""
        mutated = deepcopy(genome)
        mutations = []
        
        # Mutate entry genes
        if random.random() < self.mutation_rate:
            mutated.entry_genes['threshold'] = round(
                mutated.entry_genes['threshold'] + random.uniform(-0.1, 0.1), 2
            )
            mutations.append('entry_threshold')
        
        # Mutate exit genes
        if random.random() < self.mutation_rate:
            mutated.exit_genes['trailing_activation'] = round(
                mutated.exit_genes['trailing_activation'] + random.uniform(-0.1, 0.1), 2
            )
            mutations.append('trailing_activation')
        
        # Mutate risk genes
        if random.random() < self.mutation_rate:
            mutated.risk_genes['kelly_fraction'] = round(
                mutated.risk_genes['kelly_fraction'] + random.uniform(-0.05, 0.05), 2
            )
            mutations.append('kelly_fraction')
        
        # Mutate regime adaptation genes
        if random.random() < self.mutation_rate:
            mutated.regime_adaptation_genes['volatility_sensitivity'] = round(
                mutated.regime_adaptation_genes['volatility_sensitivity'] + 
                random.uniform(-0.1, 0.1), 2
            )
            mutations.append('volatility_sensitivity')
        
        # Mutate portfolio fit genes
        if random.random() < self.mutation_rate:
            mutated.portfolio_fit_genes['diversification_score'] = round(
                mutated.portfolio_fit_genes['diversification_score'] + 
                random.uniform(-0.1, 0.1), 2
            )
            mutations.append('diversification_score')
        
        if mutations:
            mutated.mutation_history.append({
                'generation': self.generation,
                'mutations': mutations,
                'timestamp': datetime.now().isoformat()
            })
            mutated.dna_hash = mutated._calculate_hash()
        
        return mutated
    
    def evolve_generation(self, fitness_results: Dict[str, float]):
        """Evolve one generation."""
        # Update fitness scores
        for genome in self.population:
            if genome.dna_hash in fitness_results:
                genome.fitness_score = fitness_results[genome.dna_hash]
        
        # Sort by fitness
        self.population.sort(key=lambda g: g.fitness_score, reverse=True)
        
        # Track best
        if self.population:
            self.best_genome = self.population[0]
        
        # Create new population
        new_population = []
        
        # Elitism: keep top 10%
        elite_count = max(1, self.population_size // 10)
        new_population.extend(self.population[:elite_count])
        
        # Generate offspring
        while len(new_population) < self.population_size:
            parent1, parent2 = self.select_parents()
            child1, child2 = self.crossover(parent1, parent2)
            
            child1 = self.mutate(child1)
            child2 = self.mutate(child2)
            
            new_population.append(child1)
            if len(new_population) < self.population_size:
                new_population.append(child2)
        
        self.population = new_population[:self.population_size]
        self.generation += 1
        
        # Record history
        self.fitness_history.append({
            'generation': self.generation,
            'best_fitness': self.best_genome.fitness_score if self.best_genome else 0,
            'avg_fitness': np.mean([g.fitness_score for g in self.population]),
            'best_genome': self.best_genome.dna_hash if self.best_genome else None
        })
    
    def run_evolution(self, 
                     backtest_fn,
                     statistical_test_fn,
                     target_fitness: float = 0.85) -> EnhancedGenome:
        """
        Run full evolution process.
        
        Args:
            backtest_fn: Function(genome) -> backtest_results
            statistical_test_fn: Function(results) -> statistical_tests
            target_fitness: Stop when reached
        """
        print(f"\nStarting evolution: {self.max_generations} generations")
        print("="*60)
        
        self.initialize_population()
        
        for gen in range(self.max_generations):
            # Evaluate fitness for each genome
            fitness_results = {}
            
            for genome in self.population:
                try:
                    backtest_results = backtest_fn(genome)
                    statistical_tests = statistical_test_fn(backtest_results)
                    fitness = self.calculate_fitness(backtest_results, statistical_tests)
                    fitness_results[genome.dna_hash] = fitness
                except Exception as e:
                    print(f"Error evaluating {genome.dna_hash}: {e}")
                    fitness_results[genome.dna_hash] = 0.0
            
            # Evolve
            self.evolve_generation(fitness_results)
            
            # Progress report
            if gen % 10 == 0 or gen == self.max_generations - 1:
                print(f"Gen {gen:3d}: Best={self.best_genome.fitness_score:.4f}, "
                      f"Avg={np.mean([g.fitness_score for g in self.population]):.4f}")
            
            # Early stopping
            if self.best_genome and self.best_genome.fitness_score >= target_fitness:
                print(f"\nTarget fitness reached at generation {gen}!")
                break
        
        print("="*60)
        print(f"Evolution complete! Best fitness: {self.best_genome.fitness_score:.4f}")
        
        return self.best_genome
    
    def export_results(self, filepath: str):
        """Export evolution results."""
        data = {
            'evolution_config': {
                'population_size': self.population_size,
                'max_generations': self.max_generations,
                'mutation_rate': self.mutation_rate,
                'crossover_rate': self.crossover_rate,
                'fitness_weights': self.FITNESS_WEIGHTS
            },
            'generations_run': self.generation,
            'fitness_history': self.fitness_history,
            'best_genome': self.best_genome.to_dict() if self.best_genome else None,
            'final_population': [g.to_dict() for g in self.population[:10]]  # Top 10
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"Results exported to {filepath}")


def demo_backtest(genome: EnhancedGenome) -> Dict:
    """Demo backtest function - replace with real backtesting."""
    # Simulate different performance based on genes
    kelly = genome.risk_genes.get('kelly_fraction', 0.25)
    threshold = genome.entry_genes.get('threshold', 0.65)
    diversification = genome.portfolio_fit_genes.get('diversification_score', 0.7)
    
    # Better genes = better simulated results
    base_return = (kelly * 0.5) + ((1 - threshold) * 0.3) + (diversification * 0.2)
    
    return {
        'sharpe': base_return * 3.0 + random.uniform(-0.5, 0.5),
        'max_drawdown': max(0.05, 0.25 - base_return * 0.3),
        'profit_factor': base_return * 4.0 + random.uniform(0.5, 1.5),
        'win_rate': min(0.7, base_return + random.uniform(-0.1, 0.1))
    }


def demo_statistical_tests(backtest_results: Dict) -> Dict:
    """Demo statistical tests - replace with real validation."""
    return {
        'confidence': min(1.0, backtest_results.get('win_rate', 0) * 1.5),
        'p_value': random.uniform(0.001, 0.05)
    }


if __name__ == "__main__":
    print("Enhanced DNA Genome Engine - Demo")
    print("="*60)
    
    # Create and run evolution
    engine = EnhancedDNAEngine(
        population_size=50,      # Demo size
        max_generations=50,      # Demo generations
        mutation_rate=0.10,
        crossover_rate=0.70
    )
    
    best = engine.run_evolution(
        backtest_fn=demo_backtest,
        statistical_test_fn=demo_statistical_tests,
        target_fitness=0.90
    )
    
    print("\n" + "="*60)
    print("BEST GENOME:")
    print("="*60)
    print(f"DNA Hash: {best.dna_hash}")
    print(f"Generation: {best.generation}")
    print(f"Fitness: {best.fitness_score:.4f}")
    print(f"\nEntry Genes: {json.dumps(best.entry_genes, indent=2)}")
    print(f"\nRisk Genes: {json.dumps(best.risk_genes, indent=2)}")
    print(f"\nData Quality Genes: {json.dumps(best.data_quality_genes, indent=2)}")
    print(f"\nRegime Adaptation Genes: {json.dumps(best.regime_adaptation_genes, indent=2)}")
    print(f"\nPortfolio Fit Genes: {json.dumps(best.portfolio_fit_genes, indent=2)}")
    
    # Export
    engine.export_results('genome/enhanced_evolution_results.json')
