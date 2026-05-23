"""
Strategy 091: Schaff Trend Cycle
STC cycle strategy
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class SchaffTCStrategy:
    """Schaff Trend Cycle MACD-based cycle."""
    
    def __init__(self, fast: int = 23, slow: int = 50, cycle: int = 10):
        self.fast = fast
        self.slow = slow
        self.cycle = cycle
    
    def analyze(self, closes: List[float]) -> Signal:
        if len(closes) < self.slow:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Simplified MACD
        ema_fast = np.mean(closes[-self.fast:])
        ema_slow = np.mean(closes[-self.slow:])
        macd = ema_fast - ema_slow
        
        # Simplified STC (normalized MACD)
        high_macd = max(closes[-self.cycle:]) - min(closes[-self.cycle:])
        stc = 100 * (macd / high_macd) if high_macd > 0 else 50
        stc = max(0, min(100, stc))
        
        metadata = {"stc": stc}
        
        if stc < 25:
            return Signal("buy", 0.7, metadata)
        if stc > 75:
            return Signal("sell", 0.7, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    closes = [40000 + np.sin(i*0.2)*300 for i in range(60)]
    s = SchaffTCStrategy()
    sig = s.analyze(closes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
