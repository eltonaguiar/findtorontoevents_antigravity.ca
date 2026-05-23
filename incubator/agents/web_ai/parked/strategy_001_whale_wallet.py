"""
Strategy 001: Whale Wallet Accumulation Detector
On-chain metric strategy tracking large wallet movements
"""
from dataclasses import dataclass
from typing import Optional, List
import numpy as np

@dataclass
class Signal:
    action: str  # "buy", "sell", "hold"
    confidence: float  # 0.0 to 1.0
    metadata: dict

class WhaleWalletStrategy:
    """
    Detects whale wallet accumulation/distribution patterns.
    Tracks large wallet inflows/outflows to exchanges and accumulation addresses.
    """
    
    def __init__(
        self,
        whale_threshold_btc: float = 1000.0,
        accumulation_lookback: int = 7,
        exchange_flow_threshold: float = 0.05,
        min_whale_wallets: int = 5,
        signal_threshold: float = 0.6
    ):
        self.whale_threshold = whale_threshold_btc
        self.lookback = accumulation_lookback
        self.flow_threshold = exchange_flow_threshold
        self.min_wallets = min_whale_wallets
        self.signal_threshold = signal_threshold
    
    def analyze(
        self,
        whale_balances: List[List[float]],  # List of whale wallet balances over time
        exchange_inflows: List[float],
        exchange_outflows: List[float],
        prices: List[float]
    ) -> Signal:
        """
        Analyze whale wallet behavior for trading signals.
        
        Args:
            whale_balances: List of balance histories for tracked whale wallets
            exchange_inflows: Daily BTC flowing into exchanges
            exchange_outflows: Daily BTC flowing out of exchanges
            prices: Price history
        """
        if len(prices) < self.lookback:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Calculate net whale accumulation
        whale_changes = []
        for wallet_history in whale_balances:
            if len(wallet_history) >= self.lookback:
                change = (wallet_history[-1] - wallet_history[-self.lookback]) / wallet_history[-self.lookback]
                whale_changes.append(change)
        
        if len(whale_changes) < self.min_wallets:
            return Signal("hold", 0.0, {"error": "Insufficient whale wallets tracked"})
        
        # Average whale behavior
        avg_whale_change = np.mean(whale_changes)
        whales_accumulating = sum(1 for c in whale_changes if c > 0) / len(whale_changes)
        
        # Exchange flow analysis
        recent_inflows = np.mean(exchange_inflows[-self.lookback:])
        recent_outflows = np.mean(exchange_outflows[-self.lookback:])
        net_flow = recent_inflows - recent_outflows
        flow_ratio = net_flow / (recent_outflows + 1e-8)
        
        # Price trend
        price_change = (prices[-1] - prices[-self.lookback]) / prices[-self.lookback]
        
        # Signal generation
        metadata = {
            "avg_whale_change": avg_whale_change,
            "whales_accumulating": whales_accumulating,
            "net_exchange_flow": net_flow,
            "price_change": price_change
        }
        
        # Bullish: Whales accumulating + outflows from exchanges
        if avg_whale_change > 0.02 and whales_accumulating > 0.6 and flow_ratio < -self.flow_threshold:
            confidence = min(0.95, 0.5 + avg_whale_change * 10 + whales_accumulating * 0.3)
            return Signal("buy", confidence, metadata)
        
        # Bearish: Whales distributing + inflows to exchanges
        if avg_whale_change < -0.02 and whales_accumulating < 0.4 and flow_ratio > self.flow_threshold:
            confidence = min(0.95, 0.5 - avg_whale_change * 10 + (1 - whales_accumulating) * 0.3)
            return Signal("sell", confidence, metadata)
        
        return Signal("hold", 0.3, metadata)


if __name__ == "__main__":
    # Test the strategy
    np.random.seed(42)
    
    # Generate synthetic data
    n_days = 30
    n_whales = 10
    
    # Whale balances - some accumulating, some distributing
    whale_balances = []
    for i in range(n_whales):
        base = 5000 + np.random.randn() * 1000
        trend = 0.001 if i < 7 else -0.0005  # 70% accumulating
        balances = [base * (1 + trend * d + np.random.randn() * 0.01) for d in range(n_days)]
        whale_balances.append(balances)
    
    # Exchange flows - more outflows (accumulation)
    exchange_inflows = np.random.exponential(1000, n_days)
    exchange_outflows = np.random.exponential(1500, n_days)  # Higher outflows
    
    # Price data
    prices = 45000 * np.cumprod(1 + np.random.randn(n_days) * 0.02)
    
    strategy = WhaleWalletStrategy()
    signal = strategy.analyze(whale_balances, exchange_inflows.tolist(), 
                              exchange_outflows.tolist(), prices.tolist())
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
