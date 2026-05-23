"""
Strategy 160: Prospect Ratio
Prospect theory ratio
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class ProspectStrategy:
    """Prospect theory adjusted ratio."""
    
    def __init__(self, period: int = 30, loss_aversion: float = 2.25):
        self.period = period
        self.la = loss_aversion
    
    def analyze(self, returns: List[float]) -> Signal:
        if len(returns) < self.period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        r = returns[-self.period:]
        
        gains = sum(ri for ri in r if ri > 0)
        losses = sum(abs(ri) for ri in r if ri < 0) * self.la
        
        prospect = (gains - losses) / len(r)
        
        metadata = {"prospect": prospect}
        
        if prospect > 0.005:
            return Signal("buy", 0.7, metadata)
        if prospect < -0.005:
            return Signal("sell", 0.7, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    returns = [0.001 + np.random.randn()*0.01 for _ in range(35)]
    s = ProspectStrategy()
    sig = s.analyze(returns)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
