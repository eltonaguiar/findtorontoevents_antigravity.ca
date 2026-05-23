"""
Strategy 074: Williams %R
Williams Percent Range strategy
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class WilliamsRStrategy:
    """Williams %R overbought/oversold strategy."""
    
    def __init__(self, period: int = 14, overbought: float = -20, oversold: float = -80):
        self.period = period
        self.overbought = overbought
        self.oversold = oversold
    
    def analyze(self, highs: List[float], lows: List[float], closes: List[float]) -> Signal:
        if len(closes) < self.period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        highest_high = max(highs[-self.period:])
        lowest_low = min(lows[-self.period:])
        
        if highest_high == lowest_low:
            return Signal("hold", 0.0, {"error": "No range"})
        
        wr = -100 * (highest_high - closes[-1]) / (highest_high - lowest_low)
        
        # Previous for crossover
        prev_wr = -100 * (highest_high - closes[-2]) / (highest_high - lowest_low) if len(closes) > 1 else wr
        
        metadata = {"williams_r": wr}
        
        if wr < self.oversold and prev_wr >= self.oversold:
            return Signal("buy", 0.75, metadata)
        if wr > self.overbought and prev_wr <= self.overbought:
            return Signal("sell", 0.75, metadata)
        if wr < self.oversold:
            return Signal("buy", 0.55, metadata)
        if wr > self.overbought:
            return Signal("sell", 0.55, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    highs = [40200]*15
    lows = [39800]*15
    closes = [39850]*15
    s = WilliamsRStrategy()
    sig = s.analyze(highs, lows, closes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
