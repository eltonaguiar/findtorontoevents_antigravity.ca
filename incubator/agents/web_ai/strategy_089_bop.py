"""
Strategy 089: Balance of Power
BOP trend strength
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class BOPStrategy:
    """Balance of Power buying/selling pressure."""
    
    def __init__(self, period: int = 14, threshold: float = 0.1):
        self.period = period
        self.threshold = threshold
    
    def analyze(self, opens: List[float], highs: List[float], lows: List[float], closes: List[float]) -> Signal:
        if len(closes) < self.period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # BOP calculation
        bop_values = [(c - o) / (h - l) if h != l else 0 
                      for o, h, l, c in zip(opens, highs, lows, closes)]
        
        bop = np.mean(bop_values[-self.period:])
        
        metadata = {"bop": bop}
        
        if bop > self.threshold:
            return Signal("buy", 0.7, metadata)
        if bop < -self.threshold:
            return Signal("sell", 0.7, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    opens = [40000]*20
    highs = [40200]*20
    lows = [39800]*20
    closes = [40100]*20
    s = BOPStrategy()
    sig = s.analyze(opens, highs, lows, closes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
