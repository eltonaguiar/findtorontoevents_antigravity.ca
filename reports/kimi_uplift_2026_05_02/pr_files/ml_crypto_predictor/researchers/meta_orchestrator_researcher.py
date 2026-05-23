"""Persona: Meta Orchestrator Researcher -- Coordination layer for all personas.

Part of Theme E from the hedge-fund-grade uplift plan.
Wires into: ml_crypto_predictor/researchers/coordinator.py

This researcher orchestrates the research cycles of all other personas,
ensuring that findings are synthesised, conflicts resolved, and the
aggregate research agenda prioritises the highest-impact gaps.  The core
question is: "Given limited research bandwidth, which combination of
persona experiments will produce the largest improvement in production
metrics?"

Methodology:
1. Maintain a research backlog: open questions ranked by expected impact.
2. Schedule persona experiments to minimise overlap and maximise coverage.
3. Synthesise cross-persona findings (e.g. vol-targeting + regime detection
   together may produce synergies that neither does alone).
4. Detect contradictions between persona recommendations and resolve
   via evidence-weighted voting.
5. Publish a weekly research digest for the engineering team.

Expected outputs:
- findings.md with the current research backlog and priorities
- Synthesis report combining outputs from all active personas
- Weekly research digest (markdown)
- Recommended next-3-experiments ranked by expected Sharpe improvement
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

__all__ = ["MetaOrchestratorResearcher"]


class MetaOrchestratorResearcher:
    """Researcher persona for meta-research coordination.

    Fills the coordination gap between independent researcher personas.
    Without orchestration, personas may run conflicting experiments or
    duplicate effort.  This researcher ensures the research programme
    operates as a coherent portfolio of investigations.

    Attributes
    ----------
    PERSONA_ID : str
        Unique snake_case identifier for this persona.
    THEME : str
        Theme letter from the uplift plan.
    TARGET_MODULE : str
        Production module this research wires into.
    """

    PERSONA_ID = "meta_orchestrator"
    THEME = "E"
    TARGET_MODULE = "ml_crypto_predictor/researchers/coordinator.py"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """Initialise the researcher with configuration.

        Parameters
        ----------
        config : dict or None
            Research parameters.  Expected keys:
            - ``personas`` (list): active persona IDs to orchestrate
            - ``research_budget`` (int): max parallel experiments
            - ``synthesis_frequency`` (str): how often to synthesise
        """
        self.config = config or {}
        self.personas = self.config.get(
            "personas",
            [
                "vol_targeting",
                "reconciliation",
                "hmm_regime",
                "risk_parity",
                "factor_overlay",
                "multiple_testing",
                "transaction_cost",
            ],
        )
        self.research_budget = self.config.get("research_budget", 3)
        self.synthesis_frequency = self.config.get("synthesis_frequency", "weekly")
        logger.info(
            "MetaOrchestratorResearcher initialised (%d personas, budget=%d)",
            len(self.personas),
            self.research_budget,
        )

    def run_experiment(self, data: dict[str, Any]) -> dict[str, Any]:
        """Run the persona's core experiment. Returns findings dict.

        Parameters
        ----------
        data : dict
            Experiment data with keys:
            - ``persona_findings`` (dict): map from persona_id to findings
            - ``production_metrics`` (dict): current production KPIs
            - ``backlog`` (list): open research questions

        Returns
        -------
        dict
            Findings with keys:
            - ``priorities`` (list): ranked experiment recommendations
            - ``synergies`` (list): pairs of personas with complementary findings
            - ``conflicts`` (list): contradictory findings requiring resolution
            - ``expected_improvement`` (float): aggregate expected Sharpe delta
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
        1. At least one recommended experiment has expected improvement > 0.05 Sharpe.
        2. No unresolved conflicts remain between high-priority findings.
        3. The research agenda covers all 6 themes (A-F) within the next 4 weeks.

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
