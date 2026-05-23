"""
Strategy 131: Kaufman Efficiency
Kaufman Efficiency Ratio
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class KaufmanEfficiencyStrategy:
    """Kaufman Efficiency Ratio for trend strength."""
    
    def __init__(self, period: int = 10):
        self.period = period
    
    def analyze(self, closes: List[float]) -> Signal:
        if len(closes) < self.period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        change = abs(closes[-1] - closes[-self.period])
        volatility = sum(abs(closes[i] - closes[i-1]) for i in range(-self.period+1, 0))
        
        er = change / volatility if volatility > 0 else 0
        
        metadata = {"er": er}
        
        if er > 0.6:
            return Signal("buy", 0.7, metadata)
        if er < 0.3:
            return Signal("sell", 0.6, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    closes = [40000 + i*100 for i in range(15)]
    s = KaufmanEfficiencyStrategy()
    sig = s.analyze(closes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
