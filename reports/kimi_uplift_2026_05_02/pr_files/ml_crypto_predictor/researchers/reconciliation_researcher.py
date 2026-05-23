"""Persona: Reconciliation Researcher -- Pick outcome validation across sources.

Part of Theme B from the hedge-fund-grade uplift plan.
Wires into: alpha_engine/outcome_resolver.py

This researcher investigates discrepancies between pick outcomes reported
by different data sources (e.g. exchange API vs dashboard vs backtest
engine).  The core question is: "When the same pick is resolved by two
independent systems, do they agree on the exit price, PnL, and
holding period?"

Methodology:
1. Identify overlapping pick populations across data sources.
2. Compute reconciliation deltas: |price_A - price_B|, |pnl_A - pnl_B|.
3. Root-cause analysis of large deltas (>1% for crypto, >0.1% for forex).
4. Propose data-quality gates and fallback rules.

Expected outputs:
- findings.md with reconciliation error rates per source pair
- Recommended delta thresholds per asset class
- Proposed code changes for outcome_resolver.py
- Unit tests for the reconciliation logic
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

__all__ = ["ReconciliationResearcher"]


class ReconciliationResearcher:
    """Researcher persona for pick outcome reconciliation.

    Fills the data-integrity gap between multiple systems that resolve the
    same pick.  Production currently trusts a single source; this
    researcher builds the evidence for cross-source validation and
    automatic fallback when sources disagree.

    Attributes
    ----------
    PERSONA_ID : str
        Unique snake_case identifier for this persona.
    THEME : str
        Theme letter from the uplift plan.
    TARGET_MODULE : str
        Production module this research wires into.
    """

    PERSONA_ID = "reconciliation"
    THEME = "B"
    TARGET_MODULE = "alpha_engine/outcome_resolver.py"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """Initialise the researcher with configuration.

        Parameters
        ----------
        config : dict or None
            Research parameters.  Expected keys:
            - ``price_tolerance`` (float): max acceptable price delta (frac)
            - ``pnl_tolerance`` (float): max acceptable PnL delta (frac)
            - ``min_overlap`` (int): minimum overlapping picks for analysis
        """
        self.config = config or {}
        self.price_tolerance = self.config.get("price_tolerance", 0.01)
        self.pnl_tolerance = self.config.get("pnl_tolerance", 0.02)
        self.min_overlap = self.config.get("min_overlap", 50)
        logger.info(
            "ReconciliationResearcher initialised (price_tol=%.4f, pnl_tol=%.4f)",
            self.price_tolerance,
            self.pnl_tolerance,
        )

    def run_experiment(self, data: dict[str, Any]) -> dict[str, Any]:
        """Run the persona's core experiment. Returns findings dict.

        Parameters
        ----------
        data : dict
            Experiment data with keys:
            - ``picks_source_a`` (pd.DataFrame): picks from primary source
            - ``picks_source_b`` (pd.DataFrame): picks from secondary source
            - ``join_key`` (str): column to join on (e.g. 'pick_id')

        Returns
        -------
        dict
            Findings with keys:
            - ``recon_rate`` (float): fraction of picks that reconcile
            - ``mean_price_delta`` (float): mean absolute price delta
            - ``mean_pnl_delta`` (float): mean absolute PnL delta
            - ``outliers`` (list): pick_ids with large deltas
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
        1. Reconciliation rate is >= 95% for crypto, >= 98% for forex.
        2. Mean absolute PnL delta is < 1% of mean trade PnL.
        3. At least 500 overlapping picks in the analysis set.

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
