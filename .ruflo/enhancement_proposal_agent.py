"""
Enhancement Proposal Agent — auto-generates enhancement proposals when
edge is weak, missing, or concentrated.

This agent analyses edge metrics from the .ruflo orchestrator pipeline and
produces structured Markdown proposals for data, model, and risk-management
improvements. Proposals are written to ``.ruflo/proposals/`` for review.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("ruflo.proposals")


class EnhancementProposalAgent:
    """Agent that auto-generates enhancement proposals for weak edges.

    Gap → Proposal mapping
    ----------------------
    - **NO_EDGE + low trade count** → ``propose_data_enhancements``
      (more data, sentiment feeds, on-chain data)
    - **NO_EDGE + high trade count** → ``propose_model_changes``
      (new features, ensemble methods, regime detection)
    - **CONCENTRATED edge** → ``propose_risk_adjustments``
      (diversification, risk parity, asset gating)
    - **WEAK_EDGE** → ``propose_model_changes`` + ``propose_risk_adjustments``

    Proposal priority scale
    -----------------------
    P0 — Critical, implement immediately
    P1 — High, schedule within 1 week
    P2 — Medium, schedule within 1 month
    P3 — Low, backlog for next quarter
    """

    def __init__(self, output_dir: str = ".ruflo/proposals") -> None:
        """Initialize the proposal agent.

        Parameters
        ----------
        output_dir:
            Directory where proposal Markdown files are written.
        """
        self._output_dir: str = output_dir
        os.makedirs(self._output_dir, exist_ok=True)
        logger.info("EnhancementProposalAgent initialized — output_dir=%s", output_dir)

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    def analyze_edge_gaps(self, metrics: dict[str, Any]) -> list[dict[str, Any]]:
        """Identify gaps in edge metrics and classify them.

        Parameters
        ----------
        metrics:
            Expected keys: ``asset_class``, ``ev``, ``win_rate``,
            ``profit_factor``, ``trade_count``, ``max_drawdown``,
            ``concentration_hhi`` (optional).

        Returns
        -------
        list[dict]
            Gap descriptors with keys: ``type`` (NO_EDGE | WEAK_EDGE |
            CONCENTRATED), ``asset_class``, ``description``, ``triggers``.
        """
        gaps: list[dict[str, Any]] = []
        asset: str = metrics.get("asset_class", "unknown")
        ev: float | None = metrics.get("ev")
        trade_count: int = metrics.get("trade_count", 0)
        hhi: float | None = metrics.get("concentration_hhi")

        # NO_EDGE classification
        if ev is None or (ev is not None and ev < 0.002):
            gap_type = "NO_EDGE"
            if trade_count < 20:
                description = (
                    f"{asset}: No meaningful edge with only {trade_count} trades. "
                    "Likely insufficient data."
                )
                triggers = ["low_trade_count", "insufficient_ev"]
            else:
                description = (
                    f"{asset}: No edge despite {trade_count} trades. "
                    "Model may be miscalibrated or feature set inadequate."
                )
                triggers = ["high_trade_count", "insufficient_ev"]

            gaps.append({
                "type": gap_type,
                "asset_class": asset,
                "description": description,
                "triggers": triggers,
                "metrics": {
                    "ev": ev,
                    "trade_count": trade_count,
                },
            })

        # WEAK_EDGE classification
        elif ev is not None and ev < 0.01:
            gaps.append({
                "type": "WEAK_EDGE",
                "asset_class": asset,
                "description": (
                    f"{asset}: Edge exists (EV={ev:.4f}) but is weak. "
                    "Model tuning and risk management could improve Sharpe."
                ),
                "triggers": ["low_ev", "below_target_sharpe"],
                "metrics": {
                    "ev": ev,
                    "trade_count": trade_count,
                },
            })

        # CONCENTRATED classification
        if hhi is not None and hhi > 0.30:
            gaps.append({
                "type": "CONCENTRATED",
                "asset_class": asset,
                "description": (
                    f"{asset}: Portfolio over-concentrated (HHI={hhi:.3f}). "
                    "Concentration risk may amplify drawdowns."
                ),
                "triggers": ["high_hhi", "concentration_risk"],
                "metrics": {
                    "concentration_hhi": hhi,
                },
            })

        logger.info("analyze_edge_gaps found %d gap(s) for %s", len(gaps), asset)
        return gaps

    # ------------------------------------------------------------------
    # Proposal generators
    # ------------------------------------------------------------------

    def generate_proposal(self, gap: dict[str, Any]) -> dict[str, Any]:
        """Map a gap descriptor to a structured proposal.

        Parameters
        ----------
        gap:
            Output from :meth:`analyze_edge_gaps`.

        Returns
        -------
        dict
            Full proposal with ``title``, ``description``,
            ``expected_impact``, ``implementation_steps``,
            ``relevant_files``, ``priority``.
        """
        gap_type: str = gap["type"]
        asset: str = gap.get("asset_class", "unknown")

        if gap_type == "NO_EDGE" and "low_trade_count" in gap.get("triggers", []):
            return self.propose_data_enhancements(asset)
        elif gap_type == "NO_EDGE" and "high_trade_count" in gap.get("triggers", []):
            return self.propose_model_changes(asset)
        elif gap_type == "CONCENTRATED":
            return self.propose_risk_adjustments(asset)
        elif gap_type == "WEAK_EDGE":
            # Combine model + risk proposals into a single hybrid proposal
            model_prop = self.propose_model_changes(asset)
            risk_prop = self.propose_risk_adjustments(asset)
            return {
                "title": f"Hybrid Enhancement: Model + Risk for {asset}",
                "description": f"{model_prop['description']}\n\n{risk_prop['description']}",
                "expected_impact": (
                    f"Combined improvement: {model_prop['expected_impact']} "
                    f"Additionally, {risk_prop['expected_impact']}"
                ),
                "implementation_steps": (
                    model_prop["implementation_steps"]
                    + ["---"] + risk_prop["implementation_steps"]
                ),
                "relevant_files": list(
                    set(model_prop["relevant_files"] + risk_prop["relevant_files"])
                ),
                "priority": "P0" if gap["metrics"].get("ev", 0) < 0 else "P1",
                "proposal_type": "hybrid",
                "asset_class": asset,
            }

        logger.warning("Unknown gap type '%s' — returning generic proposal", gap_type)
        return {
            "title": f"Review Required: {asset}",
            "description": f"Unclassified gap for {asset}: {gap.get('description', 'N/A')}",
            "expected_impact": "TBD after investigation",
            "implementation_steps": ["1. Investigate root cause", "2. Define remediation plan"],
            "relevant_files": [".ruflo/edge_metrics.json"],
            "priority": "P2",
            "proposal_type": "generic",
            "asset_class": asset,
        }

    def propose_data_enhancements(self, asset_class: str) -> dict[str, Any]:
        """Propose new data sources and data-quality improvements.

        Parameters
        ----------
        asset_class:
            Asset class to target (e.g., ``equities``, ``crypto``).

        Returns
        -------
        dict
            Structured proposal.
        """
        return {
            "title": f"Data Enhancement: Expand Feature Set for {asset_class}",
            "description": (
                f"The {asset_class} strategy shows no edge with low trade counts, "
                "suggesting insufficient or low-signal data. This proposal adds "
                "alternative data sources to enrich the feature space."
            ),
            "expected_impact": (
                "Increase signal-to-noise ratio, improve feature coverage, "
                "and enable more robust model training."
            ),
            "implementation_steps": [
                "1. Ingest sentiment data from social-media APIs (Twitter/X, Reddit, StockTwits)",
                "2. Add on-chain metrics for crypto (wallet flows, exchange in/out, miner activity)",
                "3. Integrate macroeconomic indicators (FRED, CPI, yield curves)",
                "4. Add options-flow and unusual-volume signals",
                "5. Backfill historical data to minimum 2-year lookback",
                "6. Run feature-importance analysis to validate new signals",
            ],
            "relevant_files": [
                "data_pipeline/ingestion.py",
                "data_pipeline/features.py",
                "data_pipeline/sentiment.py",
                "config/data_sources.yaml",
            ],
            "priority": "P1",
            "proposal_type": "data",
            "asset_class": asset_class,
        }

    def propose_model_changes(self, asset_class: str) -> dict[str, Any]:
        """Propose model architecture and feature-engineering changes.

        Parameters
        ----------
        asset_class:
            Asset class to target.

        Returns
        -------
        dict
            Structured proposal.
        """
        return {
            "title": f"Model Enhancement: Architecture & Features for {asset_class}",
            "description": (
                f"The {asset_class} strategy has sufficient trades but no edge, "
                "indicating model miscalibration or an incomplete feature set. "
                "This proposal targets model architecture and regime-aware training."
            ),
            "expected_impact": (
                "Restore positive EV through better feature engineering, "
                "ensemble diversification, and regime detection."
            ),
            "implementation_steps": [
                "1. Engineer interaction features (volatility × trend, volume × momentum)",
                "2. Implement ensemble: stack LightGBM, XGBoost, and logistic regression",
                "3. Add regime-detection layer (HMM or clustering-based market-regime classifier)",
                "4. Apply walk-forward cross-validation with regime-aware splits",
                "5. Introduce online-learning loop for incremental model updates",
                "6. Evaluate with Monte-Carlo Sharpe and probabilistic backtests",
            ],
            "relevant_files": [
                "models/ensemble.py",
                "models/regime_detector.py",
                "models/feature_engineering.py",
                "backtest/walk_forward.py",
                "config/model_config.yaml",
            ],
            "priority": "P0",
            "proposal_type": "model",
            "asset_class": asset_class,
        }

    def propose_risk_adjustments(self, asset_class: str) -> dict[str, Any]:
        """Propose risk-management and portfolio-construction changes.

        Parameters
        ----------
        asset_class:
            Asset class to target.

        Returns
        -------
        dict
            Structured proposal.
        """
        return {
            "title": f"Risk Enhancement: Diversification & Position Sizing for {asset_class}",
            "description": (
                f"The {asset_class} portfolio is over-concentrated or exhibits "
                "poor risk-adjusted returns. This proposal tightens risk controls "
                "and introduces diversification mechanisms."
            ),
            "expected_impact": (
                "Reduce max drawdown by 30-50%, lower HHI below 0.20, "
                "and improve risk-adjusted Sharpe ratio."
            ),
            "implementation_steps": [
                "1. Implement risk-parity position sizing (inverse-volatility weighting)",
                "2. Add asset-class gating: halt trading when HHI > 0.25 or MDD > 15%",
                "3. Introduce correlation-based diversification filters",
                "4. Deploy dynamic Kelly scaling with fractional constraints (0.25× Kelly)",
                "5. Add daily risk-budget enforcement in the execution layer",
                "6. Backtest with stress scenarios (flash crash, correlation spike)",
            ],
            "relevant_files": [
                "risk/position_sizer.py",
                "risk/risk_parity.py",
                "risk/asset_gating.py",
                "execution/risk_budget.py",
                "config/risk_limits.yaml",
            ],
            "priority": "P1",
            "proposal_type": "risk",
            "asset_class": asset_class,
        }

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def write_proposal_markdown(self, proposal: dict[str, Any]) -> str:
        """Write a proposal dict to a Markdown file.

        Parameters
        ----------
        proposal:
            Output from :meth:`generate_proposal` or the individual
            ``propose_*`` methods.

        Returns
        -------
        str
            Absolute path to the written file.
        """
        asset: str = proposal.get("asset_class", "unknown")
        prop_type: str = proposal.get("proposal_type", "generic")
        date_stamp = datetime.now(timezone.utc).strftime("%Y_%m_%d")
        filename = f"PROPOSAL_{date_stamp}_{asset}_{prop_type}.md"
        filepath = os.path.join(self._output_dir, filename)

        # Avoid collisions
        counter = 1
        base = filepath
        while os.path.exists(filepath):
            filename = f"PROPOSAL_{date_stamp}_{asset}_{prop_type}_{counter}.md"
            filepath = os.path.join(self._output_dir, filename)
            counter += 1

        lines: list[str] = [
            f"# {proposal['title']}",
            "",
            f"**Priority:** {proposal['priority']}  ",
            f"**Asset Class:** {asset}  ",
            f"**Type:** {prop_type}  ",
            f"**Generated:** {datetime.now(timezone.utc).isoformat()}  ",
            "",
            "## Description",
            "",
            proposal["description"],
            "",
            "## Expected Impact",
            "",
            proposal["expected_impact"],
            "",
            "## Implementation Steps",
            "",
        ]

        for step in proposal["implementation_steps"]:
            if step == "---":
                lines.append("")
            else:
                lines.append(f"- {step}")

        lines.extend([
            "",
            "## Relevant Files",
            "",
        ])
        for f in proposal["relevant_files"]:
            lines.append(f"- `{f}`")

        lines.append("")

        content = "\n".join(lines)
        with open(filepath, "w", encoding="utf-8") as fh:
            fh.write(content)

        logger.info("Proposal written to %s", filepath)
        return os.path.abspath(filepath)

    # ------------------------------------------------------------------
    # Full analysis orchestrator
    # ------------------------------------------------------------------

    def run_full_analysis(self, metrics_list: list[dict[str, Any]] | None = None) -> list[str]:
        """Run the complete gap-analysis → proposal → write pipeline.

        Parameters
        ----------
        metrics_list:
            List of metric bundles (one per asset class). If *None*,
            the agent attempts to load from the default metrics path.

        Returns
        -------
        list[str]
            Absolute paths to all generated proposal files.
        """
        paths: list[str] = []

        if metrics_list is None:
            metrics_list = self._load_default_metrics()

        for metrics in metrics_list:
            gaps = self.analyze_edge_gaps(metrics)
            for gap in gaps:
                proposal = self.generate_proposal(gap)
                path = self.write_proposal_markdown(proposal)
                paths.append(path)

        logger.info("run_full_analysis complete — %d proposal(s) generated", len(paths))
        return paths

    @staticmethod
    def _load_default_metrics() -> list[dict[str, Any]]:
        """Load metrics from the default metrics JSON if available.

        Returns
        -------
        list[dict]
            Empty list if the file is not found.
        """
        import json
        default_path = ".ruflo/edge_metrics.json"
        if not os.path.exists(default_path):
            logger.debug("Default metrics file not found at %s", default_path)
            return []
        with open(default_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, list) else [data]
