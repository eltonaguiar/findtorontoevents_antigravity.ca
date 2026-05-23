"""
Strategy 132: Fractal Dimension
Fractal dimension index
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class FractalDimensionStrategy:
    """Fractal Dimension Index for trend/range."""
    
    def __init__(self, period: int = 14):
        self.period = period
    
    def analyze(self, highs: List[float], lows: List[float]) -> Signal:
        if len(highs) < self.period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Calculate fractal dimension
        prices = [(h + l) / 2 for h, l in zip(highs[-self.period:], lows[-self.period:])]
        
        n = len(prices)
        max_p = max(prices)
        min_p = min(prices)
        
        if max_p == min_p:
            return Signal("hold", 0.0, {"error": "No range"})
        
        # Normalize
        normalized = [(p - min_p) / (max_p - min_p) for p in prices]
        
        # Simplified fractal dimension
        fd = 1 + np.std(normalized)
        
        metadata = {"fd": fd}
        
        if fd < 1.4:
            return Signal("buy", 0.65, metadata)
        if fd > 1.6:
            return Signal("sell", 0.65, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    highs = [40200]*15
    lows = [39800]*15
    s = FractalDimensionStrategy()
    sig = s.analyze(highs, lows)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
