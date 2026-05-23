"""
VolTargetingResearcher — Constant-Volatility Risk Engine (Theme A)
==================================================================

Productionizes into ``alpha_engine/regime_position_sizer.py`` and
``alpha_engine/vol_targeted_sizer.py``. The plan's biggest single
uplift: scale position sizes inversely to forecast volatility so
CRYPTO MDD-178% stops happening.

Literature
----------
* Moreira & Muir (2017) "Volatility-Managed Portfolios", Journal of Finance.
* Harvey et al. (2018) "The Impact of Volatility Targeting".
* Rohrbach et al. (2017) "Momentum Strategies in Futures Markets and Trend
  Following Funds" — vol-targeting is the CTA standard.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .base import Researcher, ResearchQuestion, ResearchResult
from datetime import datetime, timezone


class VolTargetingResearcher(Researcher):
    """Constant-vol position sizing researcher (Plan Theme A)."""

    researcher_id = "vol_targeting"
    name = "Volatility Targeting Researcher"
    specialization = "Constant-vol exposure, fractional Kelly, kill-switches"
    literature = [
        "Moreira & Muir (2017) — Volatility-Managed Portfolios",
        "Harvey et al. (2018) — The Impact of Volatility Targeting",
        "Rohrbach et al. (2017) — CTA Momentum + Vol Targeting",
    ]

    def formulate_questions(self) -> List[ResearchQuestion]:
        return [
            ResearchQuestion(
                id="vt_001",
                title="HAR-RV vs GARCH(1,1) vs EWMA: Best 1-day Vol Forecast for Sizing?",
                description=(
                    "Compare three production-grade short-horizon volatility "
                    "forecasters as inputs to a constant-vol position sizer "
                    "across CRYPTO/EQUITY/FOREX/COMMODITY closed-pick streams."
                ),
                hypothesis=(
                    "HAR-RV (Heterogeneous Auto-Regressive on Realized Variance) "
                    "will outperform GARCH(1,1) and EWMA on out-of-sample MAE "
                    "by 5-15% on liquid classes, with the largest gap on CRYPTO. "
                    "Vol-targeted sizing using HAR-RV cuts the MDD-178% number "
                    "to under 40% with <10% Sharpe degradation."
                ),
                methodology=(
                    "1) Backfill 1y of daily realized variance per symbol.\n"
                    "2) Fit HAR-RV / GARCH / EWMA(λ=0.94) walk-forward.\n"
                    "3) Score by 1-day MAE + dashboard MDD reduction.\n"
                    "4) Wire winning forecaster into vol_targeted_sizer.py."
                ),
                success_criteria={
                    "har_rv_mae_improvement_vs_ewma_pct": 5.0,
                    "crypto_mdd_after_vol_target_pct": 40.0,
                    "sharpe_degradation_pct": 10.0,
                },
                priority=1,
            )
        ]

    def prepare_data(self, question: ResearchQuestion) -> Dict[str, Any]:
        return {
            "status": "stub",
            "todo": "Backfill realized variance from closed_picks.json + market data.",
        }

    def conduct_experiment(self, question: ResearchQuestion,
                           data: Dict[str, Any]) -> ResearchResult:
        return ResearchResult(
            researcher_id=self.researcher_id,
            question_id=question.id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            findings="Stub seeded for Week-1 plan execution. See plan Theme A.",
            metrics={},
            confidence=0.0,
            reproducible=True,
            limitations=["Persona seeded; experiment not yet run."],
            recommendations={
                "wire_target": "alpha_engine/vol_targeted_sizer.py",
                "wire_caller": "alpha_engine/regime_position_sizer.py",
            },
        )

    def validate_findings(self, result: ResearchResult) -> Dict[str, Any]:
        return {"status": "pending", "result_id": result.question_id}
