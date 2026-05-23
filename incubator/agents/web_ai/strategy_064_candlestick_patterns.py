"""
Strategy 064: Candlestick Patterns
Japanese candlestick pattern recognition
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class CandlestickPatternStrategy:
    """
    Recognizes key candlestick patterns.
    Hammer, shooting star, engulfing, doji, etc.
    """
    
    def __init__(
        self,
        body_threshold: float = 0.3,
        shadow_multiplier: float = 2.0,
        confirmation: bool = True
    ):
        self.body_threshold = body_threshold
        self.shadow_mult = shadow_multiplier
        self.confirmation = confirmation
    
    def _candle_properties(self, open_p: float, high: float, low: float, close: float) -> dict:
        """Calculate candlestick properties"""
        body = abs(close - open_p)
        upper_shadow = high - max(open_p, close)
        lower_shadow = min(open_p, close) - low
        total_range = high - low
        
        return {
            "body": body,
            "upper_shadow": upper_shadow,
            "lower_shadow": lower_shadow,
            "total_range": total_range,
            "bullish": close > open_p,
            "body_pct": body / total_range if total_range > 0 else 0
        }
    
    def analyze(
        self,
        opens: List[float],
        highs: List[float],
        lows: List[float],
        closes: List[float],
        volumes: List[float]
    ) -> Signal:
        if len(opens) < 3:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Current candle
        c = self._candle_properties(opens[-1], highs[-1], lows[-1], closes[-1])
        
        # Previous candle
        p = self._candle_properties(opens[-2], highs[-2], lows[-2], closes[-2])
        
        # Pattern detection
        patterns = []
        
        # Hammer
        if c["lower_shadow"] > c["body"] * self.shadow_mult and c["upper_shadow"] < c["body"] * 0.5:
            if not c["bullish"] or c["body_pct"] < 0.4:
                patterns.append("hammer")
        
        # Shooting star
        if c["upper_shadow"] > c["body"] * self.shadow_mult and c["lower_shadow"] < c["body"] * 0.5:
            if c["bullish"] or c["body_pct"] < 0.4:
                patterns.append("shooting_star")
        
        # Doji
        if c["body_pct"] < 0.1:
            patterns.append("doji")
        
        # Bullish engulfing
        if c["bullish"] and not p["bullish"]:
            if c["body"] > p["body"] * 1.2 and closes[-1] > opens[-2]:
                patterns.append("bullish_engulfing")
        
        # Bearish engulfing
        if not c["bullish"] and p["bullish"]:
            if c["body"] > p["body"] * 1.2 and closes[-1] < opens[-2]:
                patterns.append("bearish_engulfing")
        
        # Morning star (simplified)
        if len(opens) >= 3:
            p2 = self._candle_properties(opens[-3], highs[-3], lows[-3], closes[-3])
            if not p2["bullish"] and p["body_pct"] < 0.3 and c["bullish"]:
                if closes[-1] > (opens[-3] + closes[-3]) / 2:
                    patterns.append("morning_star")
        
        # Volume confirmation
        vol_confirm = volumes[-1] > np.mean(volumes[-5:]) if len(volumes) >= 5 else False
        
        metadata = {
            "patterns": patterns,
            "bullish": c["bullish"],
            "body_pct": c["body_pct"],
            "vol_confirm": vol_confirm
        }
        
        # Bullish patterns
        if "hammer" in patterns or "bullish_engulfing" in patterns or "morning_star" in patterns:
            conf = 0.7 if vol_confirm else 0.6
            return Signal("buy", conf, {**metadata, "reason": f"Bullish pattern: {patterns}"})
        
        # Bearish patterns
        if "shooting_star" in patterns or "bearish_engulfing" in patterns:
            conf = 0.7 if vol_confirm else 0.6
            return Signal("sell", conf, {**metadata, "reason": f"Bearish pattern: {patterns}"})
        
        # Doji - indecision
        if "doji" in patterns:
            return Signal("hold", 0.3, {**metadata, "reason": "Doji - indecision"})
        
        return Signal("hold", 0.2, metadata)


if __name__ == "__main__":
    # Hammer pattern
    opens = [40000, 39800, 39500]
    highs = [40200, 40000, 39800]
    lows = [39800, 39200, 39000]
    closes = [39900, 39600, 39700]
    volumes = [1000, 1200, 1500]
    
    strategy = CandlestickPatternStrategy()
    signal = strategy.analyze(opens, highs, lows, closes, volumes)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
