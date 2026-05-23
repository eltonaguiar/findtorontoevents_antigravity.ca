"""
Baby Strategy 062: Liquidation Cascade Continuation

Rides the momentum AFTER initial liquidation cascade.
When liquidations trigger more liquidations, creating a momentum move.

Category: Liquidation Strategies
Best for: Strong trending markets with leverage washouts
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Signal:
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


class Strategy062LiquidationCascade:
    """
    Captures continuation after liquidation cascade begins.
    
    Logic:
    - Detects acceleration in price movement (cascade beginning)
    - Enters on momentum confirmation after initial liquidation spike
    - Rides the wave as more positions get liquidated
    """
    
    def __init__(self, params: Optional[dict] = None):
        self.p = params or {}
        self.accel_threshold = self.p.get('accel_threshold', 1.5)  # Acceleration factor
        self.volume_mult = self.p.get('volume_mult', 2.0)  # Volume must be 2x average
        self.tp_atr = self.p.get('tp_atr', 2.5)
        self.sl_atr = self.p.get('sl_atr', 1.0)
        self.lookback = self.p.get('lookback', 20)
        self.momentum_period = self.p.get('momentum_period', 3)
        
    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.lookback + 10 or 'volume' not in data.columns:
            return []
        
        # Calculate momentum acceleration
        returns = data['close'].pct_change()
        momentum = returns.rolling(self.momentum_period).sum()
        momentum_prev = momentum.shift(self.momentum_period)
        
        # Acceleration = current momentum / previous momentum (absolute)
        acceleration = abs(momentum) / (abs(momentum_prev) + 1e-10)
        
        # Volume confirmation
        vol_avg = data['volume'].rolling(self.lookback).mean()
        vol_ratio = data['volume'] / vol_avg
        
        # ATR for position sizing
        atr = self._atr(data, self.lookback)
        current_atr = atr.iloc[-1]
        current_price = data['close'].iloc[-1]
        
        signals = []
        
        # Check for downward cascade (long liquidations)
        if (momentum.iloc[-1] < -0.02 and  # Strong down move
            acceleration.iloc[-1] > self.accel_threshold and  # Accelerating
            vol_ratio.iloc[-1] > self.volume_mult):  # High volume
            
            # Wait for small pullback after initial cascade for better entry
            recent_low = data['low'].iloc[-self.momentum_period:].min()
            pullback_pct = (current_price - recent_low) / recent_low
            
            if pullback_pct < 0.005:  # Less than 0.5% pullback = good entry
                confidence = min(0.6 + acceleration.iloc[-1] * 0.15, 0.9)
                signals.append(Signal(
                    symbol=symbol,
                    direction="SELL",
                    confidence=round(confidence, 2),
                    entry_price=round(current_price, 2),
                    take_profit=round(current_price - current_atr * self.tp_atr, 2),
                    stop_loss=round(current_price + current_atr * self.sl_atr, 2),
                    reason=f"Down cascade accel {acceleration.iloc[-1]:.1f}x, vol {vol_ratio.iloc[-1]:.1f}x"
                ))
        
        # Check for upward cascade (short liquidations)
        elif (momentum.iloc[-1] > 0.02 and  # Strong up move
              acceleration.iloc[-1] > self.accel_threshold and
              vol_ratio.iloc[-1] > self.volume_mult):
            
            recent_high = data['high'].iloc[-self.momentum_period:].max()
            pullback_pct = (recent_high - current_price) / recent_high
            
            if pullback_pct < 0.005:
                confidence = min(0.6 + acceleration.iloc[-1] * 0.15, 0.9)
                signals.append(Signal(
                    symbol=symbol,
                    direction="BUY",
                    confidence=round(confidence, 2),
                    entry_price=round(current_price, 2),
                    take_profit=round(current_price + current_atr * self.tp_atr, 2),
                    stop_loss=round(current_price - current_atr * self.sl_atr, 2),
                    reason=f"Up cascade accel {acceleration.iloc[-1]:.1f}x, vol {vol_ratio.iloc[-1]:.1f}x"
                ))
        
        return signals
    
    def _atr(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        high, low, close = data['high'], data['low'], data['close']
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(period).mean()


if __name__ == "__main__":
    # Test with synthetic cascade data
    np.random.seed(42)
    n = 100
    base = 50000
    
    # Create accelerating down move (cascade)
    returns = np.random.randn(n) * 0.001
    # Inject cascade
    returns[45:50] = [-0.01, -0.015, -0.025, -0.035, -0.02]  # Accelerating down
    
    closes = base * (1 + np.cumsum(returns))
    opens = np.roll(closes, 1)
    opens[0] = base
    
    highs = np.maximum(opens, closes) * (1 + np.abs(np.random.randn(n)) * 0.002)
    lows = np.minimum(opens, closes) * (1 - np.abs(np.random.randn(n)) * 0.002)
    volumes = np.random.randn(n) * 100 + 1000
    volumes[45:50] = [3000, 4000, 5000, 4500, 3500]  # High volume during cascade
    
    data = pd.DataFrame({
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': volumes,
    })
    
    strategy = LiquidationCascadeContinuationStrategy()
    signals = strategy.generate_signals(data)
    print(f"Signals generated: {len(signals)}")
    for sig in signals:
        print(f"{sig.direction} {sig.symbol} @ {sig.entry_price} (conf: {sig.confidence}) - {sig.reason}")
