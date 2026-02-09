"""
Regime-Aware Allocator

Dynamically shifts strategy weights based on market regime.
When vol is high → shift to defensive/mean reversion.
When trend is strong → shift to momentum.
When DXY is strong → shift from growth to value.
"""
import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class RegimeAllocator:
    """
    Allocate strategy weights based on current market regime.
    
    This is the "mode switching" from the God-Mode spec:
    - High Volatility → silence momentum, boost mean reversion
    - Strong trend → boost momentum, reduce mean reversion
    - Strong dollar → reduce growth, boost value/dividends
    - Crisis → max defensive, min momentum
    """

    # Default weight profiles per regime
    REGIME_PROFILES = {
        "risk_on": {
            "momentum": 0.30,
            "trend": 0.15,
            "breakout": 0.10,
            "mean_reversion": 0.05,
            "earnings_drift": 0.15,
            "quality": 0.10,
            "value": 0.05,
            "dividend": 0.05,
            "ml": 0.05,
        },
        "neutral": {
            "momentum": 0.15,
            "trend": 0.10,
            "breakout": 0.05,
            "mean_reversion": 0.10,
            "earnings_drift": 0.15,
            "quality": 0.15,
            "value": 0.10,
            "dividend": 0.10,
            "ml": 0.10,
        },
        "risk_off": {
            "momentum": 0.05,
            "trend": 0.05,
            "breakout": 0.00,
            "mean_reversion": 0.15,
            "earnings_drift": 0.10,
            "quality": 0.25,
            "value": 0.15,
            "dividend": 0.20,
            "ml": 0.05,
        },
        "crisis": {
            "momentum": 0.00,
            "trend": 0.00,
            "breakout": 0.00,
            "mean_reversion": 0.20,
            "earnings_drift": 0.05,
            "quality": 0.30,
            "value": 0.15,
            "dividend": 0.25,
            "ml": 0.05,
        },
    }

    def __init__(self, custom_profiles: Dict[str, Dict[str, float]] = None):
        self.profiles = custom_profiles or self.REGIME_PROFILES.copy()
        self._regime_history: List[Dict] = []

    def get_weights(self, regime: str) -> Dict[str, float]:
        """Get strategy weights for a given regime."""
        weights = self.profiles.get(regime, self.profiles["neutral"])
        # Normalize to sum to 1
        total = sum(weights.values())
        if total > 0:
            return {k: v / total for k, v in weights.items()}
        return weights

    def compute_blended_weights(
        self,
        regime_scores: Dict[str, float],
    ) -> Dict[str, float]:
        """
        Compute blended weights from regime probability scores.
        
        Args:
            regime_scores: Dict of regime -> probability (should sum to ~1)
                          e.g., {"risk_on": 0.3, "neutral": 0.5, "risk_off": 0.2}
        
        Returns:
            Dict of strategy_type -> blended weight
        """
        blended = {}
        for regime, prob in regime_scores.items():
            if regime not in self.profiles:
                continue
            weights = self.profiles[regime]
            for strategy, weight in weights.items():
                blended[strategy] = blended.get(strategy, 0) + weight * prob

        # Normalize
        total = sum(blended.values())
        if total > 0:
            blended = {k: v / total for k, v in blended.items()}

        return blended

    def classify_regime(self, macro_data: Dict) -> Dict[str, float]:
        """
        Classify current regime from macro data into probabilities.
        
        Uses multiple signals to produce soft regime classification.
        """
        scores = {"risk_on": 0.25, "neutral": 0.25, "risk_off": 0.25, "crisis": 0.25}

        # VIX-based
        composite = macro_data.get("composite_regime", "neutral")
        if composite == "risk_on":
            scores["risk_on"] += 0.3
        elif composite == "neutral":
            scores["neutral"] += 0.3
        elif composite == "risk_off":
            scores["risk_off"] += 0.3
        elif composite == "crisis":
            scores["crisis"] += 0.3

        # Trend-based
        trend = macro_data.get("trend_regime", "neutral")
        if trend in ["strong_bull", "bull"]:
            scores["risk_on"] += 0.15
            scores["neutral"] += 0.05
        elif trend in ["bear", "strong_bear"]:
            scores["risk_off"] += 0.10
            scores["crisis"] += 0.10

        # DXY-based
        dxy_strong = macro_data.get("dxy_strong", False)
        if dxy_strong:
            # Strong dollar hurts growth/momentum
            scores["risk_off"] += 0.05

        # Normalize to probabilities
        total = sum(scores.values())
        if total > 0:
            scores = {k: v / total for k, v in scores.items()}

        self._regime_history.append({
            "scores": scores.copy(),
            "macro": {k: v for k, v in macro_data.items() if isinstance(v, (int, float, str, bool))},
        })

        return scores

    def apply_dxy_filter(
        self,
        weights: Dict[str, float],
        dxy_dist_from_sma50: float,
    ) -> Dict[str, float]:
        """
        Apply DXY filter from the God-Mode spec:
        If DXY is >2% above 50-day SMA → reduce Growth, increase Value/Dividend.
        """
        if dxy_dist_from_sma50 > 0.02:
            # Strong dollar → shift from growth to value
            shift = min((dxy_dist_from_sma50 - 0.02) * 5, 0.15)  # Max 15% shift
            growth_types = ["momentum", "breakout", "trend"]
            value_types = ["value", "dividend", "quality"]

            for gt in growth_types:
                if gt in weights:
                    weights[gt] = max(weights[gt] - shift / len(growth_types), 0)
            for vt in value_types:
                if vt in weights:
                    weights[vt] = weights[vt] + shift / len(value_types)

            # Re-normalize
            total = sum(weights.values())
            if total > 0:
                weights = {k: v / total for k, v in weights.items()}

        return weights

    def get_allocation_summary(self) -> str:
        """Get a human-readable allocation summary."""
        if not self._regime_history:
            return "No regime history available"

        latest = self._regime_history[-1]
        scores = latest["scores"]
        dominant = max(scores, key=scores.get)
        weights = self.get_weights(dominant)

        lines = [
            f"Current Regime: {dominant} (confidence: {scores[dominant]:.1%})",
            f"Regime Probabilities: {', '.join(f'{k}: {v:.1%}' for k, v in scores.items())}",
            f"",
            f"Strategy Allocation:",
        ]
        for strat, weight in sorted(weights.items(), key=lambda x: x[1], reverse=True):
            bar = "█" * int(weight * 40)
            lines.append(f"  {strat:20s} {weight:6.1%} {bar}")

        return "\n".join(lines)
