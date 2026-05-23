"""
Strategy 158: Martin Ratio
Martin ulcer ratio
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class MartinStrategy:
    """Martin ratio (return / ulcer index)."""
    
    def __init__(self, period: int = 36):
        self.period = period
    
    def analyze(self, closes: List[float]) -> Signal:
        if len(closes) < self.period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        returns = (closes[-1] - closes[-self.period]) / closes[-self.period]
        
        # Ulcer index
        dds_sq = []
        peak = closes[-self.period]
        for c in closes[-self.period:]:
            if c > peak:
                peak = c
            dds_sq.append(((peak - c) / peak * 100) ** 2)
        
        ulcer = np.sqrt(np.mean(dds_sq))
        martin = returns / ulcer if ulcer > 0 else returns
        
        metadata = {"martin": martin}
        
        if martin > 0.5:
            return Signal("buy", 0.7, metadata)
        if martin < -0.3:
            return Signal("sell", 0.7, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    closes = [40000 + i*100 for i in range(40)]
    s = MartinStrategy()
    sig = s.analyze(closes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
