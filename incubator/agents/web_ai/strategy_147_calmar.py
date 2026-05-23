"""
Strategy 147: Calmar Ratio
Calmar drawdown ratio
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class CalmarStrategy:
    """Calmar ratio (return / max drawdown)."""
    
    def __init__(self, period: int = 36):
        self.period = period
    
    def analyze(self, closes: List[float]) -> Signal:
        if len(closes) < self.period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        returns = (closes[-1] - closes[-self.period]) / closes[-self.period]
        
        # Max drawdown
        peak = closes[-self.period]
        max_dd = 0
        for c in closes[-self.period:]:
            if c > peak:
                peak = c
            dd = (peak - c) / peak
            max_dd = max(max_dd, dd)
        
        calmar = returns / max_dd if max_dd > 0 else returns
        
        metadata = {"calmar": calmar, "max_dd": max_dd}
        
        if calmar > 2:
            return Signal("buy", 0.7, metadata)
        if calmar < -1:
            return Signal("sell", 0.7, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    closes = [40000 + i*100 for i in range(40)]
    s = CalmarStrategy()
    sig = s.analyze(closes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
