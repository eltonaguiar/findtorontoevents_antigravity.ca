#!/usr/bin/env python3
"""
Strategy Evolution Script — Island-model genetic optimizer
=========================

Runs genetic algorithm evolution on strategy population.
Designed for scheduled execution (GitHub Actions, cron).

Usage:
    python genome/evolve_strategies.py
    python genome/evolve_strategies.py --generations 20 --population 100
    python genome/evolve_strategies.py --symbol BTC --mutate-best
"""

import argparse
import json
import logging
import sys
import random
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

from genome.dna_engine import (
    DNAPermutationEngine,
    StrategyDNA,
    FitnessScore,
    MarketRegime,
    create_strategy_dna,
    IslandModel,
    adaptive_mutation_rate,
)
from genome.strategy_registry import StrategyRegistry
from genome.seed_strategies import get_all_island_seeds
from genome.onchain_data import OnchainDataFetcher

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('EvolveStrategies')


def load_population(registry: StrategyRegistry, symbol: str = None, min_sharpe: float = 0.5) -> List[Tuple[StrategyDNA, FitnessScore]]:
    """Load existing strategies as initial population."""
    strategies = registry.list_strategies(
        status='active',
        symbol=symbol,
        min_sharpe=min_sharpe,
        limit=100
    )
    
    population = []
    for strategy in strategies:
        # Get latest performance
        perf = registry.get_strategy_performance(strategy.strategy_id, symbol)
        if perf:
            latest = perf[0]
            fitness = FitnessScore(
                sharpe_ratio=latest.get('sharpe_ratio', 0),
                win_rate=latest.get('win_rate', 0),
                profit_factor=latest.get('profit_factor', 0),
                max_drawdown=latest.get('max_drawdown_pct', 0),
                total_return=latest.get('total_return_pct', 0)
            )
            fitness._compute_composite_scores()
        else:
            # Default fitness for new strategies
            fitness = FitnessScore(overall_fitness=0.5, risk_adjusted_fitness=0.5)
        
        population.append((strategy, fitness))
    
    logger.info(f"Loaded {len(population)} strategies for evolution")
    return population


