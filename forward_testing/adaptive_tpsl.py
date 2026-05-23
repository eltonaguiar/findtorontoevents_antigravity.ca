#!/usr/bin/env python3
"""
Adaptive TP/SL Framework
Addresses: 94% signal expiration, tight TP/SL bands

Implements:
- Volatility-adjusted TP/SL (3x ATR TP, 1.5x ATR SL)
- Regime-specific multipliers
- Partial exit strategies
- Trailing stop integration
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class MarketRegime(Enum):
    BULL = "BULL"
    BEAR = "BEAR"
    SIDEWAYS = "SIDEWAYS"
    HIGH_VOL = "HIGH_VOL"


@dataclass
class TPSLConfig:
    """TP/SL configuration for a regime."""
    tp_multiplier: float
    sl_multiplier: float
    partial_tp_levels: list
    trailing_activation: float
    max_holding_bars: int


class AdaptiveTPSL:
    """
    Adaptive TP/SL framework with regime adjustments.
    """
    
    # Regime-specific configurations
    REGIME_CONFIGS = {
        MarketRegime.BULL: TPSLConfig(
            tp_multiplier=3.5,
            sl_multiplier=1.75,
            partial_tp_levels=[0.5, 1.0, 2.0],
            trailing_activation=0.5,
            max_holding_bars=72
        ),
        MarketRegime.SIDEWAYS: TPSLConfig(
            tp_multiplier=3.0,
            sl_multiplier=1.5,
            partial_tp_levels=[0.5, 1.0],
            trailing_activation=0.6,
            max_holding_bars=48
        ),
        MarketRegime.BEAR: TPSLConfig(
            tp_multiplier=2.5,
            sl_multiplier=1.25,
            partial_tp_levels=[0.5, 0.8],
            trailing_activation=0.4,
            max_holding_bars=36
        ),
        MarketRegime.HIGH_VOL: TPSLConfig(
            tp_multiplier=4.0,
            sl_multiplier=2.0,
            partial_tp_levels=[0.5, 1.0, 1.5, 2.0],
            trailing_activation=0.3,
            max_holding_bars=96
        )
    }
    
    def __init__(self, default_regime: MarketRegime = MarketRegime.SIDEWAYS):
        self.default_regime = default_regime
        self.atr_period = 14
    
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range."""
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        return atr
    
    def calculate_tpsl(
        self,
        entry_price: float,
        direction: str,
        df: pd.DataFrame,
        regime: Optional[MarketRegime] = None
    ) -> Dict:
        """Calculate adaptive TP/SL levels."""
        if regime is None:
            regime = self.default_regime
        
        config = self.REGIME_CONFIGS[regime]
        atr = self.calculate_atr(df).iloc[-1]
        
        if direction == 'LONG':
            sl_price = entry_price - (atr * config.sl_multiplier)
            tp_price = entry_price + (atr * config.tp_multiplier)
            partial_tps = [
                entry_price + (atr * config.tp_multiplier * level)
                for level in config.partial_tp_levels
            ]
            trailing_activation = entry_price + (atr * config.trailing_activation)
        else:  # SHORT
            sl_price = entry_price + (atr * config.sl_multiplier)
            tp_price = entry_price - (atr * config.tp_multiplier)
            partial_tps = [
                entry_price - (atr * config.tp_multiplier * level)
                for level in config.partial_tp_levels
            ]
            trailing_activation = entry_price - (atr * config.trailing_activation)
        
        return {
            'entry_price': entry_price,
            'tp_price': tp_price,
            'sl_price': sl_price,
            'atr': atr,
            'atr_mult_tp': config.tp_multiplier,
            'atr_mult_sl': config.sl_multiplier,
            'partial_tp_levels': partial_tps,
            'partial_tp_percentages': [50, 30, 20],
            'trailing_activation': trailing_activation,
            'trailing_stop_distance': atr * config.sl_multiplier * 0.8,
            'max_holding_bars': config.max_holding_bars,
            'regime': regime.value,
            'risk_reward_ratio': abs(tp_price - entry_price) / abs(entry_price - sl_price)
        }


if __name__ == "__main__":
    print("Adaptive TP/SL Framework Demo")
    print("="*60)
    
    np.random.seed(42)
    n = 100
    df = pd.DataFrame({
        'open': 100 + np.cumsum(np.random.randn(n) * 0.5),
        'high': 101 + np.cumsum(np.random.randn(n) * 0.5),
        'low': 99 + np.cumsum(np.random.randn(n) * 0.5),
        'close': 100 + np.cumsum(np.random.randn(n) * 0.5)
    })
    
    tpsl = AdaptiveTPSL()
    
    for regime in MarketRegime:
        print(f"\n{regime.value} Regime:")
        config = tpsl.calculate_tpsl(
            entry_price=85000,
            direction='LONG',
            df=df,
            regime=regime
        )
        print(f"  Entry: ${config['entry_price']:,.2f}")
        print(f"  TP: ${config['tp_price']:,.2f} ({config['atr_mult_tp']}x ATR)")
        print(f"  SL: ${config['sl_price']:,.2f} ({config['atr_mult_sl']}x ATR)")
        print(f"  R:R = {config['risk_reward_ratio']:.2f}:1")
