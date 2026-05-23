"""
Strategy 153: Maximum Drawdown
Max DD recovery
"""
from dataclasses import dataclass
from typing import List

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class MaxDrawdownStrategy:
    """Trade max drawdown recovery."""
    
    def __init__(self, threshold: float = 0.1):
        self.threshold = threshold
    
    def analyze(self, closes: List[float]) -> Signal:
        if len(closes) < 10:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        peak = closes[0]
        max_dd = 0
        peak_idx = 0
        
        for i, c in enumerate(closes):
            if c > peak:
                peak = c
                peak_idx = i
            dd = (peak - c) / peak
            if dd > max_dd:
                max_dd = dd
        
        # Recovery from max DD
        from_peak = (closes[-1] - peak) / peak
        
        metadata = {"max_dd": max_dd, "from_peak": from_peak}
        
        if max_dd > self.threshold and from_peak > -max_dd * 0.3:
            return Signal("buy", 0.7, metadata)
        if max_dd > self.threshold * 1.5:
            return Signal("sell", 0.6, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    closes = [40000, 41000, 42000, 40000, 39000, 38500, 39500, 40500]
    s = MaxDrawdownStrategy()
    sig = s.analyze(closes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
