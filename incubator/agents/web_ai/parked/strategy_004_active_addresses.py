"""
Strategy 004: Active Addresses Momentum
On-chain metric tracking active address growth/decline
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class ActiveAddressesStrategy:
    """
    Analyzes active address trends as a leading indicator of price.
    Growing active addresses often precede price increases.
    """
    
    def __init__(
        self,
        short_window: int = 7,
        long_window: int = 30,
        growth_threshold: float = 0.05,
        price_confirmation: bool = True
    ):
        self.short_window = short_window
        self.long_window = long_window
        self.growth_threshold = growth_threshold
        self.price_confirmation = price_confirmation
    
    def analyze(
        self,
        active_addresses: List[float],
        new_addresses: List[float],
        prices: List[float]
    ) -> Signal:
        if len(active_addresses) < self.long_window:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Calculate growth rates
        short_aa = np.mean(active_addresses[-self.short_window:])
        long_aa = np.mean(active_addresses[-self.long_window:])
        aa_growth = (short_aa - long_aa) / long_aa
        
        # New addresses momentum
        short_new = np.mean(new_addresses[-self.short_window:])
        long_new = np.mean(new_addresses[-self.long_window:])
        new_growth = (short_new - long_new) / long_new
        
        # Price momentum for confirmation
        price_change = (prices[-1] - prices[-self.short_window]) / prices[-self.short_window]
        
        # Network health score
        network_health = (aa_growth + new_growth) / 2
        
        metadata = {
            "active_address_growth": aa_growth,
            "new_address_growth": new_growth,
            "network_health": network_health,
            "price_change": price_change,
            "current_active": active_addresses[-1],
            "current_new": new_addresses[-1]
        }
        
        # Strong network growth
        if network_health > self.growth_threshold:
            if not self.price_confirmation or price_change > 0:
                confidence = min(0.9, 0.5 + network_health * 5)
                return Signal("buy", confidence, metadata)
        
        # Network contraction
        if network_health < -self.growth_threshold:
            if not self.price_confirmation or price_change < 0:
                confidence = min(0.9, 0.5 + abs(network_health) * 5)
                return Signal("sell", confidence, metadata)
        
        # Divergence signals
        if aa_growth > 0.02 and price_change < -0.02:
            return Signal("buy", 0.65, {**metadata, "reason": "Network growing despite price drop"})
        
        if aa_growth < -0.02 and price_change > 0.02:
            return Signal("sell", 0.65, {**metadata, "reason": "Network shrinking despite price rise"})
        
        return Signal("hold", 0.25, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    n_days = 40
    # Growing network
    active = [900000 + i * 2000 + np.random.randn() * 10000 for i in range(n_days)]
    new = [50000 + i * 100 + np.random.randn() * 5000 for i in range(n_days)]
    prices = [40000 + i * 100 + np.random.randn() * 300 for i in range(n_days)]
    
    strategy = ActiveAddressesStrategy()
    signal = strategy.analyze(active, new, prices)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
