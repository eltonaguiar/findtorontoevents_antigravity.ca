"""
Strategy 181: Regime Switching
Regime detection
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class RegimeSwitchingStrategy:
    """Markov regime switching."""
    
    def __init__(self, period: int = 30):
        self.period = period
    
    def analyze(self, returns: List[float]) -> Signal:
        if len(returns) < self.period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        r = returns[-self.period:]
        
        # Simple regime detection
        vol = np.std(r)
        mean = np.mean(r)
        
        if vol > 0.02:
            regime = "high_vol"
        elif mean > 0.001:
            regime = "trending"
        else:
            regime = "ranging"
        
        metadata = {"regime": regime}
        
        if regime == "trending" and mean > 0:
            return Signal("buy", 0.7, metadata)
        if regime == "high_vol" and mean < 0:
            return Signal("sell", 0.65, metadata)
        return Signal("hold", 0.25, metadata)

if __name__ == "__main__":
    returns = [0.002 + np.random.randn()*0.005 for _ in range(35)]
    s = RegimeSwitchingStrategy()
    sig = s.analyze(returns)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
