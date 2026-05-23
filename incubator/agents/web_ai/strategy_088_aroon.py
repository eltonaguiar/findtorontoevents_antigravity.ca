"""
Strategy 088: Aroon Oscillator
Aroon trend strength
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class AroonStrategy:
    """Aroon up/down trend detection."""
    
    def __init__(self, period: int = 14):
        self.period = period
    
    def analyze(self, highs: List[float], lows: List[float]) -> Signal:
        if len(highs) < self.period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Periods since high/low
        high_idx = len(highs) - 1 - highs[-self.period:].index(max(highs[-self.period:]))
        low_idx = len(lows) - 1 - lows[-self.period:].index(min(lows[-self.period:]))
        
        aroon_up = 100 * (self.period - (len(highs) - 1 - high_idx)) / self.period
        aroon_down = 100 * (self.period - (len(lows) - 1 - low_idx)) / self.period
        
        oscillator = aroon_up - aroon_down
        
        metadata = {"aroon_up": aroon_up, "aroon_down": aroon_down, "oscillator": oscillator}
        
        if aroon_up > 70 and aroon_down < 30:
            return Signal("buy", 0.7, metadata)
        if aroon_down > 70 and aroon_up < 30:
            return Signal("sell", 0.7, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    highs = [40000 + i*50 for i in range(15)]
    lows = [h-100 for h in highs]
    s = AroonStrategy()
    sig = s.analyze(highs, lows)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
