"""
Strategy 148: Information Ratio
Information ratio alpha
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class InformationRatioStrategy:
    """Information ratio (active return / tracking error)."""
    
    def __init__(self, period: int = 30):
        self.period = period
    
    def analyze(self, returns: List[float], benchmark: List[float]) -> Signal:
        if len(returns) < self.period or len(benchmark) < self.period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        r = returns[-self.period:]
        b = benchmark[-self.period:]
        
        active = [ri - bi for ri, bi in zip(r, b)]
        
        ir = np.mean(active) / np.std(active) if np.std(active) > 0 else 0
        
        metadata = {"ir": ir}
        
        if ir > 0.5:
            return Signal("buy", 0.7, metadata)
        if ir < -0.5:
            return Signal("sell", 0.7, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    returns = [0.001 + np.random.randn()*0.01 for _ in range(35)]
    benchmark = [0.0005 + np.random.randn()*0.008 for _ in range(35)]
    s = InformationRatioStrategy()
    sig = s.analyze(returns, benchmark)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
