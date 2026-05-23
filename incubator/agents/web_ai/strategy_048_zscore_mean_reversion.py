"""
Strategy 048: Z-Score Mean Reversion
Statistical mean reversion strategy
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class ZScoreMeanReversionStrategy:
    """
    Pure z-score based mean reversion.
    Trades extreme deviations from statistical mean.
    """
    
    def __init__(
        self,
        lookback: int = 30,
        entry_zscore: float = 2.0,
        exit_zscore: float = 0.5,
        trend_filter: bool = True
    ):
        self.lookback = lookback
        self.entry_zscore = entry_zscore
        self.exit_zscore = exit_zscore
        self.trend_filter = trend_filter
    
    def analyze(
        self,
        prices: List[float],
        volumes: List[float]
    ) -> Signal:
        if len(prices) < self.lookback:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Calculate returns for stationarity
        returns = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
        
        # Current values
        current_price = prices[-1]
        current_return = returns[-1] if returns else 0
        
        # Historical statistics
        price_mean = np.mean(prices[-self.lookback:])
        price_std = np.std(prices[-self.lookback:])
        
        return_mean = np.mean(returns[-self.lookback:]) if returns else 0
        return_std = np.std(returns[-self.lookback:]) if len(returns) >= self.lookback else 0.01
        
        # Z-scores
        price_zscore = (current_price - price_mean) / (price_std + 1e-8)
        return_zscore = (current_return - return_mean) / (return_std + 1e-8)
        
        # Trend filter
        if self.trend_filter:
            ma_short = np.mean(prices[-5:])
            ma_long = np.mean(prices[-self.lookback:])
            trend = (ma_short - ma_long) / ma_long
        else:
            trend = 0
        
        # Bollinger position
        bb_upper = price_mean + 2 * price_std
        bb_lower = price_mean - 2 * price_std
        bb_position = (current_price - bb_lower) / (bb_upper - bb_lower + 1e-8)
        
        metadata = {
            "price_zscore": price_zscore,
            "return_zscore": return_zscore,
            "price_mean": price_mean,
            "trend": trend,
            "bb_position": bb_position
        }
        
        # Extreme positive z-score - mean reversion sell
        if price_zscore > self.entry_zscore:
            if not self.trend_filter or trend < 0.02:
                confidence = min(0.8, 0.5 + (price_zscore - self.entry_zscore) * 0.15)
                return Signal("sell", confidence, {**metadata, "reason": "Extreme positive z-score"})
        
        # Extreme negative z-score - mean reversion buy
        if price_zscore < -self.entry_zscore:
            if not self.trend_filter or trend > -0.02:
                confidence = min(0.8, 0.5 + (abs(price_zscore) - self.entry_zscore) * 0.15)
                return Signal("buy", confidence, {**metadata, "reason": "Extreme negative z-score"})
        
        # Return z-score extreme
        if return_zscore > self.entry_zscore * 1.5:
            return Signal("sell", 0.65, {**metadata, "reason": "Extreme return spike"})
        
        if return_zscore < -self.entry_zscore * 1.5:
            return Signal("buy", 0.65, {**metadata, "reason": "Extreme return drop"})
        
        # Exit zone
        if abs(price_zscore) < self.exit_zscore:
            return Signal("hold", 0.3, {**metadata, "reason": "Z-score normalized"})
        
        return Signal("hold", 0.2, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    n = 40
    # Normal distribution then extreme move
    prices = [40000 + np.random.randn() * 200 for _ in range(35)]
    prices.extend([prices[-1] + 800 + i * 50 for i in range(5)])  # Extreme up
    
    volumes = [1000 + np.random.randn() * 200 for _ in range(n)]
    
    strategy = ZScoreMeanReversionStrategy()
    signal = strategy.analyze(prices, volumes)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
