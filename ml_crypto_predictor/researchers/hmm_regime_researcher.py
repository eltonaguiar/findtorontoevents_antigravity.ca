"""
HMMRegimeResearcher — Hidden-Markov Regime Detection (Theme C)
===============================================================

Deepens the existing ``regime_researcher`` with a Hidden Markov Model
over (VIX z-score, USD index momentum, BTC realized vol, 10y-2y slope)
→ 4 regimes (Risk-On / Risk-Off / Crisis / Mean-Reverting). Productionizes
into ``alpha_engine/system_trend_detector.py``.

Literature
----------
* Hamilton (1989) — "A New Approach to the Economic Analysis of
  Nonstationary Time Series and the Business Cycle".
* Ang & Bekaert (2002) — "Regime Switches in Interest Rates".
* Bridgewater All-Weather methodology — regime-based exposure.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from .base import Researcher, ResearchQuestion, ResearchResult


class HMMRegimeResearcher(Researcher):
    """Hidden Markov regime detection (Plan Theme C)."""

    researcher_id = "hmm_regime"
    name = "HMM Regime Researcher"
    specialization = "4-state HMM over macro factors; conditional Sharpe gating"
    literature = [
        "Hamilton (1989) — Markov-Switching",
        "Ang & Bekaert (2002) — Regime Switches in Interest Rates",
        "Bridgewater — All-Weather Regime Framework",
    ]

    def formulate_questions(self) -> List[ResearchQuestion]:
        return [
            ResearchQuestion(
                id="hmm_001",
                title="4-State HMM: Does Conditional-Worst-Regime Sharpe Stay Positive?",
                description=(
                    "Train a 4-state HMM on (VIX z-score, DXY momentum, BTC RV, "
                    "10y-2y slope). Stratify per-source-system Sharpe by inferred "
                    "regime. The Two Sigma test: if conditional Sharpe is positive "
                    "in *every* regime, the edge is real."
                ),
                hypothesis=(
                    "kimi_riseoftheclaw and stocks_competition show positive "
                    "Sharpe in all 4 regimes; multi_asset_copytrader shows "
                    "regime-dependent edge concentrated in Risk-On."
                ),
                methodology=(
                    "1) Pull 5y of macro factor daily series (FRED + yfinance).\n"
                    "2) Fit 4-state HMM with hmmlearn.\n"
                    "3) Tag each closed pick with inferred regime at emission.\n"
                    "4) Compute conditional Sharpe per (source, regime).\n"
                    "5) Wire regime gate into system_trend_detector.py."
                ),
                success_criteria={
                    "min_conditional_sharpe_for_promotion": 0.0,
                    "regime_classification_stability_pct": 80.0,
                },
                priority=2,
            )
        ]

    def prepare_data(self, question: ResearchQuestion) -> Dict[str, Any]:
        return {"status": "stub",
                "todo": "Backfill macro-factor matrix + HMM training set."}

    def conduct_experiment(self, question: ResearchQuestion,
                           data: Dict[str, Any]) -> ResearchResult:
        return ResearchResult(
            researcher_id=self.researcher_id,
            question_id=question.id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            findings="Stub seeded for Week-2 dashboard credibility. Plan Theme C.",
            metrics={},
            confidence=0.0,
            limitations=["Persona seeded; experiment not yet run."],
            recommendations={
                "wire_target": "alpha_engine/system_trend_detector.py",
                "deepens": "ml_crypto_predictor/researchers/regime_researcher.py",
            },
        )

    def validate_findings(self, result: ResearchResult) -> Dict[str, Any]:
        return {"status": "pending", "result_id": result.question_id}
