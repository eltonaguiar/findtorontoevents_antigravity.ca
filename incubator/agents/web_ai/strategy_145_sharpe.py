"""
Strategy 145: Sharpe Ratio
Sharpe ratio momentum
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class SharpeRatioStrategy:
    """Rolling Sharpe ratio."""
    
    def __init__(self, period: int = 30, risk_free: float = 0):
        self.period = period
        self.rf = risk_free
    
    def analyze(self, returns: List[float]) -> Signal:
        if len(returns) < self.period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        r = returns[-self.period:]
        excess = [ri - self.rf for ri in r]
        
        sharpe = np.mean(excess) / np.std(r) if np.std(r) > 0 else 0
        
        metadata = {"sharpe": sharpe}
        
        if sharpe > 1:
            return Signal("buy", 0.7, metadata)
        if sharpe < -0.5:
            return Signal("sell", 0.7, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    returns = [0.001 + np.random.randn()*0.01 for _ in range(35)]
    s = SharpeRatioStrategy()
    sig = s.analyze(returns)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
