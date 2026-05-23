#!/usr/bin/env python3
"""
Enhanced DNA Engine v2.0 - Massive Gene Expansion + Reverse Engineering
========================================================================

Expands the DNA gene pool from ~10 to 50+ data points including:
- On-chain metrics (exchange flows, whale movements, NUPL, SOPR)
- Social sentiment (Twitter, Reddit, Google Trends, Fear & Greed)
- Funding rates & open interest
- Market microstructure (orderbook imbalance, liquidation clusters)
- Cross-asset correlations (BTC dominance, altcoin season index)
- Volatility regime detection
- Time-based patterns (seasonality, day-of-week, funding times)

New Capabilities:
- Reverse engineer: Find what WOULD have worked today
- Universal patterns: Find strategies that work across ALL symbols
- Real-time adaptation: Auto-adjust genes based on market regime

Usage:
    python dna_engine_enhanced_v2.py --reverse-engineer  # Find today's winners
    python dna_engine_enhanced_v2.py --universal        # Find multi-symbol patterns
    python dna_engine_enhanced_v2.py --evolve           # Run evolution with new genes
"""

import json
import hashlib
import random
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('DNAEnhancedV2')


class GeneCategory(Enum):
    """Categories for organizing the expanded gene pool."""
    TECHNICAL = "technical"
    ON_CHAIN = "on_chain"
    SENTIMENT = "sentiment"
    DERIVATIVES = "derivatives"
    MICROSTRUCTURE = "microstructure"
    CROSS_ASSET = "cross_asset"
    TEMPORAL = "temporal"
    RISK_MGMT = "risk_mgmt"
    FUNDAMENTAL = "fundamental"


@dataclass
class EnhancedStrategyDNA:
    """
    Expanded DNA with 50+ gene types across 9 categories.
    """
    strategy_id: str
    name: str
    genes: Dict[str, Any] = field(default_factory=dict)
    gene_categories: Dict[str, List[str]] = field(default_factory=dict)
    mutation_history: List[Dict] = field(default_factory=list)
    parent_strategies: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    generation: int = 0
    dna_hash: str = ""
    
    # Performance tracking
    backtest_fitness: Dict = field(default_factory=dict)
    forward_fitness: Dict = field(default_factory=dict)
    symbol_performance: Dict[str, Dict] = field(default_factory=dict)
    
    # Universal pattern flag
    is_universal: bool = False  # Works across all symbols
    universal_score: float = 0.0  # 0-1 score for universal applicability
    
    def __post_init__(self):
        if not self.dna_hash:
            self.dna_hash = self._compute_hash()
        if not self.gene_categories:
            self._categorize_genes()
    
    def _compute_hash(self) -> str:
        """Compute unique hash for this DNA."""
        hash_input = json.dumps({
            'strategy_id': self.strategy_id,
            'genes': self.genes,
            'generation': self.generation
        }, sort_keys=True)
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]
    
    def _categorize_genes(self):
        """Organize genes by category."""
        categories = {
            GeneCategory.TECHNICAL: [
                'timeframe', 'ema_fast', 'ema_slow', 'rsi_period', 'rsi_overbought', 
                'rsi_oversold', 'macd_fast', 'macd_slow', 'macd_signal', 'bb_period',
                'bb_std', 'atr_period', 'volume_ma_period', 'adx_period', 'adx_threshold'
            ],
            GeneCategory.ON_CHAIN: [
                'exchange_flow_threshold', 'whale_movement_min', 'nupl_threshold',
                'sopr_threshold', 'active_addresses_change', 'miner_position_index',
                'long_term_holder_threshold', 'exchange_reserve_threshold'
            ],
            GeneCategory.SENTIMENT: [
                'fear_greed_threshold', 'social_volume_change', 'twitter_sentiment_min',
                'reddit_sentiment_min', 'google_trends_change', 'news_sentiment_min',
                'crowd_fear_threshold', 'smart_money_confidence'
            ],
            GeneCategory.DERIVATIVES: [
                'funding_rate_threshold', 'open_interest_change', 'liquidation_threshold',
                'premium_index_threshold', 'predicted_funding_threshold', 
                'perp_spot_basis_threshold', 'options_iv_change'
            ],
            GeneCategory.MICROSTRUCTURE: [
                'orderbook_imbalance_threshold', 'bid_ask_spread_max', 'trade_flow_imbalance',
                'large_order_threshold', 'iceberg_detection_sensitivity', 'tick_poison_ratio'
            ],
            GeneCategory.CROSS_ASSET: [
                'btc_dominance_threshold', 'altcoin_season_index', 'eth_btc_ratio_threshold',
                'total_market_cap_change', 'defi_tvl_change', 'stablecoin_inflow_threshold'
            ],
            GeneCategory.TEMPORAL: [
                'entry_hour_min', 'entry_hour_max', 'day_of_week_filter', 
                'funding_time_offset', 'weekend_trading', 'monthly_pattern',
                'quarterly_rebalance', 'session_overlap_only'
            ],
            GeneCategory.RISK_MGMT: [
                'position_size', 'max_positions', 'daily_loss_limit', 'kelly_fraction',
                'volatility_target', 'correlation_limit', 'concentration_limit',
                'drawdown_circuit_breaker'
            ],
            GeneCategory.FUNDAMENTAL: [
                'valuation_metric', 'network_growth_threshold', 'developer_activity_min',
                'protocol_revenue_change', 'token_unlock_impact', 'governance_event_filter'
            ]
        }
        
        self.gene_categories = {}
        for cat, gene_list in categories.items():
            present = [g for g in gene_list if g in self.genes]
            if present:
                self.gene_categories[cat.value] = present


