"""
Strategy 020: Cross-Asset Momentum Rank
Relative momentum across crypto assets
"""
from dataclasses import dataclass
from typing import List, Dict
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class CrossAssetMomentumStrategy:
    """
    Ranks assets by momentum and trades relative strength.
    Buy strongest, sell weakest in the basket.
    """
    
    def __init__(
        self,
        momentum_period: int = 14,
        rank_threshold: float = 0.3,
        min_assets: int = 3
    ):
        self.momentum_period = momentum_period
        self.rank_threshold = rank_threshold
        self.min_assets = min_assets
    
    def _calculate_momentum(self, prices: List[float]) -> float:
        if len(prices) < self.momentum_period:
            return 0
        return (prices[-1] - prices[-self.momentum_period]) / prices[-self.momentum_period]
    
    def analyze(
        self,
        asset_prices: Dict[str, List[float]],  # Dict of asset name to price history
        target_asset: str,
        volumes: Dict[str, List[float]]
    ) -> Signal:
        if len(asset_prices) < self.min_assets:
            return Signal("hold", 0.0, {"error": "Insufficient assets"})
        
        if target_asset not in asset_prices:
            return Signal("hold", 0.0, {"error": "Target asset not found"})
        
        # Calculate momentum for all assets
        momentums = {}
        for asset, prices in asset_prices.items():
            if len(prices) >= self.momentum_period:
                momentums[asset] = self._calculate_momentum(prices)
        
        if len(momentums) < self.min_assets:
            return Signal("hold", 0.1, {"error": "Insufficient momentum data"})
        
        # Rank assets
        sorted_assets = sorted(momentums.items(), key=lambda x: x[1], reverse=True)
        target_momentum = momentums[target_asset]
        
        # Find rank
        target_rank = next(i for i, (a, _) in enumerate(sorted_assets) if a == target_asset)
        total_assets = len(sorted_assets)
        rank_percentile = 1 - (target_rank / total_assets)
        
        # Average momentum
        avg_momentum = np.mean(list(momentums.values()))
        
        metadata = {
            "target_momentum": target_momentum,
            "target_rank": target_rank + 1,
            "total_assets": total_assets,
            "rank_percentile": rank_percentile,
            "avg_momentum": avg_momentum,
            "top_performer": sorted_assets[0][0],
            "bottom_performer": sorted_assets[-1][0]
        }
        
        # Top tier momentum
        if rank_percentile > 1 - self.rank_threshold and target_momentum > 0:
            confidence = min(0.85, 0.5 + rank_percentile * 0.3 + target_momentum * 2)
            return Signal("buy", confidence, {**metadata, "reason": "Top momentum rank"})
        
        # Bottom tier momentum
        if rank_percentile < self.rank_threshold and target_momentum < 0:
            confidence = min(0.85, 0.5 + (1 - rank_percentile) * 0.3 + abs(target_momentum) * 2)
            return Signal("sell", confidence, {**metadata, "reason": "Bottom momentum rank"})
        
        # Improving momentum
        if target_rank < total_assets // 3 and target_momentum > avg_momentum:
            return Signal("buy", 0.6, {**metadata, "reason": "Above average momentum"})
        
        return Signal("hold", 0.25, metadata)


if __name__ == "__main__":
    np.random.seed(42)
    
    n = 20
    # Multiple assets with different momentum
    assets = {
        "BTC": [40000 + i * 80 + np.random.randn() * 200 for i in range(n)],
        "ETH": [2200 + i * 20 + np.random.randn() * 50 for i in range(n)],
        "SOL": [100 + i * 3 + np.random.randn() * 5 for i in range(n)],
        "ADA": [0.5 + i * 0.005 + np.random.randn() * 0.02 for i in range(n)]
    }
    volumes = {a: [1000 + np.random.randn() * 200 for _ in range(n)] for a in assets}
    
    strategy = CrossAssetMomentumStrategy()
    signal = strategy.analyze(assets, "BTC", volumes)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
