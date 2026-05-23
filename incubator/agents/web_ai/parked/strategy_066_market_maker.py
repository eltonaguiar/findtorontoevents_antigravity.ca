"""
Strategy 066: Market Maker Tracking
Market maker activity detection
"""
from dataclasses import dataclass
from typing import List, Dict
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class MarketMakerTrackingStrategy:
    """
    Tracks market maker inventory and quote patterns.
    Identifies potential MM accumulation/distribution.
    """
    
    def __init__(
        self,
        quote_imbalance_threshold: float = 0.3,
        inventory_window: int = 20,
        spread_threshold: float = 0.001
    ):
        self.quote_threshold = quote_imbalance_threshold
        self.inventory_window = inventory_window
        self.spread_threshold = spread_threshold
    
    def analyze(
        self,
        bids: List[List[float]],  # [[price, size], ...]
        asks: List[List[float]],
        trades: List[Dict],
        prices: List[float]
    ) -> Signal:
        if not bids or not asks:
            return Signal("hold", 0.0, {"error": "No order book data"})
        
        # Quote imbalance
        bid_size = sum(b[1] for b in bids[:5])
        ask_size = sum(a[1] for a in asks[:5])
        total_size = bid_size + ask_size
        
        if total_size == 0:
            return Signal("hold", 0.0, {"error": "Zero size"})
        
        quote_imbalance = (bid_size - ask_size) / total_size
        
        # Spread analysis
        best_bid = bids[0][0]
        best_ask = asks[0][0]
        spread = (best_ask - best_bid) / ((best_bid + best_ask) / 2)
        
        # Trade flow analysis
        if trades:
            buy_flow = sum(t['size'] for t in trades if t.get('side') == 'buy')
            sell_flow = sum(t['size'] for t in trades if t.get('side') == 'sell')
            flow_imbalance = (buy_flow - sell_flow) / (buy_flow + sell_flow + 1e-8)
        else:
            flow_imbalance = 0
        
        # Quote stuffing detection (rapid quote changes)
        quote_changes = len([t for t in trades if t.get('is_quote', False)]) if trades else 0
        
        metadata = {
            "quote_imbalance": quote_imbalance,
            "spread_pct": spread * 100,
            "flow_imbalance": flow_imbalance,
            "quote_changes": quote_changes
        }
        
        # Heavy bid quoting + buy flow = MM accumulating
        if quote_imbalance > self.quote_threshold and flow_imbalance > 0.2:
            return Signal("buy", 0.7, {**metadata, "reason": "MM bid support"})
        
        # Heavy ask quoting + sell flow = MM distributing
        if quote_imbalance < -self.quote_threshold and flow_imbalance < -0.2:
            return Signal("sell", 0.7, {**metadata, "reason": "MM ask pressure"})
        
        # Tight spread + balanced flow = equilibrium
        if spread < self.spread_threshold and abs(flow_imbalance) < 0.1:
            return Signal("hold", 0.3, {**metadata, "reason": "MM equilibrium"})
        
        # Wide spread = low MM participation
        if spread > self.spread_threshold * 3:
            return Signal("hold", 0.25, {**metadata, "reason": "Wide spread - low MM activity"})
        
        return Signal("hold", 0.2, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    bids = [[39990, 10], [39980, 15], [39970, 20], [39960, 25], [39950, 30]]
    asks = [[40010, 5], [40020, 8], [40030, 12], [40040, 15], [40050, 20]]
    
    trades = [
        {"price": 40000, "size": 2, "side": "buy"},
        {"price": 40005, "size": 3, "side": "buy"},
        {"price": 39995, "size": 1, "side": "sell"}
    ]
    
    prices = [40000 + np.random.randn() * 20 for _ in range(20)]
    
    strategy = MarketMakerTrackingStrategy()
    signal = strategy.analyze(bids, asks, trades, prices)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
