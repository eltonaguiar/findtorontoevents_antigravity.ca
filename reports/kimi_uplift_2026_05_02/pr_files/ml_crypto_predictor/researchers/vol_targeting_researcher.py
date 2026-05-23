"""Persona: Volatility Targeting Researcher -- Regime-aware position sizing.

Part of Theme A from the hedge-fund-grade uplift plan.
Wires into: alpha_engine/regime_position_sizer.py

This researcher investigates volatility-forecasting models and their
integration into the position-sizing pipeline.  The core question is:
"Given a forecast of realised volatility over the trade horizon, how
should we scale the position so that the portfolio runs at constant
target risk?"

Methodology:
1. Evaluate vol-forecast models (GARCH, EWMA, realised vol) on a rolling
   walk-forward basis across all asset classes.
2. Compute the forecast-error distribution and bias.
3. Propose a regime-dependent vol-target scalar (e.g. 0.5x in high-vol
   regimes, 1.5x in low-vol regimes).
4. Validate via backtest: compare vol-targeted sizing vs fixed-lot sizing
   on the same signal set.

Expected outputs:
- findings.md with recommended vol-forecast model per asset class
- Recommended target_vol levels per regime
- Backtest comparison table (vol-targeted vs fixed-lot)
- Production-ready code snippet for regime_position_sizer.py
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

__all__ = ["VolTargetingResearcher"]


class VolTargetingResearcher:
    """Researcher persona for volatility-targeted position sizing.

    Fills the gap between raw signal generation and risk-aware position
    construction.  The current production sizer uses static leverage;
    this researcher develops the evidence base for switching to dynamic,
    vol-targeted sizing that adapts to forecast market volatility.

    Attributes
    ----------
    PERSONA_ID : str
        Unique snake_case identifier for this persona.
    THEME : str
        Theme letter from the uplift plan.
    TARGET_MODULE : str
        Production module this research wires into.
    """

    PERSONA_ID = "vol_targeting"
    THEME = "A"
    TARGET_MODULE = "alpha_engine/regime_position_sizer.py"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """Initialise the researcher with configuration.

        Parameters
        ----------
        config : dict or None
            Research parameters.  Expected keys:
            - ``target_vol`` (float): annualised target volatility
            - ``vol_lookback`` (int): window for realised vol estimation
            - ``regime_override`` (dict): per-regime vol scalars
        """
        self.config = config or {}
        self.target_vol = self.config.get("target_vol", 0.10)
        self.vol_lookback = self.config.get("vol_lookback", 30)
        self.regime_override = self.config.get("regime_override", {})
        logger.info(
            "VolTargetingResearcher initialised (target_vol=%.3f, lookback=%d)",
            self.target_vol,
            self.vol_lookback,
        )

    def run_experiment(self, data: dict[str, Any]) -> dict[str, Any]:
        """Run the persona's core experiment. Returns findings dict.

        Parameters
        ----------
        data : dict
            Experiment data with keys:
            - ``returns`` (pd.DataFrame): source-system daily returns
            - ``regimes`` (pd.Series): regime labels per date
            - ``forecasts`` (pd.DataFrame): vol forecasts per source

        Returns
        -------
        dict
            Findings with keys:
            - ``best_model`` (str): recommended vol-forecast model
            - ``rmse_by_model`` (dict): out-of-sample RMSE per model
            - ``sharpe_improvement`` (float): vol-target vs fixed-lot
            - ``recommendation`` (str): one-line production recommendation
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
        1. The recommended model has OOS RMSE lower than the EWMA baseline.
        2. The vol-targeted backtest Sharpe exceeds fixed-lot by >= 0.1.
        3. All asset classes have at least 252 days of test data.

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
