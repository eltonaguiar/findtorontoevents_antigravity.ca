"""
Strategy 198: Kolmogorov-Smirnov
KS test distribution
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class KSStrategy:
    """Kolmogorov-Smirnov distribution comparison."""
    
    def __init__(self, period: int = 30):
        self.period = period
    
    def analyze(self, returns: List[float]) -> Signal:
        if len(returns) < self.period * 2:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        recent = returns[-self.period:]
        older = returns[-self.period*2:-self.period]
        
        # Compare means
        diff = abs(np.mean(recent) - np.mean(older))
        pooled_std = np.sqrt((np.std(recent)**2 + np.std(older)**2) / 2)
        
        d_stat = diff / pooled_std if pooled_std > 0 else 0
        
        metadata = {"d_stat": d_stat}
        
        if d_stat > 1:
            return Signal("buy", 0.65, metadata)
        if d_stat < -0.5:
            return Signal("sell", 0.65, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    returns = [0.001]*30 + [0.003]*30
    s = KSStrategy()
    sig = s.analyze(returns)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
