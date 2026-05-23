"""
Strategy 135: Standard Error Bands
Standard error trend
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class StandardErrorStrategy:
    """Standard Error Bands."""
    
    def __init__(self, period: int = 21, multiplier: float = 2):
        self.period = period
        self.mult = multiplier
    
    def analyze(self, closes: List[float]) -> Signal:
        if len(closes) < self.period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        x = list(range(self.period))
        y = closes[-self.period:]
        
        # Linear regression
        slope, intercept = np.polyfit(x, y, 1)
        
        # Predicted values
        predicted = [slope * xi + intercept for xi in x]
        
        # Standard error
        se = np.sqrt(sum((yi - pi) ** 2 for yi, pi in zip(y, predicted)) / (self.period - 2))
        
        current_pred = slope * (self.period - 1) + intercept
        
        upper = current_pred + self.mult * se
        lower = current_pred - self.mult * se
        
        metadata = {"se": se, "upper": upper, "lower": lower}
        
        if closes[-1] > upper:
            return Signal("sell", 0.65, metadata)
        if closes[-1] < lower:
            return Signal("buy", 0.65, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    closes = [40000 + i*30 + np.random.randn()*50 for i in range(25)]
    s = StandardErrorStrategy()
    sig = s.analyze(closes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
