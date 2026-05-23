"""
Strategy 212: Regime-Switching GARCH
Google Antigravity Strategy #12
GARCH(1,1) forecast for volatility divergence trading
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class RegimeSwitchingGarchStrategy:
    """
    Uses GARCH(1,1) to forecast volatility.
    Trade when realized vol diverges from GARCH forecast.
    """
    
    def __init__(
        self,
        omega: float = 0.000001,
        alpha: float = 0.1,
        beta: float = 0.85,
        lookback: int = 30,
        divergence_threshold: float = 0.3
    ):
        self.omega = omega
        self.alpha = alpha
        self.beta = beta
        self.lookback = lookback
        self.div_thresh = divergence_threshold
    
    def _garch_forecast(self, returns: List[float]) -> float:
        """
        Simple GARCH(1,1) volatility forecast.
        sigma^2_t = omega + alpha*r^2_{t-1} + beta*sigma^2_{t-1}
        """
        if len(returns) < 10:
            return np.std(returns) if returns else 0.01
        
        # Initialize with unconditional variance
        var_uncond = np.var(returns)
        sigma2 = var_uncond
        
        # Iterate through returns
        for r in returns:
            sigma2 = self.omega + self.alpha * (r**2) + self.beta * sigma2
        
        return np.sqrt(sigma2)
    
    def _realized_vol(self, returns: List[float], window: int = 5) -> float:
        """Calculate realized volatility."""
        if len(returns) < window:
            return np.std(returns) if returns else 0.01
        
        return np.std(returns[-window:])
    
    def _estimate_garch_params(self, returns: List[float]) -> tuple:
        """
        Rough estimation of GARCH parameters via method of moments.
        Returns (omega, alpha, beta)
        """
        if len(returns) < self.lookback:
            return (self.omega, self.alpha, self.beta)
        
        # Simple estimation
        var = np.var(returns)
        
        # Estimate persistence (alpha + beta) from autocorrelation of squared returns
        sq_returns = [r**2 for r in returns]
        ac1 = self._autocorr(sq_returns, 1)
        persistence = min(max(ac1, 0.5), 0.99)
        
        # Split between alpha and beta
        alpha = persistence * 0.15
        beta = persistence * 0.85
        
        # Omega from unconditional variance
        omega = var * (1 - persistence)
        
        return (max(omega, 1e-8), max(alpha, 0.01), max(beta, 0.01))
    
    def _autocorr(self, series: List[float], lag: int) -> float:
        """Calculate autocorrelation."""
        if len(series) < lag + 2:
            return 0
        
        x = series[lag:]
        y = series[:-lag]
        
        x_mean, y_mean = np.mean(x), np.mean(y)
        num = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, y))
        den_x = sum((xi - x_mean)**2 for xi in x)
        den_y = sum((yi - y_mean)**2 for yi in y)
        
        if den_x == 0 or den_y == 0:
            return 0
        
        return num / np.sqrt(den_x * den_y)
    
    def analyze(self, prices: List[float], volumes: List[float]) -> Signal:
        """Generate signal based on GARCH vol divergence."""
        if len(prices) < self.lookback + 5:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Calculate returns
        returns = [(prices[i] - prices[i-1]) / prices[i-1] 
                   for i in range(1, len(prices))]
        
        # Estimate GARCH parameters
        omega, alpha, beta = self._estimate_garch_params(returns[-self.lookback:])
        
        # Store parameters temporarily
        orig_omega, orig_alpha, orig_beta = self.omega, self.alpha, self.beta
        self.omega, self.alpha, self.beta = omega, alpha, beta
        
        # GARCH forecast
        garch_vol = self._garch_forecast(returns[-self.lookback:])
        
        # Restore original parameters
        self.omega, self.alpha, self.beta = orig_omega, orig_alpha, orig_beta
        
        # Realized vol
        realized_vol = self._realized_vol(returns)
        
        # Vol divergence
        vol_ratio = realized_vol / (garch_vol + 1e-10)
        
        # Price momentum
        mom = (prices[-1] - prices[-10]) / prices[-10] if len(prices) >= 10 else 0
        
        # Vol regime classification
        if vol_ratio > 1 + self.div_thresh:
            # Realized vol > forecast = surprise vol expansion
            if mom < 0:
                # Down move with surprise vol = potential capitulation
                confidence = min((vol_ratio - 1) * 1.5, 0.9)
                return Signal("buy", confidence, {
                    "garch_vol": garch_vol,
                    "realized_vol": realized_vol,
                    "vol_ratio": vol_ratio,
                    "mom": mom,
                    "reason": "vol_expansion_capitulation_long"
                })
            else:
                # Up move with surprise vol = euphoria
                confidence = min((vol_ratio - 1) * 1.5, 0.9)
                return Signal("sell", confidence, {
                    "garch_vol": garch_vol,
                    "realized_vol": realized_vol,
                    "vol_ratio": vol_ratio,
                    "mom": mom,
                    "reason": "vol_expansion_euphoria_short"
                })
        
        elif vol_ratio < 1 - self.div_thresh:
            # Realized vol < forecast = vol compression
            if mom > 0:
                # Up move with low vol = calm trend
                confidence = min((1 - vol_ratio) * 2, 0.8)
                return Signal("buy", confidence, {
                    "garch_vol": garch_vol,
                    "realized_vol": realized_vol,
                    "vol_ratio": vol_ratio,
                    "mom": mom,
                    "reason": "vol_compression_trend_long"
                })
            else:
                # Down move with low vol = calm downtrend
                confidence = min((1 - vol_ratio) * 2, 0.8)
                return Signal("sell", confidence, {
                    "garch_vol": garch_vol,
                    "realized_vol": realized_vol,
                    "vol_ratio": vol_ratio,
                    "mom": mom,
                    "reason": "vol_compression_trend_short"
                })
        
        return Signal("hold", 0.0, {
            "garch_vol": garch_vol,
            "realized_vol": realized_vol,
            "vol_ratio": vol_ratio
        })
