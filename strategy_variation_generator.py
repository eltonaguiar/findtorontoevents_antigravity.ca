#!/usr/bin/env python3
"""
Strategy Variation Generator
============================

Generates new strategy variations based on forward testing lessons.
Uses genetic algorithm approach to combine winning DNA elements.

Reference: Edward Tufte's principles of analytical design - 
let the data guide the strategy evolution.
"""

import json
import random
import numpy as np
from datetime import datetime
from typing import List, Dict, Any
from dataclasses import dataclass, asdict
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StrategyType(Enum):
    COMPRESSION_EXPANSION = "compression_expansion"
    VWAP_REVERSAL = "vwap_reversal"
    TREND_FOLLOWING = "trend_following"
    MEAN_REVERSION = "mean_reversion"
    HYBRID = "hybrid"


@dataclass
class StrategyDNA:
    """Genetic representation of a trading strategy"""
    name: str
    version: str
    strategy_type: StrategyType
    
    # Entry genes
    entry_logic: Dict[str, Any]
    
    # Exit genes
    exit_logic: Dict[str, Any]
    
    # Risk management genes
    risk_management: Dict[str, Any]
    
    # Regime detection genes
    regime_detection: Dict[str, Any]
    
    # Symbol specialization
    symbols: List[str]
    
    # Metadata
    parent_strategies: List[str]
    created_at: str = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'version': self.version,
            'strategy_type': self.strategy_type.value,
            'entry_logic': self.entry_logic,
            'exit_logic': self.exit_logic,
            'risk_management': self.risk_management,
            'regime_detection': self.regime_detection,
            'symbols': self.symbols,
            'parent_strategies': self.parent_strategies,
            'created_at': self.created_at
        }
    
    def to_json(self, filepath: str):
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)


