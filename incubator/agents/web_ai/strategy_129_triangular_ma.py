"""
Strategy 129: Triangular MA
Triangular moving average
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class TriangularMAStrategy:
    """Triangular Moving Average."""
    
    def __init__(self, period: int = 14):
        self.period = period
    
    def analyze(self, closes: List[float]) -> Signal:
        if len(closes) < self.period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Double-smoothed SMA
        half = self.period // 2
        
        # First SMA
        sma1 = [np.mean(closes[i:i+half]) for i in range(len(closes)-self.period+1, len(closes)-half+1)]
        
        # Second SMA of first SMAs
        tma = np.mean(sma1) if sma1 else closes[-1]
        
        metadata = {"tma": tma}
        
        if closes[-1] > tma:
            return Signal("buy", 0.6, metadata)
        if closes[-1] < tma:
            return Signal("sell", 0.6, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    closes = [40000 + i*40 for i in range(20)]
    s = TriangularMAStrategy()
    sig = s.analyze(closes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
