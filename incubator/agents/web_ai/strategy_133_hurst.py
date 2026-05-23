"""
Strategy 133: Hurst Exponent
Hurst exponent mean reversion
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class HurstExponentStrategy:
    """Hurst Exponent for persistence/mean reversion."""
    
    def __init__(self, period: int = 20):
        self.period = period
    
    def analyze(self, closes: List[float]) -> Signal:
        if len(closes) < self.period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Simplified Hurst (RS analysis)
        returns = [closes[i] - closes[i-1] for i in range(-self.period+1, 0)]
        
        mean_return = np.mean(returns)
        cumdev = [sum(returns[:i+1]) - (i+1) * mean_return for i in range(len(returns))]
        
        r = max(cumdev) - min(cumdev)
        s = np.std(returns)
        
        hurst = 0.5  # Default
        if s > 0 and len(returns) > 0:
            hurst = np.log(r / s) / np.log(len(returns)) if r > 0 else 0.5
        
        metadata = {"hurst": hurst}
        
        if hurst > 0.6:
            return Signal("buy", 0.65, metadata)
        if hurst < 0.4:
            return Signal("sell", 0.65, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    closes = [40000 + i*50 for i in range(25)]
    s = HurstExponentStrategy()
    sig = s.analyze(closes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
