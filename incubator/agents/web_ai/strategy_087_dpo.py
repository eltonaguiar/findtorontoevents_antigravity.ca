"""
Strategy 087: Detrended Price Oscillator
DPO cycle strategy
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class DPOStrategy:
    """Detrended Price Oscillator cycle timing."""
    
    def __init__(self, period: int = 20):
        self.period = period
    
    def analyze(self, closes: List[float]) -> Signal:
        if len(closes) < self.period * 2:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # SMA shifted back
        sma = np.mean(closes[-self.period:])
        shift = self.period // 2 + 1
        
        dpo = closes[-1] - np.mean(closes[-self.period-shift:-shift]) if len(closes) >= self.period + shift else 0
        
        metadata = {"dpo": dpo}
        
        if dpo < -closes[-1] * 0.02:
            return Signal("buy", 0.6, metadata)
        if dpo > closes[-1] * 0.02:
            return Signal("sell", 0.6, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    closes = [40000 + np.sin(i*0.3)*500 for i in range(50)]
    s = DPOStrategy()
    sig = s.analyze(closes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
