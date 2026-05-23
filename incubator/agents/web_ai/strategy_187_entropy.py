"""
Strategy 187: Entropy
Shannon entropy
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class EntropyStrategy:
    """Shannon entropy of returns."""
    
    def __init__(self, period: int = 30, bins: int = 10):
        self.period = period
        self.bins = bins
    
    def analyze(self, returns: List[float]) -> Signal:
        if len(returns) < self.period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        r = returns[-self.period:]
        
        # Histogram
        hist, _ = np.histogram(r, bins=self.bins)
        probs = hist / len(r)
        
        # Entropy
        entropy = -sum(p * np.log(p) for p in probs if p > 0)
        
        metadata = {"entropy": entropy}
        
        if entropy < 1.5:
            return Signal("buy", 0.65, metadata)
        if entropy > 2.5:
            return Signal("sell", 0.65, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    returns = [0.001 + np.random.randn()*0.005 for _ in range(35)]
    s = EntropyStrategy()
    sig = s.analyze(returns)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
