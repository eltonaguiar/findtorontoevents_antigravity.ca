"""
Strategy 155: Pain Ratio
Pain-adjusted returns
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class PainRatioStrategy:
    """Pain ratio (return / pain index)."""
    
    def __init__(self, period: int = 36):
        self.period = period
    
    def analyze(self, closes: List[float]) -> Signal:
        if len(closes) < self.period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        returns = (closes[-1] - closes[-self.period]) / closes[-self.period]
        
        # Pain index (sum of drawdowns)
        pain = 0
        peak = closes[-self.period]
        for c in closes[-self.period:]:
            if c > peak:
                peak = c
            pain += (peak - c) / peak * 100
        
        pain_ratio = returns / pain if pain != 0 else returns
        
        metadata = {"pain_ratio": pain_ratio}
        
        if pain_ratio > 0.1:
            return Signal("buy", 0.7, metadata)
        if pain_ratio < -0.1:
            return Signal("sell", 0.7, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    closes = [40000 + i*100 for i in range(40)]
    s = PainRatioStrategy()
    sig = s.analyze(closes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
