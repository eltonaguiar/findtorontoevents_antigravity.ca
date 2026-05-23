"""
Strategy 207: VPIN Toxicity Flow
Google Antigravity Strategy #7
Order flow toxicity proxy using Volume-Synchronized Probability of Informed Trading
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class VPINToxicityFlowStrategy:
    """
    VPIN (Volume-Synchronized PIN) proxy for detecting toxic order flow.
    High VPIN = informed trading, expect volatility. Low VPIN = liquidity provision opportunity.
    """
    
    def __init__(
        self,
        bucket_volume: float = 1000.0,  # Volume bucket size (normalized)
        n_buckets: int = 20,
        vpin_threshold_high: float = 0.6,
        vpin_threshold_low: float = 0.3
    ):
        self.bucket_vol = bucket_volume
        self.n_buckets = n_buckets
        self.vpin_high = vpin_threshold_high
        self.vpin_low = vpin_threshold_low
    
    def _calculate_buy_volume_proxy(self, prices: List[float], volumes: List[float]) -> List[float]:
        """Estimate buy volume using price tick rule."""
        buy_vols = []
        for i in range(len(volumes)):
            if i == 0:
                buy_vols.append(volumes[i] * 0.5)  # Assume 50% at start
            else:
                if prices[i] > prices[i-1]:
                    buy_vols.append(volumes[i] * 0.8)  # Mostly buys on uptick
                elif prices[i] < prices[i-1]:
                    buy_vols.append(volumes[i] * 0.2)  # Mostly sells on downtick
                else:
                    buy_vols.append(volumes[i] * 0.5)  # Even on no change
        return buy_vols
    
    def _calculate_vpin(self, prices: List[float], volumes: List[float]) -> float:
        """Calculate VPIN proxy."""
        if len(volumes) < self.n_buckets:
            return 0.5  # Neutral
        
        buy_volumes = self._calculate_buy_volume_proxy(prices, volumes)
        
        # Create volume buckets
        buckets_buy = []
        buckets_total = []
        
        current_buy = 0
        current_total = 0
        
        for i in range(len(volumes)):
            current_buy += buy_volumes[i]
            current_total += volumes[i]
            
            # When bucket is full, record and reset
            if current_total >= self.bucket_vol:
                buckets_buy.append(current_buy)
                buckets_total.append(current_total)
                current_buy = 0
                current_total = 0
        
        if len(buckets_total) < self.n_buckets:
            return 0.5
        
        # Use last n buckets
        recent_buy = buckets_buy[-self.n_buckets:]
        recent_total = buckets_total[-self.n_buckets:]
        
        # VPIN = sum|buy_vol - sell_vol| / sum(total_vol)
        vpin_values = []
        for b, t in zip(recent_buy, recent_total):
            sell = t - b
            vpin_values.append(abs(b - sell) / t if t > 0 else 0)
        
        return np.mean(vpin_values)
    
    def analyze(self, prices: List[float], volumes: List[float]) -> Signal:
        """Generate signal based on VPIN toxicity."""
        if len(prices) < self.n_buckets * 2 or len(volumes) < self.n_buckets * 2:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Normalize volume bucket size based on average volume
        avg_vol = np.mean(volumes[-50:])
        self.bucket_vol = max(avg_vol * 0.5, 1.0)
        
        # Calculate VPIN
        vpin = self._calculate_vpin(prices, volumes)
        
        # Price momentum
        returns = np.diff(prices) / prices[:-1]
        mom = np.mean(returns[-5:]) if len(returns) >= 5 else 0
        
        # Volatility
        vol = np.std(returns[-20:]) if len(returns) >= 20 else 0
        
        # Trading logic
        if vpin > self.vpin_high:
            # High toxicity = informed trading, follow the move
            if mom > 0:
                return Signal("buy", min(vpin + abs(mom), 0.9), {
                    "vpin": vpin,
                    "mom": mom,
                    "toxicity": "high",
                    "reason": "toxic_flow_follow_long"
                })
            else:
                return Signal("sell", min(vpin + abs(mom), 0.9), {
                    "vpin": vpin,
                    "mom": mom,
                    "toxicity": "high",
                    "reason": "toxic_flow_follow_short"
                })
        
        elif vpin < self.vpin_low:
            # Low toxicity = uninformed flow, fade extremes
            if mom < -0.02:  # Oversold
                return Signal("buy", min((self.vpin_low - vpin) * 2, 0.7), {
                    "vpin": vpin,
                    "mom": mom,
                    "toxicity": "low",
                    "reason": "uninformed_fade_long"
                })
            elif mom > 0.02:  # Overbought
                return Signal("sell", min((self.vpin_low - vpin) * 2, 0.7), {
                    "vpin": vpin,
                    "mom": mom,
                    "toxicity": "low",
                    "reason": "uninformed_fade_short"
                })
        
        return Signal("hold", 0.0, {"vpin": vpin, "toxicity": "neutral"})
