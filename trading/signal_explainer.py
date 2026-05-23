#!/usr/bin/env python3
"""
Signal Explainer — SHAP-like Per-Trade Attribution
====================================================

Provides per-feature attribution for MetaModelScorer decisions,
explaining WHY a trade was accepted or rejected.

For the current weighted-score model (pre-XGBoost) it computes
marginal contribution of each feature to the final score, ranks
by absolute impact, and identifies which gate(s) caused rejection.

When the `shap` package is installed and an XGBoost model is
supplied, `explain_with_shap()` delegates to SHAP TreeExplainer
and falls back transparently to the weighted-attribution path.

Usage:
    from trading.signal_explainer import SignalExplainer
    from trading.institutional_overlay import MetaModelInput, MetaModelScorer

    scorer = MetaModelScorer()
    explainer = SignalExplainer(scorer)

    inp = MetaModelInput(
        strategy_confidence=0.72,
        win_rate=0.61,
        sharpe=2.1,
        risk_reward=2.4,
        regime="TRENDING_UP",
        regime_confidence=0.80,
        vol_ratio=1.3,
        momentum_24h=0.04,
        bayesian_prob_above_50=0.88,
        regime_affinity=0.82,
        drawdown_pct=0.03,
        trades_count=42,
    )
    score = scorer.score(inp)
    explanation = explainer.explain_signal(inp, score)
    card = explainer.generate_trade_card({"symbol": "BTCUSDT", ...}, explanation)
"""

from __future__ import annotations

import math
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

try:
    import shap as _shap
    _SHAP_AVAILABLE = True
except ImportError:
    _SHAP_AVAILABLE = False

from trading.institutional_overlay import MetaModelInput, MetaModelScorer


# ── Impact label thresholds ────────────────────────────────────────────

def _impact_label(contribution: float, weight: float) -> str:
    """
    Classify the qualitative impact of a feature's contribution.

    Thresholds are relative to the feature weight so that a small
    absolute contribution on a high-weight feature is still meaningful.
    """
    ratio = contribution / weight if weight > 0 else 0.0
    if contribution >= weight * 0.85:
        return "strong_positive"
    if contribution >= weight * 0.55:
        return "positive"
    if contribution >= weight * 0.35:
        return "neutral_positive"
    if contribution >= weight * 0.10:
        return "neutral_negative"
    if contribution >= 0:
        return "weak_negative"
    return "strong_negative"


# ── Feature extraction (mirrors MetaModelScorer.score exactly) ────────

def _extract_features(inp: MetaModelInput) -> Dict[str, float]:
    """
    Reconstruct the named feature vector exactly as MetaModelScorer.score()
    builds it internally.  Must stay in sync with that method.
    """
    features: Dict[str, float] = {}

    features["bayesian_prob_above_50"] = inp.bayesian_prob_above_50
    features["regime_affinity"] = inp.regime_affinity
    features["sharpe_normalized"] = (
        min(inp.sharpe / 3.0, 1.0) if inp.sharpe > 0 else 0.0
    )
    features["risk_reward_normalized"] = (
        min(inp.risk_reward / 4.0, 1.0) if inp.risk_reward > 0 else 0.0
    )
    features["strategy_confidence"] = inp.strategy_confidence
    features["win_rate"] = inp.win_rate

    if inp.vol_ratio > 2.0:
        features["vol_ratio_penalty"] = max(0.0, 1.0 - (inp.vol_ratio - 2.0) / 3.0)
    else:
        features["vol_ratio_penalty"] = 1.0

    if inp.drawdown_pct > 0.05:
        features["drawdown_penalty"] = max(
            0.0, 1.0 - (inp.drawdown_pct - 0.05) / 0.10
        )
    else:
        features["drawdown_penalty"] = 1.0

    if inp.trades_count >= 50:
        features["sample_size_bonus"] = 1.0
    elif inp.trades_count >= 30:
        features["sample_size_bonus"] = 0.8
    elif inp.trades_count >= 15:
        features["sample_size_bonus"] = 0.6
    else:
        features["sample_size_bonus"] = 0.3

    return features


# ── Human-readable feature descriptions ───────────────────────────────

