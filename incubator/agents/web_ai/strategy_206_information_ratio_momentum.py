"""
Strategy 206: Information Ratio Momentum
Google Antigravity Strategy #6
Only trades quality momentum using rolling Information Ratio as gate
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class InformationRatioMomentumStrategy:
    """
    Uses Information Ratio (risk-adjusted return vs benchmark) to filter momentum signals.
    Only enters when momentum quality is high enough.
    """
    
    def __init__(
        self,
        lookback: int = 20,
        ir_threshold: float = 0.5,
        momentum_period: int = 10,
        risk_free_rate: float = 0.02
    ):
        self.lookback = lookback
        self.ir_threshold = ir_threshold
        self.mom_period = momentum_period
        self.rf_rate = risk_free_rate / 365  # Daily
    
    def _calculate_ir(self, returns: List[float], benchmark_returns: List[float] = None) -> float:
        """Calculate Information Ratio."""
        if len(returns) < self.lookback:
            return 0
        
        recent_returns = returns[-self.lookback:]
        
        # Use zero as benchmark if not provided (absolute IR)
        if benchmark_returns is None or len(benchmark_returns) < self.lookback:
            benchmark_returns = [self.rf_rate] * self.lookback
        else:
            benchmark_returns = benchmark_returns[-self.lookback:]
        
        # Active returns
        active_returns = [r - b for r, b in zip(recent_returns, benchmark_returns)]
        
        # Information Ratio = mean(active) / std(active)
        mean_active = np.mean(active_returns)
        std_active = np.std(active_returns)
        
        if std_active == 0:
            return 0
        
        return mean_active / std_active * np.sqrt(365)  # Annualized
    
    def _calculate_momentum(self, prices: List[float]) -> float:
        """Calculate price momentum."""
        if len(prices) < self.mom_period:
            return 0
        
        return (prices[-1] - prices[-self.mom_period]) / prices[-self.mom_period]
    
    def analyze(self, prices: List[float], volumes: List[float]) -> Signal:
        """Generate signal only when IR quality is sufficient."""
        if len(prices) < self.lookback + 5:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Calculate returns
        returns = [(prices[i] - prices[i-1]) / prices[i-1] 
                   for i in range(1, len(prices))]
        
        # Calculate Information Ratio
        ir = self._calculate_ir(returns)
        
        # Calculate momentum
        momentum = self._calculate_momentum(prices)
        
        # Volume trend
        vol_sma = np.mean(volumes[-10:]) if len(volumes) >= 10 else 0
        vol_long = np.mean(volumes[-20:]) if len(volumes) >= 20 else 1
        vol_trend = vol_sma / vol_long if vol_long > 0 else 1
        
        # IR quality gate - only trade if IR > threshold
        quality_gate = ir > self.ir_threshold
        
        if quality_gate:
            if momentum > 0.02 and vol_trend > 0.9:
                # Quality upward momentum
                confidence = min(ir / 2 + abs(momentum) * 5, 0.95)
                return Signal("buy", confidence, {
                    "ir": ir,
                    "momentum": momentum,
                    "vol_trend": vol_trend,
                    "reason": "quality_momentum_long"
                })
            elif momentum < -0.02 and vol_trend > 0.9:
                # Quality downward momentum
                confidence = min(ir / 2 + abs(momentum) * 5, 0.95)
                return Signal("sell", confidence, {
                    "ir": ir,
                    "momentum": momentum,
                    "vol_trend": vol_trend,
                    "reason": "quality_momentum_short"
                })
        
        # Low IR but extreme momentum = potential reversal
        elif ir < -0.3 and abs(momentum) > 0.05:
            if momentum < 0:
                return Signal("buy", min(abs(ir) * 0.5, 0.6), {
                    "ir": ir,
                    "momentum": momentum,
                    "reason": "low_ir_reversal_long"
                })
            else:
                return Signal("sell", min(abs(ir) * 0.5, 0.6), {
                    "ir": ir,
                    "momentum": momentum,
                    "reason": "low_ir_reversal_short"
                })
        
        return Signal("hold", 0.0, {"ir": ir, "momentum": momentum, "quality_gate": quality_gate})
