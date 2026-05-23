"""
Strategy 154: Ulcer Index
Ulcer downside risk
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class UlcerIndexStrategy:
    """Ulcer Index downside risk."""
    
    def __init__(self, period: int = 14):
        self.period = period
    
    def analyze(self, closes: List[float]) -> Signal:
        if len(closes) < self.period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Rolling max
        ulcer_squared = []
        for i in range(-self.period, 0):
            c = closes[i]
            peak = max(closes[i-self.period:i+1]) if i+1 > 0 else c
            dd = (c - peak) / peak if peak > 0 else 0
            ulcer_squared.append(dd ** 2 * 100)
        
        ulcer = np.sqrt(np.mean(ulcer_squared))
        
        metadata = {"ulcer": ulcer}
        
        if ulcer > 10:
            return Signal("sell", 0.65, metadata)
        if ulcer < 3:
            return Signal("buy", 0.65, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    closes = [40000 - i*200 for i in range(20)]
    s = UlcerIndexStrategy()
    sig = s.analyze(closes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
