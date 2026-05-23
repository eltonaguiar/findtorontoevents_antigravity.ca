"""
Strategy 105: Three Line Break
Three Line Break chart
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class ThreeLineBreakStrategy:
    """Three Line Break trend strategy."""
    
    def __init__(self):
        pass
    
    def analyze(self, closes: List[float]) -> Signal:
        if len(closes) < 4:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Three consecutive higher/lower closes
        white_lines = closes[-1] > closes[-2] > closes[-3] > closes[-4]
        black_lines = closes[-1] < closes[-2] < closes[-3] < closes[-4]
        
        # Reversal (breaks lowest of last 3)
        reversal_up = closes[-1] > max(closes[-4:-1])
        reversal_down = closes[-1] < min(closes[-4:-1])
        
        metadata = {"white_lines": white_lines, "black_lines": black_lines}
        
        if reversal_up:
            return Signal("buy", 0.75, metadata)
        if reversal_down:
            return Signal("sell", 0.75, metadata)
        if white_lines:
            return Signal("buy", 0.6, metadata)
        if black_lines:
            return Signal("sell", 0.6, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    closes = [40000, 40100, 40200, 40300, 40500]
    s = ThreeLineBreakStrategy()
    sig = s.analyze(closes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
