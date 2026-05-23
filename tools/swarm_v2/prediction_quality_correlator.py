from __future__ import annotations

"""
Prediction Quality Correlator

Correlates static code-quality metrics (function length, cyclomatic complexity,
import count, test coverage) with prediction-performance metrics (win rate,
profit factor, Sharpe ratio) to identify which code modules most strongly
influence prediction outcomes.
"""

import logging
import math
from typing import Any

logger: logging.Logger = logging.getLogger("swarm_v2.quality")


# ---------------------------------------------------------------------------
# Spearman rank correlation (manual — no scipy)
# ---------------------------------------------------------------------------

def _rank_data(values: list[float]) -> list[float]:
    """
    Return the fractional (averaged) rank of each value.

    Example
    -------
    >>> _rank_data([10, 20, 20, 30])
    [1.0, 2.5, 2.5, 4.0]
    """
    indexed = sorted(enumerate(values), key=lambda x: x[1])
    ranks: list[float] = [0.0] * len(values)
    i = 0
    while i < len(indexed):
        j = i
        # Find the run of equal values
        while j + 1 < len(indexed) and indexed[j + 1][1] == indexed[i][1]:
            j += 1
        # Average rank for this run (1-based)
        avg_rank = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            original_index = indexed[k][0]
            ranks[original_index] = avg_rank
        i = j + 1
    return ranks


def spearman_rank_correlation(x: list[float], y: list[float]) -> float:
    """
    Compute Spearman's rank correlation coefficient between *x* and *y*.

    Parameters
    ----------
    x, y:
        Equal-length sequences of numeric values.

    Returns
    -------
    float
        Correlation coefficient in the range ``[-1, 1]``.
        Returns ``0.0`` if the inputs are too short or have zero variance.
    """
    if len(x) != len(y) or len(x) < 3:
        return 0.0

    rank_x = _rank_data(x)
    rank_y = _rank_data(y)

    n = len(x)
    mean_rx = sum(rank_x) / n
    mean_ry = sum(rank_y) / n

    num = sum((rx - mean_rx) * (ry - mean_ry) for rx, ry in zip(rank_x, rank_y))
    den_x = sum((rx - mean_rx) ** 2 for rx in rank_x)
    den_y = sum((ry - mean_ry) ** 2 for ry in rank_y)

    if den_x == 0.0 or den_y == 0.0:
        return 0.0

    return num / math.sqrt(den_x * den_y)


# ---------------------------------------------------------------------------
# PredictionQualityCorrelator
# ---------------------------------------------------------------------------


