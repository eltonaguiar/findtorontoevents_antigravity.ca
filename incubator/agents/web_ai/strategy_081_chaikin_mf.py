"""
Strategy 081: Chaikin Money Flow
CMF volume-weighted strategy
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class ChaikinMFStrategy:
    """Chaikin Money Flow accumulation/distribution."""
    
    def __init__(self, period: int = 20, threshold: float = 0.05):
        self.period = period
        self.threshold = threshold
    
    def analyze(self, highs: List[float], lows: List[float], closes: List[float], volumes: List[float]) -> Signal:
        if len(closes) < self.period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Money Flow Multiplier
        mfm = [((c - l) - (h - c)) / (h - l) if h != l else 0 
               for h, l, c in zip(highs[-self.period:], lows[-self.period:], closes[-self.period:])]
        
        # Money Flow Volume
        mfv = [m * v for m, v in zip(mfm, volumes[-self.period:])]
        
        # CMF
        cmf = sum(mfv) / sum(volumes[-self.period:]) if sum(volumes[-self.period:]) > 0 else 0
        
        metadata = {"cmf": cmf}
        
        if cmf > self.threshold:
            return Signal("buy", 0.7, metadata)
        if cmf < -self.threshold:
            return Signal("sell", 0.7, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    highs = [40200]*25
    lows = [39800]*25
    closes = [40100]*25
    volumes = [1500]*25
    s = ChaikinMFStrategy()
    sig = s.analyze(highs, lows, closes, volumes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
