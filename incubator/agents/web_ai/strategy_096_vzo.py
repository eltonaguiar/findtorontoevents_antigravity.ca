"""
Strategy 096: Volume Zone Oscillator
VZO volume-based trend
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class VZOStrategy:
    """Volume Zone Oscillator volume-weighted trend."""
    
    def __init__(self, period: int = 60):
        self.period = period
    
    def analyze(self, closes: List[float], volumes: List[float]) -> Signal:
        if len(closes) < self.period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # R volume (volume on up days - volume on down days)
        vp = sum(volumes[i] for i in range(-self.period, 0) if closes[i] > closes[i-1])
        vm = sum(volumes[i] for i in range(-self.period, 0) if closes[i] < closes[i-1])
        
        tv = sum(volumes[-self.period:])
        
        vzo = 100 * (vp - vm) / tv if tv > 0 else 0
        
        metadata = {"vzo": vzo}
        
        if vzo > 40:
            return Signal("buy", 0.7, metadata)
        if vzo < -40:
            return Signal("sell", 0.7, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    closes = [40000 + i*30 for i in range(70)]
    volumes = [1000 + (i%10)*100 for i in range(70)]
    s = VZOStrategy()
    sig = s.analyze(closes, volumes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
