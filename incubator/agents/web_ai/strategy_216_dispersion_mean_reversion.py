"""
Strategy 216: Dispersion Mean Reversion
Google Antigravity Strategy #16
Intra-bar dispersion z-score for panic/euphoria absorption
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class DispersionMeanReversionStrategy:
    """
    Uses intra-bar dispersion (OHLC range) z-score to detect panic/euphoria.
    Extreme dispersion = mean reversion opportunity.
    """
    
    def __init__(
        self,
        lookback: int = 20,
        zscore_threshold: float = 2.0,
        confirmation_bars: int = 2
    ):
        self.lookback = lookback
        self.z_thresh = zscore_threshold
        self.confirmation = confirmation_bars
    
    def _calculate_dispersion(self, prices: List[float], 
                             highs: List[float] = None, 
                             lows: List[float] = None) -> List[float]:
        """Calculate intra-bar dispersion (range normalized by close)."""
        dispersion = []
        
        for i in range(len(prices)):
            if highs and lows and i < len(highs) and i < len(lows):
                h, l, c = highs[i], lows[i], prices[i]
            else:
                # Estimate from adjacent prices
                if i > 0 and i < len(prices) - 1:
                    h = max(prices[i-1], prices[i], prices[i+1])
                    l = min(prices[i-1], prices[i], prices[i+1])
                else:
                    h = l = prices[i]
            
            if c > 0:
                disp = (h - l) / c
            else:
                disp = 0
            
            dispersion.append(disp)
        
        return dispersion
    
    def _zscore(self, value: float, series: List[float]) -> float:
        """Calculate z-score of value relative to series."""
        if len(series) < 2:
            return 0
        
        mean = np.mean(series)
        std = np.std(series)
        
        if std == 0:
            return 0
        
        return (value - mean) / std
    
    def analyze(self, prices: List[float], volumes: List[float],
                highs: List[float] = None, lows: List[float] = None) -> Signal:
        """Generate signal based on dispersion z-score."""
        if len(prices) < self.lookback + 5:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Calculate dispersion series
        dispersion = self._calculate_dispersion(prices, highs, lows)
        
        # Current dispersion and z-score
        current_disp = dispersion[-1]
        zscore = self._zscore(current_disp, dispersion[-self.lookback:])
        
        # Recent dispersion trend
        disp_sma = np.mean(dispersion[-5:])
        disp_trend = "expanding" if current_disp > disp_sma * 1.2 else "contracting"
        
        # Price momentum
        returns = np.diff(prices) / prices[:-1]
        mom = returns[-1] if len(returns) > 0 else 0
        mom_5 = np.mean(returns[-5:]) if len(returns) >= 5 else 0
        
        # Volume confirmation
        vol_ma = np.mean(volumes[-10:]) if len(volumes) >= 10 else 1
        vol_recent = volumes[-1] if volumes else 0
        vol_ratio = vol_recent / vol_ma if vol_ma > 0 else 1
        
        # Panic detection: extreme dispersion + down move + volume
        if zscore > self.z_thresh and mom < -0.02 and vol_ratio > 1.3:
            confidence = min(zscore / 3 + abs(mom) * 10, 0.95)
            return Signal("buy", confidence, {
                "dispersion": current_disp,
                "zscore": zscore,
                "mom": mom,
                "vol_ratio": vol_ratio,
                "reason": "panic_dispersion_long"
            })
        
        # Euphoria detection: extreme dispersion + up move + volume
        elif zscore > self.z_thresh and mom > 0.02 and vol_ratio > 1.3:
            confidence = min(zscore / 3 + mom * 10, 0.95)
            return Signal("sell", confidence, {
                "dispersion": current_disp,
                "zscore": zscore,
                "mom": mom,
                "vol_ratio": vol_ratio,
                "reason": "euphoria_dispersion_short"
            })
        
        # Low dispersion + momentum = trend continuation
        elif zscore < -1.0 and abs(mom_5) > 0.01:
            if mom_5 > 0:
                return Signal("buy", min(abs(zscore) * 0.2 + abs(mom_5) * 5, 0.7), {
                    "dispersion": current_disp,
                    "zscore": zscore,
                    "mom_5": mom_5,
                    "reason": "low_dispersion_trend_long"
                })
            else:
                return Signal("sell", min(abs(zscore) * 0.2 + abs(mom_5) * 5, 0.7), {
                    "dispersion": current_disp,
                    "zscore": zscore,
                    "mom_5": mom_5,
                    "reason": "low_dispersion_trend_short"
                })
        
        return Signal("hold", 0.0, {
            "dispersion": current_disp,
            "zscore": zscore,
            "disp_trend": disp_trend
        })
