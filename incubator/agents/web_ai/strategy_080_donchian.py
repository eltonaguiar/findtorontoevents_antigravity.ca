"""
Strategy 080: Donchian Channels
Donchian Channel breakout
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class DonchianStrategy:
    """Donchian Channel breakout system."""
    
    def __init__(self, period: int = 20):
        self.period = period
    
    def analyze(self, highs: List[float], lows: List[float], closes: List[float]) -> Signal:
        if len(closes) < self.period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        upper = max(highs[-self.period:])
        lower = min(lows[-self.period:])
        middle = (upper + lower) / 2
        
        current = closes[-1]
        prev = closes[-2]
        
        metadata = {"upper": upper, "lower": lower, "middle": middle}
        
        # Breakout
        if current > upper and prev <= upper:
            return Signal("buy", 0.75, metadata)
        if current < lower and prev >= lower:
            return Signal("sell", 0.75, metadata)
        
        # Within channel
        if current > middle:
            return Signal("buy", 0.55, metadata)
        if current < middle:
            return Signal("sell", 0.55, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    highs = [40000 + (i%20)*10 for i in range(25)]
    highs[-1] = 40500  # Breakout
    lows = [h-200 for h in highs]
    closes = [(h+l)/2 for h,l in zip(highs, lows)]
    s = DonchianStrategy()
    sig = s.analyze(highs, lows, closes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
