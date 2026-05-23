"""
Strategy 103: Point and Figure
P&F chart strategy
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class PointFigureStrategy:
    """Point and Figure chart signals."""
    
    def __init__(self, box_size: float = 50, reversal: int = 3):
        self.box_size = box_size
        self.reversal = reversal
    
    def analyze(self, closes: List[float]) -> Signal:
        if len(closes) < 10:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Trend detection
        up_boxes = sum(1 for i in range(1, len(closes)) if closes[i] > closes[i-1] + self.box_size)
        down_boxes = sum(1 for i in range(1, len(closes)) if closes[i] < closes[i-1] - self.box_size)
        
        # Double top/bottom detection
        recent_highs = [closes[i] for i in range(-5, 0) if closes[i] > closes[i-1] and closes[i] > closes[i+1]]
        recent_lows = [closes[i] for i in range(-5, 0) if closes[i] < closes[i-1] and closes[i] < closes[i+1]]
        
        double_top = len(recent_highs) >= 2 and abs(recent_highs[-1] - recent_highs[-2]) < self.box_size
        double_bottom = len(recent_lows) >= 2 and abs(recent_lows[-1] - recent_lows[-2]) < self.box_size
        
        metadata = {"up_boxes": up_boxes, "down_boxes": down_boxes}
        
        if double_bottom and up_boxes > down_boxes:
            return Signal("buy", 0.75, metadata)
        if double_top and down_boxes > up_boxes:
            return Signal("sell", 0.75, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    closes = [40000, 40100, 39900, 40000, 40200, 40100, 40300]
    s = PointFigureStrategy()
    sig = s.analyze(closes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
