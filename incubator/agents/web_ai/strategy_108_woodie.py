"""
Strategy 108: Woodie Pivots
Woodie pivot points
"""
from dataclasses import dataclass
from typing import List

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class WoodieStrategy:
    """Woodie pivot points."""
    
    def analyze(self, prev_high: float, prev_low: float, prev_close: float, current_open: float) -> Signal:
        pivot = (prev_high + prev_low + 2 * current_open) / 4
        r1 = 2 * pivot - prev_low
        s1 = 2 * pivot - prev_high
        r2 = pivot + (prev_high - prev_low)
        s2 = pivot - (prev_high - prev_low)
        
        metadata = {"pivot": pivot, "r1": r1, "s1": s1}
        
        if current_open > r2:
            return Signal("buy", 0.7, metadata)
        if current_open < s2:
            return Signal("sell", 0.7, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    s = WoodieStrategy()
    sig = s.analyze(40200, 39800, 40000, 40500)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
