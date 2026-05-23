"""
Strategy 211: Realized Volatility Smile
Google Antigravity Strategy #11
Up-vol vs down-vol asymmetry for fear/greed premium capture
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class RealizedVolSmileStrategy:
    """
    Exploits volatility smile asymmetry.
    Markets typically have higher volatility on down moves (fear) than up moves (greed).
    """
    
    def __init__(
        self,
        lookback: int = 20,
        smile_threshold: float = 1.3,
        extreme_threshold: float = 2.0
    ):
        self.lookback = lookback
        self.smile_thresh = smile_threshold
        self.extreme_thresh = extreme_threshold
    
    def _calculate_vol_smile(self, returns: List[float]) -> dict:
        """
        Calculate up-vol and down-vol separately.
        Returns dict with up_vol, down_vol, smile_ratio
        """
        if len(returns) < self.lookback:
            return {"up_vol": 0, "down_vol": 0, "smile_ratio": 1.0}
        
        recent = returns[-self.lookback:]
        
        up_returns = [r for r in recent if r > 0]
        down_returns = [r for r in recent if r < 0]
        
        up_vol = np.std(up_returns) if up_returns else 0.01
        down_vol = np.std(down_returns) if down_returns else 0.01
        
        # Smile ratio: down_vol / up_vol (usually > 1)
        smile_ratio = down_vol / (up_vol + 1e-10)
        
        return {
            "up_vol": up_vol,
            "down_vol": down_vol,
            "smile_ratio": smile_ratio
        }
    
    def _calculate_skew(self, returns: List[float]) -> float:
        """Calculate return skewness."""
        if len(returns) < self.lookback:
            return 0
        
        recent = returns[-self.lookback:]
        mean = np.mean(recent)
        std = np.std(recent)
        
        if std == 0:
            return 0
        
        skew = sum((r - mean)**3 for r in recent) / (len(recent) * std**3)
        return skew
    
    def analyze(self, prices: List[float], volumes: List[float]) -> Signal:
        """Generate signal based on vol smile asymmetry."""
        if len(prices) < self.lookback + 5:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Calculate returns
        returns = [(prices[i] - prices[i-1]) / prices[i-1] 
                   for i in range(1, len(prices))]
        
        # Calculate vol smile
        smile_data = self._calculate_vol_smile(returns)
        smile_ratio = smile_data["smile_ratio"]
        
        # Calculate skew
        skew = self._calculate_skew(returns)
        
        # Recent price action
        recent_return = sum(returns[-3:]) if len(returns) >= 3 else 0
        
        # RSI for oversold/overbought
        gains = [max(r, 0) for r in returns[-14:]]
        losses = [abs(min(r, 0)) for r in returns[-14:]]
        avg_gain = np.mean(gains) if gains else 0
        avg_loss = np.mean(losses) if losses else 0
        rs = avg_gain / (avg_loss + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        
        # Trading logic based on vol smile
        
        # Extreme fear (high smile ratio + down move) = bounce opportunity
        if smile_ratio > self.smile_thresh and recent_return < -0.03 and rsi < 35:
            confidence = min((smile_ratio - 1) * 0.5 + (35 - rsi) * 0.01, 0.9)
            return Signal("buy", confidence, {
                "smile_ratio": smile_ratio,
                "skew": skew,
                "rsi": rsi,
                "recent_return": recent_return,
                "reason": "extreme_fear_bounce_long"
            })
        
        # Extreme greed (low smile ratio + up move) = pullback opportunity  
        elif smile_ratio < 1.0 and recent_return > 0.03 and rsi > 65:
            confidence = min((1 - smile_ratio) * 0.5 + (rsi - 65) * 0.01, 0.9)
            return Signal("sell", confidence, {
                "smile_ratio": smile_ratio,
                "skew": skew,
                "rsi": rsi,
                "recent_return": recent_return,
                "reason": "extreme_greed_pullback_short"
            })
        
        # Normal smile but RSI extreme = fade
        elif smile_ratio > 1.1 and rsi < 30:
            return Signal("buy", min((30 - rsi) * 0.02, 0.7), {
                "smile_ratio": smile_ratio,
                "rsi": rsi,
                "reason": "oversold_in_normal_smile_long"
            })
        elif smile_ratio > 1.1 and rsi > 70:
            return Signal("sell", min((rsi - 70) * 0.02, 0.7), {
                "smile_ratio": smile_ratio,
                "rsi": rsi,
                "reason": "overbought_in_normal_smile_short"
            })
        
        return Signal("hold", 0.0, {
            "smile_ratio": smile_ratio,
            "skew": skew,
            "rsi": rsi
        })
