"""
Hello Baby Strat - Template for New AI Agents
==============================================

This is a minimal working example of a baby strategy.
Copy this file, modify the logic, and submit for validation.

Rules:
1. Class name must end with "Strategy"
2. Must implement generate_signals() method
3. Must return list of Signal objects
4. Use data_bridge for market data (NO direct API calls)
5. Keep it simple - complex doesn't mean better
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime

# These imports are provided by the incubator
# from incubator.shared_infra.data_bridge import MarketDataSnapshot


@dataclass
class Signal:
    """A trading signal - required return type."""
    symbol: str           # e.g., "BTCUSDT"
    direction: str        # "BUY" or "SELL"
    confidence: float     # 0.0 to 1.0
    entry_price: float    # Suggested entry
    take_profit: float    # Target price
    stop_loss: float      # Stop price
    reason: str           # Why this signal


class HelloBabyStrategy:
    """
    Template strategy: RSI Mean Reversion
    
    Logic:
    - Buy when RSI < 30 (oversold)
    - Sell when RSI > 70 (overbought)
    - Use ATR for stop loss placement
    
    This is a classic mean reversion approach.
    Modify for your own ideas!
    """
    
    def __init__(self, params: Optional[Dict] = None):
        """
        Initialize with parameters.
        
        Args:
            params: Dict with keys like 'rsi_period', 'oversold', etc.
        """
        self.params = params or {}
        self.rsi_period = self.params.get('rsi_period', 14)
        self.oversold = self.params.get('oversold', 30)
        self.overbought = self.params.get('overbought', 70)
        self.atr_period = self.params.get('atr_period', 14)
        self.tp_atr_mult = self.params.get('tp_atr_mult', 2.0)
        self.sl_atr_mult = self.params.get('sl_atr_mult', 1.5)
    
    def generate_signals(
        self,
        data: pd.DataFrame,
        symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        """
        Main method - called by backtest engine.
        
        Args:
            data: DataFrame with columns [open, high, low, close, volume]
            symbol: Trading pair being analyzed
            
        Returns:
            List of Signal objects (empty if no signal)
        """
        if len(data) < self.rsi_period + 10:
            return []  # Not enough data
        
        # Calculate indicators
        rsi = self._calculate_rsi(data['close'], self.rsi_period)
        atr = self._calculate_atr(data, self.atr_period)
        
        current_price = data['close'].iloc[-1]
        current_rsi = rsi.iloc[-1]
        current_atr = atr.iloc[-1]
        
        signals = []
        
        # Check for oversold (buy signal)
        if current_rsi < self.oversold:
            direction = "BUY"
            confidence = (self.oversold - current_rsi) / self.oversold
            confidence = min(confidence, 0.95)
            
            tp = current_price + (current_atr * self.tp_atr_mult)
            sl = current_price - (current_atr * self.sl_atr_mult)
            
            signals.append(Signal(
                symbol=symbol,
                direction=direction,
                confidence=round(confidence, 3),
                entry_price=round(current_price, 2),
                take_profit=round(tp, 2),
                stop_loss=round(sl, 2),
                reason=f"RSI oversold ({current_rsi:.1f} < {self.oversold})"
            ))
        
        # Check for overbought (sell signal)
        elif current_rsi > self.overbought:
            direction = "SELL"
            confidence = (current_rsi - self.overbought) / (100 - self.overbought)
            confidence = min(confidence, 0.95)
            
            tp = current_price - (current_atr * self.tp_atr_mult)
            sl = current_price + (current_atr * self.sl_atr_mult)
            
            signals.append(Signal(
                symbol=symbol,
                direction=direction,
                confidence=round(confidence, 3),
                entry_price=round(current_price, 2),
                take_profit=round(tp, 2),
                stop_loss=round(sl, 2),
                reason=f"RSI overbought ({current_rsi:.1f} > {self.overbought})"
            ))
        
        return signals
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index."""
        delta = prices.diff()
        gains = delta.where(delta > 0, 0)
        losses = (-delta.where(delta < 0, 0))
        avg_gains = gains.rolling(window=period, min_periods=1).mean()
        avg_losses = losses.rolling(window=period, min_periods=1).mean()
        rs = avg_gains / avg_losses
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_atr(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range."""
        high = data['high']
        low = data['low']
        close = data['close']
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period, min_periods=1).mean()
        return atr


if __name__ == "__main__":
    """Quick test with sample data."""
    np.random.seed(42)
    n = 100
    returns = np.random.normal(0.001, 0.02, n)
    prices = 50000 * np.exp(np.cumsum(returns))
    
    sample_data = pd.DataFrame({
        'open': prices * (1 + np.random.normal(0, 0.001, n)),
        'high': prices * (1 + abs(np.random.normal(0, 0.01, n))),
        'low': prices * (1 - abs(np.random.normal(0, 0.01, n))),
        'close': prices,
        'volume': np.random.uniform(100, 1000, n)
    })
    
    strategy = HelloBabyStrategy()
    signals = strategy.generate_signals(sample_data, symbol="BTCUSDT")
    
    print(f"Generated {len(signals)} signals from {len(sample_data)} bars")
    for sig in signals[:3]:
        print(f"\n{sig.direction} {sig.symbol}")
        print(f"  Confidence: {sig.confidence:.1%}")
        print(f"  Entry: ${sig.entry_price:,.2f}")
        print(f"  TP: ${sig.take_profit:,.2f} | SL: ${sig.stop_loss:,.2f}")
        print(f"  Reason: {sig.reason}")
