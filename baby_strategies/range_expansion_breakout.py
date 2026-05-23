"""
RangeExpansionBreakoutStrategy - Baby Strat
===========================================

Created by: AI Assistant
Date: 2026-02-27

Strategy Logic:
- Entry when: Price breaks out after period of range contraction (low volatility)
- Exit when: TP/SL hit or momentum fades
- Risk management: ATR-based sizing, contraction-level stop

Unique Value Proposition:
Identifies volatility compression (range contraction) followed by expansion.
Uses Average True Range (ATR) ratio to detect compression phases.
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


class RangeExpansionBreakoutStrategy:
    """
    Range Expansion Breakout Strategy
    
    Detects when market transitions from low volatility (range contraction)
    to high volatility (range expansion) and trades the breakout direction.
    """

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.atr_short = self.params.get('atr_short', 7)
        self.atr_long = self.params.get('atr_long', 21)
        self.compression_threshold = self.params.get('compression_threshold', 0.75)
        self.breakout_threshold = self.params.get('breakout_threshold', 1.0)
        self.lookback = self.params.get('lookback', 20)
        self.volume_confirm = self.params.get('volume_confirm', True)
        self.volume_mult = self.params.get('volume_mult', 1.3)
        self.tp_atr_mult = self.params.get('tp_atr_mult', 2.5)
        self.sl_atr_mult = self.params.get('sl_atr_mult', 1.0)

    def generate_signals(
        self,
        data: pd.DataFrame,
        symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        if len(data) < max(self.atr_long, self.lookback) + 10:
            return []

        # Calculate ATRs
        atr_short = self._calculate_atr(data, self.atr_short)
        atr_long = self._calculate_atr(data, self.atr_long)
        
        # ATR ratio: short-term vs long-term volatility
        atr_ratio = atr_short / atr_long
        
        # Find range boundaries
        recent_high = data['high'].iloc[-self.lookback-1:-1].max()
        recent_low = data['low'].iloc[-self.lookback-1:-1].min()
        recent_range = recent_high - recent_low
        
        current_price = data['close'].iloc[-1]
        prev_price = data['close'].iloc[-2]
        current_atr = atr_short.iloc[-1]
        current_ratio = atr_ratio.iloc[-1]
        prev_ratio = atr_ratio.iloc[-2]
        
        # Volume check
        volume_ma = data['volume'].rolling(window=20).mean().iloc[-1]
        current_volume = data['volume'].iloc[-1]
        volume_ok = current_volume > volume_ma * self.volume_mult
        
        signals = []
        
        # Detect compression breaking out
        # Was compressed (low ratio), now expanding with breakout
        was_compressed = prev_ratio < self.compression_threshold
        is_expanding = current_ratio > self.breakout_threshold
        
        if was_compressed and is_expanding:
            # Bullish breakout
            if (current_price > recent_high and 
                prev_price <= recent_high and
                (not self.volume_confirm or volume_ok)):
                
                breakout_size = (current_price - recent_high) / current_atr
                confidence = min(0.4 + breakout_size * 0.15, 0.95)
                
                tp = current_price + (current_atr * self.tp_atr_mult)
                sl = recent_low - (current_atr * 0.5)
                
                signals.append(Signal(
                    symbol=symbol,
                    direction="BUY",
                    confidence=round(confidence, 3),
                    entry_price=round(current_price, 2),
                    take_profit=round(tp, 2),
                    stop_loss=round(sl, 2),
                    reason=f"Range expansion breakout up (ATR ratio: {current_ratio:.2f})"
                ))
            
            # Bearish breakout
            elif (current_price < recent_low and 
                  prev_price >= recent_low and
                  (not self.volume_confirm or volume_ok)):
                
                breakout_size = (recent_low - current_price) / current_atr
                confidence = min(0.4 + breakout_size * 0.15, 0.95)
                
                tp = current_price - (current_atr * self.tp_atr_mult)
                sl = recent_high + (current_atr * 0.5)
                
                signals.append(Signal(
                    symbol=symbol,
                    direction="SELL",
                    confidence=round(confidence, 3),
                    entry_price=round(current_price, 2),
                    take_profit=round(tp, 2),
                    stop_loss=round(sl, 2),
                    reason=f"Range expansion breakout down (ATR ratio: {current_ratio:.2f})"
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
    
    strategy = RangeExpansionBreakoutStrategy()
    signals = strategy.generate_signals(test_data, symbol="BTCUSDT")
    
    print(f"Generated {len(signals)} signals from {len(test_data)} bars")
    for sig in signals[:3]:
        print(f"\n{sig.direction} {sig.symbol}")
        print(f"  Confidence: {sig.confidence:.1%}")
        print(f"  Entry: ${sig.entry_price:,.2f}")
        print(f"  TP: ${sig.take_profit:,.2f} | SL: ${sig.stop_loss:,.2f}")
        print(f"  Reason: {sig.reason}")