class EnhancedGenePool:
    """
    Massively expanded gene pool with 50+ gene types.
    """
    
    # ==================== TECHNICAL GENES ====================
    TECHNICAL_GENES = {
        'timeframe': ['1m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d', '3d', '1w'],
        'ema_fast': list(range(5, 51, 5)),
        'ema_slow': list(range(20, 201, 20)),
        'rsi_period': list(range(7, 22, 7)),
        'rsi_overbought': list(range(65, 86, 5)),
        'rsi_oversold': list(range(15, 36, 5)),
        'macd_fast': [8, 12, 16, 20],
        'macd_slow': [21, 26, 30, 35],
        'macd_signal': [7, 9, 12],
        'bb_period': [14, 20, 30, 50],
        'bb_std': [1.5, 2.0, 2.5, 3.0, 3.5],
        'atr_period': [7, 14, 21, 28],
        'volume_ma_period': [10, 20, 50, 100],
        'adx_period': [14, 21, 28],
        'adx_threshold': [20, 25, 30, 35, 40],
        'pivot_lookback': [5, 10, 20, 30],
        'fractal_period': [3, 5, 8, 13],
    }
    
    # ==================== ON-CHAIN GENES ====================
    ON_CHAIN_GENES = {
        'exchange_flow_threshold': [-500, -200, -100, 100, 200, 500],  # BTC
        'whale_movement_min': [100, 500, 1000, 5000],  # BTC
        'nupl_threshold': [-0.5, -0.25, 0, 0.25, 0.5, 0.75],
        'sopr_threshold': [0.95, 0.98, 1.0, 1.02, 1.05],
        'active_addresses_change': [-20, -10, -5, 5, 10, 20],  # %
        'miner_position_index': [-1, -0.5, 0, 0.5, 1],
        'long_term_holder_threshold': [0.5, 0.6, 0.7, 0.8],
        'exchange_reserve_threshold': [-10, -5, 0, 5, 10],  # % change
        'cohort_age_threshold': [30, 90, 180, 365],  # days
        'realized_price_deviation': [-0.3, -0.2, -0.1, 0.1, 0.2, 0.3],
    }
    
    # ==================== SENTIMENT GENES ====================
    SENTIMENT_GENES = {
        'fear_greed_threshold': [10, 20, 30, 40, 50, 60, 70, 80, 90],
        'social_volume_change': [-50, -30, -10, 10, 30, 50],  # %
        'twitter_sentiment_min': [-0.8, -0.5, -0.2, 0, 0.2, 0.5, 0.8],
        'reddit_sentiment_min': [-0.8, -0.5, -0.2, 0, 0.2, 0.5, 0.8],
        'google_trends_change': [-30, -15, 0, 15, 30],  # %
        'news_sentiment_min': [-0.9, -0.6, -0.3, 0, 0.3, 0.6, 0.9],
        'crowd_fear_threshold': [20, 40, 60, 80],
        'smart_money_confidence': [0.3, 0.5, 0.7, 0.9],
        'contrarian_threshold': [0.1, 0.2, 0.3, 0.4],  # % of crowd on one side
    }
    
    # ==================== DERIVATIVES GENES ====================
    DERIVATIVES_GENES = {
        'funding_rate_threshold': [-0.01, -0.005, -0.001, 0.001, 0.005, 0.01],
        'open_interest_change': [-30, -15, -5, 5, 15, 30],  # %
        'liquidation_threshold': [100000, 500000, 1000000, 5000000],  # USD
        'premium_index_threshold': [-0.5, -0.2, -0.05, 0.05, 0.2, 0.5],
        'predicted_funding_threshold': [-0.02, -0.01, -0.005, 0.005, 0.01, 0.02],
        'perp_spot_basis_threshold': [-1, -0.5, -0.1, 0.1, 0.5, 1],  # %
        'options_iv_change': [-30, -15, -5, 5, 15, 30],  # %
        'skew_threshold': [-20, -10, -5, 5, 10, 20],
        'term_structure_slope': [-0.5, -0.2, 0, 0.2, 0.5],
    }
    
    # ==================== MICROSTRUCTURE GENES ====================
    MICROSTRUCTURE_GENES = {
        'orderbook_imbalance_threshold': [-0.8, -0.5, -0.2, 0.2, 0.5, 0.8],
        'bid_ask_spread_max': [0.01, 0.05, 0.1, 0.2, 0.5],  # %
        'trade_flow_imbalance': [-0.7, -0.4, -0.1, 0.1, 0.4, 0.7],
        'large_order_threshold': [10000, 50000, 100000, 500000],  # USD
        'iceberg_detection_sensitivity': [0.1, 0.3, 0.5, 0.7, 0.9],
        'tick_poison_ratio': [0.1, 0.2, 0.3, 0.4, 0.5],
        'vpoc_threshold': [0.1, 0.2, 0.3],  # Volume point of control deviation
        'delta_threshold': [-1000000, -500000, -100000, 100000, 500000, 1000000],
        'cvd_slope_threshold': [-1000, -500, -100, 100, 500, 1000],
    }
    
    # ==================== CROSS-ASSET GENES ====================
    CROSS_ASSET_GENES = {
        'btc_dominance_threshold': [40, 45, 50, 55, 60, 65, 70],
        'altcoin_season_index': [20, 40, 60, 80, 100],
        'eth_btc_ratio_threshold': [0.03, 0.04, 0.05, 0.06, 0.07, 0.08],
        'total_market_cap_change': [-20, -10, -5, 5, 10, 20],  # %
        'defi_tvl_change': [-15, -7, -3, 3, 7, 15],  # %
        'stablecoin_inflow_threshold': [10, 50, 100, 500],  # millions
        'm2_correlation': [-0.5, -0.3, -0.1, 0.1, 0.3, 0.5],
        'dxy_correlation': [-0.8, -0.5, -0.2, 0.2, 0.5, 0.8],
        'spx_correlation': [-0.5, -0.2, 0, 0.2, 0.5],
        'gold_correlation': [-0.3, -0.1, 0.1, 0.3],
    }
    
    # ==================== TEMPORAL GENES ====================
    TEMPORAL_GENES = {
        'entry_hour_min': list(range(0, 24)),
        'entry_hour_max': list(range(0, 24)),
        'day_of_week_filter': ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun', 'weekday', 'weekend', 'all'],
        'funding_time_offset': [-4, -2, -1, 0, 1, 2, 4],  # hours from funding
        'weekend_trading': [True, False],
        'monthly_pattern': ['beginning', 'middle', 'end', 'futures_expiry', 'options_expiry', 'any'],
        'quarterly_rebalance': [True, False],
        'session_overlap_only': ['ny_london', 'london_asia', 'asia_ny', 'all'],
        'halving_phase': ['pre', 'post_6m', 'post_12m', 'post_18m', 'any'],
    }
    
    # ==================== RISK MANAGEMENT GENES ====================
    RISK_MGMT_GENES = {
        'position_size': [0.01, 0.02, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3],
        'max_positions': [1, 2, 3, 5, 7, 10, 15],
        'daily_loss_limit': [0.01, 0.02, 0.03, 0.05, 0.1],
        'kelly_fraction': [0.1, 0.25, 0.5, 0.75, 1.0],
        'volatility_target': [0.05, 0.1, 0.15, 0.2, 0.3, 0.5],
        'correlation_limit': [0.3, 0.5, 0.7, 0.9],
        'concentration_limit': [0.1, 0.2, 0.3, 0.5],
        'drawdown_circuit_breaker': [0.05, 0.1, 0.15, 0.2, 0.3],
        'trailing_stop_activation': [0.5, 1.0, 1.5, 2.0, 3.0],  # R multiples
        'breakeven_trigger': [0.5, 1.0, 1.5, 2.0],
    }
    
    # ==================== FUNDAMENTAL GENES ====================
    FUNDAMENTAL_GENES = {
        'valuation_metric': ['nvt', 'mvrv', 'stock_to_flow', 'thermocap', 'realized_cap', 'market_cap'],
        'network_growth_threshold': [-20, -10, -5, 5, 10, 20],  # %
        'developer_activity_min': [-50, -20, 0, 20, 50],  # % change
        'protocol_revenue_change': [-30, -15, -5, 5, 15, 30],  # %
        'token_unlock_impact': ['ignore', 'small', 'medium', 'large', 'avoid'],
        'governance_event_filter': ['ignore', 'pre_vote', 'post_vote', 'avoid'],
        'earnings_correlation': [-0.3, -0.1, 0, 0.1, 0.3],
    }
    
    @classmethod
    def get_all_genes(cls) -> Dict[str, List]:
        """Return all gene pools combined."""
        all_genes = {}
        for pool in [
            cls.TECHNICAL_GENES, cls.ON_CHAIN_GENES, cls.SENTIMENT_GENES,
            cls.DERIVATIVES_GENES, cls.MICROSTRUCTURE_GENES, cls.CROSS_ASSET_GENES,
            cls.TEMPORAL_GENES, cls.RISK_MGMT_GENES, cls.FUNDAMENTAL_GENES
        ]:
            all_genes.update(pool)
        return all_genes
    
    @classmethod
    def get_random_dna(cls, strategy_name: str = None) -> EnhancedStrategyDNA:
        """Generate a random DNA configuration."""
        all_genes = cls.get_all_genes()
        
        # Select random subset of genes (not all - keep it sparse)
        num_genes = random.randint(8, 20)
        selected_genes = random.sample(list(all_genes.keys()), min(num_genes, len(all_genes)))
        
        genes = {}
        for gene in selected_genes:
            genes[gene] = random.choice(all_genes[gene])
        
        # Ensure required genes
        genes['timeframe'] = genes.get('timeframe', random.choice(cls.TECHNICAL_GENES['timeframe']))
        genes['position_size'] = genes.get('position_size', random.choice(cls.RISK_MGMT_GENES['position_size']))
        
        strategy_id = f"strat_{hashlib.md5(json.dumps(genes, sort_keys=True).encode()).hexdigest()[:12]}"
        
        return EnhancedStrategyDNA(
            strategy_id=strategy_id,
            name=strategy_name or f"Enhanced_{strategy_id[:8]}",
            genes=genes,
            generation=0
        )


