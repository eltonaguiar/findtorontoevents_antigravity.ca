"""
Strategy 215: Max Drawdown Recovery Timing
Google Antigravity Strategy #15
Fade extreme drawdown/drawup using DD/DU recovery patterns
"""
from dataclasses import dataclass
from typing import List, Tuple
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class MaxDrawdownRecoveryTimingStrategy:
    """
    Times entries based on drawdown and drawup recovery patterns.
    Extreme DD = long opportunity, Extreme DU = short opportunity.
    """
    
    def __init__(
        self,
        lookback: int = 50,
        extreme_dd_threshold: float = -0.15,
        extreme_du_threshold: float = 0.20,
        recovery_confirmation: float = 0.03
    ):
        self.lookback = lookback
        self.dd_thresh = extreme_dd_threshold
        self.du_thresh = extreme_du_threshold
        self.recovery_conf = recovery_confirmation
    
    def _calculate_dd_du(self, prices: List[float]) -> Tuple[List[float], List[float]]:
        """Calculate rolling drawdown and drawup series."""
        if len(prices) < 2:
            return [0], [0]
        
        dd_series = []
        du_series = []
        peak = prices[0]
        trough = prices[0]
        
        for price in prices:
            if price > peak:
                peak = price
            if price < trough:
                trough = price
            
            dd = (price - peak) / peak
            du = (price - trough) / trough
            
            dd_series.append(dd)
            du_series.append(du)
        
        return dd_series, du_series_series
    
    def _recovery_signal(self, dd_series: List[float], du_series: List[float]) -> str:
        """Detect if we're in recovery phase."""
        if len(dd_series) < 5:
            return "none"
        
        recent_dd = dd_series[-5:]
        recent_du = du_series[-5:]
        
        # DD recovery: was at extreme, now improving
        if min(recent_dd) < self.dd_thresh * 0.7 and dd_series[-1] > recent_dd[0] * 0.5:
            return "dd_recovery"
        
        # DU reversal: was at extreme, now pulling back
        if max(recent_du) > self.du_thresh * 0.7 and du_series[-1] < recent_du[0] * 0.5:
            return "du_reversal"
        
        return "none"
    
    def analyze(self, prices: List[float], volumes: List[float]) -> Signal:
        """Generate signal based on DD/DU recovery timing."""
        if len(prices) < self.lookback:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Calculate DD and DU
        try:
            dd_series, du_series = self._calculate_dd_du(prices[-self.lookback:])
        except:
            # Fallback simple calculation
            dd_series = []
            du_series = []
            peak = prices[0]
            trough = prices[0]
            for p in prices[-self.lookback:]:
                peak = max(peak, p)
                trough = min(trough, p)
                dd_series.append((p - peak) / peak)
                du_series.append((p - trough) / trough)
        
        current_dd = dd_series[-1]
        current_du = du_series[-1]
        max_dd = min(dd_series)
        max_du = max(du_series)
        
        # Recovery detection
        recovery = self._recovery_signal(dd_series, du_series)
        
        # Price momentum
        mom_5 = (prices[-1] - prices[-6]) / prices[-6] if len(prices) >= 6 else 0
        
        # Volume confirmation
        vol_recent = np.mean(volumes[-3:]) if len(volumes) >= 3 else 0
        vol_avg = np.mean(volumes[-15:]) if len(volumes) >= 15 else 1
        vol_spike = vol_recent / vol_avg if vol_avg > 0 else 1
        
        # Extreme drawdown - buy signal
        if current_dd < self.dd_thresh or recovery == "dd_recovery":
            if mom_5 > 0 or recovery == "dd_recovery":
                # Recovery confirmed
                dd_depth = abs(current_dd)
                confidence = min(dd_depth * 3 + abs(mom_5) * 5, 0.95)
                return Signal("buy", confidence, {
                    "current_dd": current_dd,
                    "max_dd": max_dd,
                    "recovery": recovery,
                    "mom_5": mom_5,
                    "reason": "dd_recovery_long"
                })
        
        # Extreme drawup - sell signal
        if current_du > self.du_thresh or recovery == "du_reversal":
            if mom_5 < 0 or recovery == "du_reversal":
                # Reversal confirmed
                confidence = min(current_du * 2 + abs(mom_5) * 5, 0.95)
                return Signal("sell", confidence, {
                    "current_du": current_du,
                    "max_du": max_du,
                    "recovery": recovery,
                    "mom_5": mom_5,
                    "reason": "du_reversal_short"
                })
        
        # Moderate DD with volume spike = potential bottom
        if current_dd < -0.08 and vol_spike > 1.5 and mom_5 > 0.01:
            confidence = min(abs(current_dd) * 5 + (vol_spike - 1), 0.8)
            return Signal("buy", confidence, {
                "current_dd": current_dd,
                "vol_spike": vol_spike,
                "reason": "moderate_dd_volume_long"
            })
        
        return Signal("hold", 0.0, {
            "current_dd": current_dd,
            "current_du": current_du,
            "recovery": recovery
        })
