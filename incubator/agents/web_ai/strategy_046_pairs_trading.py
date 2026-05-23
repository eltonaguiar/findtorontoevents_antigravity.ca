"""
Strategy 046: Pairs Trading
Statistical arbitrage pairs strategy
"""
from dataclasses import dataclass
from typing import List, Tuple
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class PairsTradingStrategy:
    """
    Classic pairs trading using price ratio mean reversion.
    Long underperformer, short outperformer.
    """
    
    def __init__(
        self,
        lookback: int = 30,
        entry_zscore: float = 2.0,
        exit_zscore: float = 0.5,
        min_correlation: float = 0.7
    ):
        self.lookback = lookback
        self.entry_zscore = entry_zscore
        self.exit_zscore = exit_zscore
        self.min_correlation = min_correlation
    
    def _calculate_hedge_ratio(self, prices1: List[float], prices2: List[float]) -> float:
        """Calculate hedge ratio using linear regression"""
        if len(prices1) != len(prices2) or len(prices1) < 2:
            return 1.0
        
        # Simple ratio-based hedge
        return np.mean([p1 / p2 for p1, p2 in zip(prices1, prices2)])
    
    def analyze(
        self,
        asset1_prices: List[float],
        asset2_prices: List[float],
        asset1_name: str = "Asset1",
        asset2_name: str = "Asset2"
    ) -> Signal:
        if len(asset1_prices) < self.lookback or len(asset2_prices) < self.lookback:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Calculate correlation
        correlation = np.corrcoef(asset1_prices[-self.lookback:], 
                                  asset2_prices[-self.lookback:])[0, 1]
        
        if correlation < self.min_correlation:
            return Signal("hold", 0.1, {"error": f"Correlation too low: {correlation:.2f}"})
        
        # Calculate spread
        hedge_ratio = self._calculate_hedge_ratio(asset1_prices[-self.lookback:], 
                                                   asset2_prices[-self.lookback:])
        
        spread = [p1 - hedge_ratio * p2 for p1, p2 in zip(asset1_prices, asset2_prices)]
        
        # Z-score of spread
        spread_mean = np.mean(spread[-self.lookback:])
        spread_std = np.std(spread[-self.lookback:])
        current_spread = spread[-1]
        zscore = (current_spread - spread_mean) / (spread_std + 1e-8)
        
        # Spread trend
        spread_trend = current_spread - spread[-5] if len(spread) >= 5 else 0
        
        metadata = {
            "correlation": correlation,
            "hedge_ratio": hedge_ratio,
            "spread": current_spread,
            "spread_mean": spread_mean,
            "zscore": zscore,
            "spread_trend": spread_trend
        }
        
        # Spread far above mean - asset1 overvalued vs asset2
        if zscore > self.entry_zscore and spread_trend < 0:
            confidence = min(0.8, 0.5 + (zscore - self.entry_zscore) * 0.2)
            return Signal("sell", confidence, {**metadata, "reason": f"{asset1_name} rich vs {asset2_name}"})
        
        # Spread far below mean - asset1 undervalued vs asset2
        if zscore < -self.entry_zscore and spread_trend > 0:
            confidence = min(0.8, 0.5 + (abs(zscore) - self.entry_zscore) * 0.2)
            return Signal("buy", confidence, {**metadata, "reason": f"{asset1_name} cheap vs {asset2_name}"})
        
        # Exit signals
        if abs(zscore) < self.exit_zscore:
            return Signal("hold", 0.3, {**metadata, "reason": "Spread normalized - exit pairs trade"})
        
        return Signal("hold", 0.2, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    n = 40
    # Two correlated assets
    base = 40000
    asset1 = [base + i * 50 + np.random.randn() * 100 for i in range(n)]
    asset2 = [base * 0.55 + i * 30 + np.random.randn() * 80 for i in range(n)]
    
    # Create divergence
    asset1[-5:] = [a + 500 for a in asset1[-5:]]
    
    strategy = PairsTradingStrategy()
    signal = strategy.analyze(asset1, asset2, "BTC", "ETH")
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
