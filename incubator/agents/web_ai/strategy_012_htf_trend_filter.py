"""
Strategy 012: Higher Timeframe Trend Filter
Multi-timeframe confluence with HTF bias
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class HTFTrendFilterStrategy:
    """
    Uses higher timeframe (weekly/monthly) trend as filter.
    Only takes trades in direction of HTF trend.
    """
    
    def __init__(
        self,
        htf_period: int = 20,
        ltf_period: int = 10,
        pullback_threshold: float = 0.05
    ):
        self.htf_period = htf_period
        self.ltf_period = ltf_period
        self.pullback_threshold = pullback_threshold
    
    def analyze(
        self,
        htf_prices: List[float],
        ltf_prices: List[float],
        htf_volumes: List[float]
    ) -> Signal:
        if len(htf_prices) < self.htf_period or len(ltf_prices) < self.ltf_period:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Higher timeframe trend
        htf_ma = np.mean(htf_prices[-self.htf_period:])
        htf_prev = np.mean(htf_prices[-self.htf_period-5:-5])
        htf_trend = (htf_ma - htf_prev) / htf_prev
        
        # Lower timeframe analysis
        ltf_current = ltf_prices[-1]
        ltf_ma = np.mean(ltf_prices[-self.ltf_period:])
        ltf_high = max(ltf_prices[-self.ltf_period:])
        ltf_low = min(ltf_prices[-self.ltf_period:])
        
        # Pullback calculation
        if htf_trend > 0:
            pullback = (ltf_high - ltf_current) / (ltf_high - ltf_low + 1e-8)
        else:
            pullback = (ltf_current - ltf_low) / (ltf_high - ltf_low + 1e-8)
        
        metadata = {
            "htf_trend": htf_trend,
            "ltf_ma": ltf_ma,
            "pullback": pullback,
            "ltf_current": ltf_current
        }
        
        # HTF bullish - look for LTF pullbacks to enter long
        if htf_trend > 0.05:
            if pullback > self.pullback_threshold and ltf_current > ltf_ma:
                confidence = min(0.85, 0.6 + pullback)
                return Signal("buy", confidence, {**metadata, "reason": "HTF bullish, LTF pullback complete"})
            
            if ltf_current > ltf_ma * 1.02:
                return Signal("buy", 0.6, {**metadata, "reason": "HTF bullish, LTF momentum"})
        
        # HTF bearish - look for LTF rallies to enter short
        if htf_trend < -0.05:
            if pullback > self.pullback_threshold and ltf_current < ltf_ma:
                confidence = min(0.85, 0.6 + pullback)
                return Signal("sell", confidence, {**metadata, "reason": "HTF bearish, LTF rally complete"})
            
            if ltf_current < ltf_ma * 0.98:
                return Signal("sell", 0.6, {**metadata, "reason": "HTF bearish, LTF weakness"})
        
        return Signal("hold", 0.25, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    n_htf = 30
    n_ltf = 200
    
    # Strong HTF uptrend
    htf = [40000 + i * 800 + np.random.randn() * 300 for i in range(n_htf)]
    ltf = [htf[-1] - 500 + np.random.randn() * 200 for _ in range(n_ltf)]
    ltf[-20:] = [ltf[-20] + i * 30 + np.random.randn() * 50 for i in range(20)]
    
    volumes = [1000 + np.random.randn() * 200 for _ in range(n_htf)]
    
    strategy = HTFTrendFilterStrategy()
    signal = strategy.analyze(htf, ltf, volumes)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
