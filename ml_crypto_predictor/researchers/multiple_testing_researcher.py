"""
MultipleTestingResearcher — BH-FDR + PSR + DSR (Theme F)
=========================================================

Productionizes into ``alpha_engine/anti_overfit_validator.py`` and the
new ``alpha_engine/statistical_rigor.py`` (added in this PR). The
"deflation" layer that separates "we have a backtest" from "we are a
hedge fund".

Literature
----------
* Benjamini & Hochberg (1995) — "Controlling the False Discovery Rate".
* Bailey & López de Prado (2012) — "The Sharpe Ratio Efficient Frontier"
  (PSR).
* Bailey & López de Prado (2014) — "The Deflated Sharpe Ratio" (DSR).
* Harvey, Liu, Zhu (2016) — "...and the Cross-Section of Expected
  Returns" (multiple-testing in factor research).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from .base import Researcher, ResearchQuestion, ResearchResult


class MultipleTestingResearcher(Researcher):
    """Statistical-deflation researcher (Plan Theme F)."""

    researcher_id = "multiple_testing"
    name = "Multiple-Testing & Deflation Researcher"
    specialization = "BH-FDR, PSR, DSR; bootstrap CIs across the source-system grid"
    literature = [
        "Benjamini & Hochberg (1995) — FDR step-up",
        "Bailey & López de Prado (2012) — PSR",
        "Bailey & López de Prado (2014) — DSR",
        "Harvey, Liu, Zhu (2016) — Multiple Testing in Asset Pricing",
    ]

    def formulate_questions(self) -> List[ResearchQuestion]:
        return [
            ResearchQuestion(
                id="mt_001",
                title="How Many Source-Systems Survive 5%-FDR After BH Correction?",
                description=(
                    "Run a one-sided t-test of mean PnL > 0 per source-system, "
                    "then apply Benjamini-Hochberg with target FDR 5%. Compare "
                    "naive-significant count to BH-significant count."
                ),
                hypothesis=(
                    "Of ~30 source-systems, only 5-8 survive 5%-FDR, matching "
                    "the heuristic in hedge_fund_performance_review_summary "
                    "that 2 EQUITY + 2 CRYPTO sources do all the work."
                ),
                methodology=(
                    "1) Per-source one-sided t-test of mean(pnl_pct) > 0.\n"
                    "2) BH at FDR 5% via statistical_rigor.benjamini_hochberg.\n"
                    "3) Annotate audit dashboard rows with survives_bh boolean.\n"
                    "4) Wire into anti_overfit_validator.py promotion gate."
                ),
                success_criteria={
                    "bh_survivor_count_max": 10,
                    "bh_aligns_with_tier_table": True,
                },
                priority=2,
            )
        ]

    def prepare_data(self, question: ResearchQuestion) -> Dict[str, Any]:
        return {"status": "stub",
                "todo": "Compute per-source p-values from closed_picks.json."}

    def conduct_experiment(self, question: ResearchQuestion,
                           data: Dict[str, Any]) -> ResearchResult:
        return ResearchResult(
            researcher_id=self.researcher_id,
            question_id=question.id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            findings="Stub seeded for Week-2 dashboard credibility. Plan Theme F.",
            metrics={},
            confidence=0.0,
            limitations=["Persona seeded; experiment not yet run."],
            recommendations={
                "wire_target": "alpha_engine/anti_overfit_validator.py",
                "utility": "alpha_engine/statistical_rigor.py",
                "companion": "alpha_engine/deflated_sharpe.py",
            },
        )

    def validate_findings(self, result: ResearchResult) -> Dict[str, Any]:
        return {"status": "pending", "result_id": result.question_id}
