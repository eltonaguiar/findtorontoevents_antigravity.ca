"""
Strategy 113: Speed Resistance
Speed resistance lines
"""
from dataclasses import dataclass
from typing import List

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class SpeedResistanceStrategy:
    """Speed resistance fan lines."""
    
    def analyze(self, highs: List[float], lows: List[float], closes: List[float]) -> Signal:
        if len(closes) < 5:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Find trend start
        trend_start = min(lows[:5])
        trend_end = max(highs[-5:])
        
        # 1/3 and 2/3 levels
        range_size = trend_end - trend_start
        level_1_3 = trend_end - range_size * 0.333
        level_2_3 = trend_end - range_size * 0.667
        
        current = closes[-1]
        
        metadata = {"level_1_3": level_1_3, "level_2_3": level_2_3}
        
        if current > trend_end * 0.99:
            return Signal("buy", 0.6, metadata)
        if current < level_2_3:
            return Signal("sell", 0.65, metadata)
        if level_1_3 < current < trend_end:
            return Signal("hold", 0.3, metadata)
        return Signal("hold", 0.2, metadata)

if __name__ == "__main__":
    lows = [40000, 40100, 40200, 40300, 40400]
    highs = [40200, 40300, 40500, 40600, 40800]
    closes = [40700]
    s = SpeedResistanceStrategy()
    sig = s.analyze(highs, lows, closes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
