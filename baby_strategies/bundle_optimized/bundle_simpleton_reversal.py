#!/usr/bin/env python3
"""
Simpleton Trend Reversal Bundle - Regime-Aware Wrapper
=======================================================
Target: 15-25% returns with moderate drawdown tolerance (<20%)

Single-strategy bundle wrapping the Simpleton Trend Reversal with
regime-aware Half-Kelly position sizing. Reduces exposure in ranging
markets where reversals are noisy, and sizes up in strong trends
where mean-reversion signals have higher reliability.

Position Sizing: Half-Kelly formula capped at 25%, scaled by regime.
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, Optional

try:
    import pandas as pd
except ImportError:
    pd = None  # pandas optional; only needed for detect_regime()


@dataclass
class Signal:
    asset: str
    direction: str
    weight: float
    confidence: float
    expected_return: float
    volatility: float
    regime: str
    metadata: Dict = field(default_factory=dict)


class SimpletonReversalBundle:
    def __init__(self):
        self.name = "SimpletonReversal_v1"
        self.version = "1.0.0"
        self.base_allocation = 1.0  # 100% single strategy

        self.regime_multipliers = {
            "trending_strong": 1.0,
            "trending_weak": 0.7,
            "ranging": 0.3,
            "volatile": 0.5,
            "breakout": 0.8,
        }

    def detect_regime(self, df: pd.DataFrame) -> str:
        """
        Classify market regime using an ADX-style proxy.

        Uses the ratio of directional price change to total range
        over a lookback window as a trend-strength indicator.
        """
        if df is None or len(df) < 20:
            return "ranging"

        close = df["close"].values
        lookback = min(20, len(close))
        recent = close[-lookback:]

        directional_move = abs(recent[-1] - recent[0])
        total_range = np.sum(np.abs(np.diff(recent)))

        if total_range == 0:
            return "ranging"

        trend_ratio = directional_move / total_range
        volatility = np.std(np.diff(recent) / recent[:-1])

        if volatility > 0.03:
            return "volatile"
        if trend_ratio > 0.6:
            return "trending_strong"
        if trend_ratio > 0.35:
            return "trending_weak"
        if trend_ratio > 0.25:
            return "breakout"
        return "ranging"

    @staticmethod
    def half_kelly(win_rate: float, avg_win: float, avg_loss: float) -> float:
        """
        Half-Kelly position sizing, capped at 25%.

        Kelly% = (W * B - L) / B  where B = avg_win/avg_loss, W = win_rate, L = 1-W
        Half-Kelly = Kelly% / 2
        """
        if avg_loss <= 0 or avg_win <= 0:
            return 0.0

        b = avg_win / avg_loss
        kelly = (win_rate * b - (1 - win_rate)) / b
        half = kelly / 2.0
        return max(0.0, min(half, 0.25))

    def get_position_size(
        self,
        regime: str,
        win_rate: float = 0.58,
        avg_win: float = 2.5,
        avg_loss: float = 1.5,
    ) -> float:
        """Return regime-adjusted position size as a fraction of capital."""
        base_size = self.half_kelly(win_rate, avg_win, avg_loss)
        multiplier = self.regime_multipliers.get(regime, 0.3)
        return round(base_size * multiplier, 4)

    def get_metrics(self) -> Dict:
        return {
            "name": self.name,
            "version": self.version,
            "target_return": "15-25%",
            "expected_sharpe": "1.0-2.0",
            "expected_max_dd": "-12% to -20%",
            "rebalancing": "Daily",
            "num_strategies": 1,
            "base_allocation": f"{self.base_allocation * 100:.0f}%",
            "position_sizing": "Half-Kelly (capped 25%)",
            "regime_aware": True,
        }


if __name__ == "__main__":
    bundle = SimpletonReversalBundle()
    metrics = bundle.get_metrics()

    print(f"Strategy: {metrics['name']} v{metrics['version']}")
    print(f"Target Return: {metrics['target_return']}")
    print(f"Expected Sharpe: {metrics['expected_sharpe']}")
    print(f"Position Sizing: {metrics['position_sizing']}")
    print()

    print("Regime-adjusted position sizes (WR=58%, W/L=2.5/1.5):")
    for regime, mult in bundle.regime_multipliers.items():
        size = bundle.get_position_size(regime)
        print(f"  {regime:20s}: {size:.2%}  (mult={mult})")
