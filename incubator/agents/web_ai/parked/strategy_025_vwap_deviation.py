"""
Strategy 025: VWAP Deviation
Volume-weighted average price strategy
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class VWAPDeviationStrategy:
    """
    Trades deviations from VWAP.
    Price below VWAP = potential buy (mean reversion)
    Price above VWAP = potential sell
    """
    
    def __init__(
        self,
        vwap_period: int = 24,  # Hours
        deviation_threshold: float = 0.02,
        trend_filter: bool = True
    ):
        self.vwap_period = vwap_period
        self.deviation_threshold = deviation_threshold
        self.trend_filter = trend_filter
    
    def _calculate_vwap(self, prices: List[float], volumes: List[float]) -> float:
        if len(prices) != len(volumes) or len(prices) == 0:
            return prices[-1] if prices else 0
        
        period = min(self.vwap_period, len(prices))
        pv_sum = sum(p * v for p, v in zip(prices[-period:], volumes[-period:]))
        v_sum = sum(volumes[-period:])
        return pv_sum / (v_sum + 1e-8)
    
    def analyze(
        self,
        prices: List[float],
        volumes: List[float],
        highs: List[float],
        lows: List[float]
    ) -> Signal:
        if len(prices) < self.vwap_period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        current_price = prices[-1]
        vwap = self._calculate_vwap(prices, volumes)
        
        # Deviation calculation
        deviation = (current_price - vwap) / vwap
        deviation_pct = deviation * 100
        
        # Standard deviation of deviations
        historical_devs = []
        for i in range(self.vwap_period, len(prices)):
            period_vwap = self._calculate_vwap(prices[:i], volumes[:i])
            historical_devs.append((prices[i-1] - period_vwap) / period_vwap)
        
        dev_std = np.std(historical_devs) if historical_devs else 0.01
        zscore = deviation / (dev_std + 1e-8)
        
        # Trend
        if self.trend_filter and len(prices) >= 10:
            short_ma = np.mean(prices[-5:])
            long_ma = np.mean(prices[-10:])
            trend = "up" if short_ma > long_ma else "down"
        else:
            trend = "neutral"
        
        metadata = {
            "vwap": vwap,
            "current_price": current_price,
            "deviation": deviation,
            "deviation_pct": deviation_pct,
            "zscore": zscore,
            "trend": trend
        }
        
        # Significant below VWAP - mean reversion buy
        if deviation < -self.deviation_threshold and zscore < -1.5:
            confidence = min(0.8, 0.5 + abs(deviation) * 10)
            return Signal("buy", confidence, {**metadata, "reason": "Price below VWAP"})
        
        # Significant above VWAP - mean reversion sell
        if deviation > self.deviation_threshold and zscore > 1.5:
            confidence = min(0.8, 0.5 + deviation * 10)
            return Signal("sell", confidence, {**metadata, "reason": "Price above VWAP"})
        
        # VWAP breakout with trend
        if self.trend_filter:
            if deviation > 0.005 and trend == "up":
                return Signal("buy", 0.6, {**metadata, "reason": "VWAP breakout with trend"})
            if deviation < -0.005 and trend == "down":
                return Signal("sell", 0.6, {**metadata, "reason": "VWAP breakdown with trend"})
        
        return Signal("hold", 0.2, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    n = 30
    # Price below VWAP
    prices = [40000 - i * 50 + np.random.randn() * 100 for i in range(n)]
    volumes = [1000 + np.random.randn() * 200 for _ in range(n)]
    highs = [p + 100 for p in prices]
    lows = [p - 100 for p in prices]
    
    strategy = VWAPDeviationStrategy()
    signal = strategy.analyze(prices, volumes, highs, lows)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
