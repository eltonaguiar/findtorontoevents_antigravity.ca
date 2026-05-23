"""
Strategy 018: ETH-BTC Ratio Rotation
Cross-asset ratio trading strategy
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class ETHBTCRatioStrategy:
    """
    Trades the ETH/BTC ratio based on momentum and mean reversion.
    Ratio expansion = ETH outperforming (bullish ETH, bearish BTC)
    Ratio contraction = BTC outperforming (bearish ETH, bullish BTC)
    """
    
    def __init__(
        self,
        ma_period: int = 20,
        std_period: int = 30,
        zscore_threshold: float = 1.5,
        momentum_period: int = 5
    ):
        self.ma_period = ma_period
        self.std_period = std_period
        self.zscore_threshold = zscore_threshold
        self.momentum_period = momentum_period
    
    def analyze(
        self,
        eth_prices: List[float],
        btc_prices: List[float],
        eth_volumes: List[float]
    ) -> Signal:
        if len(eth_prices) < self.std_period or len(btc_prices) < self.std_period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Calculate ratio
        ratio = [e / (b + 1e-8) for e, b in zip(eth_prices, btc_prices)]
        
        # Statistics
        current_ratio = ratio[-1]
        ratio_ma = np.mean(ratio[-self.ma_period:])
        ratio_std = np.std(ratio[-self.std_period:])
        
        # Z-score
        zscore = (current_ratio - ratio_ma) / (ratio_std + 1e-8)
        
        # Momentum
        ratio_momentum = (current_ratio - ratio[-self.momentum_period]) / ratio[-self.momentum_period]
        
        # Trend
        short_ma = np.mean(ratio[-5:])
        long_ma = np.mean(ratio[-self.ma_period:])
        
        metadata = {
            "ratio": current_ratio,
            "ratio_ma": ratio_ma,
            "zscore": zscore,
            "momentum": ratio_momentum,
            "short_ma": short_ma,
            "long_ma": long_ma
        }
        
        # Mean reversion - ratio extended above mean
        if zscore > self.zscore_threshold and ratio_momentum < 0:
            confidence = min(0.8, 0.5 + (zscore - self.zscore_threshold) * 0.2)
            return Signal("sell", confidence, {**metadata, "reason": "ETH/BTC overextended, reverting"})
        
        # Mean reversion - ratio extended below mean
        if zscore < -self.zscore_threshold and ratio_momentum > 0:
            confidence = min(0.8, 0.5 + abs(zscore - self.zscore_threshold) * 0.2)
            return Signal("buy", confidence, {**metadata, "reason": "ETH/BTC oversold, reverting"})
        
        # Momentum continuation - ratio breaking out
        if zscore > 1 and short_ma > long_ma * 1.01 and ratio_momentum > 0.02:
            return Signal("buy", 0.65, {**metadata, "reason": "ETH/BTC momentum breakout"})
        
        if zscore < -1 and short_ma < long_ma * 0.99 and ratio_momentum < -0.02:
            return Signal("sell", 0.65, {**metadata, "reason": "ETH/BTC momentum breakdown"})
        
        return Signal("hold", 0.2, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    n = 40
    # ETH underperforming BTC - ratio low
    btc = [40000 + i * 50 + np.random.randn() * 200 for i in range(n)]
    eth = [2200 + i * 15 + np.random.randn() * 50 for i in range(n)]
    volumes = [1000 + np.random.randn() * 200 for _ in range(n)]
    
    strategy = ETHBTCRatioStrategy()
    signal = strategy.analyze(eth, btc, volumes)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
