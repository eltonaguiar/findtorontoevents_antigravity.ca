"""
OrderBlockRetestStrategy - Baby Strat
=====================================

Created by: AI Assistant
Date: 2026-02-27

Strategy Logic:
- Entry when: Price retests a strong order block (imbalance zone)
- Exit when: TP/SL hit or structure breaks
- Risk management: Stop beyond order block, TP at recent swing

Unique Value Proposition:
Identifies Order Blocks (strong bullish/bearish candles before major moves)
and trades retests of these key institutional levels.
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple
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


class OrderBlockRetestStrategy:
    """
    Order Block Retest Strategy
    
    Identifies Order Blocks:
    - Bullish OB: Last bearish candle before strong bullish move
    - Bearish OB: Last bullish candle before strong bearish move
    
    Then trades retests of these levels.
    """

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.lookback = self.params.get('lookback', 50)
        self.impulse_threshold = self.params.get('impulse_threshold', 3.0)
        self.ob_strength_min = self.params.get('ob_strength_min', 0.6)
        self.atr_period = self.params.get('atr_period', 14)
        self.tp_atr_mult = self.params.get('tp_atr_mult', 2.0)

    def generate_signals(
        self,
        data: pd.DataFrame,
        symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        if len(data) < self.lookback + 20:
            return []

        # Find order blocks
        bullish_obs, bearish_obs = self._find_order_blocks(data)
        
        # Calculate ATR
        atr = self._calculate_atr(data, self.atr_period)
        
        current_price = data['close'].iloc[-1]
        current_atr = atr.iloc[-1]
        
        signals = []
        
        # Check for bullish order block retest
        for ob in bullish_obs[-3:]:  # Check last 3 OBs
            ob_high = ob['high']
            ob_low = ob['low']
            
            # Price is retesting the OB zone (within or just above)
            if (current_price <= ob_high and 
                current_price >= ob_low * 0.995):  # Allow slight undershoot
                
                confidence = ob['strength'] * 0.8
                
                tp = current_price + (current_atr * self.tp_atr_mult)
                sl = ob_low - (current_atr * 0.3)
                
                signals.append(Signal(
                    symbol=symbol,
                    direction="BUY",
                    confidence=round(confidence, 3),
                    entry_price=round(current_price, 2),
                    take_profit=round(tp, 2),
                    stop_loss=round(sl, 2),
                    reason=f"Bullish OB retest ({ob_low:.2f}-{ob_high:.2f})"
                ))
                break  # Only take best OB
        
        # Check for bearish order block retest
        for ob in bearish_obs[-3:]:
            ob_high = ob['high']
            ob_low = ob['low']
            
            # Price is retesting the OB zone (within or just below)
            if (current_price >= ob_low and 
                current_price <= ob_high * 1.005):
                
                confidence = ob['strength'] * 0.8
                
                tp = current_price - (current_atr * self.tp_atr_mult)
                sl = ob_high + (current_atr * 0.3)
                
                signals.append(Signal(
                    symbol=symbol,
                    direction="SELL",
                    confidence=round(confidence, 3),
                    entry_price=round(current_price, 2),
                    take_profit=round(tp, 2),
                    stop_loss=round(sl, 2),
                    reason=f"Bearish OB retest ({ob_low:.2f}-{ob_high:.2f})"
                ))
                break
        
        return signals

    def _find_order_blocks(self, data: pd.DataFrame) -> Tuple[list, list]:
        """
        Find bullish and bearish order blocks.
        
        Bullish OB: Bearish candle immediately before strong bullish impulse
        Bearish OB: Bullish candle immediately before strong bearish impulse
        """
        bullish_obs = []
        bearish_obs = []
        
        atr = self._calculate_atr(data, 14)
        
        for i in range(5, len(data) - 5):
            # Get the candle
            candle = {
                'open': data['open'].iloc[i],
                'high': data['high'].iloc[i],
                'low': data['low'].iloc[i],
                'close': data['close'].iloc[i],
                'index': i
            }
            
            is_bullish = candle['close'] > candle['open']
            is_bearish = candle['close'] < candle['open']
            body = abs(candle['close'] - candle['open'])
            
            current_atr = atr.iloc[i] if i < len(atr) else atr.iloc[-1]
            
            # Check for bullish OB (bearish candle before strong up move)
            if is_bearish:
                # Check if followed by strong bullish impulse
                future_return = (data['close'].iloc[i+5] - candle['close']) / candle['close']
                
                if future_return > self.impulse_threshold * current_atr / candle['close']:
                    strength = body / (candle['high'] - candle['low'])
                    if strength > self.ob_strength_min:
                        bullish_obs.append({
                            'high': candle['high'],
                            'low': candle['low'],
                            'index': i,
                            'strength': strength
                        })
            
            # Check for bearish OB (bullish candle before strong down move)
            if is_bullish:
                future_return = (data['close'].iloc[i+5] - candle['close']) / candle['close']
                
                if future_return < -self.impulse_threshold * current_atr / candle['close']:
                    strength = body / (candle['high'] - candle['low'])
                    if strength > self.ob_strength_min:
                        bearish_obs.append({
                            'high': candle['high'],
                            'low': candle['low'],
                            'index': i,
                            'strength': strength
                        })
        
        return bullish_obs, bearish_obs

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
    
    strategy = OrderBlockRetestStrategy()
    signals = strategy.generate_signals(test_data, symbol="BTCUSDT")
    
    print(f"Generated {len(signals)} signals from {len(test_data)} bars")
    for sig in signals[:3]:
        print(f"\n{sig.direction} {sig.symbol}")
        print(f"  Confidence: {sig.confidence:.1%}")
        print(f"  Entry: ${sig.entry_price:,.2f}")
        print(f"  TP: ${sig.take_profit:,.2f} | SL: ${sig.stop_loss:,.2f}")
        print(f"  Reason: {sig.reason}")
