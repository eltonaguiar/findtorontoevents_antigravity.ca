"""
Strategy 146: Sortino Ratio
Sortino downside risk
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class SortinoStrategy:
    """Sortino ratio (downside deviation)."""
    
    def __init__(self, period: int = 30, target: float = 0):
        self.period = period
        self.target = target
    
    def analyze(self, returns: List[float]) -> Signal:
        if len(returns) < self.period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        r = returns[-self.period:]
        
        # Downside deviation
        downside = [min(0, ri - self.target) ** 2 for ri in r]
        dd = np.sqrt(np.mean(downside))
        
        sortino = (np.mean(r) - self.target) / dd if dd > 0 else 0
        
        metadata = {"sortino": sortino}
        
        if sortino > 1.5:
            return Signal("buy", 0.7, metadata)
        if sortino < -0.5:
            return Signal("sell", 0.7, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    returns = [0.001 + np.random.randn()*0.01 for _ in range(35)]
    s = SortinoStrategy()
    sig = s.analyze(returns)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
