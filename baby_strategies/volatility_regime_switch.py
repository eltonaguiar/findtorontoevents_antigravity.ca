"""
VolatilityRegimeSwitchStrategy - Baby Strat
===========================================

Created by: AI Assistant
Date: 2026-02-27

Strategy Logic:
- Entry when: Volatility regime changes (low→high or high→low)
- Exit when: Regime reverts or TP/SL hit
- Risk management: Regime-based position sizing and stops

Unique Value Proposition:
Uses volatility percentiles to identify regime shifts.
Different strategies for expansion (breakout) vs contraction (mean reversion).
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional
from dataclasses import dataclass


SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "TRXUSDT", "DOTUSDT",
    "LINKUSDT", "LTCUSDT", "BCHUSDT", "SHIBUSDT", "SUIUSDT",
    "INJUSDT", "NEARUSDT", "HBARUSDT", "ARBUSDT", "OPUSDT",
    "FETUSDT", "TIAUSDT", "SEIUSDT", "AAVEUSDT", "ETCUSDT",
]

@dataclass
class Signal:
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


class VolatilityRegimeSwitchStrategy:
    """
    Volatility Regime Switch Strategy
    
    Detects volatility regime changes using percentile-based thresholds:
    - Low vol regime (percentile < 20): Mean reversion trades
    - High vol regime (percentile > 80): Momentum/breakout trades
    - Normal regime: No trades
    
    Switches strategy type based on detected regime.
    """

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.vol_period = self.params.get('vol_period', 20)
        self.vol_lookback = self.params.get('vol_lookback', 100)
        self.low_vol_pctile = self.params.get('low_vol_pctile', 20)
        self.high_vol_pctile = self.params.get('high_vol_pctile', 80)
        self.bb_period = self.params.get('bb_period', 20)
        self.bb_std = self.params.get('bb_std', 2.0)
        self.atr_period = self.params.get('atr_period', 14)
        self.tp_mult = self.params.get('tp_mult', 2.0)
        self.sl_mult = self.params.get('sl_mult', 1.5)

    def generate_signals(
        self,
        data: pd.DataFrame,
        symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        if len(data) < max(self.vol_lookback, self.bb_period, self.atr_period) + 10:
            return []

        # Calculate volatility (ATR-based)
        atr = self._calculate_atr(data, self.vol_period)
        vol_percentile = atr.rolling(window=self.vol_lookback).apply(
            lambda x: (x.iloc[-1] - x.min()) / (x.max() - x.min()) * 100 if x.max() != x.min() else 50,
            raw=False
        )
        
        # Calculate Bollinger Bands for mean reversion
        sma = data['close'].rolling(window=self.bb_period).mean()
        std = data['close'].rolling(window=self.bb_period).std()
        bb_upper = sma + (std * self.bb_std)
        bb_lower = sma - (std * self.bb_std)
        
        # Current values
        current_price = data['close'].iloc[-1]
        prev_price = data['close'].iloc[-2]
        current_atr = atr.iloc[-1]
        current_vol_pct = vol_percentile.iloc[-1]
        
        bb_up = bb_upper.iloc[-1]
        bb_low = bb_lower.iloc[-1]
        sma_val = sma.iloc[-1]
        
        signals = []
        
        # LOW VOLATILITY REGIME: Mean Reversion
        if current_vol_pct < self.low_vol_pctile:
            # Price near upper band = short opportunity
            if current_price >= bb_up:
                deviation = (current_price - sma_val) / current_atr
                confidence = min(0.4 + deviation * 0.1, 0.95)
                
                tp = sma_val
                sl = current_price + (current_atr * self.sl_mult)
                
                signals.append(Signal(
                    symbol=symbol,
                    direction="SELL",
                    confidence=round(confidence, 3),
                    entry_price=round(current_price, 2),
                    take_profit=round(tp, 2),
                    stop_loss=round(sl, 2),
                    reason=f"Low vol mean rev (pct: {current_vol_pct:.0f}, upper BB)"
                ))
            
            # Price near lower band = long opportunity
            elif current_price <= bb_low:
                deviation = (sma_val - current_price) / current_atr
                confidence = min(0.4 + deviation * 0.1, 0.95)
                
                tp = sma_val
                sl = current_price - (current_atr * self.sl_mult)
                
                signals.append(Signal(
                    symbol=symbol,
                    direction="BUY",
                    confidence=round(confidence, 3),
                    entry_price=round(current_price, 2),
                    take_profit=round(tp, 2),
                    stop_loss=round(sl, 2),
                    reason=f"Low vol mean rev (pct: {current_vol_pct:.0f}, lower BB)"
                ))
        
        # HIGH VOLATILITY REGIME: Momentum/Breakout
        elif current_vol_pct > self.high_vol_pctile:
            # Calculate momentum
            momentum = (current_price - data['close'].iloc[-5]) / data['close'].iloc[-5]
            
            # Strong up move with volume
            if momentum > 0.03 and current_price > sma_val:
                confidence = min(0.5 + momentum * 5, 0.95)
                
                tp = current_price + (current_atr * self.tp_mult)
                sl = current_price - (current_atr * self.sl_mult)
                
                signals.append(Signal(
                    symbol=symbol,
                    direction="BUY",
                    confidence=round(confidence, 3),
                    entry_price=round(current_price, 2),
                    take_profit=round(tp, 2),
                    stop_loss=round(sl, 2),
                    reason=f"High vol momentum (pct: {current_vol_pct:.0f}, mom: {momentum:.1%})"
                ))
            
            # Strong down move
            elif momentum < -0.03 and current_price < sma_val:
                confidence = min(0.5 + abs(momentum) * 5, 0.95)
                
                tp = current_price - (current_atr * self.tp_mult)
                sl = current_price + (current_atr * self.sl_mult)
                
                signals.append(Signal(
                    symbol=symbol,
                    direction="SELL",
                    confidence=round(confidence, 3),
                    entry_price=round(current_price, 2),
                    take_profit=round(tp, 2),
                    stop_loss=round(sl, 2),
                    reason=f"High vol momentum (pct: {current_vol_pct:.0f}, mom: {momentum:.1%})"
                ))
        
        return signals

    def _calculate_atr(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        high = data['high']
        low = data['low']
        close = data['close']
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period, min_periods=1).mean()
        return atr


# ==============================================================================
# TESTING
# ==============================================================================

if __name__ == "__main__":
    """Quick test with synthetic data."""
    
    np.random.seed(42)
    n = 200
    returns = np.random.normal(0.0001, 0.02, n)
    prices = 50000 * np.exp(np.cumsum(returns))
    
    test_data = pd.DataFrame({
        'open': prices * (1 + np.random.normal(0, 0.001, n)),
        'high': prices * (1 + abs(np.random.normal(0, 0.01, n))),
        'low': prices * (1 - abs(np.random.normal(0, 0.01, n))),
        'close': prices,
        'volume': np.random.uniform(100, 1000, n)
    })
    
    strategy = VolatilityRegimeSwitchStrategy()
    signals = strategy.generate_signals(test_data, symbol="BTCUSDT")
    
    print(f"Generated {len(signals)} signals from {len(test_data)} bars")
    for sig in signals[:3]:
        print(f"\n{sig.direction} {sig.symbol}")
        print(f"  Confidence: {sig.confidence:.1%}")
        print(f"  Entry: ${sig.entry_price:,.2f}")
        print(f"  TP: ${sig.take_profit:,.2f} | SL: ${sig.stop_loss:,.2f}")
        print(f"  Reason: {sig.reason}")
