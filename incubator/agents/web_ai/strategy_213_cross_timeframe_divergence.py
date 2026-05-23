"""
Strategy 213: Cross-Timeframe Divergence
Google Antigravity Strategy #13
3 synthetic timeframes with fast vs slow momentum divergence
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class CrossTimeframeDivergenceStrategy:
    """
    Creates 3 synthetic timeframes and trades momentum divergence between them.
    Fast TF vs Slow TF divergence = potential reversal.
    """
    
    def __init__(
        self,
        fast_period: int = 5,
        medium_period: int = 15,
        slow_period: int = 30,
        div_threshold: float = 0.05
    ):
        self.fast = fast_period
        self.medium = medium_period
        self.slow = slow_period
        self.div_thresh = div_threshold
    
    def _synthetic_timeframe(self, prices: List[float], factor: int) -> List[float]:
        """Create synthetic higher timeframe by sampling every N bars."""
        return [prices[i] for i in range(0, len(prices), factor)]
    
    def _momentum(self, prices: List[float], period: int) -> float:
        """Calculate momentum for given period."""
        if len(prices) < period:
            return 0
        return (prices[-1] - prices[-period]) / prices[-period]
    
    def _rsi(self, prices: List[float], period: int = 14) -> float:
        """Calculate RSI."""
        if len(prices) < period + 1:
            return 50
        
        returns = [(prices[i] - prices[i-1]) / prices[i-1] 
                   for i in range(1, len(prices))]
        
        gains = [max(r, 0) for r in returns[-period:]]
        losses = [abs(min(r, 0)) for r in returns[-period:]]
        
        avg_gain = np.mean(gains) if gains else 0
        avg_loss = np.mean(losses) if losses else 0
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    def analyze(self, prices: List[float], volumes: List[float]) -> Signal:
        """Generate signal based on cross-TF divergence."""
        min_len = max(self.slow * 2, 60)
        if len(prices) < min_len:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Create synthetic timeframes
        tf1 = self._synthetic_timeframe(prices, 1)  # Original
        tf2 = self._synthetic_timeframe(prices, 2)  # 2x
        tf3 = self._synthetic_timeframe(prices, 4)  # 4x
        
        # Calculate momentum for each TF
        mom_fast = self._momentum(tf1, self.fast)
        mom_medium = self._momentum(tf2, self.medium // 2)
        mom_slow = self._momentum(tf3, self.slow // 4)
        
        # RSI for each TF
        rsi_fast = self._rsi(tf1, 14)
        rsi_slow = self._rsi(tf3, 14)
        
        # Divergence detection
        fast_slow_div = mom_fast - mom_slow
        
        # Volume confirmation
        vol_recent = np.mean(volumes[-5:]) if len(volumes) >= 5 else 0
        vol_ma = np.mean(volumes[-15:]) if len(volumes) >= 15 else 1
        vol_confirm = vol_recent > vol_ma * 0.9
        
        # Bullish divergence: fast momentum turning up while slow still down
        if mom_fast > 0.01 and mom_slow < -0.01 and fast_slow_div > self.div_thresh:
            if rsi_fast < 40 and vol_confirm:
                confidence = min(abs(fast_slow_div) * 10 + (40 - rsi_fast) * 0.01, 0.9)
                return Signal("buy", confidence, {
                    "mom_fast": mom_fast,
                    "mom_slow": mom_slow,
                    "divergence": fast_slow_div,
                    "rsi_fast": rsi_fast,
                    "reason": "bullish_tf_divergence_long"
                })
        
        # Bearish divergence: fast momentum turning down while slow still up
        elif mom_fast < -0.01 and mom_slow > 0.01 and fast_slow_div < -self.div_thresh:
            if rsi_fast > 60 and vol_confirm:
                confidence = min(abs(fast_slow_div) * 10 + (rsi_fast - 60) * 0.01, 0.9)
                return Signal("sell", confidence, {
                    "mom_fast": mom_fast,
                    "mom_slow": mom_slow,
                    "divergence": fast_slow_div,
                    "rsi_fast": rsi_fast,
                    "reason": "bearish_tf_divergence_short"
                })
        
        # Confluence trade: all TFs aligned
        elif abs(mom_fast) > 0.02 and np.sign(mom_fast) == np.sign(mom_medium) == np.sign(mom_slow):
            if mom_fast > 0 and rsi_fast > 50 and rsi_fast < 80:
                return Signal("buy", min(abs(mom_fast) * 20, 0.8), {
                    "mom_fast": mom_fast,
                    "mom_slow": mom_slow,
                    "alignment": "bullish",
                    "reason": "tf_confluence_long"
                })
            elif mom_fast < 0 and rsi_fast < 50 and rsi_fast > 20:
                return Signal("sell", min(abs(mom_fast) * 20, 0.8), {
                    "mom_fast": mom_fast,
                    "mom_slow": mom_slow,
                    "alignment": "bearish",
                    "reason": "tf_confluence_short"
                })
        
        return Signal("hold", 0.0, {
            "mom_fast": mom_fast,
            "mom_slow": mom_slow,
            "divergence": fast_slow_div
        })
