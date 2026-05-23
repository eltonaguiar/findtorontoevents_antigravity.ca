"""
Strategy 111: Andrews Pitchfork
Andrews Pitchfork median line
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class AndrewsPitchforkStrategy:
    """Andrews Pitchfork channel trading."""
    
    def analyze(self, highs: List[float], lows: List[float], closes: List[float]) -> Signal:
        if len(closes) < 10:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Find 3 pivots (simplified)
        p1 = lows[0]  # First low
        p2 = highs[len(highs)//2]  # Middle high
        p3 = lows[-1]  # Last low
        
        # Median line slope
        median_slope = (p2 - (p1 + p3) / 2) / (len(closes) / 2)
        
        # Current position relative to median
        current = closes[-1]
        median_value = (p1 + p3) / 2 + median_slope * len(closes)
        
        channel_width = abs(p2 - (p1 + p3) / 2)
        
        metadata = {"median": median_value, "width": channel_width}
        
        if current < median_value - channel_width * 0.5:
            return Signal("buy", 0.65, metadata)
        if current > median_value + channel_width * 0.5:
            return Signal("sell", 0.65, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    lows = [39000, 39200, 39500, 39800, 40000]
    highs = [39500, 39800, 40200, 40500, 40800]
    closes = [40000, 40200, 40500, 40300, 40100]
    s = AndrewsPitchforkStrategy()
    sig = s.analyze(highs, lows, closes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
