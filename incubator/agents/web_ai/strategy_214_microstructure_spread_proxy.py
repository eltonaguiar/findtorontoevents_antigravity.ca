"""
Strategy 214: Microstructure Spread Proxy
Google Antigravity Strategy #14
Corwin-Schultz spread estimator for liquidity regime change detection
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class MicrostructureSpreadProxyStrategy:
    """
    Uses Corwin-Schultz spread estimator as proxy for liquidity.
    High spread = low liquidity (wider stops), Low spread = high liquidity (tighter entries).
    """
    
    def __init__(
        self,
        lookback: int = 20,
        high_spread_threshold: float = 0.005,
        low_spread_threshold: float = 0.001,
        price_data: str = "ohlc"  # or "close_only"
    ):
        self.lookback = lookback
        self.high_thresh = high_spread_threshold
        self.low_thresh = low_spread_threshold
        self.price_data = price_data
    
    def _corwin_schultz_spread(self, highs: List[float], lows: List[float]) -> float:
        """
        Corwin-Schultz bid-ask spread estimator.
        Uses only high-low prices.
        """
        if len(highs) < 2 or len(lows) < 2:
            return 0.001
        
        # High-low ratios
        hl_ratios = [np.log(h / l)**2 for h, l in zip(highs, lows) if l > 0]
        
        if len(hl_ratios) < 2:
            return 0.001
        
        # Beta calculation (overnight variance)
        beta = np.mean(hl_ratios)
        
        # Gamma calculation (two-day high-low)
        if len(highs) >= 2:
            gamma = np.log(max(highs[-2:]) / max(lows[-2:]))**2
        else:
            gamma = beta
        
        # Alpha
        alpha = (np.sqrt(2 * beta) - np.sqrt(beta)) / (2 - np.sqrt(2))
        alpha = max(alpha, 0)
        
        # Spread estimate
        spread = 2 * (np.exp(alpha) - 1) / (1 + np.exp(alpha))
        
        return max(spread, 0.0001)
    
    def _estimate_hl_from_close(self, prices: List[float]) -> tuple:
        """Estimate high/low from close prices using volatility."""
        if len(prices) < 5:
            return prices, prices
        
        returns = np.diff(prices) / prices[:-1]
        vol = np.std(returns) if len(returns) > 1 else 0.01
        
        # Estimate H/L as close ± 1.5 * daily vol
        highs = [p * (1 + 1.5 * vol) for p in prices]
        lows = [p * (1 - 1.5 * vol) for p in prices]
        
        return highs, lows
    
    def _parkinson_vol(self, highs: List[float], lows: List[float]) -> float:
        """Parkinson volatility using high-low range."""
        if len(highs) < 2 or len(lows) < 2:
            return 0.01
        
        hl_logs = [np.log(h/l)**2 for h, l in zip(highs, lows) if l > 0]
        
        if not hl_logs:
            return 0.01
        
        return np.sqrt(np.mean(hl_logs) / (4 * np.log(2)))
    
    def analyze(self, prices: List[float], volumes: List[float],
                highs: List[float] = None, lows: List[float] = None) -> Signal:
        """Generate signal based on spread/liquidity regime."""
        if len(prices) < self.lookback + 5:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Get or estimate high/low
        if highs is None or lows is None:
            highs, lows = self._estimate_hl_from_close(prices)
        
        # Calculate spread
        spread = self._corwin_schultz_spread(
            highs[-self.lookback:],
            lows[-self.lookback:]
        )
        
        # Parkinson volatility
        park_vol = self._parkinson_vol(
            highs[-self.lookback:],
            lows[-self.lookback:]
        )
        
        # Volume trend (inverse proxy for spread)
        vol_ma_short = np.mean(volumes[-5:]) if len(volumes) >= 5 else 0
        vol_ma_long = np.mean(volumes[-20:]) if len(volumes) >= 20 else 1
        vol_ratio = vol_ma_short / vol_ma_long if vol_ma_long > 0 else 1
        
        # Price momentum
        mom = (prices[-1] - prices[-10]) / prices[-10] if len(prices) >= 10 else 0
        
        # Volatility regime
        returns = np.diff(prices) / prices[:-1]
        vol = np.std(returns[-20:]) if len(returns) >= 20 else 0.01
        
        # Trading logic
        if spread > self.high_thresh:
            # High spread = low liquidity = be cautious, wait for confirmation
            if mom > 0.03 and vol_ratio > 1.2:
                # Strong move with volume despite wide spread = breakout
                confidence = min(spread * 50, 0.8)
                return Signal("buy", confidence, {
                    "spread": spread,
                    "park_vol": park_vol,
                    "vol_ratio": vol_ratio,
                    "reason": "low_liquidity_breakout_long"
                })
            elif mom < -0.03 and vol_ratio > 1.2:
                confidence = min(spread * 50, 0.8)
                return Signal("sell", confidence, {
                    "spread": spread,
                    "park_vol": park_vol,
                    "vol_ratio": vol_ratio,
                    "reason": "low_liquidity_breakout_short"
                })
        
        elif spread < self.low_thresh:
            # Low spread = high liquidity = good for entries
            if mom > 0.015 and vol < 0.03:
                # Calm uptrend in liquid conditions
                confidence = min((self.low_thresh - spread) * 100 + abs(mom) * 10, 0.85)
                return Signal("buy", confidence, {
                    "spread": spread,
                    "park_vol": park_vol,
                    "vol": vol,
                    "reason": "high_liquidity_trend_long"
                })
            elif mom < -0.015 and vol < 0.03:
                confidence = min((self.low_thresh - spread) * 100 + abs(mom) * 10, 0.85)
                return Signal("sell", confidence, {
                    "spread": spread,
                    "park_vol": park_vol,
                    "vol": vol,
                    "reason": "high_liquidity_trend_short"
                })
        
        return Signal("hold", 0.0, {
            "spread": spread,
            "park_vol": park_vol,
            "liquidity": "normal"
        })
