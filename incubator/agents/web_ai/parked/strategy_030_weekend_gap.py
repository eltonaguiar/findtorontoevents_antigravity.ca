"""
Strategy 030: Weekend Gap Trading
Weekend price gap strategy
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class WeekendGapStrategy:
    """
    Trades gaps between Friday close and Sunday open.
    Crypto markets trade 24/7 but traditional markets close.
    """
    
    def __init__(
        self,
        gap_threshold: float = 0.01,
        fill_threshold: float = 0.5,
        max_hold_days: int = 3
    ):
        self.gap_threshold = gap_threshold
        self.fill_threshold = fill_threshold
        self.max_hold = max_hold_days
    
    def analyze(
        self,
        daily_prices: List[float],
        daily_volumes: List[float],
        weekdays: List[int]  # 0=Monday, 6=Sunday
    ) -> Signal:
        if len(daily_prices) < 7 or len(weekdays) != len(daily_prices):
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Find Friday and Sunday
        friday_idx = None
        sunday_idx = None
        
        for i, wd in enumerate(weekdays):
            if wd == 4:  # Friday
                friday_idx = i
            elif wd == 6:  # Sunday
                sunday_idx = i
        
        if friday_idx is None or sunday_idx is None or sunday_idx <= friday_idx:
            return Signal("hold", 0.0, {"error": "Weekend data not found"})
        
        friday_close = daily_prices[friday_idx]
        sunday_open = daily_prices[sunday_idx]
        current_price = daily_prices[-1]
        
        # Gap calculation
        gap = (sunday_open - friday_close) / friday_close
        gap_filled = abs(current_price - friday_close) / abs(gap * friday_close) if gap != 0 else 1
        
        # Gap direction
        gap_up = gap > self.gap_threshold
        gap_down = gap < -self.gap_threshold
        
        # Current weekday
        current_weekday = weekdays[-1]
        days_since_gap = len(daily_prices) - 1 - sunday_idx
        
        metadata = {
            "friday_close": friday_close,
            "sunday_open": sunday_open,
            "gap_pct": gap * 100,
            "gap_filled": gap_filled,
            "current_price": current_price,
            "days_since_gap": days_since_gap
        }
        
        # Gap up - potential mean reversion (sell)
        if gap_up and gap_filled < self.fill_threshold and days_since_gap < self.max_hold:
            if current_price > sunday_open * 0.998:  # Still near gap
                confidence = min(0.75, 0.5 + (gap - self.gap_threshold) * 10)
                return Signal("sell", confidence, {**metadata, "reason": "Weekend gap up - mean reversion"})
        
        # Gap down - potential mean reversion (buy)
        if gap_down and gap_filled < self.fill_threshold and days_since_gap < self.max_hold:
            if current_price < sunday_open * 1.002:  # Still near gap
                confidence = min(0.75, 0.5 + (abs(gap) - self.gap_threshold) * 10)
                return Signal("buy", confidence, {**metadata, "reason": "Weekend gap down - mean reversion"})
        
        # Gap continuation
        if gap_up and current_price > sunday_open and days_since_gap < 2:
            return Signal("buy", 0.6, {**metadata, "reason": "Gap up continuation"})
        
        if gap_down and current_price < sunday_open and days_since_gap < 2:
            return Signal("sell", 0.6, {**metadata, "reason": "Gap down continuation"})
        
        return Signal("hold", 0.2, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    # Week of data: Mon, Tue, Wed, Thu, Fri, Sat, Sun, Mon
    weekdays = [0, 1, 2, 3, 4, 5, 6, 0]
    
    # Friday close at 40000, Sunday gaps up
    prices = [39500, 39700, 39800, 39900, 40000, 40100, 40600, 40500]
    volumes = [1000, 1100, 1050, 1000, 1200, 800, 900, 1100]
    
    strategy = WeekendGapStrategy()
    signal = strategy.analyze(prices, volumes, weekdays)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
