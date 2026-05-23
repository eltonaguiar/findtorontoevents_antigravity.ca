"""
Strategy 217: Omega Ratio Quality Gate
Google Antigravity Strategy #17
Uses Omega ratio for probability-weighted edge detection
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class OmegaRatioGateStrategy:
    """
    Uses Omega ratio (probability-weighted gains/losses) as quality gate.
    Only trades when Omega indicates favorable probability distribution.
    """
    
    def __init__(
        self,
        lookback: int = 30,
        threshold: float = 0.0,
        omega_threshold: float = 1.2,
        percentile: float = 0.5
    ):
        self.lookback = lookback
        self.threshold = threshold
        self.omega_thresh = omega_threshold
        self.percentile = percentile
    
    def _calculate_omega(self, returns: List[float]) -> float:
        """
        Calculate Omega ratio.
        Omega = ∫[LIR to ∞] (1 - F(x))dx / ∫[-∞ to LIR] F(x)dx
        where LIR = Loss threshold (we use 0 for simplicity)
        
        Simplified: ratio of gains above threshold to losses below
        """
        if not returns:
            return 1.0
        
        gains = [r for r in returns if r > self.threshold]
        losses = [r for r in returns if r <= self.threshold]
        
        if not losses:
            return 10.0  # Very high if no losses
        
        # Omega = (sum of gains - threshold) / (threshold - sum of losses)
        gain_sum = sum(g - self.threshold for g in gains) if gains else 0
        loss_sum = sum(self.threshold - l for l in losses) if losses else 1e-10
        
        if loss_sum == 0:
            return 10.0
        
        return gain_sum / loss_sum
    
    def _calculate_gain_loss_stats(self, returns: List[float]) -> dict:
        """Calculate gain/loss statistics."""
        gains = [r for r in returns if r > 0]
        losses = [r for r in returns if r < 0]
        
        win_rate = len(gains) / len(returns) if returns else 0
        avg_gain = np.mean(gains) if gains else 0
        avg_loss = np.mean(losses) if losses else 0
        
        return {
            "win_rate": win_rate,
            "avg_gain": avg_gain,
            "avg_loss": avg_loss,
            "gain_loss_ratio": abs(avg_gain / avg_loss) if avg_loss != 0 else 10
        }
    
    def analyze(self, prices: List[float], volumes: List[float]) -> Signal:
        """Generate signal only when Omega ratio is favorable."""
        if len(prices) < self.lookback + 5:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Calculate returns
        returns = [(prices[i] - prices[i-1]) / prices[i-1] 
                   for i in range(1, len(prices))]
        
        # Calculate Omega ratio
        omega = self._calculate_omega(returns[-self.lookback:])
        
        # Gain/loss stats
        stats = self._calculate_gain_loss_stats(returns[-self.lookback:])
        
        # Current momentum
        mom = (prices[-1] - prices[-10]) / prices[-10] if len(prices) >= 10 else 0
        
        # Volume trend
        vol_ma = np.mean(volumes[-10:]) if len(volumes) >= 10 else 1
        vol_recent = np.mean(volumes[-3:]) if len(volumes) >= 3 else 0
        vol_trend = vol_recent / vol_ma if vol_ma > 0 else 1
        
        # Omega quality gate
        quality_pass = omega > self.omega_thresh and stats["win_rate"] > 0.4
        
        if quality_pass:
            if mom > 0.015 and stats["gain_loss_ratio"] > 1.0:
                confidence = min((omega - 1) * 0.5 + stats["win_rate"], 0.9)
                return Signal("buy", confidence, {
                    "omega": omega,
                    "win_rate": stats["win_rate"],
                    "gain_loss_ratio": stats["gain_loss_ratio"],
                    "mom": mom,
                    "reason": "omega_quality_long"
                })
            elif mom < -0.015 and stats["gain_loss_ratio"] > 1.0:
                confidence = min((omega - 1) * 0.5 + stats["win_rate"], 0.9)
                return Signal("sell", confidence, {
                    "omega": omega,
                    "win_rate": stats["win_rate"],
                    "gain_loss_ratio": stats["gain_loss_ratio"],
                    "mom": mom,
                    "reason": "omega_quality_short"
                })
        
        # Low omega but extreme momentum = potential reversal
        elif omega < 0.8 and abs(mom) > 0.05:
            if mom < 0:
                return Signal("buy", min((1 - omega) * 0.3, 0.6), {
                    "omega": omega,
                    "mom": mom,
                    "reason": "low_omega_reversal_long"
                })
            else:
                return Signal("sell", min((1 - omega) * 0.3, 0.6), {
                    "omega": omega,
                    "mom": mom,
                    "reason": "low_omega_reversal_short"
                })
        
        return Signal("hold", 0.0, {
            "omega": omega,
            "win_rate": stats["win_rate"],
            "quality_pass": quality_pass
        })