class PredictionQualityCorrelator:
    """
    Correlate code-quality metrics with prediction-performance metrics.

    Parameters
    ----------
    repo_metrics:
        Output of :meth:`RepoAnalyzerSwarm.analyze_code_quality`.
        Must contain a ``per_module`` dict mapping module paths to their
        quality metrics.
    prediction_metrics:
        Dict mapping module paths to prediction-performance dicts.
        Each inner dict may contain ``win_rate``, ``profit_factor``,
        ``sharpe_ratio``, ``total_predictions``, and ``net_pnl``.
    """

    def __init__(self, repo_metrics: dict, prediction_metrics: dict) -> None:
        self.repo_metrics: dict = repo_metrics
        self.prediction_metrics: dict = prediction_metrics
        self.per_module: dict[str, dict[str, Any]] = repo_metrics.get(
            "per_module", {}
        )
        logger.info(
            "PredictionQualityCorrelator initialised: %d repo modules, %d prediction modules",
            len(self.per_module),
            len(self.prediction_metrics),
        )

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #

    def correlate_complexity_with_accuracy(self) -> dict[str, float]:
        """
        Compute Spearman rank correlation between module-level code metrics
        and prediction win rate.

        Returns
        -------
        dict
            Keys: ``complexity_vs_winrate``, ``function_length_vs_winrate``,
            ``import_count_vs_winrate``, ``coverage_vs_winrate``.
        """
        logger.info("Correlating complexity with accuracy …")

        modules = self._aligned_modules()
        if not modules:
            return {
                "complexity_vs_winrate": 0.0,
                "function_length_vs_winrate": 0.0,
                "import_count_vs_winrate": 0.0,
                "coverage_vs_winrate": 0.0,
            }

        complexity = [m["complexity"] for m in modules]
        fn_length = [m["function_length"] for m in modules]
        imports = [m["import_count"] for m in modules]
        coverage = [m["coverage"] for m in modules]
        winrate = [m["winrate"] for m in modules]

        result = {
            "complexity_vs_winrate": spearman_rank_correlation(complexity, winrate),
            "function_length_vs_winrate": spearman_rank_correlation(
                fn_length, winrate
            ),
            "import_count_vs_winrate": spearman_rank_correlation(imports, winrate),
            "coverage_vs_winrate": spearman_rank_correlation(coverage, winrate),
        }

        logger.info("Correlation results: %s", result)
        return result

    def identify_problem_modules(self) -> list[dict[str, Any]]:
        """
        Identify modules with high complexity **and** poor prediction outcomes.

        A module is flagged when:
        - cyclomatic complexity > 75th percentile, **and**
        - win rate < 50 %.

        Returns
        -------
        list[dict]
            Each dict contains ``module``, ``complexity``, ``win_rate``,
            ``profit_factor``, ``flag_reason``.
        """
        logger.info("Identifying problem modules …")
        modules = self._aligned_modules()
        if not modules:
            return []

        # Compute 75th percentile complexity
        complexities = sorted(m["complexity"] for m in modules)
        idx_75 = int(len(complexities) * 0.75)
        threshold = complexities[min(idx_75, len(complexities) - 1)]

        problems: list[dict[str, Any]] = []
        for m in modules:
            reasons: list[str] = []
            if m["complexity"] >= threshold and m["winrate"] < 0.50:
                reasons.append(
                    f"High complexity ({m['complexity']:.1f}) + low WR ({m['winrate']:.2%})"
                )
            if m["function_length"] > 30 and m["winrate"] < 0.50:
                reasons.append(
                    f"Long functions ({m['function_length']:.1f} lines) + low WR"
                )
            if reasons:
                problems.append(
                    {
                        "module": m["module"],
                        "complexity": round(m["complexity"], 2),
                        "win_rate": round(m["winrate"], 4),
                        "profit_factor": round(m.get("profit_factor", 0.0), 2),
                        "flag_reason": "; ".join(reasons),
                    }
                )

        logger.info("Found %d problem modules", len(problems))
        return sorted(problems, key=lambda x: x["complexity"], reverse=True)

    def rank_modules_by_contribution(self) -> list[dict[str, Any]]:
        """
        Rank modules by their apparent contribution to winning predictions.

        The composite score is a weighted sum of normalised win rate,
        profit factor, and inverse complexity (simpler code that wins ranks
        higher).

        Returns
        -------
        list[dict]
            Sorted descending by ``composite_score``.
        """
        logger.info("Ranking modules by contribution …")
        modules = self._aligned_modules()
        if not modules:
            return []

        max_wr = max(m["winrate"] for m in modules) or 1.0
        max_pf = max(m.get("profit_factor", 0.0) for m in modules) or 1.0
        max_cx = max(m["complexity"] for m in modules) or 1.0

        ranked: list[dict[str, Any]] = []
        for m in modules:
            wr_norm = m["winrate"] / max_wr
            pf_norm = m.get("profit_factor", 0.0) / max_pf
            # Inverse complexity: lower complexity is better
            cx_norm = 1.0 - (m["complexity"] / max_cx) if max_cx else 0.0
            score = 0.45 * wr_norm + 0.35 * pf_norm + 0.20 * cx_norm
            ranked.append(
                {
                    "module": m["module"],
                    "composite_score": round(score, 4),
                    "win_rate": round(m["winrate"], 4),
                    "profit_factor": round(m.get("profit_factor", 0.0), 2),
                    "complexity": round(m["complexity"], 2),
                    "total_predictions": m.get("total_predictions", 0),
                }
            )

        ranked.sort(key=lambda x: x["composite_score"], reverse=True)
        logger.info("Ranked %d modules by contribution", len(ranked))
        return ranked

    def recommend_refactoring(self) -> list[dict[str, Any]]:
        """
        Generate specific refactoring recommendations for problem modules.

        Returns
        -------
        list[dict]
            Each dict has ``module``, ``issues`` (list), ``recommendations``
            (list), and ``priority`` (``high`` | ``medium`` | ``low``).
        """
        logger.info("Generating refactoring recommendations …")
        problems = self.identify_problem_modules()
        recommendations: list[dict[str, Any]] = []

        for prob in problems:
            issues: list[str] = []
            recs: list[str] = []

            if prob["complexity"] > 20:
                issues.append(
                    f"Cyclomatic complexity is {prob['complexity']}, which is very high"
                )
                recs.append(
                    "Extract helper functions to reduce branching; aim for <10 per function"
                )
                recs.append("Consider strategy-pattern decomposition for conditional logic")

            if prob.get("function_length", 0) > 30:
                issues.append("Average function length exceeds 30 lines")
                recs.append("Split large functions into smaller, testable units")

            if prob["win_rate"] < 0.40:
                issues.append(f"Win rate is only {prob['win_rate']:.1%}")
                recs.append("Add unit tests around edge-case logic paths")
                recs.append("Review feature-engineering assumptions in this module")

            priority = (
                "high"
                if prob["complexity"] > 30 or prob["win_rate"] < 0.35
                else "medium"
            )

            recommendations.append(
                {
                    "module": prob["module"],
                    "issues": issues,
                    "recommendations": recs,
                    "priority": priority,
                }
            )

        logger.info("Generated %d refactoring recommendations", len(recommendations))
        return recommendations

    def generate_correlation_report(self) -> str:
        """
        Produce a Markdown report summarising all correlation findings.

        Returns
        -------
        str
            Markdown-formatted report.
        """
        logger.info("Generating correlation report …")
        correlations = self.correlate_complexity_with_accuracy()
        problems = self.identify_problem_modules()
        ranked = self.rank_modules_by_contribution()
        refactor = self.recommend_refactoring()

        lines: list[str] = []
        lines.append("# Prediction Quality Correlation Report\n")
        lines.append(
            f"**Generated:** {__import__('datetime').datetime.now().isoformat()}\n"
        )

        # Correlation summary
        lines.append("## Code-Quality vs Prediction Correlations\n")
        lines.append("| Metric Pair | Spearman ρ | Interpretation |")
        lines.append("|-------------|-----------|----------------|")
        for key, value in correlations.items():
            label = key.replace("_", " ").title()
            interp = (
                "Strong positive"
                if value > 0.5
                else (
                    "Moderate positive"
                    if value > 0.2
                    else (
                        "Strong negative"
                        if value < -0.5
                        else (
                            "Moderate negative"
                            if value < -0.2
                            else "Weak / negligible"
                        )
                    )
                )
            )
            lines.append(f"| {label} | {value:.4f} | {interp} |")
        lines.append("")

        # Problem modules
        if problems:
            lines.append("## Problem Modules (High Complexity + Low Win Rate)\n")
            lines.append("| Module | Complexity | Win Rate | Profit Factor | Reason |")
            lines.append("|--------|-----------|----------|---------------|--------|")
            for p in problems:
                lines.append(
                    f"| `{p['module']}` | {p['complexity']} | {p['win_rate']:.2%} | "
                    f"{p['profit_factor']} | {p['flag_reason']} |"
                )
            lines.append("")

        # Top contributors
        if ranked:
            lines.append("## Top Contributing Modules\n")
            lines.append(
                "| Module | Composite Score | Win Rate | Profit Factor | Complexity |"
            )
            lines.append(
                "|--------|----------------|----------|---------------|------------|"
            )
            for r in ranked[:10]:
                lines.append(
                    f"| `{r['module']}` | {r['composite_score']:.4f} | "
                    f"{r['win_rate']:.2%} | {r['profit_factor']} | {r['complexity']} |"
                )
            lines.append("")

        # Refactoring recommendations
        if refactor:
            lines.append("## Refactoring Recommendations\n")
            for rec in refactor:
                lines.append(
                    f"### `{rec['module']}` — **{rec['priority'].upper()}**\n"
                )
                lines.append("**Issues:**")
                for issue in rec["issues"]:
                    lines.append(f"- {issue}")
                lines.append("\n**Recommendations:**")
                for suggestion in rec["recommendations"]:
                    lines.append(f"- {suggestion}")
                lines.append("")

        logger.info("Correlation report generated (%d lines)", len(lines))
        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    #  Internal helpers
    # ------------------------------------------------------------------ #

    def _aligned_modules(self) -> list[dict[str, Any]]:
        """
        Return a list of dicts where each dict contains both code-quality
        and prediction metrics for a single module.
        """
        aligned: list[dict[str, Any]] = []
        for mod_path, code_meta in self.per_module.items():
            pred_meta = self.prediction_metrics.get(mod_path)
            if pred_meta is None:
                continue

            winrate = pred_meta.get("win_rate", pred_meta.get("winrate", 0.0))
            if isinstance(winrate, (int, float)) and winrate > 1.0:
                # Normalise if expressed as 0-100
                winrate = winrate / 100.0

            aligned.append(
                {
                    "module": mod_path,
                    "complexity": code_meta.get("cyclomatic_complexity", 0.0),
                    "function_length": code_meta.get("avg_function_length", 0.0),
                    "import_count": code_meta.get("import_count", 0),
                    "coverage": code_meta.get("test_coverage_estimate", 0.0),
                    "winrate": winrate,
                    "profit_factor": pred_meta.get("profit_factor", 0.0),
                    "sharpe_ratio": pred_meta.get("sharpe_ratio", 0.0),
                    "total_predictions": pred_meta.get("total_predictions", 0),
                }
            )

        return aligned


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------

