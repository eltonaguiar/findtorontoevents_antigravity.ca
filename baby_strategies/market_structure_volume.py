"""
MarketStructureVolumeStrategy - Baby Strat
==========================================

Created by: AI Assistant
Date: 2026-02-27

Strategy Logic:
- Entry when: Price breaks market structure (CHoCH/BOS) with volume confirmation
- Exit when: TP/SL hit or structure reverses
- Risk management: ATR-based SL, structure-based TP

Unique Value Proposition:
Combines Smart Money Concepts (market structure breaks) with volume profile analysis
to identify high-probability trend continuation entries.
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


class MarketStructureVolumeStrategy:
    """
    Market Structure + Volume Confirmation Strategy
    
    Detects Change of Character (CHoCH) and Break of Structure (BOS)
    with volume confirmation for trend entries.
    """

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.swing_lookback = self.params.get('swing_lookback', 5)
        self.volume_ma_period = self.params.get('volume_ma_period', 20)
        self.volume_threshold = self.params.get('volume_threshold', 1.5)
        self.atr_period = self.params.get('atr_period', 14)
        self.tp_atr_mult = self.params.get('tp_atr_mult', 2.5)
        self.sl_atr_mult = self.params.get('sl_atr_mult', 1.0)
        self.min_structure_pivot = self.params.get('min_structure_pivot', 3)

    def generate_signals(
        self,
        data: pd.DataFrame,
        symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        if len(data) < max(self.swing_lookback, self.volume_ma_period, self.atr_period) + 20:
            return []

        # Calculate indicators
        atr = self._calculate_atr(data, self.atr_period)
        volume_ma = data['volume'].rolling(window=self.volume_ma_period).mean()
        
        # Find swing highs and lows
        swing_highs, swing_lows = self._find_structure_pivots(data, self.swing_lookback)
        
        current_price = data['close'].iloc[-1]
        current_volume = data['volume'].iloc[-1]
        current_atr = atr.iloc[-1]
        current_volume_ma = volume_ma.iloc[-1]
        
        signals = []
        
        # Need at least 2 swing points for structure
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return signals
        
        # Get recent structure points
        last_swing_high = swing_highs[-1]
        prev_swing_high = swing_highs[-2]
        last_swing_low = swing_lows[-1]
        prev_swing_low = swing_lows[-2]
        
        # Bullish Break of Structure (BOS)
        # Price breaks above previous swing high with volume
        if (current_price > prev_swing_high['price'] and 
            last_swing_high['price'] <= prev_swing_high['price'] and
            current_volume > current_volume_ma * self.volume_threshold):
            
            # Calculate confidence based on breakout strength and volume
            breakout_strength = (current_price - prev_swing_high['price']) / current_atr
            volume_ratio = current_volume / current_volume_ma
            confidence = min(0.5 + breakout_strength * 0.3 + (volume_ratio - 1) * 0.2, 0.95)
            
            tp = current_price + (current_atr * self.tp_atr_mult)
            sl = last_swing_low['price'] - (current_atr * 0.5)
            
            signals.append(Signal(
                symbol=symbol,
                direction="BUY",
                confidence=round(confidence, 3),
                entry_price=round(current_price, 2),
                take_profit=round(tp, 2),
                stop_loss=round(sl, 2),
                reason=f"Bullish BOS above {prev_swing_high['price']:.2f} with {volume_ratio:.1f}x volume"
            ))
        
        # Bearish Break of Structure (BOS)
        # Price breaks below previous swing low with volume
        elif (current_price < prev_swing_low['price'] and 
              last_swing_low['price'] >= prev_swing_low['price'] and
              current_volume > current_volume_ma * self.volume_threshold):
            
            breakout_strength = (prev_swing_low['price'] - current_price) / current_atr
            volume_ratio = current_volume / current_volume_ma
            confidence = min(0.5 + breakout_strength * 0.3 + (volume_ratio - 1) * 0.2, 0.95)
            
            tp = current_price - (current_atr * self.tp_atr_mult)
            sl = last_swing_high['price'] + (current_atr * 0.5)
            
            signals.append(Signal(
                symbol=symbol,
                direction="SELL",
                confidence=round(confidence, 3),
                entry_price=round(current_price, 2),
                take_profit=round(tp, 2),
                stop_loss=round(sl, 2),
                reason=f"Bearish BOS below {prev_swing_low['price']:.2f} with {volume_ratio:.1f}x volume"
            ))
        
        return signals

    def _find_structure_pivots(self, data: pd.DataFrame, lookback: int) -> tuple:
        """Find swing highs and lows for market structure analysis."""
        highs = data['high']
        lows = data['low']
        
        swing_highs = []
        swing_lows = []
        
        for i in range(lookback, len(data) - lookback):
            # Swing high
            if highs.iloc[i] == highs.iloc[i-lookback:i+lookback+1].max():
                swing_highs.append({
                    'index': i,
                    'price': highs.iloc[i],
                    'time': data.index[i]
                })
            
            # Swing low
            if lows.iloc[i] == lows.iloc[i-lookback:i+lookback+1].min():
                swing_lows.append({
                    'index': i,
                    'price': lows.iloc[i],
                    'time': data.index[i]
                })
        
        return swing_highs, swing_lows

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
    
    strategy = MarketStructureVolumeStrategy()
    signals = strategy.generate_signals(test_data, symbol="BTCUSDT")
    
    print(f"Generated {len(signals)} signals from {len(test_data)} bars")
    for sig in signals[:3]:
        print(f"\n{sig.direction} {sig.symbol}")
        print(f"  Confidence: {sig.confidence:.1%}")
        print(f"  Entry: ${sig.entry_price:,.2f}")
        print(f"  TP: ${sig.take_profit:,.2f} | SL: ${sig.stop_loss:,.2f}")
        print(f"  Reason: {sig.reason}")
