"""
Strategy 017: BTC-DXY Inverse Relationship
Cross-asset inverse correlation strategy
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class BTCDXYInverseStrategy:
    """
    Exploits inverse relationship between BTC and DXY (US Dollar Index).
    DXY strength often correlates with BTC weakness.
    """
    
    def __init__(
        self,
        lookback: int = 14,
        inverse_threshold: float = -0.3,
        momentum_period: int = 5
    ):
        self.lookback = lookback
        self.inverse_threshold = inverse_threshold
        self.momentum_period = momentum_period
    
    def _calculate_returns(self, prices: List[float]) -> List[float]:
        return [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
    
    def analyze(
        self,
        btc_prices: List[float],
        dxy_prices: List[float],
        btc_volumes: List[float]
    ) -> Signal:
        if len(btc_prices) < self.lookback + 1 or len(dxy_prices) < self.lookback + 1:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Calculate returns
        btc_returns = self._calculate_returns(btc_prices)
        dxy_returns = self._calculate_returns(dxy_prices)
        
        # Rolling correlation
        recent_btc = btc_returns[-self.lookback:]
        recent_dxy = dxy_returns[-self.lookback:]
        correlation = np.corrcoef(recent_btc, recent_dxy)[0, 1] if len(recent_btc) > 1 else 0
        
        # Current momentum
        btc_momentum = sum(btc_returns[-self.momentum_period:])
        dxy_momentum = sum(dxy_returns[-self.momentum_period:])
        
        # DXY regime
        dxy_ma = np.mean(dxy_prices[-self.lookback:])
        dxy_trend = "strong" if dxy_prices[-1] > dxy_ma * 1.02 else "weak" if dxy_prices[-1] < dxy_ma * 0.98 else "neutral"
        
        metadata = {
            "correlation": correlation,
            "btc_momentum": btc_momentum,
            "dxy_momentum": dxy_momentum,
            "dxy_trend": dxy_trend,
            "inverse_active": correlation < self.inverse_threshold
        }
        
        # Strong inverse correlation active
        if correlation < self.inverse_threshold:
            # DXY dropping, BTC should rise
            if dxy_momentum < -0.02 and btc_momentum > 0:
                confidence = min(0.85, 0.6 + abs(dxy_momentum) * 5)
                return Signal("buy", confidence, {**metadata, "reason": "DXY weakness, BTC strength"})
            
            # DXY rising, BTC should drop
            if dxy_momentum > 0.02 and btc_momentum < 0:
                confidence = min(0.85, 0.6 + dxy_momentum * 5)
                return Signal("sell", confidence, {**metadata, "reason": "DXY strength, BTC weakness"})
            
            # Divergence - DXY dropping but BTC not rising yet
            if dxy_momentum < -0.01 and btc_momentum < 0.01:
                return Signal("buy", 0.65, {**metadata, "reason": "DXY dropping, BTC lagging"})
        
        # Decoupling - BTC rising despite DXY strength
        if correlation > 0 and dxy_momentum > 0 and btc_momentum > 0.03:
            return Signal("buy", 0.7, {**metadata, "reason": "BTC decoupling from DXY"})
        
        return Signal("hold", 0.2, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    n = 30
    # DXY weakening
    dxy = [105 - i * 0.1 + np.random.randn() * 0.3 for i in range(n)]
    # BTC responding
    btc = [40000 + i * 100 + np.random.randn() * 300 for i in range(n)]
    volumes = [1000 + np.random.randn() * 200 for _ in range(n)]
    
    strategy = BTCDXYInverseStrategy()
    signal = strategy.analyze(btc, dxy, volumes)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
