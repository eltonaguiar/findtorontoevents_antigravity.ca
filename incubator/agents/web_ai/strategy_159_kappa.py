"""
Strategy 159: Kappa Ratio
Kappa higher moments
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class KappaStrategy:
    """Kappa ratio (return / LPM)."""
    
    def __init__(self, period: int = 30, threshold: float = 0, order: int = 3):
        self.period = period
        self.threshold = threshold
        self.order = order
    
    def analyze(self, returns: List[float]) -> Signal:
        if len(returns) < self.period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        r = returns[-self.period:]
        
        # Lower partial moment
        lpm = sum(max(0, self.threshold - ri) ** self.order for ri in r) / len(r)
        
        kappa = (np.mean(r) - self.threshold) / (lpm ** (1/self.order)) if lpm > 0 else 0
        
        metadata = {"kappa": kappa}
        
        if kappa > 1:
            return Signal("buy", 0.7, metadata)
        if kappa < -0.5:
            return Signal("sell", 0.7, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    returns = [0.001 + np.random.randn()*0.01 for _ in range(35)]
    s = KappaStrategy()
    sig = s.analyze(returns)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
