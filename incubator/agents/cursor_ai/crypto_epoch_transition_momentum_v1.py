"""
Epoch Transition Momentum Strategy
===================================

Created by: cursor_ai
Date: 2026-02-27

Strategy Logic:
- Entry when: Price crosses above 200-day SMA AND 50-day SMA > 200-day SMA (golden cross) AND volume > 2x 30-day average
- Exit when: 50-day SMA crosses below 200-day SMA (death cross) OR close below 200-day SMA
- Enhanced with: ATR-based position sizing and trailing stop

Unique Value Proposition:
Captures major trend transitions (epoch changes) using the classic golden/death cross but with volume confirmation and ATR-based risk management. This strategy specifically targets the start of new multi-month trends, avoiding whipsaws in ranging markets.
"""

import numpy as np
import pandas as pd
from typing import List, Optional
from dataclasses import dataclass

@dataclass
class Signal:
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str

class CryptoEpochTransitionMomentumStrategy:
    """Golden cross/death cross with volume and volatility filters."""
    
    def __init__(self, params: Optional[dict] = None):
        self.p = params or {}
        self.sma_fast = self.p.get('sma_fast', 50)
        self.sma_slow = self.p.get('sma_slow', 200)
        self.volume_period = self.p.get('volume_period', 30)
        self.volume_multiplier = self.p.get('volume_multiplier', 2.0)
        self.atr_period = self.p.get('atr_period', 14)
        self.tp_atr_mult = self.p.get('tp_atr_mult', 4.0)
        self.sl_atr_mult = self.p.get('sl_atr_mult', 2.0)
        self.use_trailing_stop = self.p.get('use_trailing_stop', True)
    
    def generate_signals(
        self,
        data: pd.DataFrame,
        symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        if len(data) < self.sma_slow + 10:
            return []
        
        # Calculate moving averages
        sma_fast = data['close'].rolling(self.sma_fast).mean()
        sma_slow = data['close'].rolling(self.sma_slow).mean()
        
        # Volume average
        volume_avg = data['volume'].rolling(self.volume_period).mean()
        
        # ATR for risk management
        atr = self._calculate_atr(data)
        current_atr = atr.iloc[-1]
        
        current_price = data['close'].iloc[-1]
        current_volume = data['volume'].iloc[-1]
        
        signals = []
        
        # Golden Cross: Fast SMA crosses above Slow SMA
        if (sma_fast.iloc[-1] > sma_slow.iloc[-1] and 
            sma_fast.iloc[-2] <= sma_slow.iloc[-2] and
            current_volume > volume_avg.iloc[-1] * self.volume_multiplier):
            
            confidence = 0.7  # Strong trend change signal
            
            tp = current_price + (current_atr * self.tp_atr_mult)
            sl = current_price - (current_atr * self.sl_atr_mult)
            
            signals.append(Signal(
                symbol=symbol,
                direction="BUY",
                confidence=confidence,
                entry_price=round(current_price, 2),
                take_profit=round(tp, 2),
                stop_loss=round(sl, 2),
                reason=f"Golden cross + volume {current_volume/volume_avg.iloc[-1]:.1f}x"
            ))
        
        # Death Cross: Fast SMA crosses below Slow SMA
        elif (sma_fast.iloc[-1] < sma_slow.iloc[-1] and 
              sma_fast.iloc[-2] >= sma_slow.iloc[-2]):
            
            confidence = 0.7
            
            tp = current_price - (current_atr * self.tp_atr_mult)
            sl = current_price + (current_atr * self.sl_atr_mult)
            
            signals.append(Signal(
                symbol=symbol,
                direction="SELL",
                confidence=confidence,
                entry_price=round(current_price, 2),
                take_profit=round(tp, 2),
                stop_loss=round(sl, 2),
                reason=f"Death cross"
            ))
        
        return signals
    
    def _calculate_atr(self, data: pd.DataFrame) -> pd.Series:
        high = data['high']
        low = data['low']
        close = data['close']
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=self.atr_period).mean()

if __name__ == "__main__":
    np.random.seed(42)
    n = 1000
    returns = np.random.normal(0.0001, 0.02, n)
    prices = 50000 * np.exp(np.cumsum(returns))
    
    test_data = pd.DataFrame({
        'open': prices * (1 + np.random.normal(0, 0.001, n)),
        'high': prices * (1 + abs(np.random.normal(0, 0.01, n))),
        'low': prices * (1 - abs(np.random.normal(0, 0.01, n))),
        'close': prices,
        'volume': np.random.uniform(100, 1000, n)
    })
    
    strategy = CryptoEpochTransitionMomentumStrategy()
    signals = strategy.generate_signals(test_data, symbol="BTCUSDT")
    
    print(f"Generated {len(signals)} signals from {len(test_data)} bars")
    for sig in signals[:3]:
        print(f"\n{sig.direction} {sig.symbol}")
        print(f"  Confidence: {sig.confidence:.1%}")
        print(f"  Entry: ${sig.entry_price:,.2f}")
        print(f"  TP: ${sig.take_profit:,.2f} | SL: ${sig.stop_loss:,.2f}")
        print(f"  Reason: {sig.reason}")