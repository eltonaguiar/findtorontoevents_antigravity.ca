"""
Strategy 110: Floor Trader Pivots
Floor trader pivot method
"""
from dataclasses import dataclass
from typing import List

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class FloorTraderPivotStrategy:
    """Floor trader pivot method."""
    
    def analyze(self, prev_high: float, prev_low: float, prev_close: float, current: float) -> Signal:
        pivot = (prev_high + prev_low + prev_close) / 3
        bc = (prev_high + prev_low) / 2  # Bottom central
        tc = pivot - bc + pivot  # Top central
        
        r1 = 2 * pivot - prev_low
        s1 = 2 * pivot - prev_high
        
        metadata = {"pivot": pivot, "bc": bc, "tc": tc}
        
        if current > tc:
            return Signal("buy", 0.7, metadata)
        if current < bc:
            return Signal("sell", 0.7, metadata)
        if current > pivot:
            return Signal("buy", 0.55, metadata)
        if current < pivot:
            return Signal("sell", 0.55, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    s = FloorTraderPivotStrategy()
    sig = s.analyze(40200, 39800, 40000, 40100)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
