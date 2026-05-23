"""
RegimeRouter - Hurst Exponent Regime Classification
=====================================================
Wraps HurstRegimeFilterStrategy's R/S analysis to classify market regimes.

Returns:
  - "TRENDING"       when H > HURST_TREND_THRESHOLD (persistent series)
  - "MEAN_REVERSION" when H < HURST_MR_THRESHOLD    (anti-persistent series)
  - "RANDOM"         when H is in between            (no edge)

Academic basis: Hurst (1951), Mandelbrot (1968), Qian & Rasheed (2004).
"""

import sys
import os
import numpy as np

# Allow importing baby_strategies from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from baby_strategies.hurst_regime_filter import HurstRegimeFilterStrategy
from quan_engine.config import (
    HURST_WINDOW,
    HURST_TREND_THRESHOLD,
    HURST_MR_THRESHOLD,
)


class RegimeRouter:
    """Classifies price series into TRENDING, MEAN_REVERSION, or RANDOM regimes."""

    def __init__(self):
        self._hurst = HurstRegimeFilterStrategy({
            "hurst_window": HURST_WINDOW,
            "trend_threshold": HURST_TREND_THRESHOLD,
            "mr_threshold": HURST_MR_THRESHOLD,
        })

    def classify(self, prices: np.ndarray) -> str:
        """Classify a single price series into a market regime.

        Args:
            prices: 1-D numpy array of close prices (must have >= HURST_WINDOW elements).

        Returns:
            "TRENDING", "MEAN_REVERSION", or "RANDOM".
        """
        if len(prices) < HURST_WINDOW:
            return "RANDOM"

        H = self._hurst._compute_hurst(prices[-HURST_WINDOW:])

        if H > HURST_TREND_THRESHOLD:
            return "TRENDING"
        if H < HURST_MR_THRESHOLD:
            return "MEAN_REVERSION"
        return "RANDOM"

    def classify_all(self, symbol_data: dict) -> dict:
        """Classify multiple symbols at once.

        Args:
            symbol_data: Mapping of symbol -> dict with key 'close' containing
                         a numpy array of close prices.

        Returns:
            Mapping of symbol -> regime string.
        """
        return {sym: self.classify(d["close"]) for sym, d in symbol_data.items()}
