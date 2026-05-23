"""
Strategy 194: Variance Ratio
Variance ratio test
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class VarianceRatioStrategy:
    """Variance ratio random walk test."""
    
    def __init__(self, q: int = 2):
        self.q = q
    
    def analyze(self, prices: List[float]) -> Signal:
        if len(prices) < self.q * 10:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        log_returns = [np.log(prices[i] / prices[i-1]) for i in range(1, len(prices))]
        
        # Variance ratio
        var_1 = np.var(log_returns)
        
        q_returns = [sum(log_returns[i:i+self.q]) for i in range(0, len(log_returns)-self.q, self.q)]
        var_q = np.var(q_returns) / self.q if self.q > 0 else 1
        
        vr = var_q / var_1 if var_1 > 0 else 1
        
        metadata = {"vr": vr}
        
        if vr > 1.2:
            return Signal("buy", 0.65, metadata)
        if vr < 0.8:
            return Signal("sell", 0.65, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    prices = [40000 + i*100 + np.random.randn()*50 for i in range(30)]
    s = VarianceRatioStrategy()
    sig = s.analyze(prices)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
