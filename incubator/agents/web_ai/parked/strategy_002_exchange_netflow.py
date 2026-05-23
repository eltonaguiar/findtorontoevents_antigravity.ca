"""
Strategy 002: Exchange Netflow Momentum
On-chain metric tracking exchange inflows vs outflows
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class ExchangeNetflowStrategy:
    """
    Analyzes exchange netflow patterns to predict price movements.
    Net outflows = accumulation (bullish)
    Net inflows = distribution (bearish)
    """
    
    def __init__(
        self,
        short_window: int = 3,
        medium_window: int = 7,
        long_window: int = 14,
        threshold_std: float = 2.0,
        min_volume_btc: float = 1000.0
    ):
        self.short_window = short_window
        self.medium_window = medium_window
        self.long_window = long_window
        self.threshold_std = threshold_std
        self.min_volume = min_volume_btc
    
    def analyze(
        self,
        inflows: List[float],
        outflows: List[float],
        prices: List[float]
    ) -> Signal:
        if len(inflows) < self.long_window:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Calculate netflow (positive = net inflow to exchanges = bearish)
        netflow = [inf - outf for inf, outf in zip(inflows, outflows)]
        
        # Moving averages
        short_ma = np.mean(netflow[-self.short_window:])
        medium_ma = np.mean(netflow[-self.medium_window:])
        long_ma = np.mean(netflow[-self.long_window:])
        
        # Standard deviation for anomaly detection
        netflow_std = np.std(netflow[-self.long_window:])
        
        # Current values
        current_netflow = netflow[-1]
        current_volume = inflows[-1] + outflows[-1]
        
        # Z-score
        z_score = (current_netflow - long_ma) / (netflow_std + 1e-8)
        
        # Trend analysis
        trend_short = short_ma - medium_ma
        trend_medium = medium_ma - long_ma
        
        metadata = {
            "current_netflow": current_netflow,
            "z_score": z_score,
            "short_ma": short_ma,
            "medium_ma": medium_ma,
            "long_ma": long_ma,
            "trend_alignment": np.sign(trend_short) == np.sign(trend_medium)
        }
        
        # Volume check
        if current_volume < self.min_volume:
            return Signal("hold", 0.1, {**metadata, "reason": "Low volume"})
        
        # Strong outflow (negative netflow) = bullish
        if z_score < -self.threshold_std and trend_short < 0:
            confidence = min(0.9, 0.5 + abs(z_score) * 0.1)
            return Signal("buy", confidence, metadata)
        
        # Strong inflow (positive netflow) = bearish
        if z_score > self.threshold_std and trend_short > 0:
            confidence = min(0.9, 0.5 + abs(z_score) * 0.1)
            return Signal("sell", confidence, metadata)
        
        return Signal("hold", 0.2, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    n_days = 30
    # Simulate exchange flows with trend
    base_inflow = 5000
    base_outflow = 4500
    
    inflows = [base_inflow + np.random.randn() * 1000 for _ in range(n_days)]
    outflows = [base_outflow + np.random.randn() * 1000 + (i * 50) for i in range(n_days)]  # Increasing outflows
    prices = 40000 + np.cumsum(np.random.randn(n_days) * 100)
    
    strategy = ExchangeNetflowStrategy()
    signal = strategy.analyze(inflows, outflows, prices.tolist())
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
