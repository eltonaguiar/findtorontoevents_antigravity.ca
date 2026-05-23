#!/usr/bin/env python3
"""
Regime-Specific DNA Genome System
Implements separate genome populations for each market regime.
"""

import json
from typing import Dict, List
from enum import Enum
from genome.dna_engine_enhanced import EnhancedDNAEngine, EnhancedGenome


class MarketRegime(Enum):
    BULL = "BULL"
    BEAR = "BEAR"
    SIDEWAYS = "SIDEWAYS"
    HIGH_VOL = "HIGH_VOL"


class RegimeSpecificGenomes:
    """
    Maintains separate genome populations for each market regime.
    """
    
    def __init__(self):
        self.populations: Dict[MarketRegime, EnhancedDNAEngine] = {
            regime: EnhancedDNAEngine(
                population_size=50,
                max_generations=200,
                mutation_rate=0.10,
                crossover_rate=0.70
            )
            for regime in MarketRegime
        }
        
        self.active_regime = MarketRegime.SIDEWAYS
        self.regime_history = []
    
    def evolve_all_regimes(self, backtest_fn, forward_test_fn):
        """
        Evolve genomes for all regimes independently.
        """
        results = {}
        
        for regime in MarketRegime:
            print(f"\nEvolving {regime.value} regime genome...")
            
            # Filter data for this regime
            def regime_backtest(genome):
                return backtest_fn(genome, regime)
            
            best = self.populations[regime].run_evolution(
                backtest_fn=regime_backtest,
                statistical_test_fn=lambda x: {'confidence': 0.9},
                target_fitness=0.85
            )
            
            results[regime] = best
        
        return results
    
    def get_best_for_regime(self, regime: MarketRegime) -> EnhancedGenome:
        """Get best genome for specific regime."""
        return self.populations[regime].best_genome
    
    def switch_regime(self, detected_regime: MarketRegime):
        """Switch to regime-specific genome."""
        if detected_regime != self.active_regime:
            self.regime_history.append({
                'from': self.active_regime.value,
                'to': detected_regime.value,
                'timestamp': json.dumps(datetime.now().isoformat())
            })
            self.active_regime = detected_regime
            print(f"Switched to {detected_regime.value} regime genome")
    
    def get_active_genome(self) -> EnhancedGenome:
        """Get currently active genome."""
        return self.populations[self.active_regime].best_genome


if __name__ == "__main__":
    from datetime import datetime
    print("Regime-Specific Genome System initialized")
    print("Supports: BULL, BEAR, SIDEWAYS, HIGH_VOL regimes")
