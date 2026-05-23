"""
Strategy 124: Rainbow Moving Average
Multiple EMA rainbow
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class RainbowMAStrategy:
    """Rainbow Moving Average trend."""
    
    def analyze(self, closes: List[float]) -> Signal:
        if len(closes) < 10:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Multiple EMAs
        ema2 = np.mean(closes[-2:])
        ema5 = np.mean(closes[-5:])
        ema8 = np.mean(closes[-8:])
        ema10 = np.mean(closes[-10:])
        
        # Bullish alignment
        bullish = ema2 > ema5 > ema8 > ema10
        bearish = ema2 < ema5 < ema8 < ema10
        
        metadata = {"ema2": ema2, "ema10": ema10}
        
        if bullish:
            return Signal("buy", 0.75, metadata)
        if bearish:
            return Signal("sell", 0.75, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    closes = [40000 + i*50 for i in range(15)]
    s = RainbowMAStrategy()
    sig = s.analyze(closes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
