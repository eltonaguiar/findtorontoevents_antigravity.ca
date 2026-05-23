"""
Strategy 149: Treynor Ratio
Treynor beta-adjusted
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class TreynorStrategy:
    """Treynor ratio (excess return / beta)."""
    
    def __init__(self, period: int = 36, risk_free: float = 0):
        self.period = period
        self.rf = risk_free
    
    def analyze(self, returns: List[float], market: List[float]) -> Signal:
        if len(returns) < self.period or len(market) < self.period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        r = returns[-self.period:]
        m = market[-self.period:]
        
        beta = np.cov(r, m)[0, 1] / np.var(m) if np.var(m) > 0 else 1
        
        treynor = (np.mean(r) - self.rf) / beta if beta != 0 else 0
        
        metadata = {"treynor": treynor, "beta": beta}
        
        if treynor > 0.02:
            return Signal("buy", 0.7, metadata)
        if treynor < -0.01:
            return Signal("sell", 0.7, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    returns = [0.001 + np.random.randn()*0.01 for _ in range(40)]
    market = [0.0005 + np.random.randn()*0.008 for _ in range(40)]
    s = TreynorStrategy()
    sig = s.analyze(returns, market)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
