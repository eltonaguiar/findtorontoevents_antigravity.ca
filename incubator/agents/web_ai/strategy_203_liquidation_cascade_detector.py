"""
Strategy 203: Liquidation Cascade Detector
Google Antigravity Strategy #3
Fades liquidation cascades using price acceleration + volume explosion
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class LiquidationCascadeDetectorStrategy:
    """
    Detects and fades liquidation cascades.
    Looks for price acceleration + volume spikes indicating forced liquidations.
    """
    
    def __init__(
        self,
        acceleration_threshold: float = 3.0,
        volume_spike_threshold: float = 3.0,
        cooldown_bars: int = 5,
        fade_timeout: int = 10
    ):
        self.accel_thresh = acceleration_threshold
        self.vol_spike_thresh = volume_spike_threshold
        self.cooldown = cooldown_bars
        self.fade_timeout = fade_timeout
    
    def _calculate_acceleration(self, prices: List[float]) -> float:
        """Calculate price acceleration (2nd derivative)."""
        if len(prices) < 5:
            return 0
        
        # Velocity (returns)
        v1 = (prices[-1] - prices[-2]) / prices[-2] if prices[-2] != 0 else 0
        v2 = (prices[-2] - prices[-3]) / prices[-3] if prices[-3] != 0 else 0
        v3 = (prices[-3] - prices[-4]) / prices[-4] if prices[-4] != 0 else 0
        
        # Acceleration (change in velocity)
        accel = (v1 - v3)  # 2-bar acceleration
        return accel
    
    def _detect_volume_spike(self, volumes: List[float]) -> float:
        """Detect volume spike as multiple of average."""
        if len(volumes) < 20:
            return 1.0
        
        current_vol = volumes[-1]
        avg_vol = np.mean(volumes[-20:-1])
        
        if avg_vol == 0:
            return 1.0
        
        return current_vol / avg_vol
    
    def analyze(self, prices: List[float], volumes: List[float]) -> Signal:
        """Generate fade signal after liquidation cascade."""
        if len(prices) < 20 or len(volumes) < 20:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Calculate metrics
        accel = self._calculate_acceleration(prices)
        vol_spike = self._detect_volume_spike(volumes)
        
        # Recent price change
        price_change_5 = (prices[-1] - prices[-6]) / prices[-6] if len(prices) >= 6 else 0
        price_change_10 = (prices[-1] - prices[-11]) / prices[-11] if len(prices) >= 11 else 0
        
        # Cascade detection: extreme acceleration + volume spike
        cascade_down = accel < -0.01 and vol_spike > self.vol_spike_thresh and price_change_5 < -0.05
        cascade_up = accel > 0.01 and vol_spike > self.vol_spike_thresh and price_change_5 > 0.05
        
        # RSI for oversold/overbought confirmation
        deltas = np.diff(prices)
        gains = [max(d, 0) for d in deltas[-14:]]
        losses = [abs(min(d, 0)) for d in deltas[-14:]]
        avg_gain = np.mean(gains) if gains else 0
        avg_loss = np.mean(losses) if losses else 0
        rs = avg_gain / (avg_loss + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        
        # Generate fade signals
        if cascade_down and rsi < 30:
            # Liquidation cascade down - fade with long
            confidence = min(abs(accel) * 50 + vol_spike * 0.1, 0.95)
            return Signal("buy", confidence, {
                "accel": accel,
                "vol_spike": vol_spike,
                "rsi": rsi,
                "price_change_5": price_change_5,
                "reason": "fade_liquidation_cascade_long"
            })
        
        elif cascade_up and rsi > 70:
            # Liquidation cascade up - fade with short
            confidence = min(abs(accel) * 50 + vol_spike * 0.1, 0.95)
            return Signal("sell", confidence, {
                "accel": accel,
                "vol_spike": vol_spike,
                "rsi": rsi,
                "price_change_5": price_change_5,
                "reason": "fade_liquidation_cascade_short"
            })
        
        return Signal("hold", 0.0, {
            "accel": accel,
            "vol_spike": vol_spike,
            "rsi": rsi,
            "reason": "no_cascade"
        })
