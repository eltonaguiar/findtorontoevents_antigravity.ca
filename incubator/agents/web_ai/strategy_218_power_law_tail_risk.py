"""
Strategy 218: Power Law Tail Risk
Google Antigravity Strategy #18
Hill tail estimator for fat/thin tail regime detection
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class PowerLawTailRiskStrategy:
    """
    Uses Hill estimator to detect tail risk regime.
    Fat tails = high risk of extreme moves, Thin tails = calmer regime.
    """
    
    def __init__(
        self,
        lookback: int = 50,
        tail_fraction: float = 0.1,
        hill_threshold_high: float = 3.0,
        hill_threshold_low: float = 2.0
    ):
        self.lookback = lookback
        self.tail_frac = tail_fraction
        self.hill_high = hill_threshold_high
        self.hill_low = hill_threshold_low
    
    def _hill_estimator(self, returns: List[float], tail: str = "upper") -> float:
        """
        Hill estimator for tail index.
        Lower Hill = fatter tail, Higher Hill = thinner tail.
        """
        if len(returns) < 10:
            return 3.0  # Default (normal-ish)
        
        sorted_returns = sorted(returns, reverse=(tail == "upper"))
        
        # Number of tail observations
        k = max(int(len(sorted_returns) * self.tail_frac), 5)
        k = min(k, len(sorted_returns) // 2)
        
        tail_obs = sorted_returns[:k]
        
        if len(tail_obs) < 2 or tail_obs[-1] <= 0:
            return 3.0
        
        # Hill estimator: 1/k * sum(log(Xi / Xk+1))
        threshold = tail_obs[-1]
        
        if threshold <= 0:
            return 3.0
        
        hill_sum = sum(np.log(abs(t) / threshold) for t in tail_obs if abs(t) > threshold)
        hill = k / (hill_sum + 1e-10)
        
        return hill
    
    def _calculate_var_es(self, returns: List[float], alpha: float = 0.05) -> tuple:
        """Calculate VaR and Expected Shortfall."""
        if not returns:
            return 0, 0
        
        sorted_returns = sorted(returns)
        idx = int(len(sorted_returns) * alpha)
        
        var = sorted_returns[idx] if idx < len(sorted_returns) else sorted_returns[0]
        es = np.mean(sorted_returns[:idx]) if idx > 0 else var
        
        return var, es
    
    def analyze(self, prices: List[float], volumes: List[float]) -> Signal:
        """Generate signal based on tail risk regime."""
        if len(prices) < self.lookback + 5:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Calculate returns
        returns = [(prices[i] - prices[i-1]) / prices[i-1] 
                   for i in range(1, len(prices))]
        
        # Hill estimators for both tails
        hill_upper = self._hill_estimator(returns, "upper")
        hill_lower = self._hill_estimator(returns, "lower")
        
        # Average Hill (lower = fatter tails)
        avg_hill = (hill_upper + hill_lower) / 2
        
        # VaR and ES
        var_5, es_5 = self._calculate_var_es(returns[-self.lookback:], 0.05)
        
        # Current momentum
        mom = (prices[-1] - prices[-10]) / prices[-10] if len(prices) >= 10 else 0
        
        # Tail risk classification
        fat_tail_upper = hill_upper < self.hill_low
        fat_tail_lower = hill_lower < self.hill_low
        thin_tails = avg_hill > self.hill_high
        
        # Trading logic
        if fat_tail_lower and mom < -0.03:
            # Fat lower tail + down move = extreme risk, wait or fade if oversold
            confidence = min((self.hill_low - hill_lower) * 0.3, 0.7)
            return Signal("buy", confidence, {
                "hill_upper": hill_upper,
                "hill_lower": hill_lower,
                "avg_hill": avg_hill,
                "var_5": var_5,
                "mom": mom,
                "reason": "fat_tail_bounce_long"
            })
        
        elif fat_tail_upper and mom > 0.03:
            # Fat upper tail + up move = euphoria, consider short
            confidence = min((self.hill_low - hill_upper) * 0.3, 0.7)
            return Signal("sell", confidence, {
                "hill_upper": hill_upper,
                "hill_lower": hill_lower,
                "avg_hill": avg_hill,
                "var_5": var_5,
                "mom": mom,
                "reason": "fat_tail_euphoria_short"
            })
        
        elif thin_tails and abs(mom) > 0.02:
            # Thin tails = more predictable, trend follow
            if mom > 0:
                return Signal("buy", min((avg_hill - self.hill_high) * 0.2 + abs(mom) * 5, 0.8), {
                    "hill_upper": hill_upper,
                    "hill_lower": hill_lower,
                    "avg_hill": avg_hill,
                    "mom": mom,
                    "reason": "thin_tail_trend_long"
                })
            else:
                return Signal("sell", min((avg_hill - self.hill_high) * 0.2 + abs(mom) * 5, 0.8), {
                    "hill_upper": hill_upper,
                    "hill_lower": hill_lower,
                    "avg_hill": avg_hill,
                    "mom": mom,
                    "reason": "thin_tail_trend_short"
                })
        
        return Signal("hold", 0.0, {
            "hill_upper": hill_upper,
            "hill_lower": hill_lower,
            "avg_hill": avg_hill,
            "tail_regime": "fat" if avg_hill < self.hill_low else ("thin" if avg_hill > self.hill_high else "normal")
        })
