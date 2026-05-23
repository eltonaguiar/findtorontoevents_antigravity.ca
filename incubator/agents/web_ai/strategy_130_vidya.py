"""
Strategy 130: VIDYA Volatility Index
VIDYA adaptive average
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class VIDYAStrategy:
    """Variable Index Dynamic Average."""
    
    def __init__(self, period: int = 14):
        self.period = period
    
    def analyze(self, closes: List[float]) -> Signal:
        if len(closes) < self.period + 1:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Standard deviation (volatility)
        std = np.std(closes[-self.period:])
        
        # CMO (simplified)
        changes = [closes[i] - closes[i-1] for i in range(-self.period, 0)]
        up = sum(c for c in changes if c > 0)
        down = sum(abs(c) for c in changes if c < 0)
        cmo = 100 * (up - down) / (up + down) if (up + down) > 0 else 0
        
        # VIDYA alpha
        alpha = 2 / (self.period + 1)
        sc = alpha * abs(cmo) / 100
        
        # VIDYA
        vidya = closes[-self.period]
        for close in closes[-self.period+1:]:
            vidya = sc * close + (1 - sc) * vidya
        
        metadata = {"vidya": vidya}
        
        if closes[-1] > vidya:
            return Signal("buy", 0.6, metadata)
        if closes[-1] < vidya:
            return Signal("sell", 0.6, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    closes = [40000 + i*50 for i in range(20)]
    s = VIDYAStrategy()
    sig = s.analyze(closes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
