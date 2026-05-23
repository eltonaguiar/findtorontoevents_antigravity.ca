"""
Strategy 112: Gann Lines
Gann angle lines
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class GannLinesStrategy:
    """Gann angle trading."""
    
    def __init__(self, angle: float = 45):
        self.angle = angle
    
    def analyze(self, highs: List[float], lows: List[float], closes: List[float]) -> Signal:
        if len(closes) < 10:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # 1x1 Gann angle (45 degrees = 1 price unit per 1 time unit)
        start_price = closes[0]
        gann_1x1 = start_price + len(closes) * (start_price * 0.001)  # 0.1% per period
        
        current = closes[-1]
        
        metadata = {"gann_1x1": gann_1x1, "current": current}
        
        if current > gann_1x1 * 1.02:
            return Signal("buy", 0.6, metadata)
        if current < gann_1x1 * 0.98:
            return Signal("sell", 0.6, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    closes = [40000 + i*50 for i in range(20)]
    highs = [c + 100 for c in closes]
    lows = [c - 100 for c in closes]
    s = GannLinesStrategy()
    sig = s.analyze(highs, lows, closes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
