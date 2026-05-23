"""
Strategy 162: Drawdown Duration
Drawdown duration analysis
"""
from dataclasses import dataclass
from typing import List

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class DrawdownDurationStrategy:
    """Trade based on drawdown duration."""
    
    def __init__(self, max_duration: int = 20):
        self.max_duration = max_duration
    
    def analyze(self, closes: List[float]) -> Signal:
        if len(closes) < 10:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Find current drawdown duration
        peak = closes[-1]
        duration = 0
        
        for c in reversed(closes):
            if c >= peak:
                break
            duration += 1
            peak = max(peak, c)
        
        metadata = {"duration": duration}
        
        if duration > self.max_duration:
            return Signal("buy", 0.7, metadata)
        if duration == 0 and closes[-1] > closes[-5]:
            return Signal("buy", 0.6, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    closes = [42000 - i*100 for i in range(25)]
    s = DrawdownDurationStrategy()
    sig = s.analyze(closes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
