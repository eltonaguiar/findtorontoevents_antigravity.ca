"""
Strategy 094: Force Index
Force Index volume-price
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class ForceIndexStrategy:
    """Force Index volume-price momentum."""
    
    def __init__(self, period: int = 13):
        self.period = period
    
    def analyze(self, closes: List[float], volumes: List[float]) -> Signal:
        if len(closes) < self.period + 1:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Raw force index
        fi = (closes[-1] - closes[-2]) * volumes[-1]
        
        # Smoothed
        fi_values = [(closes[i] - closes[i-1]) * volumes[i] for i in range(1, len(closes))]
        fi_ema = np.mean(fi_values[-self.period:])
        
        metadata = {"fi": fi, "fi_ema": fi_ema}
        
        if fi_ema > 0 and fi > fi_ema:
            return Signal("buy", 0.7, metadata)
        if fi_ema < 0 and fi < fi_ema:
            return Signal("sell", 0.7, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    closes = [40000 + i*50 for i in range(20)]
    volumes = [1000 + i*100 for i in range(20)]
    s = ForceIndexStrategy()
    sig = s.analyze(closes, volumes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
