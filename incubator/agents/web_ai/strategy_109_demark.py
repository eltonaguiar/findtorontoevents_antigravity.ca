"""
Strategy 109: DeMark Pivots
Tom DeMark pivot levels
"""
from dataclasses import dataclass
from typing import List

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class DeMarkStrategy:
    """DeMark pivot points."""
    
    def analyze(self, prev_open: float, prev_high: float, prev_low: float, prev_close: float, current: float) -> Signal:
        if prev_close < prev_open:
            x = prev_high + 2 * prev_low + prev_close
        elif prev_close > prev_open:
            x = 2 * prev_high + prev_low + prev_close
        else:
            x = prev_high + prev_low + 2 * prev_close
        
        r1 = x / 2 - prev_low
        s1 = x / 2 - prev_high
        
        metadata = {"x": x, "r1": r1, "s1": s1}
        
        if current > r1:
            return Signal("buy", 0.65, metadata)
        if current < s1:
            return Signal("sell", 0.65, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    s = DeMarkStrategy()
    sig = s.analyze(40000, 40200, 39800, 40100, 40300)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
