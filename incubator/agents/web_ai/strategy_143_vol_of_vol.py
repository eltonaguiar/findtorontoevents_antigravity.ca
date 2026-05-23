"""
Strategy 143: Volatility of Volatility
Vol of vol regime
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class VolOfVolStrategy:
    """Volatility of volatility regime."""
    
    def __init__(self, period: int = 20, lookback: int = 60):
        self.period = period
        self.lookback = lookback
    
    def analyze(self, closes: List[float]) -> Signal:
        if len(closes) < self.lookback + self.period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Rolling volatilities
        vols = []
        for i in range(-self.lookback, 0):
            r = [(closes[j] - closes[j-1]) / closes[j-1] for j in range(i-self.period, i)]
            vols.append(np.std(r))
        
        # Vol of vol
        vov = np.std(vols)
        
        metadata = {"vov": vov}
        
        if vov > np.percentile(vols, 90):
            return Signal("sell", 0.6, metadata)
        if vov < np.percentile(vols, 10):
            return Signal("buy", 0.6, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    closes = [40000 + np.random.randn()*400 for _ in range(90)]
    s = VolOfVolStrategy()
    sig = s.analyze(closes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
