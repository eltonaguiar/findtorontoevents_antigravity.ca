"""
Strategy 106: Pivot Points
Pivot point support/resistance
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class PivotPointStrategy:
    """Classic pivot point levels."""
    
    def __init__(self):
        pass
    
    def analyze(self, prev_high: float, prev_low: float, prev_close: float, current: float) -> Signal:
        pivot = (prev_high + prev_low + prev_close) / 3
        r1 = 2 * pivot - prev_low
        s1 = 2 * pivot - prev_high
        r2 = pivot + (prev_high - prev_low)
        s2 = pivot - (prev_high - prev_low)
        
        metadata = {"pivot": pivot, "r1": r1, "s1": s1, "r2": r2, "s2": s2}
        
        if current > r2:
            return Signal("buy", 0.7, metadata)
        if current < s2:
            return Signal("sell", 0.7, metadata)
        if current > r1:
            return Signal("buy", 0.6, metadata)
        if current < s1:
            return Signal("sell", 0.6, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    s = PivotPointStrategy()
    sig = s.analyze(40200, 39800, 40000, 40500)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
