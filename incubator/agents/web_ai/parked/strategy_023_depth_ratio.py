"""
Strategy 023: Depth Ratio Strategy
Order book depth analysis
"""
from dataclasses import dataclass
from typing import List, Dict
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class DepthRatioStrategy:
    """
    Analyzes order book depth at various price levels.
    Deep bids = strong support
    Deep asks = strong resistance
    """
    
    def __init__(
        self,
        price_range_pct: float = 0.02,
        depth_levels: int = 20,
        ratio_threshold: float = 1.5
    ):
        self.price_range = price_range_pct
        self.depth_levels = depth_levels
        self.ratio_threshold = ratio_threshold
    
    def analyze(
        self,
        order_book: Dict,  # {bids: [[p, s], ...], asks: [[p, s], ...]}
        current_price: float,
        recent_volume: float
    ) -> Signal:
        bids = order_book.get("bids", [])
        asks = order_book.get("asks", [])
        
        if not bids or not asks:
            return Signal("hold", 0.0, {"error": "Empty order book"})
        
        # Calculate price range for analysis
        lower_bound = current_price * (1 - self.price_range)
        upper_bound = current_price * (1 + self.price_range)
        
        # Sum depth within range
        bid_depth = sum(s for p, s in bids if p >= lower_bound)
        ask_depth = sum(s for p, s in asks if p <= upper_bound)
        
        # Depth ratio
        depth_ratio = bid_depth / (ask_depth + 1e-8)
        
        # Wall detection
        bid_walls = [s for p, s in bids if s > recent_volume * 0.5]
        ask_walls = [s for p, s in asks if s > recent_volume * 0.5]
        
        # Support/resistance levels
        support_levels = [(p, s) for p, s in bids[:5] if s > np.mean([b[1] for b in bids[:20]]) * 2]
        resistance_levels = [(p, s) for p, s in asks[:5] if s > np.mean([a[1] for a in asks[:20]]) * 2]
        
        metadata = {
            "depth_ratio": depth_ratio,
            "bid_depth": bid_depth,
            "ask_depth": ask_depth,
            "bid_walls": len(bid_walls),
            "ask_walls": len(ask_walls),
            "support_levels": len(support_levels),
            "resistance_levels": len(resistance_levels)
        }
        
        # Strong bid depth - support
        if depth_ratio > self.ratio_threshold and len(support_levels) >= 2:
            confidence = min(0.8, 0.5 + (depth_ratio - 1) * 0.3)
            return Signal("buy", confidence, {**metadata, "reason": "Strong bid depth, support detected"})
        
        # Strong ask depth - resistance
        if depth_ratio < 1 / self.ratio_threshold and len(resistance_levels) >= 2:
            confidence = min(0.8, 0.5 + (1/depth_ratio - 1) * 0.3)
            return Signal("sell", confidence, {**metadata, "reason": "Strong ask depth, resistance detected"})
        
        # Wall absorption
        if len(bid_walls) > len(ask_walls) and depth_ratio > 1.2:
            return Signal("buy", 0.6, {**metadata, "reason": "Bid walls dominate"})
        
        if len(ask_walls) > len(bid_walls) and depth_ratio < 0.8:
            return Signal("sell", 0.6, {**metadata, "reason": "Ask walls dominate"})
        
        return Signal("hold", 0.2, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    current_price = 40000
    
    # Generate order book with bid dominance
    bids = [[current_price - i * 10, np.random.exponential(10) + (5 if i < 3 else 0)] 
            for i in range(30)]
    asks = [[current_price + i * 10, np.random.exponential(8)] 
            for i in range(30)]
    
    order_book = {"bids": bids, "asks": asks}
    recent_volume = 100
    
    strategy = DepthRatioStrategy()
    signal = strategy.analyze(order_book, current_price, recent_volume)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
