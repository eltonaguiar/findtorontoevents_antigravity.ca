"""
Strategy 156: Sterling Ratio
Sterling risk-adjusted
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class SterlingStrategy:
    """Sterling ratio (return / avg drawdown)."""
    
    def __init__(self, period: int = 36):
        self.period = period
    
    def analyze(self, closes: List[float]) -> Signal:
        if len(closes) < self.period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        returns = (closes[-1] - closes[-self.period]) / closes[-self.period]
        
        # Average drawdown
        dds = []
        peak = closes[-self.period]
        for c in closes[-self.period:]:
            if c > peak:
                peak = c
            dds.append((peak - c) / peak)
        
        avg_dd = np.mean(dds)
        sterling = returns / avg_dd if avg_dd > 0 else returns
        
        metadata = {"sterling": sterling}
        
        if sterling > 2:
            return Signal("buy", 0.7, metadata)
        if sterling < -1:
            return Signal("sell", 0.7, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    closes = [40000 + i*100 for i in range(40)]
    s = SterlingStrategy()
    sig = s.analyze(closes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
