"""
Strategy 190: Cointegration Test
Engle-Granger test
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class CointegrationTestStrategy:
    """Cointegration trading signal."""
    
    def __init__(self, period: int = 60):
        self.period = period
    
    def analyze(self, x: List[float], y: List[float]) -> Signal:
        if len(x) < self.period or len(y) < self.period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Spread
        spread = [xi - yi for xi, yi in zip(x[-self.period:], y[-self.period:])]
        
        # Mean reversion test
        half_life = -np.log(2) / np.log(abs(np.corrcoef(spread[:-1], spread[1:])[0, 1])) if len(spread) > 1 else float('inf')
        
        z_score = (spread[-1] - np.mean(spread)) / np.std(spread) if np.std(spread) > 0 else 0
        
        metadata = {"z_score": z_score, "half_life": half_life}
        
        if half_life < 10 and z_score > 2:
            return Signal("sell", 0.75, metadata)
        if half_life < 10 and z_score < -2:
            return Signal("buy", 0.75, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    x = [40000 + i*50 for i in range(70)]
    y = [20000 + i*25 for i in range(70)]
    s = CointegrationTestStrategy()
    sig = s.analyze(x, y)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