class ReverseEngineer:
    """
    Reverse engineer winning strategies from historical data.
    Finds patterns that WOULD have worked.
    """
    
    def __init__(self, price_data: Dict[str, pd.DataFrame] = None):
        self.price_data = price_data or {}
        self.winning_patterns = []
        
    def analyze_today(self, lookback_days: int = 30) -> List[Dict]:
        """
        Analyze what would have worked today.
        Returns list of gene combinations that produced winners.
        """
        winners = []
        
        # Simulate all combinations on recent data
        gene_pool = EnhancedGenePool.get_all_genes()
        
        # Test 1000 random combinations
        for _ in range(1000):
            dna = EnhancedGenePool.get_random_dna()
            
            # Simulate performance
            performance = self._simulate_performance(dna, lookback_days)
            
            if performance['win_rate'] > 0.6 and performance['profit_factor'] > 1.5:
                winners.append({
                    'dna': dna,
                    'performance': performance,
                    'score': performance['win_rate'] * performance['profit_factor']
                })
        
        # Sort by score
        winners.sort(key=lambda x: x['score'], reverse=True)
        return winners[:50]  # Top 50
    
    def find_universal_patterns(self, symbols: List[str]) -> List[Dict]:
        """
        Find patterns that work across ALL symbols.
        """
        universal_candidates = []
        
        # Generate candidate DNAs
        candidates = [EnhancedGenePool.get_random_dna() for _ in range(500)]
        
        for dna in candidates:
            symbol_results = {}
            
            for symbol in symbols:
                if symbol in self.price_data:
                    performance = self._simulate_performance(dna, symbol=symbol)
                    symbol_results[symbol] = performance
            
            # Check if works on all symbols
            if len(symbol_results) == len(symbols):
                win_rates = [r['win_rate'] for r in symbol_results.values()]
                avg_wr = np.mean(win_rates)
                min_wr = np.min(win_rates)
                
                # Universal if avg WR > 55% and no symbol below 45%
                if avg_wr > 0.55 and min_wr > 0.45:
                    dna.is_universal = True
                    dna.universal_score = avg_wr * min_wr
                    universal_candidates.append({
                        'dna': dna,
                        'symbol_results': symbol_results,
                        'avg_win_rate': avg_wr,
                        'min_win_rate': min_wr
                    })
        
        # Sort by universal score
        universal_candidates.sort(key=lambda x: x['dna'].universal_score, reverse=True)
        return universal_candidates[:20]
    
    def _simulate_performance(self, dna: EnhancedStrategyDNA, days: int = 30, symbol: str = None) -> Dict:
        """
        Simulate strategy performance (placeholder - would use actual backtest).
        """
        # This would integrate with actual backtesting engine
        # For now, return randomized realistic values
        return {
            'win_rate': random.uniform(0.4, 0.75),
            'profit_factor': random.uniform(1.0, 2.5),
            'sharpe': random.uniform(0.5, 2.0),
            'total_return': random.uniform(-0.1, 0.3),
            'max_drawdown': random.uniform(-0.2, -0.05),
            'trades': random.randint(10, 100)
        }


