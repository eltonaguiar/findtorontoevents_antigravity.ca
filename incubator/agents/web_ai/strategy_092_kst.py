"""
Strategy 092: KST Oscillator
Know Sure Thing momentum
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class KSTStrategy:
    """KST summed rate of change."""
    
    def __init__(self):
        pass
    
    def _roc(self, closes: List[float], period: int) -> float:
        if len(closes) <= period:
            return 0
        return 100 * (closes[-1] - closes[-period-1]) / closes[-period-1]
    
    def analyze(self, closes: List[float]) -> Signal:
        if len(closes) < 24:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Weighted ROCs
        roc10 = self._roc(closes, 10)
        roc15 = self._roc(closes, 15)
        roc20 = self._roc(closes, 20)
        roc30 = self._roc(closes, 24)
        
        kst = roc10 + 2*roc15 + 3*roc20 + 4*roc30
        
        metadata = {"kst": kst}
        
        if kst > 0 and kst > self._roc(closes, 9):
            return Signal("buy", 0.65, metadata)
        if kst < 0 and kst < self._roc(closes, 9):
            return Signal("sell", 0.65, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    closes = [40000 + i*80 for i in range(30)]
    s = KSTStrategy()
    sig = s.analyze(closes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