_FEATURE_DESCRIPTIONS: Dict[str, str] = {
    "bayesian_prob_above_50": "Bayesian P(WR > 50%) posterior",
    "regime_affinity": "Strategy/regime alignment score",
    "sharpe_normalized": "Sharpe ratio (normalised to [0,1])",
    "risk_reward_normalized": "Risk/reward ratio (normalised to [0,1])",
    "strategy_confidence": "Raw strategy confidence signal",
    "win_rate": "Empirical win rate",
    "vol_ratio_penalty": "Volatility spike penalty (1.0 = no penalty)",
    "drawdown_penalty": "Drawdown penalty (1.0 = no penalty)",
    "sample_size_bonus": "Sample-size credibility bonus",
}


# ── Gate definitions (mirrors MetaModelScorer.should_trade) ───────────

_GATES: List[Dict[str, Any]] = [
    {
        "name": "meta_score_threshold",
        "description": "Meta-model score must exceed minimum threshold",
        "check": lambda score, rr, threshold: score >= threshold,
        "shortfall": lambda score, rr, threshold: threshold - score,
        "details": lambda score, rr, threshold: (
            f"score={score:.4f} vs threshold={threshold:.4f}"
        ),
    },
    {
        "name": "min_risk_reward",
        "description": "Risk/reward ratio must be >= 1.5",
        "check": lambda score, rr, threshold: rr >= MetaModelScorer.MIN_RR,
        "shortfall": lambda score, rr, threshold: MetaModelScorer.MIN_RR - rr,
        "details": lambda score, rr, threshold: (
            f"rr={rr:.2f} vs min_rr={MetaModelScorer.MIN_RR}"
        ),
    },
]


# ── Core explainer ────────────────────────────────────────────────────

