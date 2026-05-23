"""
Strategy 172: Edge Ratio
Edge ratio expectancy
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class EdgeRatioStrategy:
    """Edge ratio (MFE/MAE)."""
    
    def __init__(self, period: int = 30):
        self.period = period
    
    def analyze(self, mfes: List[float], maes: List[float]) -> Signal:
        if len(mfes) < self.period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        mfe = mfes[-self.period:]
        mae = maes[-self.period:]
        
        edge_ratios = [m / a if a > 0 else 0 for m, a in zip(mfe, mae)]
        avg_edge = np.mean(edge_ratios)
        
        metadata = {"avg_edge": avg_edge}
        
        if avg_edge > 1.5:
            return Signal("buy", 0.7, metadata)
        if avg_edge < 0.8:
            return Signal("sell", 0.7, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    mfes = [200 + np.random.randn()*50 for _ in range(35)]
    maes = [100 + np.random.randn()*30 for _ in range(35)]
    s = EdgeRatioStrategy()
    sig = s.analyze(mfes, maes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
