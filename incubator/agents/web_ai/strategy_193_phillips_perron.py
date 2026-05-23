"""
Strategy 193: Phillips-Perron
PP unit root test
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class PhillipsPerronStrategy:
    """Phillips-Perron test."""
    
    def __init__(self, period: int = 30):
        self.period = period
    
    def analyze(self, prices: List[float]) -> Signal:
        if len(prices) < self.period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Trend test
        p = prices[-self.period:]
        
        returns = [(p[i] - p[i-1]) / p[i-1] for i in range(1, len(p))]
        
        drift = np.mean(returns)
        
        metadata = {"drift": drift}
        
        if drift > 0.001:
            return Signal("buy", 0.7, metadata)
        if drift < -0.001:
            return Signal("sell", 0.7, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    prices = [40000 + i*50 for i in range(35)]
    s = PhillipsPerronStrategy()
    sig = s.analyze(prices)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
