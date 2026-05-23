"""
Strategy 021: Order Book Imbalance
Microstructure strategy using bid-ask imbalance
"""
from dataclasses import dataclass
from typing import List, Dict
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class OrderBookImbalanceStrategy:
    """
    Analyzes order book imbalance between bids and asks.
    Heavy bid side = buying pressure (bullish)
    Heavy ask side = selling pressure (bearish)
    """
    
    def __init__(
        self,
        depth_levels: int = 10,
        imbalance_threshold: float = 0.2,
        smoothing_period: int = 5
    ):
        self.depth_levels = depth_levels
        self.imbalance_threshold = imbalance_threshold
        self.smoothing_period = smoothing_period
    
    def analyze(
        self,
        bids: List[List[float]],  # [[price, size], ...]
        asks: List[List[float]],  # [[price, size], ...]
        recent_trades: List[Dict]
    ) -> Signal:
        if len(bids) < self.depth_levels or len(asks) < self.depth_levels:
            return Signal("hold", 0.0, {"error": "Insufficient book depth"})
        
        # Calculate weighted volumes
        bid_volume = sum(b[1] for b in bids[:self.depth_levels])
        ask_volume = sum(a[1] for a in asks[:self.depth_levels])
        total_volume = bid_volume + ask_volume
        
        if total_volume == 0:
            return Signal("hold", 0.0, {"error": "Zero volume"})
        
        # Imbalance ratio (-1 to 1, positive = more bids)
        imbalance = (bid_volume - ask_volume) / total_volume
        
        # Best bid/ask
        best_bid = bids[0][0] if bids else 0
        best_ask = asks[0][0] if asks else 0
        spread = best_ask - best_bid if best_ask > best_bid else 0
        spread_pct = spread / ((best_bid + best_ask) / 2) if best_bid > 0 else 0
        
        # Trade flow analysis
        if recent_trades:
            buy_volume = sum(t['size'] for t in recent_trades if t.get('side') == 'buy')
            sell_volume = sum(t['size'] for t in recent_trades if t.get('side') == 'sell')
            trade_imbalance = (buy_volume - sell_volume) / (buy_volume + sell_volume + 1e-8)
        else:
            trade_imbalance = 0
        
        metadata = {
            "imbalance": imbalance,
            "bid_volume": bid_volume,
            "ask_volume": ask_volume,
            "spread_pct": spread_pct,
            "trade_imbalance": trade_imbalance,
            "best_bid": best_bid,
            "best_ask": best_ask
        }
        
        # Strong bid imbalance with trade confirmation
        if imbalance > self.imbalance_threshold and trade_imbalance > 0.1:
            confidence = min(0.85, 0.5 + imbalance * 0.4)
            return Signal("buy", confidence, {**metadata, "reason": "Strong bid imbalance"})
        
        # Strong ask imbalance with trade confirmation
        if imbalance < -self.imbalance_threshold and trade_imbalance < -0.1:
            confidence = min(0.85, 0.5 + abs(imbalance) * 0.4)
            return Signal("sell", confidence, {**metadata, "reason": "Strong ask imbalance"})
        
        # Moderate signals
        if imbalance > self.imbalance_threshold * 0.7:
            return Signal("buy", 0.6, {**metadata, "reason": "Moderate bid imbalance"})
        
        if imbalance < -self.imbalance_threshold * 0.7:
            return Signal("sell", 0.6, {**metadata, "reason": "Moderate ask imbalance"})
        
        return Signal("hold", 0.2, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    # Generate order book with bid imbalance
    bids = [[40000 - i * 10, 5 + np.random.exponential(3)] for i in range(20)]
    asks = [[40050 + i * 10, 3 + np.random.exponential(2)] for i in range(20)]
    
    trades = [
        {"price": 40025, "size": 2.5, "side": "buy"},
        {"price": 40030, "size": 1.8, "side": "buy"},
        {"price": 40020, "size": 1.2, "side": "sell"}
    ]
    
    strategy = OrderBookImbalanceStrategy()
    signal = strategy.analyze(bids, asks, trades)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
