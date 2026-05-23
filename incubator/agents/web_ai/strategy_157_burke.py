"""
Strategy 157: Burke Ratio
Burke drawdown ratio
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class BurkeStrategy:
    """Burke ratio (return / sqrt sum of squared drawdowns)."""
    
    def __init__(self, period: int = 36):
        self.period = period
    
    def analyze(self, closes: List[float]) -> Signal:
        if len(closes) < self.period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        returns = (closes[-1] - closes[-self.period]) / closes[-self.period]
        
        # Sum of squared drawdowns
        dds_sq = []
        peak = closes[-self.period]
        for c in closes[-self.period:]:
            if c > peak:
                peak = c
            dds_sq.append(((peak - c) / peak) ** 2)
        
        burke = returns / np.sqrt(sum(dds_sq)) if sum(dds_sq) > 0 else returns
        
        metadata = {"burke": burke}
        
        if burke > 1:
            return Signal("buy", 0.7, metadata)
        if burke < -0.5:
            return Signal("sell", 0.7, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    closes = [40000 + i*100 for i in range(40)]
    s = BurkeStrategy()
    sig = s.analyze(closes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
