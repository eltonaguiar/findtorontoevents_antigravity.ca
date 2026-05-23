"""
Strategy 128: Zero Lag EMA
ZLEMA zero lag average
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class ZLEMAStrategy:
    """Zero Lag Exponential Moving Average."""
    
    def __init__(self, period: int = 14):
        self.period = period
    
    def analyze(self, closes: List[float]) -> Signal:
        if len(closes) < self.period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        lag = (self.period - 1) // 2
        
        # De-lagged data
        ema_data = [2 * closes[i] - closes[i - lag] if i >= lag else closes[i] 
                    for i in range(-self.period, 0)]
        
        # EMA of de-lagged data
        alpha = 2 / (self.period + 1)
        zlema = ema_data[0]
        for val in ema_data[1:]:
            zlema = alpha * val + (1 - alpha) * zlema
        
        metadata = {"zlema": zlema}
        
        if closes[-1] > zlema:
            return Signal("buy", 0.6, metadata)
        if closes[-1] < zlema:
            return Signal("sell", 0.6, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    closes = [40000 + i*50 for i in range(20)]
    s = ZLEMAStrategy()
    sig = s.analyze(closes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