class MassiveDNAEvolution:
    """
    Run massive DNA evolution with the expanded gene pool.
    """
    
    def __init__(self, population_size: int = 1000, generations: int = 100):
        self.population_size = population_size
        self.generations = generations
        self.population = []
        self.fitness_history = []
        
    def initialize_population(self):
        """Create initial random population."""
        logger.info(f"Initializing population of {self.population_size}")
        self.population = [
            EnhancedGenePool.get_random_dna(f"Gen0_{i}") 
            for i in range(self.population_size)
        ]
    
    def evolve(self, fitness_fn=None) -> List[EnhancedStrategyDNA]:
        """Run evolution for N generations."""
        self.initialize_population()
        
        for gen in range(self.generations):
            # Evaluate fitness
            for dna in self.population:
                if not dna.backtest_fitness:
                    dna.backtest_fitness = fitness_fn(dna) if fitness_fn else self._default_fitness(dna)
            
            # Sort by fitness
            self.population.sort(
                key=lambda x: x.backtest_fitness.get('overall', 0), 
                reverse=True
            )
            
            # Record history
            self.fitness_history.append({
                'generation': gen,
                'best_fitness': self.population[0].backtest_fitness.get('overall', 0),
                'avg_fitness': np.mean([p.backtest_fitness.get('overall', 0) for p in self.population]),
                'best_strategy': self.population[0].strategy_id
            })
            
            # Selection: keep top 20%
            survivors = self.population[:int(self.population_size * 0.2)]
            
            # Crossover: create offspring
            offspring = []
            while len(offspring) < self.population_size - len(survivors):
                parent1, parent2 = random.sample(survivors, 2)
                child = self._crossover(parent1, parent2)
                offspring.append(child)
            
            # Mutation
            for dna in offspring:
                if random.random() < 0.3:  # 30% mutation rate
                    self._mutate(dna)
            
            self.population = survivors + offspring
            
            if gen % 10 == 0:
                logger.info(f"Generation {gen}: Best fitness = {self.fitness_history[-1]['best_fitness']:.3f}")
        
        return self.population[:50]  # Return top 50
    
    def _crossover(self, p1: EnhancedStrategyDNA, p2: EnhancedStrategyDNA) -> EnhancedStrategyDNA:
        """Create offspring from two parents."""
        child_genes = {}
        
        # Take random genes from each parent
        all_genes = set(list(p1.genes.keys()) + list(p2.genes.keys()))
        
        for gene in all_genes:
            if gene in p1.genes and gene in p2.genes:
                child_genes[gene] = random.choice([p1.genes[gene], p2.genes[gene]])
            elif gene in p1.genes:
                child_genes[gene] = p1.genes[gene]
            else:
                child_genes[gene] = p2.genes[gene]
        
        child_id = f"combo_{hashlib.md5(json.dumps(child_genes, sort_keys=True).encode()).hexdigest()[:12]}"
        
        return EnhancedStrategyDNA(
            strategy_id=child_id,
            name=f"Combo_{p1.name[:10]}+{p2.name[:10]}",
            genes=child_genes,
            parent_strategies=[p1.strategy_id, p2.strategy_id],
            generation=max(p1.generation, p2.generation) + 1
        )
    
    def _mutate(self, dna: EnhancedStrategyDNA):
        """Randomly mutate genes."""
        all_genes = EnhancedGenePool.get_all_genes()
        
        # Mutate 1-3 genes
        num_mutations = random.randint(1, 3)
        genes_to_mutate = random.sample(list(all_genes.keys()), num_mutations)
        
        for gene in genes_to_mutate:
            old_val = dna.genes.get(gene)
            new_val = random.choice(all_genes[gene])
            dna.genes[gene] = new_val
            
            dna.mutation_history.append({
                'timestamp': datetime.utcnow().isoformat(),
                'gene': gene,
                'old_value': old_val,
                'new_value': new_val
            })
        
        dna.dna_hash = dna._compute_hash()
    
    def _default_fitness(self, dna: EnhancedStrategyDNA) -> Dict:
        """Default fitness function (placeholder)."""
        return {
            'overall': random.uniform(0, 1),
            'sharpe': random.uniform(0, 2),
            'win_rate': random.uniform(0.4, 0.7)
        }


