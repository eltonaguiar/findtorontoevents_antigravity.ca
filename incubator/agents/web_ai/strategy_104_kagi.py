"""
Strategy 104: Kagi Lines
Kagi chart strategy
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class KagiStrategy:
    """Kagi line reversal strategy."""
    
    def __init__(self, reversal: float = 0.02):
        self.reversal = reversal
    
    def analyze(self, closes: List[float]) -> Signal:
        if len(closes) < 5:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Shoulder and waist detection
        recent = closes[-5:]
        
        # Shoulder (local high)
        shoulder = max(recent) == recent[-2]
        # Waist (local low)
        waist = min(recent) == recent[-2]
        
        # Reversal amount
        change = (closes[-1] - closes[-5]) / closes[-5]
        
        metadata = {"change": change, "shoulder": shoulder, "waist": waist}
        
        if waist and change > self.reversal:
            return Signal("buy", 0.7, metadata)
        if shoulder and change < -self.reversal:
            return Signal("sell", 0.7, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    closes = [40000, 40200, 39800, 39900, 40500]
    s = KagiStrategy()
    sig = s.analyze(closes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
