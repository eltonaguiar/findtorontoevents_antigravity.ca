"""
Strategy 034: Perp-Spot Basis Trading
Basis arbitrage and momentum strategy
"""
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class PerpSpotBasisStrategy:
    """
    Trades the basis between perpetual and spot markets.
    Captures both arbitrage and momentum signals.
    """
    
    def __init__(
        self,
        basis_threshold: float = 0.003,
        extreme_basis: float = 0.01,
        convergence_threshold: float = 0.001,
        lookback: int = 30
    ):
        self.basis_threshold = basis_threshold
        self.extreme_basis = extreme_basis
        self.convergence_threshold = convergence_threshold
        self.lookback = lookback
    
    def analyze(
        self,
        perp_prices: List[float],
        spot_prices: List[float],
        perp_volumes: List[float],
        spot_volumes: List[float]
    ) -> Signal:
        if len(perp_prices) < self.lookback or len(spot_prices) < self.lookback:
            return Signal("hold", 0.0, {"error": "Insufficient data"})
        
        # Calculate basis
        basis = [(p - s) / s for p, s in zip(perp_prices, spot_prices)]
        
        current_basis = basis[-1]
        basis_ma = np.mean(basis[-self.lookback:])
        basis_std = np.std(basis[-self.lookback:])
        
        # Basis momentum
        basis_velocity = current_basis - basis[-3] if len(basis) >= 3 else 0
        
        # Historical extremes
        basis_max = max(basis[-self.lookback:])
        basis_min = min(basis[-self.lookback:])
        
        # Volume analysis
        perp_vol_ma = np.mean(perp_volumes[-5:])
        spot_vol_ma = np.mean(spot_volumes[-5:])
        volume_ratio = perp_vol_ma / (spot_vol_ma + 1e-8)
        
        metadata = {
            "current_basis": current_basis,
            "basis_bps": current_basis * 10000,
            "basis_ma": basis_ma,
            "basis_velocity": basis_velocity,
            "basis_range": basis_max - basis_min,
            "volume_ratio": volume_ratio,
            "extreme_high": current_basis > basis_ma + 2 * basis_std,
            "extreme_low": current_basis < basis_ma - 2 * basis_std
        }
        
        # Extreme positive basis - arbitrage sell perp buy spot
        if current_basis > self.extreme_basis:
            confidence = min(0.75, 0.5 + (current_basis - self.extreme_basis) * 50)
            return Signal("sell", confidence, {**metadata, "reason": "Extreme positive basis"})
        
        # Extreme negative basis - arbitrage buy perp sell spot
        if current_basis < -self.extreme_basis:
            confidence = min(0.75, 0.5 + (abs(current_basis) - self.extreme_basis) * 50)
            return Signal("buy", confidence, {**metadata, "reason": "Extreme negative basis"})
        
        # Basis momentum with volume
        if abs(basis_velocity) > 0.001 and volume_ratio > 1.2:
            if basis_velocity > 0 and current_basis > 0:
                return Signal("buy", 0.6, {**metadata, "reason": "Basis expanding with perp volume"})
            if basis_velocity < 0 and current_basis < 0:
                return Signal("sell", 0.6, {**metadata, "reason": "Basis contracting with perp volume"})
        
        # Mean reversion setup
        if current_basis > basis_ma + 1.5 * basis_std and basis_velocity < 0:
            return Signal("sell", 0.6, {**metadata, "reason": "Basis mean reversion"})
        
        if current_basis < basis_ma - 1.5 * basis_std and basis_velocity > 0:
            return Signal("buy", 0.6, {**metadata, "reason": "Basis mean reversion"})
        
        return Signal("hold", 0.2, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    n = 35
    base = 40000
    
    # Spot price
    spot = [base + i * 25 + np.random.randn() * 40 for i in range(n)]
    
    # Perp with high basis
    perp = [s * 1.012 for s in spot]
    
    volumes_perp = [1000 + np.random.randn() * 200 for _ in range(n)]
    volumes_spot = [800 + np.random.randn() * 150 for _ in range(n)]
    
    strategy = PerpSpotBasisStrategy()
    signal = strategy.analyze(perp, spot, volumes_perp, volumes_spot)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
