"""
Strategy 220: Cointegration Residual Spread
Google Antigravity Strategy #20
Self-cointegration with half-life for OU process mean reversion
"""
from dataclasses import dataclass
from typing import List, Tuple
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class CointegrationResidualSpreadStrategy:
    """
    Uses price series self-cointegration with half-life estimation.
    Models price as mean-reverting OU process and trades at extremes.
    """
    
    def __init__(
        self,
        lookback: int = 50,
        zscore_threshold: float = 2.0,
        half_life_min: int = 5,
        half_life_max: int = 100
    ):
        self.lookback = lookback
        self.z_thresh = zscore_threshold
        self.hl_min = half_life_min
        self.hl_max = half_life_max
    
    def _estimate_half_life(self, prices: List[float]) -> float:
        """
        Estimate half-life of mean reversion using AR(1) model.
        y(t) = a + b*y(t-1) + e(t)
        Half-life = -ln(2) / ln(b)
        """
        if len(prices) < 10:
            return 20  # Default
        
        # Price changes (delta y)
        delta_y = np.diff(prices)
        y_lag = prices[:-1]
        
        # Remove mean
        delta_y = delta_y - np.mean(delta_y)
        y_lag = y_lag - np.mean(y_lag)
        
        # Regression: delta_y = a + b*y_lag
        if np.sum(y_lag**2) == 0:
            return 20
        
        beta = np.sum(y_lag * delta_y) / np.sum(y_lag**2)
        
        if beta >= 0:
            return 1000  # No mean reversion (trending)
        
        half_life = -np.log(2) / beta
        return max(self.hl_min, min(half_life, self.hl_max))
    
    def _calculate_ou_params(self, prices: List[float]) -> Tuple[float, float, float]:
        """
        Calculate Ornstein-Uhlenbeck parameters.
        Returns (theta, mu, sigma)
        """
        if len(prices) < 10:
            return 0, np.mean(prices), np.std(prices) if len(prices) > 1 else 1
        
        # Long-term mean
        mu = np.mean(prices)
        
        # Volatility
        sigma = np.std(prices) if len(prices) > 1 else 1
        
        # Speed of reversion (estimated from half-life)
        hl = self._estimate_half_life(prices)
        theta = np.log(2) / hl if hl > 0 else 0.1
        
        return theta, mu, sigma
    
    def _zscore(self, value: float, mean: float, std: float) -> float:
        """Calculate z-score."""
        if std == 0:
            return 0
        return (value - mean) / std
    
    def _calculate_residual_spread(self, prices: List[float]) -> List[float]:
        """Calculate residual spread from linear trend."""
        if len(prices) < 5:
            return [0] * len(prices)
        
        x = np.arange(len(prices))
        slope, intercept = np.polyfit(x, prices, 1)
        
        trend = [slope * i + intercept for i in x]
        residuals = [p - t for p, t in zip(prices, trend)]
        
        return residuals
    
    def analyze(self, prices: List[float], volumes: List[float]) -> Signal:
        """Generate signal based on OU process mean reversion."""
        if len(prices) < self.lookback + 5:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        recent_prices = prices[-self.lookback:]
        
        # OU parameters
        theta, mu, sigma = self._calculate_ou_params(recent_prices)
        
        # Half-life
        hl = self._estimate_half_life(recent_prices)
        
        # Calculate residual spread
        residuals = self._calculate_residual_spread(recent_prices)
        res_mean = np.mean(residuals)
        res_std = np.std(residuals)
        current_res = residuals[-1]
        
        # Z-score of residual
        res_zscore = self._zscore(current_res, res_mean, res_std)
        
        # Price z-score relative to OU mean
        price_zscore = self._zscore(prices[-1], mu, sigma)
        
        # Volume confirmation
        vol_ma = np.mean(volumes[-10:]) if len(volumes) >= 10 else 1
        vol_recent = np.mean(volumes[-3:]) if len(volumes) >= 3 else 0
        vol_confirm = vol_recent > vol_ma * 0.9
        
        # Mean reversion trading based on OU dynamics
        if self.hl_min <= hl <= self.hl_max:
            # Valid mean reversion regime
            
            if price_zscore < -self.z_thresh and res_zscore < -1.5:
                # Price below equilibrium and residual negative = strong buy
                confidence = min(abs(price_zscore) / 3 + abs(res_zscore) / 3, 0.95)
                return Signal("buy", confidence, {
                    "half_life": hl,
                    "theta": theta,
                    "price_zscore": price_zscore,
                    "res_zscore": res_zscore,
                    "regime": "mean_reverting",
                    "reason": "ou_extreme_long"
                })
            
            elif price_zscore > self.z_thresh and res_zscore > 1.5:
                # Price above equilibrium and residual positive = strong sell
                confidence = min(price_zscore / 3 + res_zscore / 3, 0.95)
                return Signal("sell", confidence, {
                    "half_life": hl,
                    "theta": theta,
                    "price_zscore": price_zscore,
                    "res_zscore": res_zscore,
                    "regime": "mean_reverting",
                    "reason": "ou_extreme_short"
                })
            
            elif abs(price_zscore) > self.z_thresh * 0.7 and vol_confirm:
                # Moderate extreme
                confidence = min(abs(price_zscore) / 4, 0.75)
                if price_zscore < 0:
                    return Signal("buy", confidence, {
                        "half_life": hl,
                        "price_zscore": price_zscore,
                        "reason": "ou_moderate_long"
                    })
                else:
                    return Signal("sell", confidence, {
                        "half_life": hl,
                        "price_zscore": price_zscore,
                        "reason": "ou_moderate_short"
                    })
        
        elif hl > self.hl_max:
            # Long half-life = trending regime
            momentum = (prices[-1] - prices[-10]) / prices[-10] if len(prices) >= 10 else 0
            if momentum > 0.02:
                return Signal("buy", min(momentum * 20, 0.7), {
                    "half_life": hl,
                    "momentum": momentum,
                    "regime": "trending",
                    "reason": "trend_follow_long"
                })
            elif momentum < -0.02:
                return Signal("sell", min(abs(momentum) * 20, 0.7), {
                    "half_life": hl,
                    "momentum": momentum,
                    "regime": "trending",
                    "reason": "trend_follow_short"
                })
        
        return Signal("hold", 0.0, {
            "half_life": hl,
            "theta": theta,
            "price_zscore": price_zscore,
            "regime": "mean_reverting" if hl <= self.hl_max else "trending"
        })
