"""
Strategy 075: CCI Commodity Channel
CCI overbought/oversold strategy
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class CCIStrategy:
    """Commodity Channel Index strategy."""
    
    def __init__(self, period: int = 20, overbought: float = 100, oversold: float = -100):
        self.period = period
        self.overbought = overbought
        self.oversold = oversold
    
    def analyze(self, highs: List[float], lows: List[float], closes: List[float]) -> Signal:
        if len(closes) < self.period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Typical price
        tp = [(h + l + c) / 3 for h, l, c in zip(highs, lows, closes)]
        
        # SMA of typical price
        sma_tp = np.mean(tp[-self.period:])
        
        # Mean deviation
        mean_dev = np.mean([abs(t - sma_tp) for t in tp[-self.period:]])
        
        if mean_dev == 0:
            return Signal("hold", 0.0, {"error": "No deviation"})
        
        cci = (tp[-1] - sma_tp) / (0.015 * mean_dev)
        
        metadata = {"cci": cci}
        
        if cci < self.oversold:
            return Signal("buy", 0.7, metadata)
        if cci > self.overbought:
            return Signal("sell", 0.7, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    highs = [40200]*25
    lows = [39800]*25
    closes = [40000 + np.sin(i*0.5)*300 for i in range(25)]
    s = CCIStrategy()
    sig = s.analyze(highs, lows, closes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
