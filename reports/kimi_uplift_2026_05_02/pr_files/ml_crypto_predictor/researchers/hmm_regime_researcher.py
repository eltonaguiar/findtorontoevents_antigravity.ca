"""Persona: HMM Regime Researcher -- Hidden Markov Model regime detection.

Part of Theme C from the hedge-fund-grade uplift plan.
Wires into: alpha_engine/system_trend_detector.py

This researcher investigates Hidden Markov Models for regime detection
in multi-asset return series.  The core question is: "Can an HMM
identify persistent market regimes (trending, mean-reverting, high-vol,
low-vol) with sufficient accuracy and lead time to adjust strategy
weights before the regime change damages PnL?"

Methodology:
1. Fit GaussianHMM to multi-variate return features (returns, vol,
   correlation, skewness) on a rolling window.
2. Use Bayesian Information Criterion (BIC) to select the optimal number
   of regimes (typically 3-5).
3. Evaluate regime-prediction accuracy via forward-labelled confusion
   matrix.
4. Backtest regime-dependent strategy rotation vs static weights.

Expected outputs:
- findings.md with optimal n_regimes per asset class
- Regime transition matrix (P(regime_t | regime_{t-1}))
- Forward-prediction accuracy per regime
- Recommended code changes for system_trend_detector.py
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

__all__ = ["HMMRegimeResearcher"]


class HMMRegimeResearcher:
    """Researcher persona for HMM-based regime detection.

    Fills the regime-detection gap in the production trend-detection
    pipeline.  The current system uses simple moving-average crossovers;
    this researcher builds the evidence base for switching to a
    probabilistic HMM regime model that can anticipate transitions.

    Attributes
    ----------
    PERSONA_ID : str
        Unique snake_case identifier for this persona.
    THEME : str
        Theme letter from the uplift plan.
    TARGET_MODULE : str
        Production module this research wires into.
    """

    PERSONA_ID = "hmm_regime"
    THEME = "C"
    TARGET_MODULE = "alpha_engine/system_trend_detector.py"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """Initialise the researcher with configuration.

        Parameters
        ----------
        config : dict or None
            Research parameters.  Expected keys:
            - ``n_regimes_range`` (list): candidate regime counts to test
            - ``lookback_window`` (int): rolling window for HMM fitting
            - ``features`` (list): feature columns to use (e.g. ['returns', 'vol'])
        """
        self.config = config or {}
        self.n_regimes_range = self.config.get("n_regimes_range", [3, 4, 5])
        self.lookback_window = self.config.get("lookback_window", 252)
        self.features = self.config.get("features", ["returns", "volatility", "skewness"])
        logger.info(
            "HMMRegimeResearcher initialised (regimes=%s, lookback=%d)",
            self.n_regimes_range,
            self.lookback_window,
        )

    def run_experiment(self, data: dict[str, Any]) -> dict[str, Any]:
        """Run the persona's core experiment. Returns findings dict.

        Parameters
        ----------
        data : dict
            Experiment data with keys:
            - ``features_df`` (pd.DataFrame): multi-feature time series
            - ``returns`` (pd.Series): target returns to predict regime for
            - ``train_size`` (float): fraction for train/test split

        Returns
        -------
        dict
            Findings with keys:
            - ``best_n_regimes`` (int): BIC-optimal regime count
            - ``bic_scores`` (dict): BIC per candidate n_regimes
            - ``transition_matrix`` (np.ndarray): regime transition probs
            - ``forward_accuracy`` (float): out-of-sample regime accuracy
            - ``sharpe_improvement`` (float): regime-rotation vs static
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
        1. Forward regime-prediction accuracy is >= 60% (better than random).
        2. The regime-rotation backtest Sharpe exceeds static by >= 0.15.
        3. BIC clearly selects one n_regimes (delta-BIC > 10 vs runner-up).

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
