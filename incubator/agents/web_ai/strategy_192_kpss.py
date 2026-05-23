"""
Strategy 192: KPSS Test
KPSS trend stationarity
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class KPSSStrategy:
    """KPSS test for trend."""
    
    def __init__(self, period: int = 30):
        self.period = period
    
    def analyze(self, prices: List[float]) -> Signal:
        if len(prices) < self.period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        p = prices[-self.period:]
        
        # Detrend
        trend = np.polyfit(range(len(p)), p, 1)
        residuals = [p[i] - (trend[0] * i + trend[1]) for i in range(len(p))]
        
        # Variance of residuals
        var_resid = np.var(residuals)
        var_price = np.var(p)
        
        ratio = var_resid / var_price if var_price > 0 else 1
        
        metadata = {"ratio": ratio}
        
        if ratio < 0.3 and trend[0] > 0:
            return Signal("buy", 0.7, metadata)
        if ratio < 0.3 and trend[0] < 0:
            return Signal("sell", 0.7, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    prices = [40000 + i*100 for i in range(35)]
    s = KPSSStrategy()
    sig = s.analyze(prices)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
