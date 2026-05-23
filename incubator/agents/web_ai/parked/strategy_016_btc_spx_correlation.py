"""
Strategy 016: BTC-SPX Correlation Divergence
Cross-asset correlation strategy
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class BTCSpxCorrelationStrategy:
    """
    Monitors BTC-SPX correlation and divergence.
    When BTC diverges from SPX, potential mean reversion or breakout.
    """
    
    def __init__(
        self,
        correlation_period: int = 20,
        divergence_threshold: float = 0.05,
        zscore_threshold: float = 2.0
    ):
        self.corr_period = correlation_period
        self.divergence_threshold = divergence_threshold
        self.zscore_threshold = zscore_threshold
    
    def _calculate_correlation(self, x: List[float], y: List[float]) -> float:
        if len(x) != len(y) or len(x) < 2:
            return 0
        return np.corrcoef(x, y)[0, 1]
    
    def _calculate_beta(self, btc_returns: List[float], spx_returns: List[float]) -> float:
        if len(btc_returns) < 2:
            return 1
        covariance = np.cov(btc_returns, spx_returns)[0, 1]
        variance = np.var(spx_returns)
        return covariance / (variance + 1e-8)
    
    def analyze(
        self,
        btc_prices: List[float],
        spx_prices: List[float],
        btc_volumes: List[float]
    ) -> Signal:
        if len(btc_prices) < self.corr_period + 1 or len(spx_prices) < self.corr_period + 1:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Calculate returns
        btc_returns = [(btc_prices[i] - btc_prices[i-1]) / btc_prices[i-1] 
                       for i in range(1, len(btc_prices))]
        spx_returns = [(spx_prices[i] - spx_prices[i-1]) / spx_prices[i-1] 
                       for i in range(1, len(spx_prices))]
        
        # Rolling correlation
        recent_btc = btc_returns[-self.corr_period:]
        recent_spx = spx_returns[-self.corr_period:]
        correlation = self._calculate_correlation(recent_btc, recent_spx)
        
        # Beta
        beta = self._calculate_beta(recent_btc, recent_spx)
        
        # Expected BTC return based on SPX
        spx_recent_return = sum(recent_spx)
        expected_btc_return = beta * spx_recent_return
        actual_btc_return = sum(recent_btc)
        
        # Divergence
        divergence = actual_btc_return - expected_btc_return
        
        # Historical divergence for z-score
        divergences = []
        for i in range(self.corr_period, len(btc_returns)):
            window_btc = btc_returns[i-self.corr_period:i]
            window_spx = spx_returns[i-self.corr_period:i]
            b = self._calculate_beta(window_btc, window_spx)
            exp = b * sum(window_spx)
            act = sum(window_btc)
            divergences.append(act - exp)
        
        div_std = np.std(divergences) if divergences else 0.01
        div_zscore = divergence / (div_std + 1e-8)
        
        metadata = {
            "correlation": correlation,
            "beta": beta,
            "divergence": divergence,
            "div_zscore": div_zscore,
            "expected_return": expected_btc_return,
            "actual_return": actual_btc_return
        }
        
        # BTC underperforming - potential catch-up
        if div_zscore < -self.zscore_threshold and correlation > 0.5:
            confidence = min(0.8, 0.5 + abs(div_zscore) * 0.1)
            return Signal("buy", confidence, {**metadata, "reason": "BTC underperforming SPX"})
        
        # BTC outperforming - potential mean reversion
        if div_zscore > self.zscore_threshold and correlation > 0.5:
            confidence = min(0.75, 0.5 + div_zscore * 0.1)
            return Signal("sell", confidence, {**metadata, "reason": "BTC outperforming SPX"})
        
        # Low correlation regime - trade BTC trend independently
        if correlation < 0.3 and actual_btc_return > 0.05:
            return Signal("buy", 0.6, {**metadata, "reason": "BTC decoupled, strong momentum"})
        
        return Signal("hold", 0.2, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    n = 50
    # SPX trending up
    spx = [4000 + i * 10 + np.random.randn() * 20 for i in range(n)]
    # BTC lagging
    btc = [40000 + i * 30 + np.random.randn() * 500 for i in range(n)]
    volumes = [1000 + np.random.randn() * 200 for _ in range(n)]
    
    strategy = BTCSpxCorrelationStrategy()
    signal = strategy.analyze(btc, spx, volumes)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
