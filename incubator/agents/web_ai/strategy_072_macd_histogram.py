"""
Strategy 072: MACD Histogram
MACD histogram momentum strategy
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class MACDHistogramStrategy:
    """Trades MACD histogram divergences and zero-line crosses."""
    
    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        self.fast = fast
        self.slow = slow
        self.signal = signal
    
    def _ema(self, data: List[float], period: int) -> List[float]:
        multiplier = 2 / (period + 1)
        ema = [data[0]]
        for price in data[1:]:
            ema.append((price - ema[-1]) * multiplier + ema[-1])
        return ema
    
    def analyze(self, prices: List[float], volumes: List[float]) -> Signal:
        if len(prices) < self.slow + self.signal:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        fast_ema = self._ema(prices, self.fast)
        slow_ema = self._ema(prices, self.slow)
        
        macd_line = [f - s for f, s in zip(fast_ema, slow_ema)]
        signal_line = self._ema(macd_line, self.signal)
        
        histogram = [m - s for m, s in zip(macd_line[-len(signal_line):], signal_line)]
        
        # Signals
        hist_rising = histogram[-1] > histogram[-2] > histogram[-3]
        hist_falling = histogram[-1] < histogram[-2] < histogram[-3]
        zero_cross_up = histogram[-2] < 0 and histogram[-1] > 0
        zero_cross_down = histogram[-2] > 0 and histogram[-1] < 0
        
        metadata = {"histogram": histogram[-1], "macd": macd_line[-1]}
        
        if zero_cross_up:
            return Signal("buy", 0.75, metadata)
        if zero_cross_down:
            return Signal("sell", 0.75, metadata)
        if hist_rising and histogram[-1] > 0:
            return Signal("buy", 0.6, metadata)
        if hist_falling and histogram[-1] < 0:
            return Signal("sell", 0.6, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    prices = [40000 + i*50 + np.random.randn()*100 for i in range(50)]
    s = MACDHistogramStrategy()
    sig = s.analyze(prices, [1000]*50)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
