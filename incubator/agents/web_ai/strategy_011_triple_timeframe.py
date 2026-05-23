"""
Strategy 011: Triple Timeframe Alignment
Multi-timeframe confluence strategy
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class TripleTimeframeStrategy:
    """
    Requires alignment across weekly, daily, and hourly timeframes.
    All three must agree for high-confidence signals.
    """
    
    def __init__(
        self,
        weekly_weight: float = 0.5,
        daily_weight: float = 0.3,
        hourly_weight: float = 0.2,
        min_alignment: float = 0.7
    ):
        self.weights = [weekly_weight, daily_weight, hourly_weight]
        self.min_alignment = min_alignment
    
    def _trend_direction(self, prices: List[float], period: int = 10) -> int:
        """Returns -1 (down), 0 (neutral), 1 (up)"""
        if len(prices) < period:
            return 0
        ma = np.mean(prices[-period:])
        prev_ma = np.mean(prices[-period-5:-5])
        diff = (ma - prev_ma) / prev_ma
        if diff > 0.02:
            return 1
        elif diff < -0.02:
            return -1
        return 0
    
    def analyze(
        self,
        weekly_prices: List[float],
        daily_prices: List[float],
        hourly_prices: List[float]
    ) -> Signal:
        if len(weekly_prices) < 10 or len(daily_prices) < 10 or len(hourly_prices) < 10:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Get trend directions
        weekly_trend = self._trend_direction(weekly_prices, 8)
        daily_trend = self._trend_direction(daily_prices, 20)
        hourly_trend = self._trend_direction(hourly_prices, 50)
        
        trends = [weekly_trend, daily_trend, hourly_trend]
        
        # Calculate alignment score
        bullish_score = sum(w * (1 if t == 1 else 0) for w, t in zip(self.weights, trends))
        bearish_score = sum(w * (1 if t == -1 else 0) for w, t in zip(self.weights, trends))
        
        metadata = {
            "weekly_trend": weekly_trend,
            "daily_trend": daily_trend,
            "hourly_trend": hourly_trend,
            "bullish_score": bullish_score,
            "bearish_score": bearish_score
        }
        
        # All aligned bullish
        if bullish_score >= self.min_alignment:
            confidence = min(0.9, bullish_score)
            return Signal("buy", confidence, {**metadata, "reason": "Full timeframe alignment bullish"})
        
        # All aligned bearish
        if bearish_score >= self.min_alignment:
            confidence = min(0.9, bearish_score)
            return Signal("sell", confidence, {**metadata, "reason": "Full timeframe alignment bearish"})
        
        # Partial alignment
        if bullish_score > 0.5:
            return Signal("buy", 0.55, {**metadata, "reason": "Partial bullish alignment"})
        if bearish_score > 0.5:
            return Signal("sell", 0.55, {**metadata, "reason": "Partial bearish alignment"})
        
        return Signal("hold", 0.2, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    # Generate aligned trending data
    n = 50
    weekly = [40000 + i * 500 + np.random.randn() * 200 for i in range(n)]
    daily = [40000 + i * 100 + np.random.randn() * 100 for i in range(n*7)]
    hourly = [40000 + i * 5 + np.random.randn() * 50 for i in range(n*7*24)]
    
    strategy = TripleTimeframeStrategy()
    signal = strategy.analyze(weekly, daily, hourly)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
