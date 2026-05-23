"""
Concentration Analyzer

Analyses pick-distribution concentration across asset classes using the
Herfindahl–Hirschman Index (HHI), Gini coefficient, and a composite
diversification score.  Provides actionable rebalancing recommendations.

Part of the swarm risk-management layer (PR-2).
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("swarm.concentration")


class ConcentrationAnalyzer:
    """Analyses concentration of picks across asset classes.

    Parameters
    ----------
    picks:
        List of pick dictionaries.  Each dict must contain at least an
        ``"asset_class"`` key (str).  Optional ``"weight"`` key (float)
        overrides uniform weighting for that pick.
    """

    # HHI risk thresholds
    _HHI_LOW: float = 0.15
    _HHI_MODERATE: float = 0.25
    _HHI_HIGH: float = 0.40

    # Gini risk thresholds
    _GINI_LOW: float = 0.20
    _GINI_MODERATE: float = 0.35
    _GINI_HIGH: float = 0.50

    def __init__(self, picks: list[dict[str, Any]]) -> None:
        self.picks: list[dict[str, Any]] = picks
        self._asset_class_counts: dict[str, int] | None = None
        self._asset_class_weights: dict[str, float] | None = None

        logger.info(
            "ConcentrationAnalyzer initialised with %d picks", len(picks)
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def herfindahl_index(self) -> float:
        """Compute the Herfindahl–Hirschman Index (HHI) of pick distribution.

        HHI is defined as the sum of squared market shares:

        .. math::

            \\text{HHI} = \\sum_{i} w_i^2

        where :math:`w_i` is the fractional share of picks (by count or weight)
        belonging to asset class *i*.

        Returns
        -------
        float
            HHI in ``[0.0, 1.0]``.  ``0`` = perfectly diversified,
            ``1`` = fully concentrated in a single class.
        """
        weights = self._compute_weights()
        if not weights:
            return 0.0

        hhi: float = sum(w * w for w in weights.values())
        logger.debug("herfindahl_index: %.6f", hhi)
        return hhi

    def gini_coefficient(self) -> float:
        """Compute the Gini coefficient of the pick distribution.

        Uses the standard formula for a finite set:

        .. math::

            G = \\frac{2 \\sum_{i=1}^{n} i \\cdot y_i}{n \\sum y_i} - \\frac{n+1}{n}

        where :math:`y_i` are the sorted ascending shares per asset class.

        Returns
        -------
        float
            Gini in ``[0.0, 1.0]``.  ``0`` = perfectly equal,
            ``1`` = maximally unequal.
        """
        weights = self._compute_weights()
        if not weights:
            return 0.0

        shares: list[float] = sorted(weights.values())
        n: int = len(shares)
        if n == 0:
            return 0.0

        total: float = sum(shares)
        if total == 0:
            return 0.0

        # Standard Gini for finite population
        numerator: float = sum((idx + 1) * val for idx, val in enumerate(shares))
        gini: float = (2.0 * numerator) / (n * total) - (n + 1.0) / n

        # Clamp to [0, 1] in case of floating-point drift
        gini = max(0.0, min(1.0, gini))

        logger.debug("gini_coefficient: %.6f", gini)
        return gini

    def diversification_score(self) -> float:
        """Compute a composite diversification score on a 0–100 scale.

        The score linearly blends the inverse of HHI and the complement of the
        Gini coefficient, each contributing 50 %:

        .. math::

            S = 50 \\times (1 - \\text{HHI}) + 50 \\times (1 - \\text{Gini})

        Returns
        -------
        float
            Score in ``[0.0, 100.0]``.
        """
        hhi: float = self.herfindahl_index()
        gini: float = self.gini_coefficient()

        score: float = 50.0 * (1.0 - hhi) + 50.0 * (1.0 - gini)
        score = max(0.0, min(100.0, score))

        logger.info(
            "diversification_score: %.2f/100 (hhi=%.4f gini=%.4f)",
            score,
            hhi,
            gini,
        )
        return score

    def asset_class_distribution(self) -> dict[str, int]:
        """Return the raw count of picks per asset class.

        Returns
        -------
        dict[str, int]
            Mapping ``asset_class → count``.
        """
        if self._asset_class_counts is not None:
            return dict(self._asset_class_counts)

        counts: dict[str, int] = {}
        for pick in self.picks:
            ac: str = pick.get("asset_class", "UNKNOWN")
            counts[ac] = counts.get(ac, 0) + 1

        self._asset_class_counts = counts
        return dict(counts)

    def recommend_rebalancing(
        self,
        target_max_pct: float = 0.30,
    ) -> list[dict[str, Any]]:
        """Suggest rebalancing actions to reduce concentration.

        For each asset class whose share exceeds *target_max_pct*, a
        recommendation is generated with the current share, suggested target
        share (equalised across classes), and the required delta.

        Parameters
        ----------
        target_max_pct:
            Maximum desired share for any single asset class (0.0–1.0).
            Default ``0.30`` (30 %).

        Returns
        -------
        list[dict]
            Each dict contains ``asset_class``, ``current_share``,
            ``target_share``, ``delta``, ``action``.
        """
        weights = self._compute_weights()
        n_classes: int = len(weights)
        if n_classes == 0:
            return []

        equal_target: float = 1.0 / n_classes
        recommendations: list[dict[str, Any]] = []

        for ac, share in sorted(weights.items(), key=lambda x: x[1], reverse=True):
            if share > target_max_pct:
                rec = {
                    "asset_class": ac,
                    "current_share": round(share, 4),
                    "target_share": round(equal_target, 4),
                    "delta": round(share - equal_target, 4),
                    "action": (
                        f"REDUCE_{ac}_BY_{(share - equal_target) * 100:.1f}pct_"
                        f"TO_TARGET_{equal_target * 100:.1f}pct"
                    ),
                }
                recommendations.append(rec)
                logger.info(
                    "Rebalance: %s current=%.2f%% target=%.2f%%",
                    ac,
                    share * 100,
                    equal_target * 100,
                )
            else:
                logger.debug("Rebalance: %s at %.2f%% — within limit", ac, share * 100)

        return recommendations

    def concentration_risk_level(self) -> str:
        """Classify overall concentration risk into four buckets.

        Combines HHI and Gini thresholds with a worst-of heuristic:
        the higher of the two individual risk levels is returned.

        Returns
        -------
        str
            ``"LOW"``, ``"MODERATE"``, ``"HIGH"``, or ``"EXTREME"``.
        """
        hhi: float = self.herfindahl_index()
        gini: float = self.gini_coefficient()

        hhi_level: str = self._hhi_risk_level(hhi)
        gini_level: str = self._gini_risk_level(gini)

        # Worst-of heuristic
        level: str = self._worst_of(hhi_level, gini_level)

        logger.info(
            "concentration_risk_level: %s (hhi=%.4f/%s gini=%.4f/%s)",
            level,
            hhi,
            hhi_level,
            gini,
            gini_level,
        )
        return level

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _compute_weights(self) -> dict[str, float]:
        """Return the fractional weight of each asset class.

        Weights are driven by ``"weight"`` field in each pick dict when present,
        otherwise uniform count weighting is used.
        """
        if self._asset_class_weights is not None:
            return self._asset_class_weights

        # Aggregate by asset class
        class_totals: dict[str, float] = {}
        total_weight: float = 0.0

        for pick in self.picks:
            ac: str = pick.get("asset_class", "UNKNOWN")
            w: float = pick.get("weight", 1.0)
            class_totals[ac] = class_totals.get(ac, 0.0) + w
            total_weight += w

        if total_weight == 0:
            self._asset_class_weights = {}
            return {}

        weights: dict[str, float] = {
            ac: val / total_weight for ac, val in class_totals.items()
        }
        self._asset_class_weights = weights
        return weights

    @staticmethod
    def _hhi_risk_level(hhi: float) -> str:
        """Map HHI value to a risk level string."""
        if hhi < ConcentrationAnalyzer._HHI_LOW:
            return "LOW"
        if hhi < ConcentrationAnalyzer._HHI_MODERATE:
            return "MODERATE"
        if hhi < ConcentrationAnalyzer._HHI_HIGH:
            return "HIGH"
        return "EXTREME"

    @staticmethod
    def _gini_risk_level(gini: float) -> str:
        """Map Gini value to a risk level string."""
        if gini < ConcentrationAnalyzer._GINI_LOW:
            return "LOW"
        if gini < ConcentrationAnalyzer._GINI_MODERATE:
            return "MODERATE"
        if gini < ConcentrationAnalyzer._GINI_HIGH:
            return "HIGH"
        return "EXTREME"

    @staticmethod
    def _worst_of(level_a: str, level_b: str) -> str:
        """Return the more severe of two risk-level strings."""
        severity = {"LOW": 0, "MODERATE": 1, "HIGH": 2, "EXTREME": 3}
        return level_a if severity[level_a] >= severity[level_b] else level_b
