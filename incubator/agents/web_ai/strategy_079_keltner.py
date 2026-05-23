"""
Strategy 079: Keltner Channels
Keltner Channel breakout strategy
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class KeltnerStrategy:
    """Keltner Channel trend and breakout."""
    
    def __init__(self, ema_period: int = 20, atr_period: int = 10, multiplier: float = 2):
        self.ema_period = ema_period
        self.atr_period = atr_period
        self.mult = multiplier
    
    def _ema(self, data: List[float], period: int) -> float:
        return np.mean(data[-period:])
    
    def _atr(self, highs: List[float], lows: List[float], closes: List[float]) -> float:
        tr_list = []
        for i in range(1, min(self.atr_period + 1, len(highs))):
            tr = max(highs[-i] - lows[-i], abs(highs[-i] - closes[-i-1]), abs(lows[-i] - closes[-i-1]))
            tr_list.append(tr)
        return np.mean(tr_list) if tr_list else 0
    
    def analyze(self, highs: List[float], lows: List[float], closes: List[float]) -> Signal:
        if len(closes) < self.ema_period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        middle = self._ema(closes, self.ema_period)
        atr = self._atr(highs, lows, closes)
        
        upper = middle + self.mult * atr
        lower = middle - self.mult * atr
        
        current = closes[-1]
        
        metadata = {"middle": middle, "upper": upper, "lower": lower}
        
        if current > upper:
            return Signal("buy", 0.7, metadata)
        if current < lower:
            return Signal("sell", 0.7, metadata)
        if lower < current < middle:
            return Signal("buy", 0.55, metadata)
        if middle < current < upper:
            return Signal("sell", 0.55, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    highs = [40200]*25
    lows = [39800]*25
    closes = [40100]*25
    s = KeltnerStrategy()
    sig = s.analyze(highs, lows, closes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
