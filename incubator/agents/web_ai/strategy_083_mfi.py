"""
Strategy 083: MFI Money Flow Index
MFI overbought/oversold
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class MFIStrategy:
    """Money Flow Index strategy."""
    
    def __init__(self, period: int = 14, overbought: float = 80, oversold: float = 20):
        self.period = period
        self.overbought = overbought
        self.oversold = oversold
    
    def analyze(self, highs: List[float], lows: List[float], closes: List[float], volumes: List[float]) -> Signal:
        if len(closes) < self.period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Typical price
        tp = [(h + l + c) / 3 for h, l, c in zip(highs, lows, closes)]
        
        # Raw money flow
        rmf = [t * v for t, v in zip(tp, volumes)]
        
        # Positive/negative money flow
        pos_mf = sum(rmf[i] for i in range(-self.period+1, 0) if tp[i] > tp[i-1])
        neg_mf = sum(rmf[i] for i in range(-self.period+1, 0) if tp[i] < tp[i-1])
        
        if neg_mf == 0:
            mfi = 100
        else:
            mfi = 100 - (100 / (1 + pos_mf / neg_mf))
        
        metadata = {"mfi": mfi}
        
        if mfi < self.oversold:
            return Signal("buy", 0.75, metadata)
        if mfi > self.overbought:
            return Signal("sell", 0.75, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    highs = [40200]*20
    lows = [39800]*20
    closes = [39900]*20
    volumes = [1000]*20
    s = MFIStrategy()
    sig = s.analyze(highs, lows, closes, volumes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
