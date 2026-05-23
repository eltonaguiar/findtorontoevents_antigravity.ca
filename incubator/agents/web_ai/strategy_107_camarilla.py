"""
Strategy 107: Camarilla Pivots
Camarilla pivot levels
"""
from dataclasses import dataclass
from typing import List

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class CamarillaStrategy:
    """Camarilla pivot points."""
    
    def analyze(self, prev_high: float, prev_low: float, prev_close: float, current: float) -> Signal:
        range_hl = prev_high - prev_low
        
        h4 = prev_close + range_hl * 1.1 / 2
        h3 = prev_close + range_hl * 1.1 / 4
        l3 = prev_close - range_hl * 1.1 / 4
        l4 = prev_close - range_hl * 1.1 / 2
        
        metadata = {"h3": h3, "h4": h4, "l3": l3, "l4": l4}
        
        if current > h4:
            return Signal("buy", 0.75, metadata)
        if current < l4:
            return Signal("sell", 0.75, metadata)
        if current > h3:
            return Signal("sell", 0.6, metadata)  # Mean reversion
        if current < l3:
            return Signal("buy", 0.6, metadata)  # Mean reversion
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    s = CamarillaStrategy()
    sig = s.analyze(40200, 39800, 40000, 39600)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
