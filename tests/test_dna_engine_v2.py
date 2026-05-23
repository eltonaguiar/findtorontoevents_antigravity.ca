"""Tests for DNA Engine v2 features: adaptive mutation, NSGA-II fitness, island model."""
import importlib.util
import sys
import os
import numpy as np

# Load modules directly to avoid genome/__init__.py pandas import
def _load_module(name, rel_path):
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    spec = importlib.util.spec_from_file_location(name, os.path.join(base, rel_path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

dna_engine = _load_module("genome.dna_engine", "genome/dna_engine.py")
seed_strategies = _load_module("genome.seed_strategies", "genome/seed_strategies.py")

DNAPermutationEngine = dna_engine.DNAPermutationEngine
StrategyDNA = dna_engine.StrategyDNA
create_strategy_dna = dna_engine.create_strategy_dna
FitnessScore = dna_engine.FitnessScore
IslandModel = dna_engine.IslandModel
adaptive_mutation_rate = dna_engine.adaptive_mutation_rate
get_all_island_seeds = seed_strategies.get_all_island_seeds

# --- Adaptive Mutation Rate ---

def test_adaptive_rate_ramps_on_stagnation():
    rate_normal = adaptive_mutation_rate(generation=5, stagnation_count=0)
    rate_stagnant = adaptive_mutation_rate(generation=5, stagnation_count=8)
    assert rate_stagnant > rate_normal
    assert rate_stagnant <= 0.25

def test_adaptive_rate_decays_on_progress():
    rate_early = adaptive_mutation_rate(generation=1, stagnation_count=0)
    rate_late = adaptive_mutation_rate(generation=50, stagnation_count=0)
    assert rate_late < rate_early
    assert rate_late >= 0.005

def test_adaptive_rate_never_exceeds_cap():
    rate = adaptive_mutation_rate(generation=0, stagnation_count=100)
    assert rate <= 0.25

# --- FitnessScore.to_objectives ---

def test_fitness_returns_three_objectives():
    fs = FitnessScore(
        sharpe_ratio=1.5, win_rate=0.6, profit_factor=2.0,
        max_drawdown=-0.15, total_return=0.3, volatility=0.1,
        calmar_ratio=2.0, sortino_ratio=1.8, omega_ratio=1.5,
        overall_fitness=0.0, risk_adjusted_fitness=0.0,
        trade_count=50,
    )
    objs = fs.to_objectives()
    assert len(objs) == 3
    assert objs[0] == 1.5  # sharpe
    assert objs[1] == 0.15  # abs(max_drawdown)
    assert abs(objs[2] - 0.6 * np.sqrt(50)) < 0.01

# --- Island Model ---

def test_island_model_creates_4_islands():
    model = IslandModel(seeds=get_all_island_seeds(), island_size=15)
    assert len(model.islands) == 4

def test_island_model_fills_to_target_size():
    model = IslandModel(seeds=get_all_island_seeds(), island_size=15)
    for name, island in model.islands.items():
        assert len(island["population"]) == 15

def test_island_migration_transfers_strategies():
    model = IslandModel(seeds=get_all_island_seeds(), island_size=10)
    bear_ids_before = {s.strategy_id for s in model.islands["bear"]["population"]}
    model.migrate(n_migrants=2)
    bull_ids_after = {s.strategy_id for s in model.islands["bull"]["population"]}
    overlap = bear_ids_before & bull_ids_after
    assert len(overlap) >= 1

# --- Biased Mutation ---

def test_mutate_dna_with_onchain_bias():
    engine = DNAPermutationEngine()
    dna = create_strategy_dna(
        name="test", timeframe="4h", primary_indicator="RSI",
        entry_logic="rsi_oversold", exit_logic="take_profit",
        risk_profile="moderate",
    )
    bias = {"entry_direction": "long"}
    long_count = 0
    for _ in range(20):
        mutated = engine.mutate_dna(dna, mutation_rate=1.0, bias=bias)
        el = mutated.genes.get("entry_logic", "")
        if any(x in el for x in ["golden_cross", "support_bounce", "rsi_oversold",
                                   "momentum", "breakout", "macd_crossover"]):
            long_count += 1
    assert long_count >= 8
