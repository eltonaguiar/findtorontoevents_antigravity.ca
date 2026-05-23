"""
Strategy 086: Rate of Change
ROC momentum strategy
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class ROCStrategy:
    """Rate of Change momentum."""
    
    def __init__(self, period: int = 12, threshold: float = 5):
        self.period = period
        self.threshold = threshold
    
    def analyze(self, closes: List[float]) -> Signal:
        if len(closes) <= self.period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        roc = 100 * (closes[-1] - closes[-self.period-1]) / closes[-self.period-1]
        
        metadata = {"roc": roc}
        
        if roc > self.threshold:
            return Signal("buy", 0.65, metadata)
        if roc < -self.threshold:
            return Signal("sell", 0.65, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    closes = [40000 + i*100 for i in range(15)]
    s = ROCStrategy()
    sig = s.analyze(closes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
