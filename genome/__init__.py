"""
DNA-Based Strategy Permutation Engine
======================================

A genetic algorithm system for crypto trading strategy evolution and combination.

This package provides:
- StrategyDNA: Genetic representation of trading strategies
- DNAPermutationEngine: Core engine for combining and evolving strategies
- DNABacktester: Walk-forward backtesting with Phoenix revival
- StrategyRegistry: Central SQLite registry for strategies and signals

Quick Start:
    from genome import DNAPermutationEngine, StrategyDNA, create_strategy_dna
    
    # Create strategies
    s1 = create_strategy_dna("EMA Cross", timeframe="1h", primary_indicator="EMA")
    s2 = create_strategy_dna("RSI Reversion", timeframe="1h", primary_indicator="RSI")
    
    # Combine
    engine = DNAPermutationEngine()
    combo = engine.combine_dna([s1, s2])
    
    # Generate all permutations
    perms = engine.generate_all_permutations([s1, s2, s3], max_combo_size=3)
"""

__version__ = "1.0.0"
__author__ = "findtorontoevents.ca"

from .dna_engine import (
    StrategyDNA,
    DNAPermutationEngine,
    FitnessScore,
    CombinationLogic,
    MarketRegime,
    RiskProfile,
    create_strategy_dna
)

try:
    from .dna_backtester import (
        DNABacktester,
        BacktestResult,
        Trade,
        PhoenixRevivalTracker,
        WalkForwardTester
    )
except ImportError:
    # dna_backtester requires pandas — skip if not available
    DNABacktester = None
    BacktestResult = None
    Trade = None
    PhoenixRevivalTracker = None
    WalkForwardTester = None

from .strategy_registry import (
    StrategyRegistry,
    StrategyRecord,
    PermutationRecord,
    BacktestRecord,
    LiveSignalRecord
)

__all__ = [
    # Core DNA
    'StrategyDNA',
    'DNAPermutationEngine',
    'FitnessScore',
    'CombinationLogic',
    'MarketRegime',
    'RiskProfile',
    'create_strategy_dna',
    
    # Backtesting
    'DNABacktester',
    'BacktestResult',
    'Trade',
    'PhoenixRevivalTracker',
    'WalkForwardTester',
    
    # Registry
    'StrategyRegistry',
    'StrategyRecord',
    'PermutationRecord',
    'BacktestRecord',
    'LiveSignalRecord'
]