class StrategyVariationGenerator:
    """
    Generates strategy variations based on forward testing lessons.
    """
    
    def __init__(self, seed: int = None):
        if seed:
            random.seed(seed)
            np.random.seed(seed)
        
        # Winning DNA templates from forward testing
        self.winning_dna = {
            'keltner_compression': {
                'indicator': 'keltner_channels',
                'compression_periods': 3,
                'band_width_threshold': 0.5,  # ATR multiple
                'entry_trigger': 'band_expansion',
                'direction': 'breakout_direction'
            },
            'vwap_reversion': {
                'indicator': 'vwap',
                'deviation_threshold': 1.5,  # Standard deviations
                'volume_confirmation': True,
                'volatility_filter': True
            },
            'regime_detection': {
                'trend_timeframe': '4h',
                'adx_threshold': 25,
                'trade_with_trend': True,
                'disable_counter_trend': True
            },
            'time_exits': {
                'max_hold_time': 12,  # hours
                'profit_target_time': 6,  # hours
                'partial_exit_time': 8
            }
        }
    
    def generate_keltner_variations(self, count: int = 3) -> List[StrategyDNA]:
        """Generate variations of the winning Keltner compression strategy"""
        variations = []
        
        base_params = {
            'btc': {'atr_mult': 2.0, 'band_width': 0.5, 'compression_bars': 3},
            'eth': {'atr_mult': 2.5, 'band_width': 0.6, 'compression_bars': 4},
            'sol': {'atr_mult': 1.8, 'band_width': 0.4, 'compression_bars': 3}
        }
        
        for symbol in ['BTC', 'ETH', 'SOL']:
            params = base_params[symbol.lower()]
            
            for i in range(count):
                # Add random mutations
                atr_var = params['atr_mult'] * random.uniform(0.8, 1.2)
                bw_var = params['band_width'] * random.uniform(0.8, 1.3)
                comp_var = max(2, params['compression_bars'] + random.randint(-1, 1))
                
                dna = StrategyDNA(
                    name=f"keltner_compression_{symbol.lower()}_v{i+2}",
                    version=f"1.{i+1}",
                    strategy_type=StrategyType.COMPRESSION_EXPANSION,
                    entry_logic={
                        'type': 'keltner_compression',
                        'compression_bars': comp_var,
                        'band_width_threshold': bw_var,
                        'atr_period': 14,
                        'atr_multiplier': atr_var,
                        'entry_trigger': 'band_expansion',
                        'volume_confirmation': random.choice([True, False])
                    },
                    exit_logic={
                        'tp_type': 'atr_based',
                        'tp_atr_mult': 2.5 + random.uniform(-0.5, 0.5),
                        'sl_type': 'atr_based',
                        'sl_atr_mult': 1.5 + random.uniform(-0.3, 0.3),
                        'time_exit_hours': 12,
                        'trailing_stop': random.choice([True, False]),
                        'trailing_activation': 1.0
                    },
                    risk_management={
                        'position_size': 0.1,
                        'max_positions': 3,
                        'daily_loss_limit': 0.03,
                        'consecutive_loss_adjustment': True
                    },
                    regime_detection={
                        'enabled': True,
                        'trend_timeframe': '4h',
                        'adx_threshold': 25,
                        'trade_with_trend_only': random.choice([True, False]),
                        'disable_in_chop': True
                    },
                    symbols=[f"{symbol}USDT"],
                    parent_strategies=['crypto_keltner_compression_expansion_v1']
                )
                variations.append(dna)
        
        logger.info(f"Generated {len(variations)} Keltner variations")
        return variations
    
    def generate_hybrid_strategies(self, count: int = 4) -> List[StrategyDNA]:
        """Generate hybrid strategies combining multiple winning elements"""
        hybrids = []
        
        hybrid_configs = [
            {
                'name': 'keltner_vwap_hybrid',
                'entry': 'keltner',
                'filter': 'vwap',
                'exit': 'combined'
            },
            {
                'name': 'compression_momentum',
                'entry': 'keltner',
                'filter': 'momentum',
                'exit': 'trailing'
            },
            {
                'name': 'regime_aware_vwap',
                'entry': 'vwap',
                'filter': 'regime',
                'exit': 'time_based'
            },
            {
                'name': 'multi_factor_breakout',
                'entry': 'keltner',
                'filter': 'volume+volatility',
                'exit': 'partial'
            }
        ]
        
        for config in hybrid_configs[:count]:
            dna = StrategyDNA(
                name=f"{config['name']}_v1",
                version="1.0",
                strategy_type=StrategyType.HYBRID,
                entry_logic={
                    'primary': config['entry'],
                    'secondary_filter': config['filter'],
                    'confirmation_required': True,
                    'min_score': 0.7
                },
                exit_logic={
                    'strategy': config['exit'],
                    'tp_atr_mult': 2.5,
                    'sl_atr_mult': 1.5,
                    'time_exit_hours': 12,
                    'partial_tp_1': 1.5,
                    'partial_tp_2': 2.5,
                    'partial_size_1': 0.5,
                    'partial_size_2': 0.25
                },
                risk_management={
                    'position_size': 0.08,
                    'max_positions': 5,
                    'correlation_filter': True,
                    'volatility_adjustment': True
                },
                regime_detection={
                    'enabled': True,
                    'regime_timeframe': '4h',
                    'strategy_per_regime': {
                        'trending': 'follow',
                        'ranging': 'revert',
                        'volatile': 'compress'
                    }
                },
                symbols=['BTCUSDT', 'ETHUSDT', 'SOLUSDT'],
                parent_strategies=['crypto_keltner_compression_expansion_v1', 
                                  'crypto_vwap_deviation_reversion_volfilter_v1']
            )
            hybrids.append(dna)
        
        logger.info(f"Generated {len(hybrids)} hybrid strategies")
        return hybrids
    
    def generate_regime_specific_strategies(self) -> List[StrategyDNA]:
        """Generate strategies optimized for specific market regimes"""
        regimes = []
        
        # Trend Following Strategy
        trend_dna = StrategyDNA(
            name="trend_follow_breakout_v1",
            version="1.0",
            strategy_type=StrategyType.TREND_FOLLOWING,
            entry_logic={
                'type': 'breakout',
                'lookback_periods': 20,
                'volume_confirmation': True,
                'min_volume_mult': 1.5,
                'pullback_entry': True,
                'pullback_ma': 20
            },
            exit_logic={
                'tp_type': 'trailing',
                'trailing_stop_pct': 0.02,
                'sl_type': 'swing_low',
                'time_exit_hours': 24,
                'move_stop_to_breakeven': True,
                'breakeven_trigger': 1.5
            },
            risk_management={
                'position_size': 0.12,
                'pyramiding': True,
                'max_pyramid_levels': 2,
                'pyramid_size': 0.05
            },
            regime_detection={
                'enabled': True,
                'required_regime': 'trending',
                'adx_min': 30,
                'adx_max': 60
            },
            symbols=['BTCUSDT', 'ETHUSDT', 'SOLUSDT'],
            parent_strategies=['crypto_keltner_compression_expansion_v1']
        )
        regimes.append(trend_dna)
        
        # Mean Reversion Strategy
        mr_dna = StrategyDNA(
            name="mean_reversion_vwap_v1",
            version="1.0",
            strategy_type=StrategyType.MEAN_REVERSION,
            entry_logic={
                'type': 'vwap_deviation',
                'deviation_threshold': 2.0,
                'rsi_confirmation': True,
                'rsi_oversold': 35,
                'rsi_overbought': 65,
                'volume_confirmation': True
            },
            exit_logic={
                'tp_type': 'mean_reversion',
                'tp_target': 'vwap',
                'sl_type': 'fixed',
                'sl_pct': 1.5,
                'time_exit_hours': 8,
                'exit_on_vwap_touch': True
            },
            risk_management={
                'position_size': 0.08,
                'max_positions': 4,
                'skip_if_trending': True
            },
            regime_detection={
                'enabled': True,
                'required_regime': 'ranging',
                'adx_max': 20,
                'range_bound_confirmation': True
            },
            symbols=['BTCUSDT', 'ETHUSDT'],
            parent_strategies=['crypto_vwap_deviation_reversion_volfilter_v1']
        )
        regimes.append(mr_dna)
        
        # Volatility Expansion Strategy
        vol_dna = StrategyDNA(
            name="volatility_expansion_v1",
            version="1.0",
            strategy_type=StrategyType.COMPRESSION_EXPANSION,
            entry_logic={
                'type': 'volatility_breakout',
                'compression_period': 4,
                'breakout_threshold': 1.5,
                'atr_period': 14,
                'min_volatility_increase': 1.5
            },
            exit_logic={
                'tp_type': 'atr_based',
                'tp_atr_mult': 3.0,
                'sl_type': 'atr_based',
                'sl_atr_mult': 1.0,
                'time_exit_hours': 6,
                'volatility_contraction_exit': True
            },
            risk_management={
                'position_size': 0.06,
                'volatility_adjusted_sizing': True,
                'reduce_size_high_vol': True
            },
            regime_detection={
                'enabled': True,
                'required_regime': 'volatile',
                'atr_percentile_threshold': 80
            },
            symbols=['BTCUSDT', 'SOLUSDT'],
            parent_strategies=['crypto_keltner_compression_expansion_v1']
        )
        regimes.append(vol_dna)
        
        logger.info(f"Generated {len(regimes)} regime-specific strategies")
        return regimes
    
    def generate_adaptive_strategies(self, count: int = 3) -> List[StrategyDNA]:
        """Generate strategies with adaptive parameters based on recent performance"""
        adaptives = []
        
        for i in range(count):
            dna = StrategyDNA(
                name=f"adaptive_multi_factor_v{i+1}",
                version="1.0",
                strategy_type=StrategyType.HYBRID,
                entry_logic={
                    'type': 'multi_factor',
                    'factors': [
                        {'name': 'compression', 'weight': 0.4},
                        {'name': 'vwap_deviation', 'weight': 0.3},
                        {'name': 'momentum', 'weight': 0.3}
                    ],
                    'threshold': 0.6,
                    'adaptive_weights': True,
                    'lookback_periods': 50
                },
                exit_logic={
                    'type': 'adaptive',
                    'base_tp': 2.0,
                    'base_sl': 1.5,
                    'adaptation_lookback': 20,
                    'win_rate_adjustment': True,
                    'profit_factor_adjustment': True
                },
                risk_management={
                    'position_size': 0.1,
                    'adaptive_sizing': True,
                    'kelly_fraction': 0.5,
                    'recent_performance_lookback': 20,
                    'max_size_increase': 1.5,
                    'max_size_decrease': 0.5
                },
                regime_detection={
                    'enabled': True,
                    'auto_detect': True,
                    'strategy_rotation': True
                },
                symbols=['BTCUSDT', 'ETHUSDT', 'SOLUSDT'],
                parent_strategies=['crypto_keltner_compression_expansion_v1',
                                  'crypto_vwap_deviation_reversion_volfilter_v1',
                                  'crypto_kalman_trend_residual_reversion_v1']
            )
            adaptives.append(dna)
        
        logger.info(f"Generated {len(adaptives)} adaptive strategies")
        return adaptives
    
    def generate_all_variations(self) -> List[StrategyDNA]:
        """Generate complete set of strategy variations"""
        all_variations = []
        
        all_variations.extend(self.generate_keltner_variations(count=2))
        all_variations.extend(self.generate_hybrid_strategies(count=4))
        all_variations.extend(self.generate_regime_specific_strategies())
        all_variations.extend(self.generate_adaptive_strategies(count=2))
        
        logger.info(f"Total strategy variations generated: {len(all_variations)}")
        return all_variations
    
    def export_variations(self, variations: List[StrategyDNA], output_dir: str = "strategy_variations"):
        """Export all variations to JSON files"""
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        manifest = {
            'generated_at': datetime.now().isoformat(),
            'total_variations': len(variations),
            'variations': []
        }
        
        for var in variations:
            filename = f"{var.name}.json"
            filepath = os.path.join(output_dir, filename)
            var.to_json(filepath)
            
            manifest['variations'].append({
                'name': var.name,
                'type': var.strategy_type.value,
                'file': filename,
                'symbols': var.symbols
            })
        
        # Save manifest
        manifest_path = os.path.join(output_dir, 'manifest.json')
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        logger.info(f"Exported {len(variations)} variations to {output_dir}/")
        return manifest


def main():
    """Generate strategy variations and export"""
    generator = StrategyVariationGenerator(seed=42)
    
    # Generate all variations
    variations = generator.generate_all_variations()
    
    # Export to JSON
    manifest = generator.export_variations(variations)
    
    # Print summary
    print("\n" + "="*60)
    print("STRATEGY VARIATIONS GENERATED")
    print("="*60)
    
    by_type = {}
    for var in variations:
        st = var.strategy_type.value
        by_type[st] = by_type.get(st, 0) + 1
    
    print("\nBy Type:")
    for st, count in sorted(by_type.items()):
        print(f"  {st}: {count}")
    
    print(f"\nTotal: {len(variations)} variations")
    print(f"Exported to: strategy_variations/")
    print("="*60)


if __name__ == "__main__":
    main()
