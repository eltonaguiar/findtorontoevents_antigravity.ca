"""
FactorOverlayResearcher — Per-Class Factor Sleeves (Theme D)
=============================================================

Productionizes into the ``alpha_engine/baby_strategies/`` family. Adds
the canonical academic factor sleeves the audit is missing:

* EQUITY: 12-1 momentum, quality (gross profitability), low-vol,
  post-earnings drift, short-interest squeeze.
* FOREX: G10 carry, dollar-block momentum, value (PPP deviation),
  interest-rate-differential.
* COMMODITY: term-structure roll yield, seasonal patterns, COT extremes.
* BOND: 10y-2y duration timing, breakeven inflation factor, credit
  spread mean-reversion.
* CROSS-ASSET: trend-following overlay (CTA replicator) + macro overlay.

Literature
----------
* Fama & French (1993, 2015) — 3- and 5-factor models.
* Carhart (1997) — Momentum factor.
* Asness, Moskowitz, Pedersen (2013) — "Value and Momentum Everywhere".
* Koijen et al. (2018) — "Carry".
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from .base import Researcher, ResearchQuestion, ResearchResult


class FactorOverlayResearcher(Researcher):
    """Per-class factor-sleeve researcher (Plan Theme D)."""

    researcher_id = "factor_overlay"
    name = "Factor Overlay Researcher"
    specialization = "FF5 + momentum + carry + trend across asset classes"
    literature = [
        "Fama & French (1993, 2015) — Factor models",
        "Carhart (1997) — Momentum",
        "Asness, Moskowitz, Pedersen (2013) — Value & Momentum Everywhere",
        "Koijen et al. (2018) — Carry",
    ]

    def formulate_questions(self) -> List[ResearchQuestion]:
        return [
            ResearchQuestion(
                id="fac_001",
                title="EQUITY 12-1 Momentum + Quality: Lift on Existing Sleeve?",
                description=(
                    "Add a 12-1-month momentum + Novy-Marx gross-profitability "
                    "quality screen on top of the EQUITY pick stream. Each new "
                    "sleeve must clear anti_overfit_validator.py before reaching "
                    "the audit."
                ),
                hypothesis=(
                    "Momentum-quality double screen lifts EQUITY PF from 1.385 "
                    "(Tier 2 candidate) to 1.7+ (Tier 1 candidate) with <5pp "
                    "MDD increase, on n>=100 walk-forward folds."
                ),
                methodology=(
                    "1) Compute 12-1 return + gross-profitability score per "
                    "ticker, monthly rebalance.\n"
                    "2) Top-tercile intersection only.\n"
                    "3) Backtest 5y; Sharpe / PF / MDD / turnover.\n"
                    "4) Walk-forward + CPCV cross-check.\n"
                    "5) Promote into alpha_engine/baby_strategies/."
                ),
                success_criteria={
                    "equity_pf_target": 1.70,
                    "max_mdd_increase_pp": 5.0,
                    "passes_anti_overfit_gate": True,
                },
                priority=2,
            )
        ]

    def prepare_data(self, question: ResearchQuestion) -> Dict[str, Any]:
        return {"status": "stub",
                "todo": "Pull 5y of fundamentals + price-momentum series."}

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
                "wire_target": "alpha_engine/baby_strategies/",
                "gate": "alpha_engine/anti_overfit_validator.py",
            },
        )

    def validate_findings(self, result: ResearchResult) -> Dict[str, Any]:
        return {"status": "pending", "result_id": result.question_id}
