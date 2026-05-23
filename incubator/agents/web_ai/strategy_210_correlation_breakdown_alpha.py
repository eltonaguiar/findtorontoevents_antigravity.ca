"""
Strategy 210: Correlation Breakdown Alpha
Google Antigravity Strategy #10
Autocorrelation regime detection for both trend & mean-reversion modes
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class CorrelationBreakdownAlphaStrategy:
    """
    Detects autocorrelation regime breakdowns.
    High AC = trending (follow), Low/Negative AC = mean-reversion (fade).
    """
    
    def __init__(
        self,
        ac_period: int = 10,
        lookback: int = 30,
        ac_threshold_high: float = 0.3,
        ac_threshold_low: float = -0.1
    ):
        self.ac_period = ac_period
        self.lookback = lookback
        self.ac_high = ac_threshold_high
        self.ac_low = ac_threshold_low
    
    def _autocorrelation(self, series: List[float], lag: int = 1) -> float:
        """Calculate autocorrelation at given lag."""
        if len(series) < lag + 2:
            return 0
        
        x = series[lag:]
        y = series[:-lag]
        
        x_mean, y_mean = np.mean(x), np.mean(y)
        
        numerator = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, y))
        denom_x = sum((xi - x_mean)**2 for xi in x)
        denom_y = sum((yi - y_mean)**2 for yi in y)
        
        if denom_x == 0 or denom_y == 0:
            return 0
        
        return numerator / np.sqrt(denom_x * denom_y)
    
    def _rolling_ac(self, returns: List[float]) -> List[float]:
        """Calculate rolling autocorrelation."""
        ac_values = []
        for i in range(self.lookback, len(returns) + 1):
            window = returns[i-self.lookback:i]
            ac = self._autocorrelation(window, self.ac_period)
            ac_values.append(ac)
        return ac_values
    
    def analyze(self, prices: List[float], volumes: List[float]) -> Signal:
        """Generate signal based on autocorrelation regime."""
        if len(prices) < self.lookback + self.ac_period + 5:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Calculate returns
        returns = [(prices[i] - prices[i-1]) / prices[i-1] 
                   for i in range(1, len(prices))]
        
        # Current autocorrelation
        current_ac = self._autocorrelation(returns[-self.lookback:], self.ac_period)
        
        # Recent AC trend
        ac_series = self._rolling_ac(returns)
        ac_trend = np.mean(ac_series[-5:]) - np.mean(ac_series[-10:-5]) if len(ac_series) >= 10 else 0
        
        # Price momentum
        mom = (prices[-1] - prices[-10]) / prices[-10] if len(prices) >= 10 else 0
        
        # Volume confirmation
        vol_ma = np.mean(volumes[-10:]) if len(volumes) >= 10 else 0
        vol_long = np.mean(volumes[-20:]) if len(volumes) >= 20 else 1
        vol_trend = vol_ma / vol_long if vol_long > 0 else 1
        
        # Regime-based signals
        if current_ac > self.ac_high:
            # High autocorrelation = trending regime
            if mom > 0 and ac_trend >= 0:
                return Signal("buy", min(current_ac + abs(ac_trend), 0.9), {
                    "ac": current_ac,
                    "ac_trend": ac_trend,
                    "mom": mom,
                    "regime": "trending",
                    "reason": "high_ac_trend_long"
                })
            elif mom < 0 and ac_trend <= 0:
                return Signal("sell", min(current_ac + abs(ac_trend), 0.9), {
                    "ac": current_ac,
                    "ac_trend": ac_trend,
                    "mom": mom,
                    "regime": "trending",
                    "reason": "high_ac_trend_short"
                })
        
        elif current_ac < self.ac_low:
            # Low/negative autocorrelation = mean-reverting regime
            if mom < -0.02:  # Oversold
                return Signal("buy", min(abs(current_ac) + abs(mom), 0.85), {
                    "ac": current_ac,
                    "ac_trend": ac_trend,
                    "mom": mom,
                    "regime": "mean_reverting",
                    "reason": "low_ac_reversion_long"
                })
            elif mom > 0.02:  # Overbought
                return Signal("sell", min(abs(current_ac) + abs(mom), 0.85), {
                    "ac": current_ac,
                    "ac_trend": ac_trend,
                    "mom": mom,
                    "regime": "mean_reverting",
                    "reason": "low_ac_reversion_short"
                })
        
        # AC breakdown (rapid change) = potential reversal
        elif abs(ac_trend) > 0.2:
            if ac_trend < 0 and mom > 0:  # AC breaking down in uptrend
                return Signal("sell", min(abs(ac_trend), 0.7), {
                    "ac": current_ac,
                    "ac_trend": ac_trend,
                    "reason": "ac_breakdown_short"
                })
            elif ac_trend > 0 and mom < 0:  # AC building in downtrend
                return Signal("buy", min(abs(ac_trend), 0.7), {
                    "ac": current_ac,
                    "ac_trend": ac_trend,
                    "reason": "ac_buildup_long"
                })
        
        return Signal("hold", 0.0, {"ac": current_ac, "regime": "neutral"})
