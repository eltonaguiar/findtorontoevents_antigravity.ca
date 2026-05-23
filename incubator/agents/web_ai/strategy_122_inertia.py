"""
Strategy 122: Inertia
Inertia trend measurement
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class InertiaStrategy:
    """Inertia indicator (linear regression R-squared)."""
    
    def __init__(self, period: int = 20):
        self.period = period
    
    def analyze(self, closes: List[float]) -> Signal:
        if len(closes) < self.period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        x = list(range(self.period))
        y = closes[-self.period:]
        
        slope = np.polyfit(x, y, 1)[0]
        
        metadata = {"slope": slope}
        
        if slope > 50:
            return Signal("buy", 0.65, metadata)
        if slope < -50:
            return Signal("sell", 0.65, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    closes = [40000 + i*60 for i in range(25)]
    s = InertiaStrategy()
    sig = s.analyze(closes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
