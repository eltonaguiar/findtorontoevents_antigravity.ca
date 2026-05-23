"""Persona: Factor Overlay Researcher -- Multi-factor alpha overlays.

Part of Theme D from the hedge-fund-grade uplift plan.
Wires into: alpha_engine/baby_strategies/

This researcher investigates classical factor premiums (momentum, value,
carry, low-vol) as overlays on top of the existing baby-strategy
ecosystem.  The core question is: "Can a disciplined factor overlay
improve the risk-adjusted return of baby strategies by dynamically
shifting exposure toward factors that are currently rewarded?"

Methodology:
1. Construct factor mimicking portfolios for each asset class.
2. Compute factor returns and rolling factor Sharpe ratios.
3. Evaluate factor timing models (simple vs machine-learning-based).
4. Backtest overlay on baby strategies: baseline vs factor-enhanced.
5. Measure interaction effects between factor overlays and existing
   strategy signals.

Expected outputs:
- findings.md with factor definitions and construction methodology
- Factor performance summary (Sharpe, max drawdown, skew)
- Overlay backtest results: baseline vs enhanced
- Recommended factor weights per regime
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

__all__ = ["FactorOverlayResearcher"]


class FactorOverlayResearcher:
    """Researcher persona for multi-factor overlay research.

    Fills the factor-exposure gap in the baby-strategies pipeline.
    Production baby strategies are pure technical; this researcher
    develops the evidence for adding fundamental factor overlays that
    adapt to macro-regime conditions.

    Attributes
    ----------
    PERSONA_ID : str
        Unique snake_case identifier for this persona.
    THEME : str
        Theme letter from the uplift plan.
    TARGET_MODULE : str
        Production module this research wires into.
    """

    PERSONA_ID = "factor_overlay"
    THEME = "D"
    TARGET_MODULE = "alpha_engine/baby_strategies/"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """Initialise the researcher with configuration.

        Parameters
        ----------
        config : dict or None
            Research parameters.  Expected keys:
            - ``factors`` (list): factor names to investigate
            - ``lookback_window`` (int): rolling window for factor estimation
            - ``regime_aware`` (bool): whether to time factors by regime
        """
        self.config = config or {}
        self.factors = self.config.get(
            "factors", ["momentum", "value", "carry", "low_vol", "quality"]
        )
        self.lookback_window = self.config.get("lookback_window", 252)
        self.regime_aware = self.config.get("regime_aware", True)
        logger.info(
            "FactorOverlayResearcher initialised (factors=%s, regime_aware=%s)",
            self.factors,
            self.regime_aware,
        )

    def run_experiment(self, data: dict[str, Any]) -> dict[str, Any]:
        """Run the persona's core experiment. Returns findings dict.

        Parameters
        ----------
        data : dict
            Experiment data with keys:
            - ``prices_df`` (pd.DataFrame): OHLCV prices per asset
            - ``baby_strategy_signals`` (pd.DataFrame): signal matrix
            - ``regimes`` (pd.Series): regime labels per date

        Returns
        -------
        dict
            Findings with keys:
            - ``factor_sharpes`` (dict): Sharpe per factor
            - ``best_factor`` (str): highest-Sharpe factor
            - ``overlay_improvement`` (float): Sharpe delta with overlay
            - ``regime_factor_map`` (dict): best factor per regime
        """
        raise NotImplementedError("Subclasses must implement run_experiment")

    def generate_findings(self, data: dict[str, Any]) -> str:
        """Generate findings.md content. Returns markdown string.

        Parameters
        ----------
        data : dict
            Output from ``run_experiment``.

        Returns
        -------
        str
            Markdown-formatted findings document ready for commit.
        """
        raise NotImplementedError("Subclasses must implement generate_findings")

    def validate_for_production(self, findings: dict[str, Any]) -> tuple[bool, str]:
        """Check if findings meet production bar. Returns (bool, reason).

        A finding meets the production bar when:
        1. At least one factor has OOS Sharpe > 0.5.
        2. The combined overlay improves baby-strategy Sharpe by >= 0.1.
        3. Factor turnover is < 20% per month (reasonable t-cost).

        Parameters
        ----------
        findings : dict
            Output from ``run_experiment``.

        Returns
        -------
        tuple
            (passes: bool, reason: str)
        """
        raise NotImplementedError("Subclasses must implement validate_for_production")
