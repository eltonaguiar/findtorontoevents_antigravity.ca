"""
Strategy 163: Time Under Water
Time under water analysis
"""
from dataclasses import dataclass
from typing import List

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class TimeUnderWaterStrategy:
    """Trade time under water."""
    
    def __init__(self, threshold: int = 15):
        self.threshold = threshold
    
    def analyze(self, closes: List[float]) -> Signal:
        if len(closes) < 5:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        all_time_high = max(closes)
        tuw = 0
        
        for c in reversed(closes):
            if c >= all_time_high:
                break
            tuw += 1
        
        metadata = {"tuw": tuw}
        
        if tuw > self.threshold:
            return Signal("buy", 0.7, metadata)
        if tuw == 0:
            return Signal("sell", 0.6, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    closes = [40000 + (i%20)*50 for i in range(30)]
    s = TimeUnderWaterStrategy()
    sig = s.analyze(closes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
