"""
Strategy 117: Trend Intensity
Trend intensity index
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class TrendIntensityStrategy:
    """Trend Intensity Index."""
    
    def __init__(self, period: int = 30):
        self.period = period
    
    def analyze(self, closes: List[float]) -> Signal:
        if len(closes) < self.period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        sma = np.mean(closes[-self.period:])
        
        # Count closes above/below SMA
        above = sum(1 for c in closes[-self.period:] if c > sma)
        below = self.period - above
        
        tii = 100 * above / self.period
        
        metadata = {"tii": tii}
        
        if tii > 80:
            return Signal("buy", 0.75, metadata)
        if tii < 20:
            return Signal("sell", 0.75, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    closes = [40000 + i*50 for i in range(35)]
    s = TrendIntensityStrategy()
    sig = s.analyze(closes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
