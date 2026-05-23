"""
Strategy 068: Mempool Gas Arb
Gas price arbitrage strategy
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class MempoolGasStrategy:
    """
    Trades based on mempool congestion and gas prices.
    High gas = network congestion = potential volatility.
    """
    
    def __init__(
        self,
        high_gas_threshold: float = 100,  # gwei
        low_gas_threshold: float = 20,
        congestion_lookback: int = 24
    ):
        self.high_gas = high_gas_threshold
        self.low_gas = low_gas_threshold
        self.lookback = congestion_lookback
    
    def analyze(
        self,
        gas_prices: List[float],  # gwei
        pending_tx_count: List[int],
        prices: List[float]
    ) -> Signal:
        if len(gas_prices) < self.lookback:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        current_gas = gas_prices[-1]
        gas_ma = np.mean(gas_prices[-self.lookback:])
        
        # Gas trend
        gas_change = (current_gas - gas_prices[-self.lookback]) / gas_prices[-self.lookback]
        
        # Pending transactions
        current_pending = pending_tx_count[-1]
        pending_ma = np.mean(pending_tx_count[-self.lookback:])
        
        # Congestion level
        congestion = current_gas / gas_ma if gas_ma > 0 else 1
        
        # Price context
        price_change = (prices[-1] - prices[-5]) / prices[-5] if len(prices) >= 5 else 0
        
        metadata = {
            "current_gas": current_gas,
            "gas_ma": gas_ma,
            "congestion": congestion,
            "pending_tx": current_pending,
            "gas_change": gas_change
        }
        
        # Extreme gas spike - network stress, often volatile
        if current_gas > self.high_gas and congestion > 2:
            if price_change > 0:
                return Signal("buy", 0.65, {**metadata, "reason": "High gas with price up"})
            else:
                return Signal("sell", 0.65, {**metadata, "reason": "High gas with price down"})
        
        # Gas dropping from extreme - activity resuming
        if gas_prices[-3] > self.high_gas and current_gas < gas_ma:
            if price_change > 0:
                return Signal("buy", 0.6, {**metadata, "reason": "Gas normalizing, bullish"})
        
        # Very low gas - accumulation opportunity
        if current_gas < self.low_gas and congestion < 0.5:
            return Signal("buy", 0.55, {**metadata, "reason": "Low gas - cheap transactions"})
        
        return Signal("hold", 0.2, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    n = 30
    # Gas spiking
    gas = [30 + np.random.randn() * 5 for _ in range(25)]
    gas.extend([80, 120, 150, 100, 80])
    
    pending = [10000 + np.random.randn() * 1000 for _ in range(25)]
    pending.extend([20000, 35000, 40000, 30000, 25000])
    
    prices = [40000 + i * 50 for i in range(n)]
    
    strategy = MempoolGasStrategy()
    signal = strategy.analyze(gas, pending, prices)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
