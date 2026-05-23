"""
Strategy 161: Conditional Sharpe
Conditional Sharpe ratio
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class ConditionalSharpeStrategy:
    """Sharpe in different regimes."""
    
    def __init__(self, period: int = 30):
        self.period = period
    
    def analyze(self, returns: List[float], market_returns: List[float]) -> Signal:
        if len(returns) < self.period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        r = returns[-self.period:]
        m = market_returns[-self.period:]
        
        # Bull/bear regime
        bull = np.mean(m) > 0
        
        sharpe = np.mean(r) / np.std(r) if np.std(r) > 0 else 0
        
        metadata = {"sharpe": sharpe, "bull": bull}
        
        if bull and sharpe > 0.5:
            return Signal("buy", 0.7, metadata)
        if not bull and sharpe > 0.3:
            return Signal("buy", 0.65, metadata)
        if sharpe < -0.3:
            return Signal("sell", 0.7, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    returns = [0.001 + np.random.randn()*0.01 for _ in range(35)]
    market = [0.0005 + np.random.randn()*0.008 for _ in range(35)]
    s = ConditionalSharpeStrategy()
    sig = s.analyze(returns, market)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
