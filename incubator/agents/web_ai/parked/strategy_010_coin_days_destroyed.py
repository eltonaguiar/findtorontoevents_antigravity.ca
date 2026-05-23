"""
Strategy 010: Coin Days Destroyed Anomaly
On-chain metric tracking old coin movement
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class CDDCVDDStrategy:
    """
    Coin Days Destroyed (CDD) and Cumulative Value Days Destroyed (CVDD).
    High CDD = old coins moving (potential distribution)
    CVDD can indicate market bottoms.
    """
    
    def __init__(
        self,
        cdd_threshold_std: float = 2.5,
        cvdd_proximity: float = 0.1,
        ma_period: int = 30,
        lookback: int = 90
    ):
        self.cdd_threshold = cdd_threshold_std
        self.cvdd_proximity = cvdd_proximity
        self.ma_period = ma_period
        self.lookback = lookback
    
    def analyze(
        self,
        cdd: List[float],
        cvdd: float,
        prices: List[float]
    ) -> Signal:
        if len(cdd) < self.lookback:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        current_cdd = cdd[-1]
        cdd_ma = np.mean(cdd[-self.ma_period:])
        cdd_std = np.std(cdd[-self.lookback:])
        
        # Z-score
        cdd_zscore = (current_cdd - cdd_ma) / (cdd_std + 1e-8)
        
        # Trend
        recent_cdd = np.mean(cdd[-7:])
        older_cdd = np.mean(cdd[-14:-7])
        cdd_trend = recent_cdd - older_cdd
        
        # CVDD proximity
        current_price = prices[-1]
        cvdd_distance = (current_price - cvdd) / cvdd
        near_cvdd = abs(cvdd_distance) < self.cvdd_proximity
        
        metadata = {
            "cdd": current_cdd,
            "cdd_zscore": cdd_zscore,
            "cdd_trend": cdd_trend,
            "cvdd": cvdd,
            "cvdd_distance": cvdd_distance,
            "near_cvdd": near_cvdd
        }
        
        # Extreme CDD spike - potential top/distribution
        if cdd_zscore > self.cdd_threshold and cdd_trend > 0:
            confidence = min(0.85, 0.5 + (cdd_zscore - self.cdd_threshold) * 0.1)
            return Signal("sell", confidence, {**metadata, "reason": "Old coins moving - distribution"})
        
        # Price near CVDD - potential bottom
        if near_cvdd and cdd_zscore < 1:
            confidence = min(0.8, 0.6 + (self.cvdd_proximity - abs(cvdd_distance)) * 2)
            return Signal("buy", confidence, {**metadata, "reason": "Price near CVDD floor"})
        
        # Low CDD in uptrend - hodling strong
        if cdd_zscore < -1 and current_price > prices[-self.ma_period] * 1.05:
            return Signal("buy", 0.65, {**metadata, "reason": "Strong holding in uptrend"})
        
        return Signal("hold", 0.2, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    n_days = 100
    # Normal CDD with occasional spikes
    cdd = [1e8 + np.random.exponential(5e7) for _ in range(n_days)]
    # Recent spike
    cdd[-3:] = [5e8, 6e8, 4e8]
    
    cvdd = 35000
    prices = [40000 + np.random.randn() * 2000 for _ in range(n_days)]
    
    strategy = CDDCVDDStrategy()
    signal = strategy.analyze(cdd, cvdd, prices)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
