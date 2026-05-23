"""
Strategy 170: R-Multiple
R-multiple distribution
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class RMultipleStrategy:
    """R-multiple trade sizing."""
    
    def __init__(self, period: int = 30):
        self.period = period
    
    def analyze(self, returns: List[float], risks: List[float]) -> Signal:
        if len(returns) < self.period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        r_multiples = [ret / risk if risk > 0 else 0 for ret, risk in zip(returns[-self.period:], risks[-self.period:])]
        
        avg_r = np.mean(r_multiples)
        
        metadata = {"avg_r": avg_r}
        
        if avg_r > 2:
            return Signal("buy", 0.75, metadata)
        if avg_r < 0.5:
            return Signal("sell", 0.7, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    returns = [0.02 if i%4==0 else -0.005 for i in range(35)]
    risks = [0.01]*35
    s = RMultipleStrategy()
    sig = s.analyze(returns, risks)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
