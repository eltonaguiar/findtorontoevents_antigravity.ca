# Crypto Risk‑Parity Portfolio Optimizer
# Simple risk‑parity based on inverse volatility weighting.

import numpy as np

class RiskParityOptimizer:
    """Calculate portfolio weights that equalize risk contributions across assets."""
    def __init__(self, vol_series=None):
        # vol_series: dict {symbol: annualized volatility}
        self.vol_series = vol_series or {}

    def compute_weights(self):
        # Inverse volatility weighting
        vol = np.array([self.vol_series.get(sym, 1.0) for sym in self.vol_series])
        if vol.size == 0:
            return {}
        inv_vol = 1.0 / vol
        raw_weights = inv_vol / inv_vol.sum()
        # Return dict {symbol: weight}
        return {sym: w for sym, w in zip(self.vol_series.keys(), raw_weights)}
