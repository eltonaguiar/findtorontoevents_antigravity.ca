"""
Strategy 144: Beta Adjusted
Beta adjusted returns
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class BetaAdjustedStrategy:
    """Beta adjusted market exposure."""
    
    def __init__(self, period: int = 60):
        self.period = period
    
    def analyze(self, asset_returns: List[float], market_returns: List[float]) -> Signal:
        if len(asset_returns) < self.period or len(market_returns) < self.period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        a = asset_returns[-self.period:]
        m = market_returns[-self.period:]
        
        # Beta
        covariance = np.cov(a, m)[0, 1]
        variance = np.var(m)
        beta = covariance / variance if variance > 0 else 1
        
        # Alpha
        alpha = np.mean(a) - beta * np.mean(m)
        
        metadata = {"beta": beta, "alpha": alpha}
        
        if alpha > 0.001 and beta > 0:
            return Signal("buy", 0.7, metadata)
        if alpha < -0.001:
            return Signal("sell", 0.7, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    asset_r = [0.001 + np.random.randn()*0.01 for _ in range(70)]
    market_r = [0.0005 + np.random.randn()*0.008 for _ in range(70)]
    s = BetaAdjustedStrategy()
    sig = s.analyze(asset_r, market_r)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
