"""
Strategy 095: Ease of Movement
EOM volume-price ease
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class EOMStrategy:
    """Ease of Movement volume-price relationship."""
    
    def __init__(self, period: int = 14, threshold: float = 0.0001):
        self.period = period
        self.threshold = threshold
    
    def analyze(self, highs: List[float], lows: List[float], volumes: List[float]) -> Signal:
        if len(highs) < self.period + 1:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Distance moved
        dm = ((highs[-1] + lows[-1]) / 2) - ((highs[-2] + lows[-2]) / 2)
        
        # Box ratio
        br = volumes[-1] / (highs[-1] - lows[-1]) if highs[-1] != lows[-1] else 0
        
        # EOM
        eom = dm / br if br != 0 else 0
        
        # Smoothed
        eom_values = []
        for i in range(1, min(self.period + 1, len(highs))):
            dm_i = ((highs[-i] + lows[-i]) / 2) - ((highs[-i-1] + lows[-i-1]) / 2)
            br_i = volumes[-i] / (highs[-i] - lows[-i]) if highs[-i] != lows[-i] else 1
            eom_values.append(dm_i / br_i if br_i != 0 else 0)
        
        eom_smooth = np.mean(eom_values) if eom_values else 0
        
        metadata = {"eom": eom, "eom_smooth": eom_smooth}
        
        if eom_smooth > self.threshold:
            return Signal("buy", 0.65, metadata)
        if eom_smooth < -self.threshold:
            return Signal("sell", 0.65, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    highs = [40200]*20
    lows = [39800]*20
    volumes = [1000]*20
    s = EOMStrategy()
    sig = s.analyze(highs, lows, volumes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
