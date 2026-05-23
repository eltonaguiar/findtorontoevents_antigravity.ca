"""
Strategy 126: Hull Moving Average
Hull MA fast response
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class HullMAStrategy:
    """Hull Moving Average."""
    
    def __init__(self, period: int = 16):
        self.period = period
    
    def _wma(self, data: List[float], period: int) -> float:
        weights = list(range(1, period + 1))
        return sum(d * w for d, w in zip(data[-period:], weights)) / sum(weights)
    
    def analyze(self, closes: List[float]) -> Signal:
        if len(closes) < self.period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        half = self.period // 2
        sqrt_period = int(np.sqrt(self.period))
        
        wma_half = self._wma(closes, half)
        wma_full = self._wma(closes, self.period)
        
        raw = 2 * wma_half - wma_full
        
        # Simplified HMA
        hma = np.mean(closes[-sqrt_period:])
        
        metadata = {"hma": hma}
        
        if closes[-1] > hma and closes[-2] <= hma:
            return Signal("buy", 0.7, metadata)
        if closes[-1] < hma and closes[-2] >= hma:
            return Signal("sell", 0.7, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    closes = [40000 + i*50 for i in range(20)]
    s = HullMAStrategy()
    sig = s.analyze(closes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
