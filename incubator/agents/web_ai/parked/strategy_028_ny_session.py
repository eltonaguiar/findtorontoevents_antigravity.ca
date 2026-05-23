"""
Strategy 028: NY Session Volatility
New York session volatility expansion
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class NYSessionVolatilityStrategy:
    """
    Trades volatility expansion during NY session (13:00 - 22:00 UTC).
    NY session often brings increased volatility and trend continuation.
    """
    
    def __init__(
        self,
        ny_start: int = 13,
        ny_end: int = 22,
        vol_threshold: float = 0.015,
        atr_period: int = 14
    ):
        self.ny_start = ny_start
        self.ny_end = ny_end
        self.vol_threshold = vol_threshold
        self.atr_period = atr_period
    
    def _calculate_atr(self, highs: List[float], lows: List[float], closes: List[float]) -> float:
        if len(highs) < 2:
            return 0
        tr_list = []
        for i in range(1, len(highs)):
            tr1 = highs[i] - lows[i]
            tr2 = abs(highs[i] - closes[i-1])
            tr3 = abs(lows[i] - closes[i-1])
            tr_list.append(max(tr1, tr2, tr3))
        return np.mean(tr_list[-self.atr_period:])
    
    def analyze(
        self,
        hourly_prices: List[float],
        hourly_highs: List[float],
        hourly_lows: List[float],
        hours: List[int]
    ) -> Signal:
        if len(hourly_prices) < 24:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Pre-NY session
        pre_ny_indices = [i for i, h in enumerate(hours) if h < self.ny_start]
        ny_indices = [i for i, h in enumerate(hours) if self.ny_start <= h <= self.ny_end]
        
        if len(ny_indices) < 3 or len(pre_ny_indices) < 5:
            return Signal("hold", 0.0, {"error": "Insufficient session data"})
        
        # Calculate ATR for both periods
        pre_ny_atr = self._calculate_atr(
            [hourly_highs[i] for i in pre_ny_indices],
            [hourly_lows[i] for i in pre_ny_indices],
            [hourly_prices[i] for i in pre_ny_indices]
        )
        
        ny_prices = [hourly_prices[i] for i in ny_indices]
        ny_highs = [hourly_highs[i] for i in ny_indices]
        ny_lows = [hourly_lows[i] for i in ny_indices]
        ny_atr = self._calculate_atr(ny_highs, ny_lows, ny_prices)
        
        # Volatility expansion
        vol_expansion = ny_atr / (pre_ny_atr + 1e-8)
        
        # Direction
        ny_open = ny_prices[0]
        ny_current = ny_prices[-1]
        ny_high = max(ny_highs)
        ny_low = min(ny_lows)
        
        direction = (ny_current - ny_open) / ny_open
        
        # Range extension
        range_pct = (ny_high - ny_low) / ny_open
        
        metadata = {
            "pre_ny_atr": pre_ny_atr,
            "ny_atr": ny_atr,
            "vol_expansion": vol_expansion,
            "direction": direction,
            "range_pct": range_pct,
            "ny_high": ny_high,
            "ny_low": ny_low
        }
        
        # Volatility expansion with direction
        if vol_expansion > 1.5 and range_pct > self.vol_threshold:
            if direction > 0:
                confidence = min(0.85, 0.6 + direction * 20)
                return Signal("buy", confidence, {**metadata, "reason": "NY vol expansion bullish"})
            else:
                confidence = min(0.85, 0.6 + abs(direction) * 20)
                return Signal("sell", confidence, {**metadata, "reason": "NY vol expansion bearish"})
        
        # High volatility range
        if range_pct > self.vol_threshold * 1.5:
            mid = (ny_high + ny_low) / 2
            if ny_current > mid and direction > 0:
                return Signal("buy", 0.6, {**metadata, "reason": "NY session upper half"})
            if ny_current < mid and direction < 0:
                return Signal("sell", 0.6, {**metadata, "reason": "NY session lower half"})
        
        return Signal("hold", 0.2, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    hours = list(range(24))
    base = 40000
    
    # Pre-NY calm
    prices = [base + np.random.randn() * 20 for _ in range(13)]
    highs = [p + 30 for p in prices]
    lows = [p - 30 for p in prices]
    
    # NY volatile bullish
    for h in range(13, 23):
        prices.append(prices[-1] + 80 + np.random.randn() * 50)
        highs.append(prices[-1] + 60)
        lows.append(prices[-1] - 40)
    
    strategy = NYSessionVolatilityStrategy()
    signal = strategy.analyze(prices, highs, lows, hours)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
