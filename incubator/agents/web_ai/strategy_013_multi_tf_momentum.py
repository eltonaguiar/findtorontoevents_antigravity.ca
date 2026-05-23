"""
Strategy 013: Multi-TF Momentum Confluence
Momentum alignment across timeframes
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class MultiTFMomentumStrategy:
    """
    Analyzes momentum indicators across multiple timeframes.
    Seeks confluence in momentum direction.
    """
    
    def __init__(
        self,
        rsi_period: int = 14,
        momentum_threshold: float = 50,
        confluence_required: int = 2
    ):
        self.rsi_period = rsi_period
        self.momentum_threshold = momentum_threshold
        self.confluence_required = confluence_required
    
    def _calculate_rsi(self, prices: List[float]) -> float:
        if len(prices) < self.rsi_period + 1:
            return 50
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        avg_gain = np.mean(gains[-self.rsi_period:])
        avg_loss = np.mean(losses[-self.rsi_period:])
        if avg_loss == 0:
            return 100
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    def _calculate_momentum(self, prices: List[float], period: int = 10) -> float:
        if len(prices) < period:
            return 0
        return (prices[-1] - prices[-period]) / prices[-period] * 100
    
    def analyze(
        self,
        weekly_prices: List[float],
        daily_prices: List[float],
        hourly_prices: List[float]
    ) -> Signal:
        if len(weekly_prices) < 20 or len(daily_prices) < 20 or len(hourly_prices) < 20:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Calculate momentum for each timeframe
        weekly_mom = self._calculate_momentum(weekly_prices, 4)
        daily_mom = self._calculate_momentum(daily_prices, 10)
        hourly_mom = self._calculate_momentum(hourly_prices, 24)
        
        # RSI for each timeframe
        weekly_rsi = self._calculate_rsi(weekly_prices)
        daily_rsi = self._calculate_rsi(daily_prices)
        hourly_rsi = self._calculate_rsi(hourly_prices)
        
        # Count bullish/bearish signals
        bullish_count = sum([
            weekly_mom > 0 and weekly_rsi > 50,
            daily_mom > 0 and daily_rsi > 50,
            hourly_mom > 0 and hourly_rsi > 50
        ])
        
        bearish_count = sum([
            weekly_mom < 0 and weekly_rsi < 50,
            daily_mom < 0 and daily_rsi < 50,
            hourly_mom < 0 and hourly_rsi < 50
        ])
        
        metadata = {
            "weekly_mom": weekly_mom,
            "daily_mom": daily_mom,
            "hourly_mom": hourly_mom,
            "weekly_rsi": weekly_rsi,
            "daily_rsi": daily_rsi,
            "hourly_rsi": hourly_rsi,
            "bullish_count": bullish_count,
            "bearish_count": bearish_count
        }
        
        # Strong confluence
        if bullish_count >= self.confluence_required:
            confidence = 0.5 + (bullish_count / 6)
            return Signal("buy", confidence, {**metadata, "reason": "Multi-TF momentum bullish"})
        
        if bearish_count >= self.confluence_required:
            confidence = 0.5 + (bearish_count / 6)
            return Signal("sell", confidence, {**metadata, "reason": "Multi-TF momentum bearish"})
        
        return Signal("hold", 0.2, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    n = 50
    # Bullish momentum across timeframes
    weekly = [40000 + i * 600 + np.random.randn() * 200 for i in range(n)]
    daily = [40000 + i * 120 + np.random.randn() * 100 for i in range(n*7)]
    hourly = [40000 + i * 6 + np.random.randn() * 30 for i in range(n*7*24)]
    
    strategy = MultiTFMomentumStrategy()
    signal = strategy.analyze(weekly, daily, hourly)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
