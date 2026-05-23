"""
Strategy 118: Vertical Horizontal Filter
VHF trend detection
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class VHFStrategy:
    """Vertical Horizontal Filter."""
    
    def __init__(self, period: int = 28):
        self.period = period
    
    def analyze(self, closes: List[float]) -> Signal:
        if len(closes) < self.period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        highest = max(closes[-self.period:])
        lowest = min(closes[-self.period:])
        
        changes = sum(abs(closes[i] - closes[i-1]) for i in range(-self.period+1, 0))
        
        vhf = (highest - lowest) / changes if changes > 0 else 0
        
        metadata = {"vhf": vhf}
        
        if vhf > 0.5:
            return Signal("buy", 0.65, metadata)
        if vhf < 0.3:
            return Signal("sell", 0.65, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    closes = [40000 + i*100 for i in range(30)]
    s = VHFStrategy()
    sig = s.analyze(closes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
