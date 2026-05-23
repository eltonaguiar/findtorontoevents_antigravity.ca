"""
Strategy 184: Change Point
Change point detection
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class ChangePointStrategy:
    """Bayesian change point detection."""
    
    def __init__(self, period: int = 30):
        self.period = period
    
    def analyze(self, returns: List[float]) -> Signal:
        if len(returns) < self.period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Simple change detection
        first_half = np.mean(returns[-self.period:-self.period//2])
        second_half = np.mean(returns[-self.period//2:])
        
        change = abs(second_half - first_half)
        
        metadata = {"change": change}
        
        if change > 0.005 and second_half > first_half:
            return Signal("buy", 0.7, metadata)
        if change > 0.005 and second_half < first_half:
            return Signal("sell", 0.7, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    returns = [0.001]*15 + [0.005]*15
    s = ChangePointStrategy()
    sig = s.analyze(returns)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
