"""
Strategy 093: Elder Ray
Elder Ray bull/bear power
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class ElderRayStrategy:
    """Elder Ray bull and bear power."""
    
    def __init__(self, period: int = 13):
        self.period = period
    
    def analyze(self, highs: List[float], lows: List[float], closes: List[float]) -> Signal:
        if len(closes) < self.period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        ema = np.mean(closes[-self.period:])
        
        bull_power = highs[-1] - ema
        bear_power = lows[-1] - ema
        
        metadata = {"bull_power": bull_power, "bear_power": bear_power}
        
        if bull_power > 0 and bear_power > 0:
            return Signal("buy", 0.7, metadata)
        if bull_power < 0 and bear_power < 0:
            return Signal("sell", 0.7, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    highs = [40200]*15
    lows = [40100]*15
    closes = [40150]*15
    s = ElderRayStrategy()
    sig = s.analyze(highs, lows, closes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
