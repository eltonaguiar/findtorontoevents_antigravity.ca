"""
Strategy 205: Jump Diffusion Detector
Google Antigravity Strategy #5
Uses BNS jump test to fade extreme jumps
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class JumpDiffusionDetectorStrategy:
    """
    Detects and fades price jumps using Barndorff-Nielsen-Shephard (BNS) test.
    Separates continuous volatility from discrete jumps.
    """
    
    def __init__(
        self,
        lookback: int = 20,
        jump_threshold: float = 3.0,
        bipower_period: int = 10
    ):
        self.lookback = lookback
        self.jump_threshold = jump_threshold
        self.bp_period = bipower_period
    
    def _calculate_returns(self, prices: List[float]) -> List[float]:
        """Calculate log returns."""
        return [np.log(prices[i]/prices[i-1]) 
                for i in range(1, len(prices)) if prices[i-1] > 0]
    
    def _realized_variance(self, returns: List[float]) -> float:
        """Calculate realized variance (sum of squared returns)."""
        return sum(r**2 for r in returns)
    
    def _bipower_variation(self, returns: List[float]) -> float:
        """Calculate bipower variation (BNS estimator for continuous vol)."""
        if len(returns) < self.bp_period + 1:
            return self._realized_variance(returns)
        
        mu1 = np.sqrt(2/np.pi)  # Expected value of |Z| where Z~N(0,1)
        
        bpv = 0
        for i in range(1, min(len(returns), self.bp_period + 1)):
            bpv += abs(returns[i]) * abs(returns[i-1])
        
        return bpv / (mu1**2)
    
    def _detect_jump(self, returns: List[float]) -> tuple:
        """Detect jump using BNS test."""
        if len(returns) < self.bp_period + 2:
            return False, 0, 0, 0
        
        rv = self._realized_variance(returns[-self.lookback:])
        bpv = self._bipower_variation(returns[-self.bp_period:])
        
        # Jump component = RV - BPV
        jump_var = max(0, rv - bpv)
        
        # Jump ratio
        jump_ratio = jump_var / (rv + 1e-10)
        
        # Statistical test (simplified)
        if rv > 0:
            test_stat = (rv - bpv) / (rv * np.sqrt(2/self.lookback))
            is_jump = abs(test_stat) > self.jump_threshold
        else:
            is_jump = False
            test_stat = 0
        
        return is_jump, jump_ratio, test_stat, jump_var
    
    def analyze(self, prices: List[float], volumes: List[float]) -> Signal:
        """Generate fade signal after detected jumps."""
        if len(prices) < self.lookback + 5:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        returns = self._calculate_returns(prices)
        
        if len(returns) < self.lookback:
            return Signal("hold", 0.0, {"error": "Insufficient returns"})
        
        # Detect jump
        is_jump, jump_ratio, test_stat, jump_var = self._detect_jump(returns)
        
        # Recent price action
        recent_return = returns[-1] if returns else 0
        cumulative_return = sum(returns[-5:]) if len(returns) >= 5 else 0
        
        # Volume confirmation
        avg_vol = np.mean(volumes[-20:]) if len(volumes) >= 20 else 1
        recent_vol = np.mean(volumes[-3:]) if len(volumes) >= 3 else 0
        vol_spike = recent_vol / (avg_vol + 1e-10)
        
        # Generate fade signals
        if is_jump and abs(recent_return) > 0.02:
            if recent_return < 0 and cumulative_return < -0.05:
                # Downward jump - fade long
                confidence = min(abs(test_stat)/5 + jump_ratio, 0.9)
                return Signal("buy", confidence, {
                    "jump_ratio": jump_ratio,
                    "test_stat": test_stat,
                    "recent_return": recent_return,
                    "vol_spike": vol_spike,
                    "reason": "fade_downward_jump_long"
                })
            elif recent_return > 0 and cumulative_return > 0.05:
                # Upward jump - fade short
                confidence = min(abs(test_stat)/5 + jump_ratio, 0.9)
                return Signal("sell", confidence, {
                    "jump_ratio": jump_ratio,
                    "test_stat": test_stat,
                    "recent_return": recent_return,
                    "vol_spike": vol_spike,
                    "reason": "fade_upward_jump_short"
                })
        
        return Signal("hold", 0.0, {
            "is_jump": is_jump,
            "jump_ratio": jump_ratio,
            "recent_return": recent_return
        })
