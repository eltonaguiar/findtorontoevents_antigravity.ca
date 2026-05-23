"""Persona: Risk Parity Researcher -- Hierarchical Risk Parity allocation research.

Part of Theme D from the hedge-fund-grade uplift plan.
Wires into: alpha_engine/hrp_allocator.py

This researcher investigates HRP parameter choices and compares them to
alternative allocation schemes (equal weight, minimum variance, maximum
Sharpe, inverse-volatility).  The core question is: "Does HRP produce
more stable out-of-sample weights and better risk-adjusted returns than
simpler heuristics when allocating across source-systems?"

Methodology:
1. Backtest HRP vs alternatives on rolling 90-day windows of source-system
   returns.
2. Measure weight turnover (mean absolute delta between rebalances).
3. Measure out-of-sample Sharpe, max drawdown, and Calmar ratio.
4. Grid-search linkage method (single, complete, average, Ward).
5. Stress-test with synthetic correlation breakdown scenarios.

Expected outputs:
- findings.md with recommended linkage method and rebalance frequency
- Comparison table: HRP vs EW vs MinVar vs InvVol
- Turnover analysis and transaction-cost-adjusted returns
- Recommended allocation weights for current source-systems
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

__all__ = ["RiskParityResearcher"]


class RiskParityResearcher:
    """Researcher persona for HRP allocation research.

    Fills the capital-allocation research gap.  Production currently uses
    fixed or ad-hoc weights across source-systems; this researcher builds
    the evidence for switching to a principled HRP allocation that adapts
    to the correlation structure of source-system returns.

    Attributes
    ----------
    PERSONA_ID : str
        Unique snake_case identifier for this persona.
    THEME : str
        Theme letter from the uplift plan.
    TARGET_MODULE : str
        Production module this research wires into.
    """

    PERSONA_ID = "risk_parity"
    THEME = "D"
    TARGET_MODULE = "alpha_engine/hrp_allocator.py"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """Initialise the researcher with configuration.

        Parameters
        ----------
        config : dict or None
            Research parameters.  Expected keys:
            - ``linkage_methods`` (list): hierarchical linkage methods to test
            - ``rebalance_freqs`` (list): rebalance frequencies in days
            - ``lookback_window`` (int): trailing days for covariance estimation
        """
        self.config = config or {}
        self.linkage_methods = self.config.get(
            "linkage_methods", ["single", "complete", "average", "ward"]
        )
        self.rebalance_freqs = self.config.get("rebalance_freqs", [5, 10, 20, 30])
        self.lookback_window = self.config.get("lookback_window", 90)
        logger.info(
            "RiskParityResearcher initialised (methods=%s, lookback=%d)",
            self.linkage_methods,
            self.lookback_window,
        )

    def run_experiment(self, data: dict[str, Any]) -> dict[str, Any]:
        """Run the persona's core experiment. Returns findings dict.

        Parameters
        ----------
        data : dict
            Experiment data with keys:
            - ``returns_df`` (pd.DataFrame): source-system daily returns
            - ``transaction_cost`` (float): one-way cost as fraction
            - ``test_fraction`` (float): fraction for OOS test

        Returns
        -------
        dict
            Findings with keys:
            - ``best_linkage`` (str): recommended linkage method
            - ``best_rebalance_freq`` (int): recommended rebalance days
            - ``sharpe_by_method`` (dict): OOS Sharpe per method
            - ``turnover_by_method`` (dict): mean turnover per method
            - ``cost_adjusted_sharpe`` (dict): after-cost Sharpe per method
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
        1. HRP OOS Sharpe is within 0.05 of the best alternative.
        2. HRP turnover is <= 75% of MaxSharpe turnover (stability win).
        3. After-cost Sharpe of HRP exceeds equal-weight by >= 0.05.

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
