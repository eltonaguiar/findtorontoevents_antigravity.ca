"""
Strategy 134: Mean Absolute Deviation
MAD volatility
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class MADStrategy:
    """Mean Absolute Deviation bands."""
    
    def __init__(self, period: int = 20, multiplier: float = 2):
        self.period = period
        self.mult = multiplier
    
    def analyze(self, closes: List[float]) -> Signal:
        if len(closes) < self.period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        median = np.median(closes[-self.period:])
        mad = np.mean([abs(c - median) for c in closes[-self.period:]])
        
        upper = median + self.mult * mad
        lower = median - self.mult * mad
        
        current = closes[-1]
        
        metadata = {"median": median, "upper": upper, "lower": lower}
        
        if current > upper:
            return Signal("sell", 0.65, metadata)
        if current < lower:
            return Signal("buy", 0.65, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    closes = [40000 + np.random.randn()*200 for _ in range(25)]
    s = MADStrategy()
    sig = s.analyze(closes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