class SignalExplainer:
    """
    SHAP-like attribution for MetaModelScorer signal decisions.

    Computes per-feature marginal contributions to the final weighted
    score, identifies gate failures, and surfaces the primary reasons
    a trade was accepted or rejected.
    """

    def __init__(self, scorer: Optional[MetaModelScorer] = None) -> None:
        self.scorer = scorer or MetaModelScorer()
        self._weights: Dict[str, float] = dict(self.scorer.FEATURE_WEIGHTS)

    # ── Public API ─────────────────────────────────────────────────────

    def explain_signal(
        self,
        meta_model_input: MetaModelInput,
        meta_score: float,
        threshold: float = 0.65,
    ) -> Dict[str, Any]:
        """
        Compute per-feature attribution for a single signal.

        Parameters
        ----------
        meta_model_input : MetaModelInput
            The feature vector passed to MetaModelScorer.score().
        meta_score : float
            The score returned by MetaModelScorer.score().
        threshold : float
            Acceptance threshold (default matches MetaModelScorer.MIN_META_SCORE).

        Returns
        -------
        dict matching the documented explanation schema.
        """
        features = _extract_features(meta_model_input)
        contributions = self._compute_contributions(features)
        ranked = sorted(contributions, key=lambda c: abs(c["contribution"]), reverse=True)

        positive = [c for c in ranked if c["contribution"] > 0]
        negative = [c for c in ranked if c["contribution"] <= 0]

        top_positive = positive[0]["feature"] if positive else None
        top_negative = negative[0]["feature"] if negative else None

        decision = "ACCEPT" if meta_score >= threshold else "REJECT"
        margin = round(meta_score - threshold, 6)

        # Verify our reconstruction matches the actual score within tolerance
        reconstructed = sum(c["contribution"] for c in contributions)
        reconstruction_error = abs(reconstructed - meta_score)

        return {
            "symbol": getattr(meta_model_input, "symbol", "UNKNOWN"),
            "strategy": getattr(meta_model_input, "strategy", "UNKNOWN"),
            "meta_score": meta_score,
            "threshold": threshold,
            "decision": decision,
            "margin": margin,
            "feature_contributions": ranked,
            "top_positive": top_positive,
            "top_negative": top_negative,
            "gate_failures": [],
            "reconstruction_error": round(reconstruction_error, 8),
            "regime": meta_model_input.regime,
            "trades_count": meta_model_input.trades_count,
            "explained_at": datetime.now(timezone.utc).isoformat(),
        }

    def explain_rejection(
        self,
        meta_model_input: MetaModelInput,
        meta_score: float,
        gates_result: Optional[Dict[str, Any]] = None,
        threshold: float = 0.65,
    ) -> Dict[str, Any]:
        """
        Explain WHY a signal was rejected: which gate failed and by how much.

        Parameters
        ----------
        meta_model_input : MetaModelInput
        meta_score : float
        gates_result : dict, optional
            Pre-computed gate evaluation.  If None, gates are evaluated here.
        threshold : float
            Score threshold for acceptance.

        Returns
        -------
        dict with base explanation enriched by gate_failures and
        required_improvements.
        """
        explanation = self.explain_signal(meta_model_input, meta_score, threshold)

        rr = meta_model_input.risk_reward
        gate_failures: List[Dict[str, Any]] = []

        for gate in _GATES:
            passed = gate["check"](meta_score, rr, threshold)
            if not passed:
                shortfall = gate["shortfall"](meta_score, rr, threshold)
                gate_failures.append(
                    {
                        "gate": gate["name"],
                        "description": gate["description"],
                        "shortfall": round(shortfall, 6),
                        "details": gate["details"](meta_score, rr, threshold),
                    }
                )

        explanation["gate_failures"] = gate_failures
        explanation["decision"] = "REJECT"

        # What it would take to flip each failing gate
        required_improvements: List[Dict[str, Any]] = []
        if gate_failures:
            features = _extract_features(meta_model_input)
            contributions = self._compute_contributions(features)
            ranked_by_weight = sorted(
                contributions, key=lambda c: c["weight"], reverse=True
            )
            score_gap = max(0.0, threshold - meta_score)

            if score_gap > 0:
                for fc in ranked_by_weight:
                    feat = fc["feature"]
                    current_val = fc["value"]
                    weight = fc["weight"]
                    if weight <= 0:
                        continue
                    max_possible_gain = (1.0 - current_val) * weight
                    if max_possible_gain >= score_gap:
                        required_delta = score_gap / weight
                        required_improvements.append(
                            {
                                "feature": feat,
                                "description": _FEATURE_DESCRIPTIONS.get(feat, feat),
                                "current_value": round(current_val, 6),
                                "required_value": round(
                                    min(1.0, current_val + required_delta), 6
                                ),
                                "delta_needed": round(required_delta, 6),
                                "would_close_gap": True,
                            }
                        )
                    else:
                        required_improvements.append(
                            {
                                "feature": feat,
                                "description": _FEATURE_DESCRIPTIONS.get(feat, feat),
                                "current_value": round(current_val, 6),
                                "required_value": 1.0,
                                "delta_needed": round(1.0 - current_val, 6),
                                "max_possible_gain": round(max_possible_gain, 6),
                                "would_close_gap": False,
                            }
                        )

        explanation["required_improvements"] = required_improvements
        return explanation

    def generate_trade_card(
        self,
        signal_dict: Dict[str, Any],
        explanation: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Build a structured dict suitable for a Discord embed or dashboard tile.

        Parameters
        ----------
        signal_dict : dict
            Raw signal data (symbol, entry, target, stop, strategy, etc.)
        explanation : dict
            Output of explain_signal() or explain_rejection().

        Returns
        -------
        dict with keys: header, score_summary, top_factors, gate_status,
        signal_details, metadata.
        """
        meta_score = explanation.get("meta_score", 0.0)
        threshold = explanation.get("threshold", 0.65)
        decision = explanation.get("decision", "UNKNOWN")
        margin = explanation.get("margin", 0.0)

        score_pct = int(round(meta_score * 100))
        threshold_pct = int(round(threshold * 100))

        # Emoji/indicator for score level (plain ascii variants for environments
        # that strip unicode)
        if meta_score >= 0.80:
            score_tier = "STRONG"
        elif meta_score >= threshold:
            score_tier = "PASS"
        elif meta_score >= threshold - 0.05:
            score_tier = "BORDERLINE"
        else:
            score_tier = "FAIL"

        # Top 3 positive and top 1 negative factors
        feature_contributions = explanation.get("feature_contributions", [])
        top_positive_factors = [
            {
                "feature": fc["feature"],
                "description": _FEATURE_DESCRIPTIONS.get(fc["feature"], fc["feature"]),
                "value": fc["value"],
                "contribution": fc["contribution"],
                "impact": fc["impact"],
            }
            for fc in feature_contributions
            if fc["contribution"] > 0
        ][:3]

        top_negative_factors = [
            {
                "feature": fc["feature"],
                "description": _FEATURE_DESCRIPTIONS.get(fc["feature"], fc["feature"]),
                "value": fc["value"],
                "contribution": fc["contribution"],
                "impact": fc["impact"],
            }
            for fc in feature_contributions
            if fc["contribution"] <= 0
        ][:2]

        gate_failures = explanation.get("gate_failures", [])
        gate_status = "ALL_PASS" if not gate_failures else "FAILED"

        symbol = signal_dict.get("symbol", explanation.get("symbol", "UNKNOWN"))
        strategy = signal_dict.get("strategy", explanation.get("strategy", "UNKNOWN"))

        return {
            "header": {
                "symbol": symbol,
                "strategy": strategy,
                "decision": decision,
                "score_tier": score_tier,
            },
            "score_summary": {
                "meta_score": meta_score,
                "meta_score_pct": score_pct,
                "threshold": threshold,
                "threshold_pct": threshold_pct,
                "margin": margin,
                "margin_pct": int(round(margin * 100)),
                "regime": explanation.get("regime", "UNKNOWN"),
                "trades_count": explanation.get("trades_count", 0),
            },
            "top_factors": {
                "positive": top_positive_factors,
                "negative": top_negative_factors,
                "top_positive_label": explanation.get("top_positive"),
                "top_negative_label": explanation.get("top_negative"),
            },
            "gate_status": {
                "status": gate_status,
                "failures": gate_failures,
                "required_improvements": explanation.get("required_improvements", []),
            },
            "signal_details": {
                "entry": signal_dict.get("entry") or signal_dict.get("entryPrice"),
                "target": signal_dict.get("target") or signal_dict.get("targetPrice"),
                "stop": signal_dict.get("stop") or signal_dict.get("stopPrice"),
                "risk_reward": signal_dict.get("risk_reward") or signal_dict.get("rr"),
                "side": signal_dict.get("side") or signal_dict.get("signal", "LONG"),
                "timeframe": signal_dict.get("timeframe"),
            },
            "metadata": {
                "explained_at": explanation.get("explained_at"),
                "reconstruction_error": explanation.get("reconstruction_error", 0.0),
                "shap_method": explanation.get("shap_method", "weighted_attribution"),
            },
        }

    def batch_explain(
        self,
        signals_list: List[Dict[str, Any]],
        threshold: float = 0.65,
    ) -> Dict[str, Any]:
        """
        Explain multiple signals and return per-signal explanations plus
        aggregate summary statistics.

        Each element of signals_list must be a dict with keys:
            - "meta_model_input": MetaModelInput instance
            - "meta_score": float
            - "signal_dict": dict (optional, for trade card)
            - "rejected": bool (optional, triggers explain_rejection path)

        Returns
        -------
        dict with keys: explanations, summary.
        """
        explanations: List[Dict[str, Any]] = []

        for item in signals_list:
            inp: MetaModelInput = item["meta_model_input"]
            score: float = item["meta_score"]
            rejected: bool = item.get("rejected", score < threshold)
            sig_dict: Dict[str, Any] = item.get("signal_dict", {})

            if rejected:
                exp = self.explain_rejection(inp, score, threshold=threshold)
            else:
                exp = self.explain_signal(inp, score, threshold=threshold)

            if sig_dict:
                exp["trade_card"] = self.generate_trade_card(sig_dict, exp)

            explanations.append(exp)

        summary = self._build_batch_summary(explanations, threshold)

        return {
            "explanations": explanations,
            "summary": summary,
        }

    def get_feature_importance_summary(
        self,
        explanations_list: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Aggregate feature importances across a collection of explanations.

        Parameters
        ----------
        explanations_list : list
            Output explanations from explain_signal() / explain_rejection() /
            batch_explain()["explanations"].

        Returns
        -------
        dict with per-feature aggregated stats and a ranked importance list.
        """
        if not explanations_list:
            return {"features": {}, "ranked": [], "n_signals": 0}

        # Flatten batch results if needed
        flat: List[Dict[str, Any]] = []
        for item in explanations_list:
            if "explanations" in item:
                flat.extend(item["explanations"])
            else:
                flat.append(item)

        agg: Dict[str, Dict[str, Any]] = {}

        for exp in flat:
            for fc in exp.get("feature_contributions", []):
                feat = fc["feature"]
                if feat not in agg:
                    agg[feat] = {
                        "total_contribution": 0.0,
                        "abs_contribution": 0.0,
                        "positive_count": 0,
                        "negative_count": 0,
                        "count": 0,
                        "weight": fc["weight"],
                        "description": _FEATURE_DESCRIPTIONS.get(feat, feat),
                    }
                a = agg[feat]
                a["total_contribution"] += fc["contribution"]
                a["abs_contribution"] += abs(fc["contribution"])
                a["count"] += 1
                if fc["contribution"] > 0:
                    a["positive_count"] += 1
                else:
                    a["negative_count"] += 1

        # Compute averages and positivity rate
        for feat, a in agg.items():
            n = a["count"]
            if n > 0:
                a["avg_contribution"] = round(a["total_contribution"] / n, 6)
                a["avg_abs_contribution"] = round(a["abs_contribution"] / n, 6)
                a["positivity_rate"] = round(a["positive_count"] / n, 4)
            else:
                a["avg_contribution"] = 0.0
                a["avg_abs_contribution"] = 0.0
                a["positivity_rate"] = 0.0

        ranked = sorted(
            [
                {
                    "rank": 0,  # filled below
                    "feature": feat,
                    "description": a["description"],
                    "weight": a["weight"],
                    "avg_contribution": a["avg_contribution"],
                    "avg_abs_contribution": a["avg_abs_contribution"],
                    "positivity_rate": a["positivity_rate"],
                    "n_signals": a["count"],
                }
                for feat, a in agg.items()
            ],
            key=lambda x: x["avg_abs_contribution"],
            reverse=True,
        )
        for i, entry in enumerate(ranked, start=1):
            entry["rank"] = i

        return {
            "features": agg,
            "ranked": ranked,
            "n_signals": len(flat),
        }

    # ── SHAP bridge (future XGBoost) ───────────────────────────────────

    def explain_with_shap(
        self,
        model: Any,
        meta_model_input: MetaModelInput,
        meta_score: float,
        threshold: float = 0.65,
    ) -> Dict[str, Any]:
        """
        Use SHAP TreeExplainer if the `shap` package is installed and a
        trained model is supplied.  Falls back to weighted attribution if
        shap is unavailable or if the model is None.

        Parameters
        ----------
        model : XGBoost / sklearn model or None
            Trained estimator.  If None, falls back to weighted attribution.
        meta_model_input : MetaModelInput
        meta_score : float
        threshold : float

        Returns
        -------
        Explanation dict (same schema as explain_signal), with
        ``shap_method`` set to ``"shap_tree"`` or ``"weighted_attribution"``.
        """
        features = _extract_features(meta_model_input)

        if _SHAP_AVAILABLE and model is not None:
            try:
                feature_names = list(self._weights.keys())
                feature_values = [features.get(k, 0.0) for k in feature_names]

                explainer_shap = _shap.TreeExplainer(model)
                shap_values = explainer_shap.shap_values(
                    [feature_values]
                )

                # shap_values may be list (multi-class) or array
                if isinstance(shap_values, list):
                    sv = shap_values[1][0] if len(shap_values) > 1 else shap_values[0][0]
                else:
                    sv = shap_values[0]

                contributions = []
                for idx, feat in enumerate(feature_names):
                    shap_contrib = float(sv[idx]) if idx < len(sv) else 0.0
                    val = features.get(feat, 0.0)
                    weight = self._weights.get(feat, 0.0)
                    contributions.append(
                        {
                            "feature": feat,
                            "description": _FEATURE_DESCRIPTIONS.get(feat, feat),
                            "value": round(val, 6),
                            "weight": round(weight, 6),
                            "contribution": round(shap_contrib, 6),
                            "impact": _impact_label(shap_contrib, weight),
                        }
                    )

                ranked = sorted(
                    contributions, key=lambda c: abs(c["contribution"]), reverse=True
                )
                positive = [c for c in ranked if c["contribution"] > 0]
                negative = [c for c in ranked if c["contribution"] <= 0]
                decision = "ACCEPT" if meta_score >= threshold else "REJECT"
                margin = round(meta_score - threshold, 6)

                return {
                    "symbol": getattr(meta_model_input, "symbol", "UNKNOWN"),
                    "strategy": getattr(meta_model_input, "strategy", "UNKNOWN"),
                    "meta_score": meta_score,
                    "threshold": threshold,
                    "decision": decision,
                    "margin": margin,
                    "feature_contributions": ranked,
                    "top_positive": positive[0]["feature"] if positive else None,
                    "top_negative": negative[0]["feature"] if negative else None,
                    "gate_failures": [],
                    "reconstruction_error": 0.0,
                    "regime": meta_model_input.regime,
                    "trades_count": meta_model_input.trades_count,
                    "explained_at": datetime.now(timezone.utc).isoformat(),
                    "shap_method": "shap_tree",
                }

            except Exception:
                # Any SHAP failure: fall back silently to weighted method
                pass

        # Fallback to weighted attribution
        result = self.explain_signal(meta_model_input, meta_score, threshold)
        result["shap_method"] = "weighted_attribution"
        return result

    # ── Internal helpers ────────────────────────────────────────────────

    def _compute_contributions(
        self, features: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """
        Compute each feature's marginal contribution to the total score.

        contribution_i = feature_value_i * weight_i

        This is the exact decomposition of MetaModelScorer's weighted sum,
        so contributions always sum to meta_score (within floating-point
        precision).
        """
        contributions = []
        for feat, weight in self._weights.items():
            val = features.get(feat, 0.0)
            contrib = val * weight
            contributions.append(
                {
                    "feature": feat,
                    "description": _FEATURE_DESCRIPTIONS.get(feat, feat),
                    "value": round(val, 6),
                    "weight": round(weight, 6),
                    "contribution": round(contrib, 6),
                    "impact": _impact_label(contrib, weight),
                }
            )
        return contributions

    def _build_batch_summary(
        self,
        explanations: List[Dict[str, Any]],
        threshold: float,
    ) -> Dict[str, Any]:
        """Build aggregate statistics from a list of explanations."""
        if not explanations:
            return {
                "n_total": 0,
                "n_accepted": 0,
                "n_rejected": 0,
                "accept_rate": 0.0,
                "avg_meta_score": 0.0,
                "avg_margin": 0.0,
                "most_common_top_positive": None,
                "most_common_top_negative": None,
                "most_common_gate_failure": None,
            }

        n = len(explanations)
        accepted = [e for e in explanations if e.get("decision") == "ACCEPT"]
        rejected = [e for e in explanations if e.get("decision") == "REJECT"]

        scores = [e["meta_score"] for e in explanations if "meta_score" in e]
        margins = [e["margin"] for e in explanations if "margin" in e]
        avg_score = sum(scores) / len(scores) if scores else 0.0
        avg_margin = sum(margins) / len(margins) if margins else 0.0

        top_pos_counter: Dict[str, int] = {}
        top_neg_counter: Dict[str, int] = {}
        gate_fail_counter: Dict[str, int] = {}

        for exp in explanations:
            tp = exp.get("top_positive")
            if tp:
                top_pos_counter[tp] = top_pos_counter.get(tp, 0) + 1
            tn = exp.get("top_negative")
            if tn:
                top_neg_counter[tn] = top_neg_counter.get(tn, 0) + 1
            for gf in exp.get("gate_failures", []):
                name = gf.get("gate", "unknown")
                gate_fail_counter[name] = gate_fail_counter.get(name, 0) + 1

        most_common_top_pos = (
            max(top_pos_counter, key=top_pos_counter.get) if top_pos_counter else None
        )
        most_common_top_neg = (
            max(top_neg_counter, key=top_neg_counter.get) if top_neg_counter else None
        )
        most_common_gate = (
            max(gate_fail_counter, key=gate_fail_counter.get)
            if gate_fail_counter
            else None
        )

        return {
            "n_total": n,
            "n_accepted": len(accepted),
            "n_rejected": len(rejected),
            "accept_rate": round(len(accepted) / n, 4),
            "avg_meta_score": round(avg_score, 4),
            "avg_margin": round(avg_margin, 4),
            "most_common_top_positive": most_common_top_pos,
            "most_common_top_negative": most_common_top_neg,
            "most_common_gate_failure": most_common_gate,
            "top_positive_counts": top_pos_counter,
            "top_negative_counts": top_neg_counter,
            "gate_failure_counts": gate_fail_counter,
        }
