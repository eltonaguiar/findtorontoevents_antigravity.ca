"""
TransactionCostResearcher — Slippage + Market-Impact Modeling (Theme A/D)
==========================================================================

Productionizes into the existing ``alpha_engine/execution_researcher``
caller path. The transaction-cost layer was drafted in
``reports/RESEARCH_KELLY_AND_SLIPPAGE.md`` but never wired — this
persona owns landing it.

Literature
----------
* Almgren & Chriss (2000) — "Optimal Execution of Portfolio
  Transactions" (the canonical impact model).
* Kissell (2014) — "The Science of Algorithmic Trading and Portfolio
  Management".
* Frazzini, Israel, Moskowitz (2018) — "Trading Costs of Asset Pricing
  Anomalies" (capacity / decay analysis).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from .base import Researcher, ResearchQuestion, ResearchResult


class TransactionCostResearcher(Researcher):
    """Transaction-cost / market-impact researcher (Plan Theme A/D)."""

    researcher_id = "transaction_cost"
    name = "Transaction-Cost / Market-Impact Researcher"
    specialization = "Almgren-Chriss impact, capacity-aware sizing, slippage models"
    literature = [
        "Almgren & Chriss (2000) — Optimal Execution",
        "Kissell (2014) — The Science of Algorithmic Trading",
        "Frazzini, Israel, Moskowitz (2018) — Trading Costs of Anomalies",
    ]

    def formulate_questions(self) -> List[ResearchQuestion]:
        return [
            ResearchQuestion(
                id="tc_001",
                title="Square-Root Impact Model: Calibration Per Asset Class",
                description=(
                    "Calibrate the Almgren-Chriss square-root market-impact "
                    "coefficient per asset class so that pick PnL on the audit "
                    "page is *net* of realistic execution cost, not gross."
                ),
                hypothesis=(
                    "Realistic transaction costs reduce gross PF on micro-cap "
                    "CRYPTO picks by 20-40%; institutional-cap EQUITY picks "
                    "by <5%. The CRYPTO MDD-178% number is partly a sizing-"
                    "without-impact artifact."
                ),
                methodology=(
                    "1) Estimate ADV (average daily volume) per symbol.\n"
                    "2) Fit σ · sqrt(Q / ADV) impact model to historical "
                    "fills where available; literature priors otherwise.\n"
                    "3) Apply to closed_picks.json; recompute net PnL.\n"
                    "4) Wire into execution_researcher caller and surface a "
                    "'net of impact' toggle on the audit page."
                ),
                success_criteria={
                    "net_pnl_estimate_within_pct_of_realised": 20.0,
                    "capacity_warnings_emitted_for_microcaps": True,
                },
                priority=2,
            )
        ]

    def prepare_data(self, question: ResearchQuestion) -> Dict[str, Any]:
        return {"status": "stub",
                "todo": "Pull ADV per symbol; estimate impact coeffs."}

    def conduct_experiment(self, question: ResearchQuestion,
                           data: Dict[str, Any]) -> ResearchResult:
        return ResearchResult(
            researcher_id=self.researcher_id,
            question_id=question.id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            findings="Stub seeded — completes RESEARCH_KELLY_AND_SLIPPAGE.md draft.",
            metrics={},
            confidence=0.0,
            limitations=["Persona seeded; impact-model calibration pending."],
            recommendations={
                "wire_target": "alpha_engine/execution_researcher.py callers",
                "draft_source": "reports/RESEARCH_KELLY_AND_SLIPPAGE.md",
            },
        )

    def validate_findings(self, result: ResearchResult) -> Dict[str, Any]:
        return {"status": "pending", "result_id": result.question_id}
