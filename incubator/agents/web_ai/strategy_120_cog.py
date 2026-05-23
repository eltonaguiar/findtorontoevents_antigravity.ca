"""
Strategy 120: Center of Gravity
COG oscillator
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class COGStrategy:
    """Center of Gravity oscillator."""
    
    def __init__(self, period: int = 10):
        self.period = period
    
    def analyze(self, closes: List[float]) -> Signal:
        if len(closes) < self.period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        period_closes = closes[-self.period:]
        
        num = sum((i + 1) * period_closes[i] for i in range(self.period))
        den = sum(period_closes)
        
        cog = -num / den if den > 0 else 0
        
        metadata = {"cog": cog}
        
        if cog < -0.05:
            return Signal("buy", 0.65, metadata)
        if cog > 0.05:
            return Signal("sell", 0.65, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    closes = [40000 + np.sin(i*0.5)*200 for i in range(15)]
    s = COGStrategy()
    sig = s.analyze(closes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
