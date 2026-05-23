"""
Strategy 165: Gain to Pain
Gain to pain ratio
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class GainPainStrategy:
    """Gain to pain ratio."""
    
    def __init__(self, period: int = 36):
        self.period = period
    
    def analyze(self, returns: List[float]) -> Signal:
        if len(returns) < self.period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        r = returns[-self.period:]
        
        sum_returns = sum(r)
        sum_abs = sum(abs(ri) for ri in r)
        
        gpr = sum_returns / sum_abs if sum_abs > 0 else 0
        
        metadata = {"gpr": gpr}
        
        if gpr > 0.3:
            return Signal("buy", 0.7, metadata)
        if gpr < -0.2:
            return Signal("sell", 0.7, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    returns = [0.001 + np.random.randn()*0.01 for _ in range(40)]
    s = GainPainStrategy()
    sig = s.analyze(returns)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
