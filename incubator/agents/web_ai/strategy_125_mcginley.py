"""
Strategy 125: McGinley Dynamic
McGinley Dynamic average
"""
from dataclasses import dataclass
from typing import List

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class McGinleyStrategy:
    """McGinley Dynamic Moving Average."""
    
    def __init__(self, period: int = 10):
        self.period = period
    
    def analyze(self, closes: List[float]) -> Signal:
        if len(closes) < 2:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Simplified McGinley
        md = closes[0]
        for close in closes[1:]:
            md = md + (close - md) / (0.6 * self.period * (close / md) ** 4)
        
        metadata = {"md": md}
        
        if closes[-1] > md:
            return Signal("buy", 0.6, metadata)
        if closes[-1] < md:
            return Signal("sell", 0.6, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    closes = [40000 + i*40 for i in range(15)]
    s = McGinleyStrategy()
    sig = s.analyze(closes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
