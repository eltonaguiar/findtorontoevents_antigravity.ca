"""
Strategy 076: ADX Trend Strength
Average Directional Index strategy
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class ADXStrategy:
    """ADX trend strength with DI crossovers."""
    
    def __init__(self, period: int = 14, threshold: float = 25):
        self.period = period
        self.threshold = threshold
    
    def analyze(self, highs: List[float], lows: List[float], closes: List[float]) -> Signal:
        if len(closes) < self.period + 1:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Calculate +DM and -DM
        plus_dm = [highs[i] - highs[i-1] if highs[i] - highs[i-1] > lows[i-1] - lows[i] else 0 
                   for i in range(1, len(highs))]
        minus_dm = [lows[i-1] - lows[i] if lows[i-1] - lows[i] > highs[i] - highs[i-1] else 0
                    for i in range(1, len(lows))]
        
        # True range
        tr = [max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
              for i in range(1, len(highs))]
        
        # Smoothed averages
        atr = np.mean(tr[-self.period:])
        plus_di = 100 * np.mean(plus_dm[-self.period:]) / atr if atr > 0 else 0
        minus_di = 100 * np.mean(minus_dm[-self.period:]) / atr if atr > 0 else 0
        
        # ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di) if (plus_di + minus_di) > 0 else 0
        
        metadata = {"adx": dx, "plus_di": plus_di, "minus_di": minus_di}
        
        if dx > self.threshold and plus_di > minus_di:
            return Signal("buy", 0.75, metadata)
        if dx > self.threshold and minus_di > plus_di:
            return Signal("sell", 0.75, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    highs = [40000 + i*100 for i in range(20)]
    lows = [39900 + i*100 for i in range(20)]
    closes = [39950 + i*100 for i in range(20)]
    s = ADXStrategy()
    sig = s.analyze(highs, lows, closes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
