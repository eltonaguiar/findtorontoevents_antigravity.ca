"""
Strategy 005: Miner Position Index (MPI)
On-chain metric tracking miner selling behavior
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class MinerPositionStrategy:
    """
    Monitors miner position index - ratio of miner outflows to 1-year moving average.
    High MPI = miners selling (potentially bearish)
    Low MPI = miners holding (potentially bullish)
    """
    
    def __init__(
        self,
        mpi_threshold_high: float = 2.0,
        mpi_threshold_low: float = 0.5,
        ma_period: int = 365,
        lookback: int = 30
    ):
        self.mpi_high = mpi_threshold_high
        self.mpi_low = mpi_threshold_low
        self.ma_period = ma_period
        self.lookback = lookback
    
    def analyze(
        self,
        miner_outflows: List[float],
        miner_balances: List[float],
        prices: List[float]
    ) -> Signal:
        if len(miner_outflows) < self.ma_period:
            return Signal("hold", 0.0, {"error": "Insufficient data for MPI calculation"})
        
        # Calculate MPI
        current_outflow = miner_outflows[-1]
        historical_ma = np.mean(miner_outflows[-self.ma_period:])
        mpi = current_outflow / (historical_ma + 1e-8)
        
        # Recent trend
        recent_mpi = [out / (historical_ma + 1e-8) for out in miner_outflows[-self.lookback:]]
        mpi_trend = recent_mpi[-1] - recent_mpi[0]
        
        # Miner balance change
        balance_change = (miner_balances[-1] - miner_balances[-self.lookback]) / miner_balances[-self.lookback]
        
        # Price context
        price_trend = (prices[-1] - prices[-self.lookback]) / prices[-self.lookback]
        
        metadata = {
            "mpi": mpi,
            "mpi_trend": mpi_trend,
            "balance_change": balance_change,
            "price_trend": price_trend,
            "current_outflow": current_outflow
        }
        
        # Extreme selling - contrarian buy signal (miners exhausted)
        if mpi > self.mpi_high and mpi_trend < 0:
            confidence = min(0.85, 0.5 + (mpi - self.mpi_high) * 0.2)
            return Signal("buy", confidence, {**metadata, "reason": "Miner selling exhaustion"})
        
        # Strong holding - bullish
        if mpi < self.mpi_low and balance_change > 0:
            confidence = min(0.85, 0.5 + (self.mpi_low - mpi) * 0.3)
            return Signal("buy", confidence, {**metadata, "reason": "Miners accumulating"})
        
        # Increasing selling pressure
        if mpi > self.mpi_high and mpi_trend > 0.5:
            confidence = min(0.8, 0.5 + mpi_trend * 0.3)
            return Signal("sell", confidence, {**metadata, "reason": "Increasing miner selling"})
        
        return Signal("hold", 0.3, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    n_days = 400
    # Simulate miner data
    base_outflow = 1000
    miner_outflows = [base_outflow + np.random.randn() * 200 for _ in range(n_days)]
    # Spike in outflows recently
    miner_outflows[-5:] = [2500, 2800, 2200, 1500, 1200]
    
    miner_balances = [100000 - sum(miner_outflows[:i+1]) * 0.01 for i in range(n_days)]
    prices = [40000 + np.random.randn() * 1000 for _ in range(n_days)]
    
    strategy = MinerPositionStrategy()
    signal = strategy.analyze(miner_outflows, miner_balances, prices)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
