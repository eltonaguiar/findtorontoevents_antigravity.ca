"""
RiskParityResearcher — HRP Allocator over Source-Systems (Theme D)
====================================================================

Productionizes into ``alpha_engine/hrp_allocator.py`` (added in this
PR) and its target caller ``alpha_engine/regime_position_sizer.py``.
The plan's "AQR move": allocate by Sharpe / cluster-variance, not by
pick count.

Literature
----------
* López de Prado (2016) — "Building Diversified Portfolios that
  Outperform Out-of-Sample", Journal of Portfolio Management.
* Maillard, Roncalli, Teiletche (2010) — "The Properties of Equally
  Weighted Risk Contribution Portfolios".
* AQR Capital — Risk Parity Fund methodology.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from .base import Researcher, ResearchQuestion, ResearchResult


class RiskParityResearcher(Researcher):
    """HRP source-system allocator (Plan Theme D)."""

    researcher_id = "risk_parity"
    name = "Risk-Parity / HRP Researcher"
    specialization = "Hierarchical Risk Parity over source-systems"
    literature = [
        "López de Prado (2016) — HRP",
        "Maillard, Roncalli, Teiletche (2010) — Equally Weighted Risk Contribution",
        "AQR Risk Parity Fund methodology",
    ]

    def formulate_questions(self) -> List[ResearchQuestion]:
        return [
            ResearchQuestion(
                id="rp_001",
                title="HRP vs Equal-Weight: Out-of-Sample Sharpe Lift on Source-Systems?",
                description=(
                    "Compute HRP weights per the López de Prado 2016 algorithm "
                    "over the source-system return matrix and compare to the "
                    "current implicit equal-weight allocation."
                ),
                hypothesis=(
                    "HRP increases portfolio Sharpe by 15-25% on out-of-sample "
                    "data vs equal-weight, with the largest lift coming from "
                    "automatic down-weighting of zombie sources (goldmine_stocks, "
                    "fast_stocks_competition) without an explicit kill-list."
                ),
                methodology=(
                    "1) Build source × day return matrix from closed_picks.json.\n"
                    "2) Walk-forward HRP weights with 90d training / 30d test.\n"
                    "3) Compare cumulative return + Sharpe + turnover vs EW.\n"
                    "4) Wire into regime_position_sizer.py with multiplicative "
                    "stack: HRP source weight × per-symbol vol-target."
                ),
                success_criteria={
                    "sharpe_lift_pct_vs_equal_weight": 15.0,
                    "max_turnover_per_month_pct": 50.0,
                },
                priority=2,
            )
        ]

    def prepare_data(self, question: ResearchQuestion) -> Dict[str, Any]:
        return {"status": "stub",
                "todo": "Build source × day pivot from closed_picks.json."}

    def conduct_experiment(self, question: ResearchQuestion,
                           data: Dict[str, Any]) -> ResearchResult:
        return ResearchResult(
            researcher_id=self.researcher_id,
            question_id=question.id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            findings="Stub seeded for Week-3 plan execution. See plan Theme D.",
            metrics={},
            confidence=0.0,
            limitations=["Persona seeded; experiment not yet run."],
            recommendations={
                "wire_target": "alpha_engine/hrp_allocator.py",
                "wire_caller": "alpha_engine/regime_position_sizer.py",
            },
        )

    def validate_findings(self, result: ResearchResult) -> Dict[str, Any]:
        return {"status": "pending", "result_id": result.question_id}
