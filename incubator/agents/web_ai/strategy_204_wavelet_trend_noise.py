"""
Strategy 204: Wavelet Trend-Noise Separation
Google Antigravity Strategy #4
Uses Haar wavelet decomposition for signal-to-noise ratio trading
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class WaveletTrendNoiseStrategy:
    """
    Separates trend from noise using Haar wavelet decomposition.
    Trade when signal (trend) dominates noise.
    """
    
    def __init__(
        self,
        decomposition_levels: int = 3,
        snr_threshold: float = 1.5,
        trend_threshold: float = 0.02
    ):
        self.levels = decomposition_levels
        self.snr_threshold = snr_threshold
        self.trend_threshold = trend_threshold
    
    def _haar_transform(self, data: List[float]) -> tuple:
        """Apply Haar wavelet transform."""
        coeffs = []
        approx = data.copy()
        
        for _ in range(self.levels):
            if len(approx) < 2:
                break
            
            # Detail coefficients (differences)
            detail = [(approx[2*i] - approx[2*i+1])/2 
                      for i in range(len(approx)//2)]
            
            # Approximation coefficients (averages)
            approx = [(approx[2*i] + approx[2*i+1])/2 
                     for i in range(len(approx)//2)]
            
            coeffs.append(detail)
        
        return approx, coeffs
    
    def _calculate_snr(self, approx: List[float], details: List[List[float]]) -> float:
        """Calculate signal-to-noise ratio."""
        if not approx or not details:
            return 0
        
        # Signal power (from approximation/trend)
        signal_power = np.var(approx) if len(approx) > 1 else 0
        
        # Noise power (from detail coefficients)
        noise_power = sum(np.var(d) for d in details if len(d) > 1)
        
        if noise_power == 0:
            return 10.0  # Very high SNR
        
        return signal_power / noise_power
    
    def analyze(self, prices: List[float], volumes: List[float]) -> Signal:
        """Generate signal based on wavelet SNR."""
        min_len = 2 ** self.levels * 2
        if len(prices) < min_len:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Detrend prices (use returns)
        returns = np.diff(prices) / prices[:-1]
        
        # Apply wavelet transform
        approx, details = self._haar_transform(returns[-min_len:].tolist())
        
        # Calculate SNR
        snr = self._calculate_snr(approx, details)
        
        # Trend direction from approximation
        trend = np.mean(approx) if approx else 0
        
        # Volume confirmation
        vol_ma = np.mean(volumes[-10:])
        vol_recent = np.mean(volumes[-3:])
        vol_confirm = vol_recent > vol_ma
        
        # Generate signals
        if snr > self.snr_threshold:
            if trend > self.trend_threshold and vol_confirm:
                return Signal("buy", min(snr/3, 0.9), {
                    "snr": snr,
                    "trend": trend,
                    "levels": self.levels,
                    "reason": "high_snr_trend_long"
                })
            elif trend < -self.trend_threshold and vol_confirm:
                return Signal("sell", min(snr/3, 0.9), {
                    "snr": snr,
                    "trend": trend,
                    "levels": self.levels,
                    "reason": "high_snr_trend_short"
                })
        
        # Low SNR = noisy market, look for mean reversion
        elif snr < 0.5:
            recent_return = returns[-1] if len(returns) > 0 else 0
            if recent_return < -0.03:  # Oversold bounce
                return Signal("buy", min((0.5 - snr), 0.6), {
                    "snr": snr,
                    "recent_return": recent_return,
                    "reason": "low_snr_bounce_long"
                })
            elif recent_return > 0.03:  # Overbought pullback
                return Signal("sell", min((0.5 - snr), 0.6), {
                    "snr": snr,
                    "recent_return": recent_return,
                    "reason": "low_snr_pullback_short"
                })
        
        return Signal("hold", 0.0, {"snr": snr, "trend": trend})
