"""
Multi-Timeframe EMA Confluence Strategy
======================================

Created by: cursor_ai
Date: 2026-02-27

Strategy Logic:
- Entry when: 1h EMA(20) > 1h EMA(50) AND 4h EMA(20) > 4h EMA(50) AND 1h close > 4h EMA(50)
- Exit when: Take profit (1.5x ATR) or stop loss (1.2x ATR)
- Filter: Only trade when 4h EMA(20) is rising (confirming trend)

Unique Value Proposition:
Combines multi-timeframe EMA alignment with trend confirmation, reducing false signals that occur in single-timeframe EMA strategies. The 4h EMA rising filter ensures we only trade with the dominant trend, not against it.
"""

import numpy as np
import pandas as pd
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Signal:
    """A trading signal - required return type."""
    symbol: str
    direction: str  # "BUY" or "SELL"
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str

class MultiTimeframeEMAConfluenceStrategy:
    """
    Multi-Timeframe EMA Confluence Strategy
    
    Logic:
    - Entry when: 1h EMA(20) > 1h EMA(50) AND 4h EMA(20) > 4h EMA(50) AND 1h close > 4h EMA(50)
    - Exit when: Take profit (1.5x ATR) or stop loss (1.2x ATR)
    - Filter: Only trade when 4h EMA(20) is rising (confirming trend)
    """
    
    def __init__(self, params: Optional[dict] = None):
        """
        Initialize with parameters.
        
        Args:
            params: Dictionary with keys like 'ema_short', 'ema_long', etc.
        """
        self.p = params or {}
        self.ema_short = self.p.get('ema_short', 20)
        self.ema_long = self.p.get('ema_long', 50)
        self.atr_period = self.p.get('atr_period', 14)
        self.tp_atr_mult = self.p.get('tp_atr_mult', 1.5)
        self.sl_atr_mult = self.p.get('sl_atr_mult', 1.2)
    
    def generate_signals(
        self,
        data_1h: pd.DataFrame,
        data_4h: pd.DataFrame,
        symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        """
        Main method - called by backtest engine.
        
        Args:
            data_1h: DataFrame with 1h timeframe data
            data_4h: DataFrame with 4h timeframe data
            symbol: Trading pair being analyzed
            
        Returns:
            List of Signal objects (empty if no signal)
        """
        if len(data_1h) < 100 or len(data_4h) < 50:
            return []  # Not enough data
        
        # Calculate EMAs
        ema_1h_short = data_1h['close'].ewm(span=self.ema_short).mean()
        ema_1h_long = data_1h['close'].ewm(span=self.ema_long).mean()
        ema_4h_short = data_4h['close'].ewm(span=self.ema_short).mean()
        ema_4h_long = data_4h['close'].ewm(span=self.ema_long).mean()
        
        # Current prices
        price_1h = data_1h['close'].iloc[-1]
        price_4h = data_4h['close'].iloc[-1]
        
        # Check EMA alignments
        ema_1h_short_curr = ema_1h_short.iloc[-1]
        ema_1h_long_curr = ema_1h_long.iloc[-1]
        ema_4h_short_curr = ema_4h_short.iloc[-1]
        ema_4h_long_curr = ema_4h_long.iloc[-1]
        ema_4h_short_prev = ema_4h_short.iloc[-2]
        
        # Check if 4h EMA(20) is rising
        ema_4h_rising = ema_4h_short_curr > ema_4h_short_prev
        
        signals = []
        
        # Buy signal: Bullish confluence
        if (ema_1h_short_curr > ema_1h_long_curr and
            ema_4h_short_curr > ema_4h_long_curr and
            price_1h > ema_4h_long_curr and
            ema_4h_rising):
            
            atr = self._calculate_atr(data_1h).iloc[-1]
            direction = "BUY"
            confidence = 0.7  # High confidence due to multiple confirmations
            tp = price_1h + (atr * self.tp_atr_mult)
            sl = price_1h - (atr * self.sl_atr_mult)
            
            signals.append(Signal(
                symbol=symbol,
                direction=direction,
                confidence=confidence,
                entry_price=round(price_1h, 2),
                take_profit=round(tp, 2),
                stop_loss=round(sl, 2),
                reason=f"Bullish confluence: 1h short > long & 4h short > long & price > 4h long & 4h rising"
            ))
        
        # Sell signal: Bearish confluence
        elif (ema_1h_short_curr < ema_1h_long_curr and
              ema_4h_short_curr < ema_4h_long_curr and
              price_1h < ema_4h_long_curr and
              not ema_4h_rising):
            
            atr = self._calculate_atr(data_1h).iloc[-1]
            direction = "SELL"
            confidence = 0.7
            tp = price_1h - (atr * self.tp_atr_mult)
            sl = price_1h + (atr * self.sl_atr_mult)
            
            signals.append(Signal(
                symbol=symbol,
                direction=direction,
                confidence=confidence,
                entry_price=round(price_1h, 2),
                take_profit=round(tp, 2),
                stop_loss=round(sl, 2),
                reason=f"Bearish confluence: 1h short < long & 4h short < long & price < 4h long & 4h not rising"
            ))
        
        return signals
    
    def _calculate_atr(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range."""
        high = data['high']
        low = data['low']
        close = data['close']
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        return atr

# ==============================================================================
# TESTING - Required: Verify your strategy works
# ==============================================================================

if __name__ == "__main__":
    """Quick test with synthetic data."""
    
    # Create synthetic 1h data
    np.random.seed(42)
    n_1h = 200
    returns_1h = np.random.normal(0.0002, 0.02, n_1h)
    prices_1h = 50000 * np.exp(np.cumsum(returns_1h))
    
    data_1h = pd.DataFrame({
        'open': prices_1h * (1 + np.random.normal(0, 0.001, n_1h)),
        'high': prices_1h * (1 + abs(np.random.normal(0, 0.01, n_1h))),
        'low': prices_1h * (1 - abs(np.random.normal(0, 0.01, n_1h))),
        'close': prices_1h,
        'volume': np.random.uniform(100, 1000, n_1h)
    })
    
    # Create synthetic 4h data (every 4th 1h bar)
    data_4h = data_1h[::4].copy()
    
    # Test strategy
    strategy = MultiTimeframeEMAConfluenceStrategy()
    signals = strategy.generate_signals(data_1h, data_4h, symbol="BTCUSDT")
    
    print(f"Generated {len(signals)} signals from {len(data_1h)} 1h bars")
    for sig in signals[:3]:
        print(f"\n{sig.direction} {sig.symbol}")
        print(f"  Confidence: {sig.confidence:.1%}")
        print(f"  Entry: ${sig.entry_price:,.2f}")
        print(f"  TP: ${sig.take_profit:,.2f} | SL: ${sig.stop_loss:,.2f}")
        print(f"  Reason: {sig.reason}")
        print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")