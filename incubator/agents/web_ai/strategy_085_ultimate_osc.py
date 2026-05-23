"""
Strategy 085: Ultimate Oscillator
Ultimate Oscillator combined timeframe
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class UltimateOscillatorStrategy:
    """Ultimate Oscillator multi-timeframe momentum."""
    
    def __init__(self, short: int = 7, medium: int = 14, long: int = 28):
        self.short = short
        self.medium = medium
        self.long = long
    
    def _bp(self, closes: List[float], lows: List[float]) -> List[float]:
        return [c - min(l, pc) for c, l, pc in zip(closes[1:], lows[1:], closes[:-1])]
    
    def _tr(self, highs: List[float], lows: List[float], closes: List[float]) -> List[float]:
        return [max(h - l, abs(h - pc), abs(l - pc)) for h, l, pc in zip(highs[1:], lows[1:], closes[:-1])]
    
    def analyze(self, highs: List[float], lows: List[float], closes: List[float]) -> Signal:
        if len(closes) < self.long + 1:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        bp = self._bp(closes, lows)
        tr = self._tr(highs, lows, closes)
        
        # Average for each period
        avg_short = sum(bp[-self.short:]) / sum(tr[-self.short:]) if sum(tr[-self.short:]) > 0 else 0
        avg_medium = sum(bp[-self.medium:]) / sum(tr[-self.medium:]) if sum(tr[-self.medium:]) > 0 else 0
        avg_long = sum(bp[-self.long:]) / sum(tr[-self.long:]) if sum(tr[-self.long:]) > 0 else 0
        
        # Weighted
        uo = 100 * (4 * avg_short + 2 * avg_medium + avg_long) / 7
        
        metadata = {"uo": uo}
        
        if uo < 30:
            return Signal("buy", 0.7, metadata)
        if uo > 70:
            return Signal("sell", 0.7, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    highs = [40200]*30
    lows = [39800]*30
    closes = [39900]*30
    s = UltimateOscillatorStrategy()
    sig = s.analyze(highs, lows, closes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
