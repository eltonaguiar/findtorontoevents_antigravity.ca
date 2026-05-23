"""
Strategy 038: Volatility Breakout
Range expansion trading
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class VolatilityBreakoutStrategy:
    """
    Trades when volatility expands beyond recent ranges.
    Captures the start of new trends.
    """
    
    def __init__(
        self,
        lookback_period: int = 20,
        breakout_multiplier: float = 1.5,
        min_range_pct: float = 0.01
    ):
        self.lookback = lookback_period
        self.multiplier = breakout_multiplier
        self.min_range = min_range_pct
    
    def analyze(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        volumes: List[float]
    ) -> Signal:
        if len(highs) < self.lookback + 5:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Recent range
        recent_highs = highs[-self.lookback:]
        recent_lows = lows[-self.lookback:]
        
        recent_range_high = max(recent_highs)
        recent_range_low = min(recent_lows)
        recent_range = recent_range_high - recent_range_low
        recent_range_pct = recent_range / recent_range_low
        
        # Current candle
        current_high = highs[-1]
        current_low = lows[-1]
        current_close = closes[-1]
        prev_close = closes[-2]
        
        # Breakout detection
        breakout_up = current_high > recent_range_high * (1 + 0.001)
        breakout_down = current_low < recent_range_low * (1 - 0.001)
        
        # Range expansion
        current_range = current_high - current_low
        avg_range = np.mean([h - l for h, l in zip(highs[-self.lookback:], lows[-self.lookback:])])
        range_expansion = current_range / (avg_range + 1e-8)
        
        # Volume
        vol_ma = np.mean(volumes[-5:])
        vol_ratio = volumes[-1] / vol_ma if vol_ma > 0 else 1
        
        # Momentum
        momentum = (current_close - prev_close) / prev_close
        
        metadata = {
            "recent_range_high": recent_range_high,
            "recent_range_low": recent_range_low,
            "recent_range_pct": recent_range_pct * 100,
            "breakout_up": breakout_up,
            "breakout_down": breakout_down,
            "range_expansion": range_expansion,
            "vol_ratio": vol_ratio,
            "momentum": momentum
        }
        
        # Range too small - avoid false signals
        if recent_range_pct < self.min_range:
            return Signal("hold", 0.1, {**metadata, "reason": "Range too small"})
        
        # Breakout up with expansion
        if breakout_up and range_expansion > self.multiplier:
            if momentum > 0 and vol_ratio > 1.2:
                confidence = min(0.85, 0.6 + (range_expansion - 1) * 0.2)
                return Signal("buy", confidence, {**metadata, "reason": "Volatility breakout up"})
        
        # Breakout down with expansion
        if breakout_down and range_expansion > self.multiplier:
            if momentum < 0 and vol_ratio > 1.2:
                confidence = min(0.85, 0.6 + (range_expansion - 1) * 0.2)
                return Signal("sell", confidence, {**metadata, "reason": "Volatility breakout down"})
        
        # Moderate breakout
        if breakout_up and vol_ratio > 1.3:
            return Signal("buy", 0.6, {**metadata, "reason": "Range breakout up"})
        
        if breakout_down and vol_ratio > 1.3:
            return Signal("sell", 0.6, {**metadata, "reason": "Range breakout down"})
        
        return Signal("hold", 0.2, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    n = 30
    base = 40000
    
    # Consolidation period
    highs = [base + 200 + np.random.randn() * 50 for _ in range(25)]
    lows = [base - 200 + np.random.randn() * 50 for _ in range(25)]
    closes = [(h + l) / 2 for h, l in zip(highs, lows)]
    volumes = [1000 + np.random.randn() * 150 for _ in range(25)]
    
    # Breakout candle
    highs.append(max(highs) + 500)
    lows.append(closes[-1] + 100)
    closes.append(highs[-1] - 50)
    volumes.append(2000)
    
    strategy = VolatilityBreakoutStrategy()
    signal = strategy.analyze(highs, lows, closes, volumes)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
