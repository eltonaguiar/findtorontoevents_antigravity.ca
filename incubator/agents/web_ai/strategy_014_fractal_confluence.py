"""
Strategy 014: Fractal Pattern Confluence
Multi-timeframe fractal pattern detection
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class FractalConfluenceStrategy:
    """
    Detects similar patterns across timeframes (fractals).
    When patterns align, signals are stronger.
    """
    
    def __init__(
        self,
        pattern_length: int = 5,
        similarity_threshold: float = 0.8,
        min_timeframes: int = 2
    ):
        self.pattern_length = pattern_length
        self.similarity_threshold = similarity_threshold
        self.min_timeframes = min_timeframes
    
    def _normalize_pattern(self, prices: List[float]) -> List[float]:
        """Normalize price pattern to 0-1 range"""
        if len(prices) < 2:
            return [0.5]
        pmin, pmax = min(prices), max(prices)
        if pmax == pmin:
            return [0.5] * len(prices)
        return [(p - pmin) / (pmax - pmin) for p in prices]
    
    def _detect_pattern(self, prices: List[float]) -> str:
        """Detect basic pattern: higher_high, lower_low, consolidation"""
        if len(prices) < self.pattern_length:
            return "unknown"
        
        recent = prices[-self.pattern_length:]
        normalized = self._normalize_pattern(recent)
        
        # Check for higher highs
        highs = [normalized[i] > normalized[i-1] for i in range(1, len(normalized))]
        if sum(highs) >= len(highs) * 0.7:
            return "higher_highs"
        
        # Check for lower lows
        lows = [normalized[i] < normalized[i-1] for i in range(1, len(normalized))]
        if sum(lows) >= len(lows) * 0.7:
            return "lower_lows"
        
        # Consolidation
        if max(normalized) - min(normalized) < 0.3:
            return "consolidation"
        
        return "mixed"
    
    def analyze(
        self,
        weekly_prices: List[float],
        daily_prices: List[float],
        hourly_prices: List[float]
    ) -> Signal:
        if len(weekly_prices) < 10 or len(daily_prices) < 10 or len(hourly_prices) < 10:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Detect patterns on each timeframe
        weekly_pattern = self._detect_pattern(weekly_prices)
        daily_pattern = self._detect_pattern(daily_prices)
        hourly_pattern = self._detect_pattern(hourly_prices)
        
        patterns = [weekly_pattern, daily_pattern, hourly_pattern]
        
        # Count pattern occurrences
        hh_count = patterns.count("higher_highs")
        ll_count = patterns.count("lower_lows")
        cons_count = patterns.count("consolidation")
        
        metadata = {
            "weekly_pattern": weekly_pattern,
            "daily_pattern": daily_pattern,
            "hourly_pattern": hourly_pattern,
            "hh_count": hh_count,
            "ll_count": ll_count,
            "cons_count": cons_count
        }
        
        # Fractal confluence - higher highs on multiple timeframes
        if hh_count >= self.min_timeframes:
            confidence = 0.5 + (hh_count * 0.15)
            return Signal("buy", confidence, {**metadata, "reason": "Fractal higher highs confluence"})
        
        # Fractal confluence - lower lows on multiple timeframes
        if ll_count >= self.min_timeframes:
            confidence = 0.5 + (ll_count * 0.15)
            return Signal("sell", confidence, {**metadata, "reason": "Fractal lower lows confluence"})
        
        # Consolidation breakout setup
        if cons_count >= 2 and hh_count >= 1:
            return Signal("buy", 0.6, {**metadata, "reason": "Consolidation with bullish breakout"})
        
        if cons_count >= 2 and ll_count >= 1:
            return Signal("sell", 0.6, {**metadata, "reason": "Consolidation with bearish breakdown"})
        
        return Signal("hold", 0.2, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    # Create higher high patterns across timeframes
    n = 20
    weekly = [40000 + i * 500 + abs(np.random.randn()) * 100 for i in range(n)]
    daily = [40000 + i * 100 + abs(np.random.randn()) * 50 for i in range(n*7)]
    hourly = [40000 + i * 5 + abs(np.random.randn()) * 20 for i in range(n*7*24)]
    
    strategy = FractalConfluenceStrategy()
    signal = strategy.analyze(weekly, daily, hourly)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
