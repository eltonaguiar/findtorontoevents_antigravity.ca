"""
Strategy 101: Heikin Ashi
Heikin Ashi candlestick strategy
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class HeikinAshiStrategy:
    """Heikin Ashi trend identification."""
    
    def __init__(self):
        pass
    
    def analyze(self, opens: List[float], highs: List[float], lows: List[float], closes: List[float]) -> Signal:
        if len(closes) < 3:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Calculate Heikin Ashi
        ha_close = (opens[-1] + highs[-1] + lows[-1] + closes[-1]) / 4
        ha_open = (opens[-2] + closes[-2]) / 2
        ha_high = max(highs[-1], ha_open, ha_close)
        ha_low = min(lows[-1], ha_open, ha_close)
        
        # Previous HA
        prev_ha_close = (opens[-2] + highs[-2] + lows[-2] + closes[-2]) / 4
        prev_ha_open = (opens[-3] + closes[-3]) / 2 if len(opens) >= 3 else prev_ha_close
        
        # Trend
        bullish = ha_close > ha_open
        prev_bullish = prev_ha_close > prev_ha_open
        
        # Strong trend (no lower shadow for bullish, no upper for bearish)
        strong_bullish = bullish and ha_low == ha_open
        strong_bearish = not bullish and ha_high == ha_open
        
        metadata = {"ha_close": ha_close, "ha_open": ha_open, "bullish": bullish}
        
        if strong_bullish and not prev_bullish:
            return Signal("buy", 0.75, metadata)
        if strong_bearish and prev_bullish:
            return Signal("sell", 0.75, metadata)
        if bullish:
            return Signal("buy", 0.6, metadata)
        return Signal("sell", 0.6, metadata)

if __name__ == "__main__":
    opens = [40000, 40100, 40200]
    highs = [40200, 40300, 40500]
    lows = [39900, 40000, 40100]
    closes = [40100, 40250, 40400]
    s = HeikinAshiStrategy()
    sig = s.analyze(opens, highs, lows, closes)
    print(f"Signal: {sig.action}, Confidence: {sig.confidence:.2f}")
