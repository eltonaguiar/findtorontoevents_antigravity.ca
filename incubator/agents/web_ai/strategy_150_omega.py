"""
Strategy 150: Omega Ratio
Omega downside/upside
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class OmegaStrategy:
    """Omega ratio (gains/losses relative to threshold)."""
    
    def __init__(self, period: int = 30, threshold: float = 0):
        self.period = period
        self.threshold = threshold
    
    def analyze(self, returns: List[float]) -> Signal:
        if len(returns) < self.period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        r = returns[-self.period:]
        
        gains = sum(max(0, ri - self.threshold) for ri in r)
        losses = sum(max(0, self.threshold - ri) for ri in r)
        
        omega = gains / losses if losses > 0 else float('inf')
        
        metadata = {"omega": omega}
        
        if omega > 1.5:
            return Signal("buy", 0.7, metadata)
        if omega < 0.7:
            return Signal("sell", 0.7, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    returns = [0.001 + np.random.randn()*0.01 for _ in range(35)]
    s = OmegaStrategy()
    sig = s.analyze(returns)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
