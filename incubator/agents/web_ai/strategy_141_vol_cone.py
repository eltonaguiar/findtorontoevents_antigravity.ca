"""
Strategy 141: Volatility Cone
Volatility cone analysis
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class VolatilityConeStrategy:
    """Volatility cone percentile."""
    
    def __init__(self, lookback: int = 252):
        self.lookback = lookback
    
    def analyze(self, closes: List[float]) -> Signal:
        if len(closes) < self.lookback:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Realized volatilities for different windows
        windows = [10, 20, 60, 120]
        current_vols = []
        
        for w in windows:
            returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(-w, 0)]
            current_vols.append(np.std(returns) * np.sqrt(365))
        
        # Compare to historical distribution
        avg_vol = np.mean(current_vols)
        
        metadata = {"avg_vol": avg_vol}
        
        if avg_vol > np.percentile(current_vols, 90):
            return Signal("sell", 0.65, metadata)
        if avg_vol < np.percentile(current_vols, 10):
            return Signal("buy", 0.65, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    closes = [40000 + np.random.randn()*300 for _ in range(260)]
    s = VolatilityConeStrategy()
    sig = s.analyze(closes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
