"""
Strategy 024: Trade Flow Imbalance
Microstructure trade flow analysis
"""
from dataclasses import dataclass
from typing import List, Dict
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class TradeFlowImbalanceStrategy:
    """
    Analyzes aggressive buyers vs sellers through trade flow.
    Aggressive buyers hitting asks = bullish
    Aggressive sellers hitting bids = bearish
    """
    
    def __init__(
        self,
        window_size: int = 50,
        imbalance_threshold: float = 0.6,
        large_trade_multiplier: float = 3.0
    ):
        self.window_size = window_size
        self.imbalance_threshold = imbalance_threshold
        self.large_multiplier = large_trade_multiplier
    
    def analyze(
        self,
        trades: List[Dict],  # [{price, size, side, timestamp}, ...]
        best_bid: float,
        best_ask: float
    ) -> Signal:
        if len(trades) < self.window_size:
            return Signal("hold", 0.0, {"error": "Insufficient trades"})
        
        recent_trades = trades[-self.window_size:]
        
        # Calculate volume-weighted flow
        buy_volume = 0
        sell_volume = 0
        large_buy_volume = 0
        large_sell_volume = 0
        
        avg_size = np.mean([t['size'] for t in recent_trades])
        
        for trade in recent_trades:
            size = trade['size']
            side = trade.get('side', 'unknown')
            
            # Determine aggressor
            if side == 'buy':
                buy_volume += size
                if size > avg_size * self.large_multiplier:
                    large_buy_volume += size
            elif side == 'sell':
                sell_volume += size
                if size > avg_size * self.large_multiplier:
                    large_sell_volume += size
        
        total_volume = buy_volume + sell_volume
        if total_volume == 0:
            return Signal("hold", 0.0, {"error": "Zero volume"})
        
        # Imbalance metrics
        flow_imbalance = buy_volume / total_volume
        large_imbalance = (large_buy_volume + 1e-8) / (large_buy_volume + large_sell_volume + 1e-8)
        
        # Delta (buy - sell volume)
        delta = buy_volume - sell_volume
        delta_normalized = delta / total_volume
        
        # Cumulative delta trend
        if len(trades) >= self.window_size * 2:
            prev_window = trades[-self.window_size*2:-self.window_size]
            prev_buy = sum(t['size'] for t in prev_window if t.get('side') == 'buy')
            prev_sell = sum(t['size'] for t in prev_window if t.get('side') == 'sell')
            delta_trend = delta - (prev_buy - prev_sell)
        else:
            delta_trend = 0
        
        metadata = {
            "flow_imbalance": flow_imbalance,
            "large_imbalance": large_imbalance,
            "delta_normalized": delta_normalized,
            "delta_trend": delta_trend,
            "buy_volume": buy_volume,
            "sell_volume": sell_volume,
            "large_buys": large_buy_volume,
            "large_sells": large_sell_volume
        }
        
        # Strong buying pressure
        if flow_imbalance > self.imbalance_threshold and large_imbalance > 0.55:
            confidence = min(0.85, 0.5 + (flow_imbalance - 0.5) * 0.7)
            return Signal("buy", confidence, {**metadata, "reason": "Aggressive buying detected"})
        
        # Strong selling pressure
        if flow_imbalance < (1 - self.imbalance_threshold) and large_imbalance < 0.45:
            confidence = min(0.85, 0.5 + (0.5 - flow_imbalance) * 0.7)
            return Signal("sell", confidence, {**metadata, "reason": "Aggressive selling detected"})
        
        # Delta trend continuation
        if delta_trend > 0 and flow_imbalance > 0.55:
            return Signal("buy", 0.6, {**metadata, "reason": "Delta increasing"})
        
        if delta_trend < 0 and flow_imbalance < 0.45:
            return Signal("sell", 0.6, {**metadata, "reason": "Delta decreasing"})
        
        return Signal("hold", 0.2, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    # Generate trade flow with buy dominance
    trades = []
    for i in range(100):
        side = "buy" if np.random.random() > 0.4 else "sell"  # 60% buys
        size = np.random.exponential(1.5) * (3 if np.random.random() > 0.9 else 1)
        trades.append({
            "price": 40000 + np.random.randn() * 50,
            "size": size,
            "side": side,
            "timestamp": i
        })
    
    strategy = TradeFlowImbalanceStrategy()
    signal = strategy.analyze(trades, 39999, 40001)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
