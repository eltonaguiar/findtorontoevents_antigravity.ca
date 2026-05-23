"""
Strategy 191: Augmented Dickey-Fuller
ADF stationarity test
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class ADFStrategy:
    """ADF test for mean reversion."""
    
    def __init__(self, period: int = 30):
        self.period = period
    
    def analyze(self, prices: List[float]) -> Signal:
        if len(prices) < self.period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Simplified mean reversion test
        changes = [prices[i] - prices[i-1] for i in range(-self.period+1, 0)]
        
        # Autocorrelation
        if len(changes) > 1:
            autocorr = np.corrcoef(changes[:-1], changes[1:])[0, 1]
        else:
            autocorr = 0
        
        metadata = {"autocorr": autocorr}
        
        if autocorr < -0.3:
            return Signal("buy", 0.7, metadata)
        if autocorr > 0.5:
            return Signal("sell", 0.7, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    prices = [40000 + np.sin(i*0.5)*500 for i in range(35)]
    s = ADFStrategy()
    sig = s.analyze(prices)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
