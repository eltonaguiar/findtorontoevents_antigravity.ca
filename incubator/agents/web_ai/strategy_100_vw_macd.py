"""
Strategy 100: Volume Weighted MACD
VW-MACD volume-weighted
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class VWMACDStrategy:
    """Volume Weighted MACD."""
    
    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        self.fast = fast
        self.slow = slow
        self.signal = signal
    
    def _vwema(self, closes: List[float], volumes: List[float], period: int) -> float:
        weights = volumes[-period:]
        values = closes[-period:]
        return sum(v * w for v, w in zip(values, weights)) / sum(weights) if sum(weights) > 0 else values[-1]
    
    def analyze(self, closes: List[float], volumes: List[float]) -> Signal:
        if len(closes) < self.slow:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        fast_vwema = self._vwema(closes, volumes, self.fast)
        slow_vwema = self._vwema(closes, volumes, self.slow)
        
        vw_macd = fast_vwema - slow_vwema
        
        metadata = {"vw_macd": vw_macd}
        
        if vw_macd > 0:
            return Signal("buy", 0.65, metadata)
        if vw_macd < 0:
            return Signal("sell", 0.65, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    closes = [40000 + i*60 for i in range(30)]
    volumes = [1000 + i*50 for i in range(30)]
    s = VWMACDStrategy()
    sig = s.analyze(closes, volumes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
