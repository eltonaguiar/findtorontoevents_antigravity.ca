"""
Strategy 183: CUSUM
CUSUM control chart
"""
from dataclasses import dataclass
from typing import List

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class CUSUMStrategy:
    """CUSUM change detection."""
    
    def __init__(self, threshold: float = 5):
        self.threshold = threshold
    
    def analyze(self, returns: List[float]) -> Signal:
        if len(returns) < 10:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # CUSUM
        s_pos = 0
        s_neg = 0
        
        for r in returns[-10:]:
            s_pos = max(0, s_pos + r - 0.001)
            s_neg = min(0, s_neg + r + 0.001)
        
        metadata = {"s_pos": s_pos, "s_neg": s_neg}
        
        if s_pos > self.threshold:
            return Signal("buy", 0.75, metadata)
        if abs(s_neg) > self.threshold:
            return Signal("sell", 0.75, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    returns = [0.01]*15
    s = CUSUMStrategy()
    sig = s.analyze(returns)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
