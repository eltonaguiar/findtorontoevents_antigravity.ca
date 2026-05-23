"""
Baby Strategy 061: Liquidation Wick Capture

Captures mean reversion after liquidation-induced price wicks.
When price spikes/drops rapidly due to liquidations, then reverses quickly,
this strategy enters in the reversal direction.

Category: Liquidation Strategies
Best for: Volatile markets with frequent liquidation cascades
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Signal:
    symbol: str
    direction: str  # "BUY" or "SELL"
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


class Strategy061LiquidationWickCapture:
    """
    Captures price wicks caused by liquidations.
    
    Logic:
    - Detects rapid price movement (wick) followed by quick reversal
    - Enters when wick exceeds ATR threshold and price returns toward open
    - Targets partial retracement of the wick
    """
    
    def __init__(self, params: Optional[dict] = None):
        self.p = params or {}
        self.wick_mult = self.p.get('wick_mult', 2.0)  # Wick must be 2x ATR
        self.reversal_pct = self.p.get('reversal_pct', 0.3)  # 30% retracement for entry
        self.tp_atr = self.p.get('tp_atr', 1.5)
        self.sl_atr = self.p.get('sl_atr', 1.0)
        self.lookback = self.p.get('lookback', 20)
        
    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.lookback + 5:
            return []
        
        # Calculate ATR
        atr = self._atr(data, self.lookback)
        current_atr = atr.iloc[-1]
        
        # Get recent candle data
        prev_idx = -2  # Previous completed candle
        open_price = data['open'].iloc[prev_idx]
        high_price = data['high'].iloc[prev_idx]
        low_price = data['low'].iloc[prev_idx]
        close_price = data['close'].iloc[prev_idx]
        current_price = data['close'].iloc[-1]
        
        # Calculate wick sizes
        upper_wick = high_price - max(open_price, close_price)
        lower_wick = min(open_price, close_price) - low_price
        body_size = abs(close_price - open_price)
        
        signals = []
        
        # Long wick down (liquidation of longs) followed by reversal
        if lower_wick > self.wick_mult * current_atr and lower_wick > body_size * 2:
            # Check for reversal - price has moved back up from the low
            reversal_from_low = (current_price - low_price) / lower_wick
            if reversal_from_low >= self.reversal_pct:
                confidence = min(0.5 + reversal_from_low * 0.4, 0.9)
                signals.append(Signal(
                    symbol=symbol,
                    direction="BUY",
                    confidence=round(confidence, 2),
                    entry_price=round(current_price, 2),
                    take_profit=round(current_price + current_atr * self.tp_atr, 2),
                    stop_loss=round(current_price - current_atr * self.sl_atr, 2),
                    reason=f"Long liq wick {lower_wick/current_atr:.1f}x ATR, {reversal_from_low*100:.0f}% retraced"
                ))
        
        # Long wick up (liquidation of shorts) followed by reversal
        elif upper_wick > self.wick_mult * current_atr and upper_wick > body_size * 2:
            # Check for reversal - price has moved back down from the high
            reversal_from_high = (high_price - current_price) / upper_wick
            if reversal_from_high >= self.reversal_pct:
                confidence = min(0.5 + reversal_from_high * 0.4, 0.9)
                signals.append(Signal(
                    symbol=symbol,
                    direction="SELL",
                    confidence=round(confidence, 2),
                    entry_price=round(current_price, 2),
                    take_profit=round(current_price - current_atr * self.tp_atr, 2),
                    stop_loss=round(current_price + current_atr * self.sl_atr, 2),
                    reason=f"Short liq wick {upper_wick/current_atr:.1f}x ATR, {reversal_from_high*100:.0f}% retraced"
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
    # Test with synthetic liquidation wick data
    np.random.seed(42)
    n = 100
    base = 50000
    
    # Create data with a liquidation wick
    closes = np.random.randn(n).cumsum() * 100 + base
    opens = np.roll(closes, 1)
    opens[0] = base
    
    # Inject a liquidation wick
    idx = 50
    opens[idx] = closes[idx-1]
    closes[idx] = opens[idx] - 200  # Down candle
    highs = np.maximum(opens, closes) + np.abs(np.random.randn(n)) * 50
    lows = np.minimum(opens, closes) - np.abs(np.random.randn(n)) * 50
    
    # Make a big lower wick (liquidation)
    lows[idx] = min(opens[idx], closes[idx]) - 800  # Big wick down
    
    data = pd.DataFrame({
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
    })
    
    strategy = LiquidationWickCaptureStrategy()
    signals = strategy.generate_signals(data)
    print(f"Signals generated: {len(signals)}")
    for sig in signals:
        print(f"{sig.direction} {sig.symbol} @ {sig.entry_price} (conf: {sig.confidence}) - {sig.reason}")
