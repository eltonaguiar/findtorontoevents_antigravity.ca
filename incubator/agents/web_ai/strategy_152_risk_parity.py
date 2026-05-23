"""
Strategy 152: Risk Parity
Equal risk contribution
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class RiskParityStrategy:
    """Risk parity allocation."""
    
    def __init__(self, period: int = 30):
        self.period = period
    
    def analyze(self, returns: List[float], volatilities: List[float]) -> Signal:
        if len(returns) < self.period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Inverse volatility weighting
        inv_vol = [1 / v if v > 0 else 0 for v in volatilities[-self.period:]]
        total = sum(inv_vol)
        
        weights = [iv / total for iv in inv_vol] if total > 0 else [1/self.period] * self.period
        
        avg_return = np.mean(returns[-self.period:])
        
        metadata = {"avg_return": avg_return}
        
        if avg_return > 0 and weights[-1] > np.mean(weights):
            return Signal("buy", 0.65, metadata)
        if avg_return < 0:
            return Signal("sell", 0.65, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    returns = [0.001 + np.random.randn()*0.01 for _ in range(35)]
    vols = [0.01 + abs(np.random.randn())*0.005 for _ in range(35)]
    s = RiskParityStrategy()
    sig = s.analyze(returns, vols)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
