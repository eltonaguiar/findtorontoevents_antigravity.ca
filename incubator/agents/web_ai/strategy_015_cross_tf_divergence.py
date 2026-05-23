"""
Strategy 015: Cross-Timeframe Divergence
Detects divergences between timeframes
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class CrossTFDivergenceStrategy:
    """
    Identifies divergences between higher and lower timeframes.
    HTF bullish + LTF bearish = potential buying opportunity.
    """
    
    def __init__(
        self,
        htf_trend_period: int = 20,
        ltf_oscillator_period: int = 14,
        divergence_threshold: float = 0.1
    ):
        self.htf_period = htf_trend_period
        self.ltf_period = ltf_oscillator_period
        self.divergence_threshold = divergence_threshold
    
    def _calculate_roc(self, prices: List[float], period: int) -> float:
        if len(prices) < period:
            return 0
        return (prices[-1] - prices[-period]) / prices[-period]
    
    def analyze(
        self,
        htf_prices: List[float],
        ltf_prices: List[float],
        ltf_volumes: List[float]
    ) -> Signal:
        if len(htf_prices) < self.htf_period or len(ltf_prices) < self.ltf_period * 2:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Higher timeframe trend
        htf_roc = self._calculate_roc(htf_prices, self.htf_period)
        htf_trend = "bullish" if htf_roc > 0.02 else "bearish" if htf_roc < -0.02 else "neutral"
        
        # Lower timeframe momentum
        ltf_recent = ltf_prices[-self.ltf_period:]
        ltf_previous = ltf_prices[-self.ltf_period*2:-self.ltf_period]
        
        ltf_recent_high = max(ltf_recent)
        ltf_recent_low = min(ltf_recent)
        ltf_prev_high = max(ltf_previous)
        ltf_prev_low = min(ltf_previous)
        
        # Detect LTF pattern
        if ltf_recent_high > ltf_prev_high and ltf_recent_low > ltf_prev_low:
            ltf_pattern = "higher_highs"
        elif ltf_recent_high < ltf_prev_high and ltf_recent_low < ltf_prev_low:
            ltf_pattern = "lower_lows"
        else:
            ltf_pattern = "mixed"
        
        metadata = {
            "htf_trend": htf_trend,
            "htf_roc": htf_roc,
            "ltf_pattern": ltf_pattern,
            "ltf_recent_high": ltf_recent_high,
            "ltf_prev_high": ltf_prev_high
        }
        
        # Bullish divergence: HTF up, LTF pullback
        if htf_trend == "bullish" and ltf_pattern == "lower_lows":
            confidence = min(0.8, 0.5 + abs(htf_roc) * 5)
            return Signal("buy", confidence, {**metadata, "reason": "HTF bullish, LTF pullback"})
        
        # Bearish divergence: HTF down, LTF rally
        if htf_trend == "bearish" and ltf_pattern == "higher_highs":
            confidence = min(0.8, 0.5 + abs(htf_roc) * 5)
            return Signal("sell", confidence, {**metadata, "reason": "HTF bearish, LTF rally"})
        
        # Alignment signals
        if htf_trend == "bullish" and ltf_pattern == "higher_highs":
            return Signal("buy", 0.65, {**metadata, "reason": "Full alignment bullish"})
        
        if htf_trend == "bearish" and ltf_pattern == "lower_lows":
            return Signal("sell", 0.65, {**metadata, "reason": "Full alignment bearish"})
        
        return Signal("hold", 0.2, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    n_htf = 25
    n_ltf = 150
    
    # HTF bullish, LTF pullback
    htf = [40000 + i * 400 + np.random.randn() * 200 for i in range(n_htf)]
    ltf = [htf[-1] + 500 - i * 10 + np.random.randn() * 100 for i in range(n_ltf)]
    volumes = [1000 + np.random.randn() * 200 for _ in range(n_ltf)]
    
    strategy = CrossTFDivergenceStrategy()
    signal = strategy.analyze(htf, ltf, volumes)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
