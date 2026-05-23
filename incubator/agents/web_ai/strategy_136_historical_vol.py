"""
Strategy 136: Historical Volatility
HV percentile strategy
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class HistoricalVolatilityStrategy:
    """Historical Volatility percentile."""
    
    def __init__(self, period: int = 20, lookback: int = 100):
        self.period = period
        self.lookback = lookback
    
    def analyze(self, closes: List[float]) -> Signal:
        if len(closes) < self.lookback:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Current HV
        returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(-self.period, 0)]
        current_hv = np.std(returns) * np.sqrt(365)
        
        # Historical HVs
        hvs = []
        for i in range(-self.lookback + self.period, 0):
            r = [(closes[j] - closes[j-1]) / closes[j-1] for j in range(i-self.period, i)]
            hvs.append(np.std(r) * np.sqrt(365))
        
        percentile = sum(1 for hv in hvs if hv < current_hv) / len(hvs) if hvs else 0.5
        
        metadata = {"hv": current_hv, "percentile": percentile}
        
        if percentile > 0.8:
            return Signal("sell", 0.65, metadata)
        if percentile < 0.2:
            return Signal("buy", 0.65, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    closes = [40000 + np.random.randn()*500 for _ in range(120)]
    s = HistoricalVolatilityStrategy()
    sig = s.analyze(closes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
