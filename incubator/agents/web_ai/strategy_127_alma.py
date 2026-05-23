"""
Strategy 127: Arnaud Legoux MA
ALMA Gaussian filter
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class ALMAStrategy:
    """Arnaud Legoux Moving Average."""
    
    def __init__(self, period: int = 9, offset: float = 0.85, sigma: float = 6):
        self.period = period
        self.offset = offset
        self.sigma = sigma
    
    def analyze(self, closes: List[float]) -> Signal:
        if len(closes) < self.period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Simplified ALMA (Gaussian weighted)
        m = self.offset * (self.period - 1)
        s = self.period / self.sigma
        
        weights = [np.exp(-((i - m) ** 2) / (2 * s ** 2)) for i in range(self.period)]
        weights = [w / sum(weights) for w in weights]
        
        alma = sum(c * w for c, w in zip(closes[-self.period:], weights))
        
        metadata = {"alma": alma}
        
        if closes[-1] > alma:
            return Signal("buy", 0.6, metadata)
        if closes[-1] < alma:
            return Signal("sell", 0.6, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    closes = [40000 + i*40 for i in range(15)]
    s = ALMAStrategy()
    sig = s.analyze(closes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
