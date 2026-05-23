"""
Strategy 209: Adaptive Kelly Regime Sizing
Google Antigravity Strategy #9
Kelly criterion embedded with dynamic sizing based on regime
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class AdaptiveKellyRegimeStrategy:
    """
    Uses Kelly Criterion for position sizing with regime-dependent parameters.
    Adapts Kelly fraction based on market regime (trending vs mean-reverting).
    """
    
    def __init__(
        self,
        lookback: int = 30,
        kelly_fraction: float = 0.5,  # Half-Kelly for safety
        regime_window: int = 20
    ):
        self.lookback = lookback
        self.kelly_frac = kelly_fraction
        self.regime_window = regime_window
    
    def _calculate_kelly(self, wins: List[float], losses: List[float]) -> float:
        """
        Calculate Kelly Criterion: f* = (p*b - q) / b
        where p = win rate, q = loss rate, b = avg win/avg loss
        """
        if not wins or not losses:
            return 0
        
        p = len(wins) / (len(wins) + len(losses))
        q = 1 - p
        
        avg_win = np.mean(wins) if wins else 0
        avg_loss = abs(np.mean(losses)) if losses else 1
        
        b = avg_win / avg_loss if avg_loss > 0 else 1
        
        kelly = (p * b - q) / b if b > 0 else 0
        return max(0, min(kelly, 1))  # Cap at 1 (100%)
    
    def _detect_regime(self, prices: List[float]) -> str:
        """Detect market regime: trending or mean-reverting."""
        if len(prices) < self.regime_window:
            return "unknown"
        
        returns = np.diff(prices) / prices[:-1]
        recent_returns = returns[-self.regime_window:]
        
        # Hurst-like exponent proxy
        # Trending: positive autocorrelation
        # Mean-reverting: negative autocorrelation
        
        if len(recent_returns) < 10:
            return "unknown"
        
        # Variance ratio test proxy
        var_1 = np.var(recent_returns)
        
        # 5-period returns
        if len(recent_returns) >= 10:
            returns_5 = [sum(recent_returns[i:i+5]) for i in range(0, len(recent_returns)-4, 5)]
            var_5 = np.var(returns_5) / 5 if len(returns_5) > 1 else var_1
        else:
            var_5 = var_1
        
        ratio = var_5 / (var_1 + 1e-10)
        
        if ratio > 1.2:
            return "trending"
        elif ratio < 0.8:
            return "mean_reverting"
        else:
            return "random"
    
    def analyze(self, prices: List[float], volumes: List[float]) -> Signal:
        """Generate signal with Kelly-sized position recommendation."""
        if len(prices) < self.lookback + 10:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Calculate returns
        returns = [(prices[i] - prices[i-1]) / prices[i-1] 
                   for i in range(1, len(prices))]
        
        # Separate wins and losses
        wins = [r for r in returns[-self.lookback:] if r > 0]
        losses = [r for r in returns[-self.lookback:] if r < 0]
        
        # Calculate Kelly
        kelly = self._calculate_kelly(wins, losses)
        
        # Detect regime
        regime = self._detect_regime(prices)
        
        # Adjust Kelly based on regime
        regime_mult = {
            "trending": 1.0,       # Full Kelly in trends
            "mean_reverting": 0.5,  # Half Kelly in MR
            "random": 0.25,         # Quarter Kelly in noise
            "unknown": 0.25
        }.get(regime, 0.25)
        
        adjusted_kelly = kelly * self.kelly_frac * regime_mult
        
        # Current momentum
        mom = (prices[-1] - prices[-10]) / prices[-10] if len(prices) >= 10 else 0
        
        # Volatility filter
        vol = np.std(returns[-20:]) if len(returns) >= 20 else 0
        vol_filter = vol < 0.05  # Only trade in moderate vol regimes
        
        # Generate signals
        if adjusted_kelly > 0.1 and vol_filter:
            if mom > 0.02:
                return Signal("buy", min(adjusted_kelly * 2, 0.95), {
                    "kelly": kelly,
                    "adjusted_kelly": adjusted_kelly,
                    "regime": regime,
                    "mom": mom,
                    "reason": "kelly_sized_long"
                })
            elif mom < -0.02:
                return Signal("sell", min(adjusted_kelly * 2, 0.95), {
                    "kelly": kelly,
                    "adjusted_kelly": adjusted_kelly,
                    "regime": regime,
                    "mom": mom,
                    "reason": "kelly_sized_short"
                })
        
        return Signal("hold", 0.0, {
            "kelly": kelly,
            "adjusted_kelly": adjusted_kelly,
            "regime": regime
        })
