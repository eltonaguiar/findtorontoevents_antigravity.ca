"""
ReconciliationResearcher — Settlement Integrity SLA (Theme B)
==============================================================

Productionizes into ``alpha_engine/outcome_resolver.py`` and the new
``alpha_engine/reconciliation_report.py``. The P0 unblocker for
FOREX/COMMODITY verdicts.

Literature
----------
* Easley, López de Prado, O'Hara (2013) — "The Volume Clock: Insights into
  the High-Frequency Paradigm" (settlement-integrity foundations).
* SEC Rule 15c3-3 (Customer Protection) — institutional reconciliation
  standards.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from .base import Researcher, ResearchQuestion, ResearchResult


class ReconciliationResearcher(Researcher):
    """Settlement-integrity SLA researcher (Plan Theme B)."""

    researcher_id = "reconciliation"
    name = "Reconciliation / Settlement Integrity Researcher"
    specialization = "EOD reconciliation, snapshot-at-emission, T+1 blotters"
    literature = [
        "Easley, López de Prado, O'Hara (2013) — Volume Clock",
        "SEC Rule 15c3-3 — Customer Protection / Reconciliation",
        "FINRA Rule 4530 — Reportable Events (settlement breaks)",
    ]

    def formulate_questions(self) -> List[ResearchQuestion]:
        return [
            ResearchQuestion(
                id="rec_001",
                title="Snapshot-at-emission vs Live-fetch: How Much Noise Does Each Add?",
                description=(
                    "The current resolver fetches yfinance at *resolution time*, "
                    "not pick emission time. Quantify the resolver-flicker share "
                    "this introduces by class (FOREX 63%, COMMODITY 67% per the "
                    "2026-04-27 deep dive)."
                ),
                hypothesis=(
                    "Switching to snapshot-at-emission removes 60-70% of "
                    "FOREX/COMMODITY 'wins' that are actually 1bp resolver flicker, "
                    "making the asset-class verdict tables actionable."
                ),
                methodology=(
                    "1) Diff yfinance close at emission timestamp vs resolution "
                    "timestamp on n=1,400 historical FOREX/COMMODITY picks.\n"
                    "2) Recompute pnl_pct using emission snapshot.\n"
                    "3) Compare WR/PF/MDD before vs after.\n"
                    "4) Wire emission snapshot into outcome_resolver.py:384-405."
                ),
                success_criteria={
                    "forex_clean_win_share_after_pct": 90.0,
                    "commodity_clean_win_share_after_pct": 90.0,
                },
                priority=1,
            )
        ]

    def prepare_data(self, question: ResearchQuestion) -> Dict[str, Any]:
        return {"status": "stub",
                "todo": "Pull n=1,400 FOREX/COMMODITY rows + emission timestamps."}

    def conduct_experiment(self, question: ResearchQuestion,
                           data: Dict[str, Any]) -> ResearchResult:
        return ResearchResult(
            researcher_id=self.researcher_id,
            question_id=question.id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            findings="Stub seeded for Week-1 P0 unblocker. See plan Theme B.",
            metrics={},
            confidence=0.0,
            limitations=["Persona seeded; experiment not yet run."],
            recommendations={
                "wire_target": "alpha_engine/outcome_resolver.py",
                "report_target": "alpha_engine/reconciliation_report.py",
            },
        )

    def validate_findings(self, result: ResearchResult) -> Dict[str, Any]:
        return {"status": "pending", "result_id": result.question_id}
