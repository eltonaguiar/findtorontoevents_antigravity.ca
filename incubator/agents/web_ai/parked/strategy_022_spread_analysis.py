"""
Strategy 022: Bid-Ask Spread Analysis
Microstructure spread-based strategy
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class SpreadAnalysisStrategy:
    """
    Analyzes bid-ask spread dynamics.
    Spread compression often precedes volatility expansion.
    Wide spreads indicate low liquidity/risk.
    """
    
    def __init__(
        self,
        spread_ma_period: int = 20,
        compression_threshold: float = 0.7,
        expansion_threshold: float = 1.5
    ):
        self.ma_period = spread_ma_period
        self.compression_threshold = compression_threshold
        self.expansion_threshold = expansion_threshold
    
    def analyze(
        self,
        spreads: List[float],  # Historical spreads
        prices: List[float],
        volumes: List[float]
    ) -> Signal:
        if len(spreads) < self.ma_period:
            return Signal("hold", 0.0, {"error": "Insufficient spread data"})
        
        current_spread = spreads[-1]
        spread_ma = np.mean(spreads[-self.ma_period:])
        spread_std = np.std(spreads[-self.ma_period:])
        
        # Spread metrics
        spread_ratio = current_spread / spread_ma if spread_ma > 0 else 1
        spread_zscore = (current_spread - spread_ma) / (spread_std + 1e-8)
        
        # Trend
        price_change = (prices[-1] - prices[-5]) / prices[-5] if len(prices) >= 5 else 0
        volume_surge = volumes[-1] / np.mean(volumes[-5:]) if len(volumes) >= 5 else 1
        
        metadata = {
            "current_spread": current_spread,
            "spread_ma": spread_ma,
            "spread_ratio": spread_ratio,
            "spread_zscore": spread_zscore,
            "price_change": price_change,
            "volume_surge": volume_surge
        }
        
        # Spread compression - volatility expansion coming
        if spread_ratio < self.compression_threshold and volume_surge > 1.2:
            # Direction based on price trend
            if price_change > 0:
                return Signal("buy", 0.7, {**metadata, "reason": "Spread compression, bullish bias"})
            elif price_change < 0:
                return Signal("sell", 0.7, {**metadata, "reason": "Spread compression, bearish bias"})
            else:
                return Signal("buy", 0.55, {**metadata, "reason": "Spread compression, awaiting breakout"})
        
        # Spread expansion - potential reversal
        if spread_ratio > self.expansion_threshold and spread_zscore > 2:
            if price_change > 0.02:
                return Signal("sell", 0.65, {**metadata, "reason": "Wide spread after rally - exhaustion"})
            if price_change < -0.02:
                return Signal("buy", 0.65, {**metadata, "reason": "Wide spread after drop - capitulation"})
        
        # Normal spread with momentum
        if spread_ratio < 1.1 and price_change > 0.01:
            return Signal("buy", 0.55, {**metadata, "reason": "Normal spread, positive momentum"})
        
        return Signal("hold", 0.2, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    n = 30
    # Spreads compressing
    spreads = [50 - i * 1 + np.random.randn() * 5 for i in range(n)]
    spreads[-5:] = [15, 14, 16, 15, 14]  # Compressed
    
    prices = [40000 + i * 50 + np.random.randn() * 100 for i in range(n)]
    volumes = [1000 + np.random.randn() * 200 for _ in range(n)]
    volumes[-1] = 1500  # Volume surge
    
    strategy = SpreadAnalysisStrategy()
    signal = strategy.analyze(spreads, prices, volumes)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
