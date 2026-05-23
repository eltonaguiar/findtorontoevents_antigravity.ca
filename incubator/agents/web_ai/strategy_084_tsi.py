"""
Strategy 084: True Strength Index
TSI momentum strategy
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class TSIStrategy:
    """True Strength Index double-smoothed momentum."""
    
    def __init__(self, long_period: int = 25, short_period: int = 13, signal_period: int = 7):
        self.long_p = long_period
        self.short_p = short_period
        self.signal_p = signal_period
    
    def analyze(self, closes: List[float]) -> Signal:
        if len(closes) < self.long_p + 10:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Price change
        pc = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        
        # Double smoothed (simplified)
        abs_pc = [abs(p) for p in pc]
        
        double_smooth_pc = np.mean(pc[-self.long_p:])
        double_smooth_abs = np.mean(abs_pc[-self.long_p:])
        
        if double_smooth_abs == 0:
            return Signal("hold", 0.0, {"error": "No momentum"})
        
        tsi = 100 * double_smooth_pc / double_smooth_abs
        
        metadata = {"tsi": tsi}
        
        if tsi > 25:
            return Signal("buy", 0.65, metadata)
        if tsi < -25:
            return Signal("sell", 0.65, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    closes = [40000 + i*50 for i in range(40)]
    s = TSIStrategy()
    sig = s.analyze(closes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
