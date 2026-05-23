"""Persona: Multiple Testing Researcher -- Overfitting defense calibration.

Part of Theme F from the hedge-fund-grade uplift plan.
Wires into: alpha_engine/anti_overfit_validator.py

This researcher investigates the multiple-testing problem in strategy
selection and calibrates the statistical filters used to defend against
overfitting.  The core question is: "How many strategies were actually
tested before the best one was selected, and does it survive correction
for that selection bias?"

Methodology:
1. Audit the strategy generation pipeline to estimate the true number of
   independent trials (n_trials).
2. Calibrate DSR thresholds for different n_trials values.
3. Evaluate CPCV/PBO on recent strategy cohorts.
4. Apply Benjamini-Hochberg FDR correction across strategy families.
5. Compare multiple-testing-adjusted vs raw Sharpe rankings.

Expected outputs:
- findings.md with estimated n_trials per strategy family
- DSR calibration table (n_trials vs minimum acceptable Sharpe)
- CPCV/PBO estimates for recent strategy cohorts
- Recommended FDR thresholds per asset class
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

__all__ = ["MultipleTestingResearcher"]


class MultipleTestingResearcher:
    """Researcher persona for multiple-testing defense calibration.

    Fills the statistical-rigor gap in the anti-overfitting pipeline.
    Production currently uses a fixed Sharpe threshold; this researcher
    develops evidence for switching to DSR-adjusted thresholds that
    account for the true search space of the strategy generator.

    Attributes
    ----------
    PERSONA_ID : str
        Unique snake_case identifier for this persona.
    THEME : str
        Theme letter from the uplift plan.
    TARGET_MODULE : str
        Production module this research wires into.
    """

    PERSONA_ID = "multiple_testing"
    THEME = "F"
    TARGET_MODULE = "alpha_engine/anti_overfit_validator.py"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """Initialise the researcher with configuration.

        Parameters
        ----------
        config : dict or None
            Research parameters.  Expected keys:
            - ``alpha`` (float): target FDR level
            - ``n_trials_estimate`` (int): estimated independent tests
            - ``dsr_threshold`` (float): minimum DSR for promotion
        """
        self.config = config or {}
        self.alpha = self.config.get("alpha", 0.05)
        self.n_trials_estimate = self.config.get("n_trials_estimate", 100)
        self.dsr_threshold = self.config.get("dsr_threshold", 0.95)
        logger.info(
            "MultipleTestingResearcher initialised (alpha=%.3f, n_trials=%d, dsr_threshold=%.2f)",
            self.alpha,
            self.n_trials_estimate,
            self.dsr_threshold,
        )

    def run_experiment(self, data: dict[str, Any]) -> dict[str, Any]:
        """Run the persona's core experiment. Returns findings dict.

        Parameters
        ----------
        data : dict
            Experiment data with keys:
            - ``strategy_returns`` (pd.DataFrame): returns matrix (T x S)
            - ``strategy_metadata`` (pd.DataFrame): per-strategy info
            - ``family_labels`` (pd.Series): family ID per strategy

        Returns
        -------
        dict
            Findings with keys:
            - ``estimated_n_trials`` (int): effective independent tests
            - ``dsr_by_strategy`` (pd.Series): DSR per strategy
            - ``fdr_rejected`` (np.ndarray): BH-FDR rejected nulls
            - ``surviving_strategies`` (list): strategies passing all gates
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
        1. DSR threshold >= 0.95 is achievable with the estimated n_trials.
        2. At least 5 strategies pass all filters (diversity requirement).
        3. BH-FDR correction does not reject > 80% of strategies (power check).

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