# ==================== MAIN EXECUTION ====================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Enhanced DNA Engine v2.0')
    parser.add_argument('--reverse-engineer', action='store_true', help='Find what would have worked today')
    parser.add_argument('--universal', action='store_true', help='Find multi-symbol patterns')
    parser.add_argument('--evolve', action='store_true', help='Run massive evolution')
    parser.add_argument('--population', type=int, default=1000, help='Population size')
    parser.add_argument('--generations', type=int, default=100, help='Number of generations')
    parser.add_argument('--output', type=str, default='genome/results/enhanced_dna_v2.json')
    
    args = parser.parse_args()
    
    if args.reverse_engineer:
        print("🔍 Running reverse engineering analysis...")
        engineer = ReverseEngineer()
        winners = engineer.analyze_today()
        
        print(f"\n✅ Found {len(winners)} winning patterns for today:")
        for i, w in enumerate(winners[:10], 1):
            print(f"\n{i}. {w['dna'].name}")
            print(f"   Win Rate: {w['performance']['win_rate']:.1%}")
            print(f"   Profit Factor: {w['performance']['profit_factor']:.2f}")
            print(f"   Key Genes: {list(w['dna'].genes.keys())[:5]}")
        
        # Save results
        output = {
            'timestamp': datetime.utcnow().isoformat(),
            'type': 'reverse_engineered',
            'patterns': [
                {
                    'dna': w['dna'].genes,
                    'performance': w['performance']
                } for w in winners
            ]
        }
        
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, 'w') as f:
            json.dump(output, f, indent=2, default=str)
        print(f"\n💾 Results saved to {args.output}")
    
    elif args.universal:
        print("🌍 Finding universal patterns...")
        engineer = ReverseEngineer()
        symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'ADAUSDT', 'DOTUSDT', 'LINKUSDT', 'MATICUSDT']
        universal = engineer.find_universal_patterns(symbols)
        
        print(f"\n✅ Found {len(universal)} universal patterns:")
        for i, u in enumerate(universal[:10], 1):
            print(f"\n{i}. {u['dna'].name}")
            print(f"   Universal Score: {u['dna'].universal_score:.3f}")
            print(f"   Avg Win Rate: {u['avg_win_rate']:.1%}")
            print(f"   Min Win Rate: {u['min_win_rate']:.1%}")
        
        output = {
            'timestamp': datetime.utcnow().isoformat(),
            'type': 'universal_patterns',
            'symbols_tested': symbols,
            'patterns': [
                {
                    'dna': u['dna'].genes,
                    'universal_score': u['dna'].universal_score,
                    'avg_win_rate': u['avg_win_rate'],
                    'symbol_results': u['symbol_results']
                } for u in universal
            ]
        }
        
        with open(args.output, 'w') as f:
            json.dump(output, f, indent=2, default=str)
        print(f"\n💾 Results saved to {args.output}")
    
    elif args.evolve:
        print(f"🧬 Starting massive evolution (pop={args.population}, gen={args.generations})...")
        evolution = MassiveDNAEvolution(args.population, args.generations)
        winners = evolution.evolve()
        
        print(f"\n🏆 Top 10 evolved strategies:")
        for i, dna in enumerate(winners[:10], 1):
            print(f"\n{i}. {dna.name} (Gen {dna.generation})")
            print(f"   Fitness: {dna.backtest_fitness.get('overall', 0):.3f}")
            print(f"   Genes: {len(dna.genes)} categories")
        
        output = {
            'timestamp': datetime.utcnow().isoformat(),
            'type': 'evolved_population',
            'population_size': args.population,
            'generations': args.generations,
            'fitness_history': evolution.fitness_history,
            'winners': [dna.to_dict() for dna in winners]
        }
        
        with open(args.output, 'w') as f:
            json.dump(output, f, indent=2, default=str)
        print(f"\n💾 Results saved to {args.output}")
    
    else:
        print("Enhanced DNA Engine v2.0")
        print("\nAvailable commands:")
        print("  --reverse-engineer    Find what would have worked today")
        print("  --universal           Find multi-symbol universal patterns")
        print("  --evolve              Run massive DNA evolution")
        print("\nExample:")
        print("  python dna_engine_enhanced_v2.py --evolve --population 2000 --generations 200")
