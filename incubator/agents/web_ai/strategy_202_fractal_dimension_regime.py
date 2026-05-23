"""
Strategy 202: Fractal Dimension Regime Detection
Google Antigravity Strategy #2
Uses Higuchi fractal dimension for scale-invariant regime detection
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class FractalDimensionRegimeStrategy:
    """
    Higuchi fractal dimension for detecting market regime changes.
    High fractal dimension = more noise/trending, Low = smoother/mean-reverting.
    """
    
    def __init__(
        self,
        k_max: int = 8,
        fd_threshold_high: float = 1.6,
        fd_threshold_low: float = 1.3,
        lookback: int = 50
    ):
        self.k_max = k_max
        self.fd_high = fd_threshold_high
        self.fd_low = fd_threshold_low
        self.lookback = lookback
    
    def _higuchi_fd(self, series: List[float]) -> float:
        """Calculate Higuchi fractal dimension."""
        N = len(series)
        if N < self.k_max * 2:
            return 1.5  # Neutral
        
        L_values = []
        k_values = []
        
        for k in range(1, self.k_max + 1):
            L_k = []
            for m in range(k):
                # Construct new series
                indices = list(range(m, N, k))
                if len(indices) < 2:
                    continue
                
                subset = [series[i] for i in indices]
                L_m = sum(abs(subset[i] - subset[i-1]) for i in range(1, len(subset)))
                L_m *= (N - 1) / (k * (len(subset) - 1))
                L_k.append(L_m)
            
            if L_k:
                L_values.append(np.mean(L_k))
                k_values.append(k)
        
        if len(k_values) < 2:
            return 1.5
        
        # Slope of log(L) vs log(1/k)
        log_L = np.log(L_values + [1e-10])
        log_k = np.log([1.0/k for k in k_values])
        
        slope = np.polyfit(log_k, log_L, 1)[0]
        return slope
    
    def analyze(self, prices: List[float], volumes: List[float]) -> Signal:
        """Generate signal based on fractal dimension regime."""
        if len(prices) < self.lookback + self.k_max:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Calculate fractal dimension
        fd = self._higuchi_fd(prices[-self.lookback:])
        
        # Calculate price momentum
        returns = np.diff(prices) / prices[:-1]
        momentum = np.mean(returns[-10:]) if len(returns) >= 10 else 0
        
        # Volume trend
        vol_sma = np.mean(volumes[-10:])
        vol_prev = np.mean(volumes[-20:-10])
        vol_increasing = vol_sma > vol_prev * 1.1
        
        # Regime detection
        if fd > self.fd_high:
            # High fractal dimension = noisy/trending market
            if momentum > 0 and vol_increasing:
                return Signal("buy", min(fd/2, 0.9), {
                    "fd": fd,
                    "regime": "trending",
                    "momentum": momentum,
                    "reason": "trending_long"
                })
            elif momentum < 0 and vol_increasing:
                return Signal("sell", min(fd/2, 0.9), {
                    "fd": fd,
                    "regime": "trending",
                    "momentum": momentum,
                    "reason": "trending_short"
                })
        
        elif fd < self.fd_low:
            # Low fractal dimension = smooth/mean-reverting
            if momentum < -0.02:  # Oversold
                return Signal("buy", min((self.fd_low - fd) * 2, 0.85), {
                    "fd": fd,
                    "regime": "mean_reverting",
                    "momentum": momentum,
                    "reason": "mean_reversion_long"
                })
            elif momentum > 0.02:  # Overbought
                return Signal("sell", min((self.fd_low - fd) * 2, 0.85), {
                    "fd": fd,
                    "regime": "mean_reverting",
                    "momentum": momentum,
                    "reason": "mean_reversion_short"
                })
        
        return Signal("hold", 0.0, {"fd": fd, "regime": "transitional"})