def build_prediction_metrics_from_outcomes(
    module_outcomes: dict[str, list[dict[str, Any]]],
) -> dict[str, dict[str, Any]]:
    """
    Derive prediction-performance metrics from a raw list of per-module
    outcome dicts.

    Parameters
    ----------
    module_outcomes:
        ``{module_path: [outcome_dict, …]}`` where each outcome dict has
        keys ``result`` (``"win"`` | ``"loss"``) and optionally ``pnl``.

    Returns
    -------
    dict
        ``{module_path: {win_rate, profit_factor, total_predictions, net_pnl}}``
    """
    metrics: dict[str, dict[str, Any]] = {}
    for mod_path, outcomes in module_outcomes.items():
        wins = sum(1 for o in outcomes if o.get("result") == "win")
        losses = sum(1 for o in outcomes if o.get("result") == "loss")
        total = wins + losses

        win_rate = wins / total if total else 0.0
        gross_profit = sum(
            o.get("pnl", 0.0) for o in outcomes if o.get("result") == "win"
        )
        gross_loss = sum(
            abs(o.get("pnl", 0.0)) for o in outcomes if o.get("result") == "loss"
        )
        profit_factor = (
            gross_profit / gross_loss if gross_loss and gross_loss > 0 else 0.0
        )
        net_pnl = gross_profit - gross_loss

        # Sharpe-like ratio (simplified, no risk-free rate)
        pnls = [o.get("pnl", 0.0) for o in outcomes]
        avg_pnl = sum(pnls) / len(pnls) if pnls else 0.0
        std_pnl = math.sqrt(
            sum((p - avg_pnl) ** 2 for p in pnls) / len(pnls)
        ) if pnls else 0.0
        sharpe = avg_pnl / std_pnl if std_pnl else 0.0

        metrics[mod_path] = {
            "win_rate": win_rate,
            "profit_factor": round(profit_factor, 4),
            "total_predictions": total,
            "net_pnl": round(net_pnl, 4),
            "sharpe_ratio": round(sharpe, 4),
        }

    logger.info(
        "Built prediction metrics for %d modules from raw outcomes", len(metrics)
    )
    return metrics


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:  # pragma: no cover
    """CLI convenience runner."""
    print("PredictionQualityCorrelator — import and use programmatically.")
    print("Example:")
    print("  from prediction_quality_correlator import PredictionQualityCorrelator")
    print("  correlator = PredictionQualityCorrelator(repo_metrics, pred_metrics)")
    print("  print(correlator.generate_correlation_report())")


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO)
    main()