def evolve(
    initial_population: List[Tuple[StrategyDNA, FitnessScore]] = None,
    generations: int = 10,
    population_size: int = 50,
    mutation_rate: float = 0.1,
    elite_ratio: float = 0.1,
    seed: int = None,
    use_islands: bool = False,
    use_onchain: bool = False,
) -> Tuple[List[StrategyDNA], List[dict]]:
    """Run genetic algorithm evolution.

    When *use_islands* is True the 4-island model is used (bear/bull/range/recent)
    with adaptive mutation rates and optional on-chain bias.  Otherwise the legacy
    single-population path is taken.
    """
    engine = DNAPermutationEngine(seed=seed)

    # ── Legacy path (unchanged) ──────────────────────────────────────
    if not use_islands:
        if initial_population is None:
            initial_population = []
        final_pop, history = engine.evolve_population(
            initial_population,
            generations=generations,
            population_size=population_size,
            mutation_rate=mutation_rate,
            elite_ratio=elite_ratio,
        )
        return final_pop, history

    # ── Island-model path ────────────────────────────────────────────
    seeds = get_all_island_seeds()
    island_size = max(population_size // 4, 4)
    island_model = IslandModel(seeds=seeds, island_size=island_size, engine=engine)

    # Optional on-chain bias
    onchain_bias: dict = {}
    if use_onchain:
        try:
            genes = OnchainDataFetcher().get_all_genes()
            onchain_bias = OnchainDataFetcher.get_mutation_bias(genes)
            logger.info(f"On-chain bias: {onchain_bias}")
        except Exception as exc:
            logger.warning(f"On-chain fetch failed, continuing without bias: {exc}")

    history: List[dict] = []

    for gen in range(generations):
        gen_record = {"generation": gen, "islands": {}}

        for name, island in island_model.islands.items():
            pop = island["population"]
            rate = adaptive_mutation_rate(gen, island["stagnation_count"], base_rate=mutation_rate)

            # Mutate non-elite members
            n_elite = max(1, int(len(pop) * elite_ratio))
            new_pop = pop[:n_elite]  # keep elites
            for dna in pop[n_elite:]:
                mutant = engine.mutate_dna(dna, mutation_rate=rate, bias=onchain_bias or None)
                new_pop.append(mutant)

            island["population"] = new_pop

            # Track stagnation via best-fitness proxy (gene diversity)
            prev_best = island["fitness_history"][-1] if island["fitness_history"] else 0.0
            # Use a simple hash-based diversity score as fitness proxy
            diversity = len({d.dna_hash for d in new_pop if hasattr(d, "dna_hash")})
            current_best = diversity / max(len(new_pop), 1)
            island["fitness_history"].append(current_best)

            if current_best <= prev_best:
                island["stagnation_count"] += 1
            else:
                island["stagnation_count"] = 0

            gen_record["islands"][name] = {
                "size": len(new_pop),
                "mutation_rate": round(rate, 5),
                "stagnation": island["stagnation_count"],
            }

        # Migrate every 10 generations
        if gen > 0 and gen % 10 == 0:
            island_model.migrate()
            logger.info(f"Generation {gen}: migration complete")

        history.append(gen_record)

    # Merge all island populations
    final_pop: List[StrategyDNA] = []
    for island in island_model.islands.values():
        final_pop.extend(island["population"])

    logger.info(f"Island evolution complete: {len(final_pop)} strategies across {len(island_model.islands)} islands")
    return final_pop, history


def save_evolution_results(
    population: List[StrategyDNA],
    history: List[dict],
    registry: StrategyRegistry,
    output_dir: str = "genome/results"
):
    """Save evolution results."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    
    # Save evolved strategies
    evolved_data = {
        'timestamp': datetime.utcnow().isoformat(),
        'count': len(population),
        'strategies': [s.to_dict() for s in population]
    }
    
    output_file = Path(output_dir) / f"evolved_population_{timestamp}.json"
    with open(output_file, 'w') as f:
        json.dump(evolved_data, f, indent=2)
    
    # Save evolution history
    history_file = Path(output_dir) / f"evolution_history_{timestamp}.json"
    with open(history_file, 'w') as f:
        json.dump({
            'timestamp': datetime.utcnow().isoformat(),
            'history': history
        }, f, indent=2)
    
    # Register new strategies
    registry.auto_register_strategies(population)
    
    logger.info(f"Evolution results saved to {output_dir}")
    return output_file, history_file


def main():
    parser = argparse.ArgumentParser(description='Evolve strategy population using genetic algorithm')
    parser.add_argument('--generations', type=int, default=10, help='Number of generations')
    parser.add_argument('--population', type=int, default=50, help='Population size')
    parser.add_argument('--mutation-rate', type=float, default=0.1, help='Mutation rate (0-1)')
    parser.add_argument('--elite-ratio', type=float, default=0.1, help='Elite preservation ratio')
    parser.add_argument('--symbol', type=str, default=None, help='Symbol to specialize for')
    parser.add_argument('--seed', type=int, default=None, help='Random seed for reproducibility')
    parser.add_argument('--output-dir', type=str, default='genome/results', help='Output directory')
    parser.add_argument('--islands', type=int, default=0, help='Number of islands (0=legacy, 4=island mode)')
    parser.add_argument('--onchain', action='store_true', help='Fetch real on-chain data for mutation bias')

    args = parser.parse_args()
    
    logger.info(f"Starting evolution: {args.generations} generations, population {args.population}")
    
    # Initialize registry
    registry = StrategyRegistry()
    
    # Load initial population
    initial_pop = load_population(registry, args.symbol)
    
    if len(initial_pop) < 5:
        logger.warning("Too few strategies, adding synthetic ones")
        # Add some synthetic strategies
        for i in range(5 - len(initial_pop)):
            s = create_strategy_dna(f"Synthetic_{i}", timeframe=random.choice(['1h', '4h']))
            initial_pop.append((s, FitnessScore(overall_fitness=0.5)))
    
    # Run evolution
    final_pop, history = evolve(
        initial_pop,
        generations=args.generations,
        population_size=args.population,
        mutation_rate=args.mutation_rate,
        elite_ratio=args.elite_ratio,
        seed=args.seed,
        use_islands=args.islands >= 4,
        use_onchain=args.onchain,
    )
    
    # Save results
    output_file, history_file = save_evolution_results(
        final_pop, history, registry, args.output_dir
    )
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"Evolution Complete")
    print(f"{'='*60}")
    print(f"Generations: {len(history)}")
    if history:
        # best_fitness may not exist in island-based evolution records
        if 'best_fitness' in history[0]:
            print(f"Initial best fitness: {history[0]['best_fitness']:.4f}")
            print(f"Final best fitness: {history[-1]['best_fitness']:.4f}")
            print(f"Improvement: {(history[-1]['best_fitness'] - history[0]['best_fitness']):.4f}")
        else:
            print(f"Island evolution mode — {len(history[0].get('islands', {}))} islands tracked")
    print(f"Final population: {len(final_pop)}")
    print(f"Results saved: {output_file}")
    print(f"{'='*60}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
