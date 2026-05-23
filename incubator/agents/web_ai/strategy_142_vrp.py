"""
Strategy 142: Volatility Risk Premium
VRP strategy
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class VRPStrategy:
    """Volatility Risk Premium (IV - RV)."""
    
    def __init__(self, rv_period: int = 20):
        self.rv_period = rv_period
    
    def analyze(self, closes: List[float], implied_vol: float) -> Signal:
        if len(closes) < self.rv_period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Realized volatility
        returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(-self.rv_period, 0)]
        rv = np.std(returns) * np.sqrt(365)
        
        # VRP
        vrp = implied_vol - rv
        
        metadata = {"vrp": vrp, "iv": implied_vol, "rv": rv}
        
        if vrp > 0.05:
            return Signal("sell", 0.65, metadata)
        if vrp < -0.05:
            return Signal("buy", 0.65, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    closes = [40000 + np.random.randn()*200 for _ in range(25)]
    s = VRPStrategy()
    sig = s.analyze(closes, 0.8)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
