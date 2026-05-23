"""
Meta-Swarm Orchestrator — PR-4 Meta-Improvement Swarm.

A self-improving orchestrator that reviews past outputs from the six swarm
engines (Coding, PR Review, GitHub Actions, Research, Ensemble, Hierarchical)
and optimises future runs via:

* Quality scoring across multiple dimensions.
* A/B testing of prompt/persona variants with Thompson sampling.
* Weak-persona identification and targeted improvement recommendations.
* Skill export for downstream consumption.

Typical usage::

    orchestrator = MetaSwarmOrchestrator(memory_path="./meta_memory.json")
    review = orchestrator.run_meta_review_cycle()
    print(review)
"""
from __future__ import annotations

import json
import logging
import math
import os
import random
import time
from typing import Any

logger = logging.getLogger("swarm_v2.meta")


# ---------------------------------------------------------------------------
# Thompson Sampling helper (pure Python)
# ---------------------------------------------------------------------------

def _thompson_sample(wins_a: int, losses_a: int, wins_b: int, losses_b: int) -> str:
    """Return the winning variant ('A' or 'B') via Thompson sampling.

    Draws one sample from each arm's Beta posterior and returns the arm
    with the higher draw.

    Parameters
    ----------
    wins_a, losses_a:
        Observed wins/losses for variant A.
    wins_b, losses_b:
        Observed wins/losses for variant B.
    """
    # Add 1 for Laplace smoothing to avoid degenerate Beta(0, *) or Beta(*, 0)
    sample_a = random.betavariate(wins_a + 1, losses_a + 1)
    sample_b = random.betavariate(wins_b + 1, losses_b + 1)
    return "A" if sample_a >= sample_b else "B"


def _beta_mode(alpha: float, beta: float) -> float:
    """Mode of Beta(alpha, beta) — useful for summarising a posterior."""
    if alpha <= 1 or beta <= 1:
        # Mode is at a boundary; return mean as fallback
        return alpha / (alpha + beta)
    return (alpha - 1.0) / (alpha + beta - 2.0)


# ---------------------------------------------------------------------------
# Quality scoring engine
# ---------------------------------------------------------------------------

class _QualityScorer:
    """Score swarm outputs across multiple quality dimensions.

    Each dimension produces a float in ``[0.0, 1.0]``.  The overall score
    is a weighted average.
    """

    # Weights for the overall composite score
    DIMENSION_WEIGHTS: dict[str, float] = {
        "prediction_accuracy": 0.25,
        "code_correctness": 0.25,
        "review_thoroughness": 0.25,
        "actionability": 0.25,
    }

    @classmethod
    def score(cls, output: dict[str, Any]) -> dict[str, float]:
        """Score a single swarm output.

        Parameters
        ----------
        output:
            Dict describing the swarm engine output.  Expected keys::

                {
                    "engine": str,           # e.g. "coding", "pr_review"
                    "output_type": str,      # "code" | "review" | "research" | "prediction"
                    "content_preview": str,  # First ~500 chars of output
                    "metadata": {
                        "lines_of_code": int,      # for code
                        "issues_found": int,       # for review
                        "predictions": list,       # for predictions
                        "accuracy": float,         # if known
                        "test_pass_rate": float,   # 0..1
                    },
                }

        Returns
        -------
        dict
            ``{"prediction_accuracy": float, "code_correctness": float,
            "review_thoroughness": float, "actionability": float,
            "overall": float}``
        """
        meta = output.get("metadata", {})
        out_type = output.get("output_type", "unknown")

        # --- Prediction accuracy ---
        pred_acc: float = 0.5
        if out_type == "prediction":
            if "accuracy" in meta:
                pred_acc = float(meta["accuracy"])
            elif "predictions" in meta:
                preds = meta["predictions"]
                if isinstance(preds, list) and preds:
                    # Simple heuristic: fraction of non-None predictions
                    valid = sum(1 for p in preds if p is not None)
                    pred_acc = valid / len(preds)
        elif out_type in ("code", "review", "research"):
            pred_acc = 0.5  # Neutral for non-prediction outputs

        # --- Code correctness ---
        code_corr: float = 0.5
        if out_type == "code":
            test_rate = meta.get("test_pass_rate")
            if test_rate is not None:
                code_corr = float(test_rate)
            elif "lines_of_code" in meta:
                loc = int(meta["lines_of_code"])
                # Heuristic: moderate LOC suggests focused, reviewable code
                code_corr = 0.7 if 10 <= loc <= 500 else 0.4 if loc > 500 else 0.6
        elif out_type in ("prediction", "review", "research"):
            code_corr = 0.5

        # --- Review thoroughness ---
        review_thor: float = 0.5
        if out_type == "review":
            issues = meta.get("issues_found")
            if issues is not None:
                n = int(issues)
                review_thor = min(0.3 + n * 0.1, 1.0)
            else:
                review_thor = 0.5
        elif out_type in ("code", "prediction", "research"):
            review_thor = 0.5

        # --- Actionability (applies to all) ---
        actionability: float = 0.5
        preview = output.get("content_preview", "")
        actionable_markers = ["TODO:", "FIXME:", "RECOMMENDATION:", "ACTION:", "STEP:", "IMPLEMENT"]
        marker_hits = sum(1 for m in actionable_markers if m in preview.upper())
        if marker_hits >= 2:
            actionability = 0.8
        elif marker_hits == 1:
            actionability = 0.65
        else:
            # Check for list-like structure (numbered steps)
            lines = preview.splitlines()
            numbered = sum(1 for ln in lines if ln.strip() and ln.strip()[0].isdigit() and "." in ln[:3])
            actionability = 0.7 if numbered >= 2 else 0.45

        # Composite
        overall = (
            cls.DIMENSION_WEIGHTS["prediction_accuracy"] * pred_acc +
            cls.DIMENSION_WEIGHTS["code_correctness"] * code_corr +
            cls.DIMENSION_WEIGHTS["review_thoroughness"] * review_thor +
            cls.DIMENSION_WEIGHTS["actionability"] * actionability
        )

        return {
            "prediction_accuracy": round(pred_acc, 4),
            "code_correctness": round(code_corr, 4),
            "review_thoroughness": round(review_thor, 4),
            "actionability": round(actionability, 4),
            "overall": round(overall, 4),
        }


# ---------------------------------------------------------------------------
# MetaSwarmOrchestrator
# ---------------------------------------------------------------------------

class MetaSwarmOrchestrator:
    """Self-improving orchestrator for the swarm_v2 system.

    Reviews outputs from the six swarm engines, scores them, runs A/B tests
    of prompt/persona variants via Thompson sampling, identifies weak
    personas, and exports improved skill definitions.

    Parameters
    ----------
    memory_path:
        Path to a JSON file used as the persistent memory store.  If the file
        exists it is loaded; otherwise a fresh store is created.
    """

    # The six swarm engines that produce outputs
    SWARM_ENGINES: list[str] = [
        "coding",
        "pr_review",
        "github_actions",
        "research",
        "ensemble",
        "hierarchical",
    ]

    def __init__(self, memory_path: str) -> None:
        self.memory_path: str = memory_path

        # output_log: list of scored outputs
        self._output_log: list[dict[str, Any]] = []

        # ab_tests: {test_id: {"base_prompt": str, "variant_prompt": str,
        #                       "wins_a": int, "losses_a": int,
        #                       "wins_b": int, "losses_b": int,
        #                       "created_at": float, "results": [...]}}
        self._ab_tests: dict[str, dict[str, Any]] = {}

        # personas: {persona_name: {"engine": str, "scores": [float],
        #                           "outputs": [int] (indices into _output_log)}}
        self._personas: dict[str, dict[str, Any]] = {}

        # skill_improvements: {skill_name: [{"change": str, "rationale": str, "timestamp": float}, ...]}
        self._skill_improvements: dict[str, list[dict[str, Any]]] = {}

        self._load_or_init()

        logger.info(
            "MetaSwarmOrchestrator initialised | memory=%s | outputs=%d | ab_tests=%d | personas=%d",
            memory_path, len(self._output_log), len(self._ab_tests), len(self._personas),
        )

    # -- Persistence ---------------------------------------------------------

    def _load_or_init(self) -> None:
        """Load memory from disk or start fresh."""
        if os.path.exists(self.memory_path):
            try:
                with open(self.memory_path, "r", encoding="utf-8") as fh:
                    payload = json.load(fh)
                self._output_log = payload.get("output_log", [])
                self._ab_tests = payload.get("ab_tests", {})
                self._personas = payload.get("personas", {})
                self._skill_improvements = payload.get("skill_improvements", {})
                logger.debug(
                    "Loaded memory: %d outputs, %d A/B tests, %d personas",
                    len(self._output_log), len(self._ab_tests), len(self._personas),
                )
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Failed to load memory from %s: %s — starting fresh", self.memory_path, exc)
                self._output_log = []
                self._ab_tests = {}
                self._personas = {}
                self._skill_improvements = {}
        else:
            logger.debug("No memory file at %s — starting fresh", self.memory_path)

    def _persist(self) -> None:
        """Write current state to the JSON memory file."""
        payload = {
            "output_log": self._output_log,
            "ab_tests": self._ab_tests,
            "personas": self._personas,
            "skill_improvements": self._skill_improvements,
            "saved_at": time.time(),
        }
        os.makedirs(os.path.dirname(self.memory_path), exist_ok=True) if os.path.dirname(self.memory_path) else None
        with open(self.memory_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, default=str)
        logger.debug("Persisted meta-memory to %s", self.memory_path)

    # -- Output ingestion ----------------------------------------------------

    def _ingest_output(self, output: dict[str, Any]) -> int:
        """Ingest and score a single swarm-engine output.

        Returns the index of the scored entry in ``_output_log``.
        """
        scores = _QualityScorer.score(output)
        entry = {
            **output,
            "scores": scores,
            "ingested_at": time.time(),
        }
        idx = len(self._output_log)
        self._output_log.append(entry)

        # Update per-persona stats
        persona = output.get("persona", output.get("engine", "unknown"))
        if persona not in self._personas:
            self._personas[persona] = {"engine": output.get("engine", "unknown"), "scores": [], "outputs": []}
        self._personas[persona]["scores"].append(scores["overall"])
        self._personas[persona]["outputs"].append(idx)

        self._persist()
        return idx

    # -- Public API ----------------------------------------------------------

    def review_past_outputs(self, n_recent: int = 10) -> dict[str, Any]:
        """Score the *n_recent* most recent swarm outputs and summarise.

        Parameters
        ----------
        n_recent:
            Number of recent outputs to review (default 10).

        Returns
        -------
        dict
            Summary containing ``reviewed_count``, ``avg_scores`` per
            dimension, ``best_output``, ``worst_output``, and per-engine
            breakdowns.
        """
        if not self._output_log:
            return {
                "reviewed_count": 0,
                "message": "No outputs available for review.",
            }

        recent = self._output_log[-n_recent:]
        n = len(recent)

        # Aggregate dimension scores
        dims = ["prediction_accuracy", "code_correctness", "review_thoroughness", "actionability", "overall"]
        avg_scores: dict[str, float] = {}
        for dim in dims:
            values = [e["scores"][dim] for e in recent]
            avg_scores[dim] = round(sum(values) / len(values), 4) if values else 0.0

        # Best / worst by overall score
        best_entry = max(recent, key=lambda e: e["scores"]["overall"])
        worst_entry = min(recent, key=lambda e: e["scores"]["overall"])

        # Per-engine breakdown
        engine_stats: dict[str, dict[str, Any]] = {}
        for entry in recent:
            engine = entry.get("engine", "unknown")
            if engine not in engine_stats:
                engine_stats[engine] = {"count": 0, "scores": []}
            engine_stats[engine]["count"] += 1
            engine_stats[engine]["scores"].append(entry["scores"]["overall"])

        for engine in engine_stats:
            scores = engine_stats[engine]["scores"]
            engine_stats[engine]["avg_score"] = round(sum(scores) / len(scores), 4)
            del engine_stats[engine]["scores"]

        result = {
            "reviewed_count": n,
            "avg_scores": avg_scores,
            "best_output": {
                "engine": best_entry.get("engine"),
                "persona": best_entry.get("persona", best_entry.get("engine")),
                "overall_score": best_entry["scores"]["overall"],
                "timestamp": best_entry.get("ingested_at"),
            },
            "worst_output": {
                "engine": worst_entry.get("engine"),
                "persona": worst_entry.get("persona", worst_entry.get("engine")),
                "overall_score": worst_entry["scores"]["overall"],
                "timestamp": worst_entry.get("ingested_at"),
            },
            "per_engine": engine_stats,
        }

        logger.info(
            "Reviewed %d recent outputs | avg overall=%.3f | best=%s(%.3f) | worst=%s(%.3f)",
            n, avg_scores["overall"],
            result["best_output"]["engine"], result["best_output"]["overall_score"],
            result["worst_output"]["engine"], result["worst_output"]["overall_score"],
        )
        return result

    def ab_test_prompt_variant(
        self,
        base_prompt: str,
        variant_prompt: str,
        test_cases: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Run an A/B test between two prompt variants using Thompson sampling.

        Each entry in *test_cases* is executed against both variants; a
        Thompson-sample draw decides which variant's output is "used".  The
        winner gets a +1 win; the loser a +1 loss.  Results are persisted.

        Parameters
        ----------
        base_prompt:
            The existing (control) prompt text.
        variant_prompt:
            The new (treatment) prompt text.
        test_cases:
            List of input dicts to exercise the prompts.

        Returns
        -------
        dict
            ``{"test_id": str, "base_prompt_sha256": str, "variant_prompt_sha256": str,
            "test_cases_run": int, "wins_base": int, "wins_variant": int,
            "win_rate_base": float, "win_rate_variant": float,
            "thompson_recommendation": str, "confidence": float}``
        """
        import hashlib

        test_id = f"ab_{int(time.time())}_{random.randint(1000, 9999)}"
        base_hash = hashlib.sha256(base_prompt.encode()).hexdigest()[:16]
        var_hash = hashlib.sha256(variant_prompt.encode()).hexdigest()[:16]

        wins_a = losses_a = wins_b = losses_b = 0
        results: list[dict[str, Any]] = []

        for i, test_case in enumerate(test_cases):
            # Score the output that would come from each variant
            # (In production this calls the actual LLM; here we simulate scoring)
            base_meta = {"prompt_variant": "A", **test_case.get("metadata", {})}
            var_meta = {"prompt_variant": "B", **test_case.get("metadata", {})}

            base_output = {
                "engine": test_case.get("engine", "unknown"),
                "output_type": test_case.get("output_type", "code"),
                "content_preview": test_case.get("content_preview", base_prompt[:200]),
                "metadata": base_meta,
            }
            var_output = {
                "engine": test_case.get("engine", "unknown"),
                "output_type": test_case.get("output_type", "code"),
                "content_preview": test_case.get("content_preview", variant_prompt[:200]),
                "metadata": var_meta,
            }

            base_scores = _QualityScorer.score(base_output)
            var_scores = _QualityScorer.score(var_output)

            # Thompson sampling: draw from Beta posteriors and pick winner
            winner = _thompson_sample(wins_a, losses_a, wins_b, losses_b)

            if winner == "A":
                wins_a += 1
                losses_b += 1
            else:
                wins_b += 1
                losses_a += 1

            results.append({
                "case_index": i,
                "winner": winner,
                "base_score": base_scores["overall"],
                "variant_score": var_scores["overall"],
            })

        total = len(test_cases)
        wr_base = wins_a / total if total > 0 else 0.0
        wr_variant = wins_b / total if total > 0 else 0.0

        # Posterior summary
        post_mode_a = _beta_mode(wins_a + 1, losses_a + 1)
        post_mode_b = _beta_mode(wins_b + 1, losses_b + 1)

        # Recommendation
        if wr_variant > wr_base and wins_b >= wins_a + 2:
            recommendation = "ADOPT_VARIANT"
            confidence = min(wr_variant, 0.99)
        elif wr_base > wr_variant and wins_a >= wins_b + 2:
            recommendation = "KEEP_BASE"
            confidence = min(wr_base, 0.99)
        else:
            recommendation = "INCONCLUSIVE"
            confidence = 0.5

        # Persist
        self._ab_tests[test_id] = {
            "test_id": test_id,
            "base_prompt_hash": base_hash,
            "variant_prompt_hash": var_hash,
            "wins_a": wins_a,
            "losses_a": losses_a,
            "wins_b": wins_b,
            "losses_b": losses_b,
            "post_mode_a": round(post_mode_a, 4),
            "post_mode_b": round(post_mode_b, 4),
            "results": results,
            "recommendation": recommendation,
            "created_at": time.time(),
        }
        self._persist()

        logger.info(
            "A/B test %s complete | base=%d/%d (%.2f%%) | variant=%d/%d (%.2f%%) | rec=%s",
            test_id, wins_a, total, wr_base * 100, wins_b, total, wr_variant * 100, recommendation,
        )

        return {
            "test_id": test_id,
            "base_prompt_sha256": base_hash,
            "variant_prompt_sha256": var_hash,
            "test_cases_run": total,
            "wins_base": wins_a,
            "wins_variant": wins_b,
            "win_rate_base": round(wr_base, 4),
            "win_rate_variant": round(wr_variant, 4),
            "thompson_recommendation": recommendation,
            "confidence": round(confidence, 4),
        }

    def identify_weak_personas(self) -> list[dict[str, Any]]:
        """Identify personas with consistently low output quality.

        A persona is flagged as *weak* when its average overall score falls
        below 0.50 or when it has at least 5 outputs and the average is
        below 0.60.

        Returns
        -------
        list[dict]
            Each dict has ``persona``, ``engine``, ``avg_score``,
            ``output_count``, and ``weakness_reason``.
        """
        weak: list[dict[str, Any]] = []
        for persona, data in self._personas.items():
            scores = data.get("scores", [])
            if not scores:
                continue
            avg_score = sum(scores) / len(scores)
            count = len(scores)

            is_weak = False
            reason = ""
            if avg_score < 0.50:
                is_weak = True
                reason = f"Average score {avg_score:.3f} below 0.50 threshold"
            elif count >= 5 and avg_score < 0.60:
                is_weak = True
                reason = f"Average score {avg_score:.3f} below 0.60 with {count} outputs"

            if is_weak:
                weak.append({
                    "persona": persona,
                    "engine": data.get("engine", "unknown"),
                    "avg_score": round(avg_score, 4),
                    "output_count": count,
                    "weakness_reason": reason,
                })

        weak.sort(key=lambda p: p["avg_score"])
        logger.info("Identified %d weak persona(s) out of %d", len(weak), len(self._personas))
        return weak

    def recommend_persona_improvements(self) -> list[dict[str, Any]]:
        """Generate specific improvement recommendations for weak personas.

        Analyses the output history of each weak persona and suggests
        concrete changes (prompt refinements, additional context, tool
        additions, etc.).

        Returns
        -------
        list[dict]
            Each dict has ``persona``, ``current_avg_score``,
            ``recommendations`` (list of str), and ``priority``.
        """
        weak_personas = self.identify_weak_personas()
        recommendations: list[dict[str, Any]] = []

        for wp in weak_personas:
            persona = wp["persona"]
            engine = wp["engine"]
            recs: list[str] = []

            # Inspect recent outputs for this persona
            output_indices = self._personas[persona].get("outputs", [])
            recent_indices = output_indices[-10:] if len(output_indices) > 10 else output_indices
            recent_outputs = [self._output_log[i] for i in recent_indices if i < len(self._output_log)]

            # Diagnose based on dimension scores
            dim_avgs: dict[str, float] = {}
            for dim in ["prediction_accuracy", "code_correctness", "review_thoroughness", "actionability"]:
                vals = [o["scores"][dim] for o in recent_outputs]
                dim_avgs[dim] = sum(vals) / len(vals) if vals else 0.0

            lowest_dim = min(dim_avgs, key=dim_avgs.get) if dim_avgs else "overall"
            lowest_score = dim_avgs.get(lowest_dim, 0.0)

            if lowest_dim == "prediction_accuracy" and lowest_score < 0.5:
                recs.append("Add more few-shot examples with known-correct predictions")
                recs.append("Include confidence calibration instructions in the prompt")
            elif lowest_dim == "code_correctness" and lowest_score < 0.5:
                recs.append("Require unit-test generation alongside every code block")
                recs.append("Inject static-analysis rules (lint, type-check) into the prompt")
            elif lowest_dim == "review_thoroughness" and lowest_score < 0.5:
                recs.append("Expand review checklist to cover security, performance, and edge cases")
                recs.append("Require explicit issue severity classification (critical/warning/info)")
            elif lowest_dim == "actionability" and lowest_score < 0.5:
                recs.append("Add structured output format: SUMMARY → FINDINGS → RECOMMENDATIONS → NEXT STEPS")
                recs.append("Require every recommendation to include a concrete code snippet or command")
            else:
                recs.append("Run an A/B test with a prompt variant that includes more context")
                recs.append("Review and refresh the persona's system prompt for outdated instructions")

            # General recommendations based on engine type
            if engine == "coding":
                recs.append("Enable the 'test-first' constraint: require tests before implementation")
            elif engine == "pr_review":
                recs.append("Add diff-context size parameter: increase surrounding lines to 10")
            elif engine == "research":
                recs.append("Require source citations for every factual claim")
            elif engine in ("ensemble", "hierarchical"):
                recs.append("Review sub-agent selection weights; consider boosting high-performing sub-agents")

            priority = "HIGH" if wp["avg_score"] < 0.45 else "MEDIUM"
            recommendations.append({
                "persona": persona,
                "engine": engine,
                "current_avg_score": wp["avg_score"],
                "lowest_dimension": lowest_dim,
                "lowest_dim_score": round(lowest_score, 4),
                "recommendations": recs,
                "priority": priority,
            })

            # Store for export
            self._skill_improvements.setdefault(persona, []).append({
                "change": "; ".join(recs[:2]),
                "rationale": wp["weakness_reason"],
                "timestamp": time.time(),
            })

        self._persist()
        logger.info("Generated %d persona improvement recommendation(s)", len(recommendations))
        return recommendations

    def export_improved_skills(self, output_dir: str) -> int:
        """Export improved skill definitions to *output_dir*.

        For each persona with recorded improvements, writes a JSON file
        containing the accumulated recommendations and a refactored skill
        definition.

        Parameters
        ----------
        output_dir:
            Destination directory for the exported skill files.

        Returns
        -------
        int
            Number of skill files exported.
        """
        os.makedirs(output_dir, exist_ok=True)
        count = 0

        # Also export improvements for personas that have recommendations
        persona_improvements = self.recommend_persona_improvements()
        improvements_by_persona: dict[str, dict[str, Any]] = {
            p["persona"]: p for p in persona_improvements
        }

        for persona, improvements in self._skill_improvements.items():
            rec_data = improvements_by_persona.get(persona, {})
            skill_def: dict[str, Any] = {
                "skill_name": persona,
                "version": f"2.{len(improvements)}",
                "engine": self._personas.get(persona, {}).get("engine", "unknown"),
                "improvements": improvements,
                "latest_recommendations": rec_data.get("recommendations", []),
                "priority": rec_data.get("priority", "LOW"),
                "exported_at": time.time(),
                "metadata": {
                    "avg_score": rec_data.get("current_avg_score"),
                    "total_outputs": self._personas.get(persona, {}).get("scores", []).__len__(),
                },
            }

            # Build an evolved prompt incorporating the recommendations
            evolved_prompt = self._build_evolved_prompt(persona, rec_data.get("recommendations", []))
            skill_def["evolved_prompt"] = evolved_prompt

            path = os.path.join(output_dir, f"{persona}_improved.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(skill_def, fh, indent=2, default=str)
            count += 1

        logger.info("Exported %d improved skill(s) to %s", count, output_dir)
        return count

    @staticmethod
    def _build_evolved_prompt(persona: str, recommendations: list[str]) -> str:
        """Construct an evolved prompt string from improvement recommendations."""
        lines = [
            f"# Evolved Prompt: {persona}",
            "",
            "## System Instructions",
            f"You are the '{persona}' persona in the swarm_v2 system.",
            "Your outputs are continuously evaluated for quality and improved over time.",
            "",
            "## Quality Constraints",
        ]
        for rec in recommendations:
            lines.append(f"- {rec}")
        lines.extend([
            "",
            "## Output Format",
            "Produce structured, actionable output with clear next steps.",
            "Include specific code snippets, commands, or references where applicable.",
            "",
        ])
        return "\n".join(lines)

    def run_meta_review_cycle(self) -> str:
        """Execute a full meta-review cycle and return a markdown report.

        The cycle comprises:

        1. Review recent outputs and compute quality scores.
        2. Identify weak personas.
        3. Generate persona improvement recommendations.
        4. Summarise active A/B tests.
        5. Compile everything into a markdown report.

        Returns
        -------
        str
            Markdown-formatted meta-review report.
        """
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        lines: list[str] = [
            "# Meta-Swarm Review Cycle",
            "",
            f"_Generated: {now_str}_",
            "",
        ]

        # --- Section 1: Recent output review ---
        lines.append("## 1. Recent Output Quality Review")
        lines.append("")
        review = self.review_past_outputs(n_recent=10)
        if review.get("reviewed_count", 0) == 0:
            lines.append("_No outputs to review._")
        else:
            lines.append(f"**Outputs reviewed**: {review['reviewed_count']}")
            lines.append("")
            lines.append("### Average Scores")
            for dim, score in review["avg_scores"].items():
                bar = "█" * int(score * 20) + "░" * (20 - int(score * 20))
                lines.append(f"- **{dim}**: {score:.3f} {bar}")
            lines.append("")
            best = review["best_output"]
            worst = review["worst_output"]
            lines.append(f"**Best output**: `{best['engine']}` (score={best['overall_score']:.3f})")
            lines.append(f"**Worst output**: `{worst['engine']}` (score={worst['overall_score']:.3f})")
            lines.append("")
            lines.append("### Per-Engine Breakdown")
            lines.append("| Engine | Count | Avg Score |")
            lines.append("|--------|------:|----------:|")
            for engine, stats in review.get("per_engine", {}).items():
                lines.append(f"| {engine} | {stats['count']} | {stats['avg_score']:.3f} |")
        lines.append("")

        # --- Section 2: Weak personas ---
        lines.append("## 2. Weak Persona Identification")
        lines.append("")
        weak = self.identify_weak_personas()
        if not weak:
            lines.append("✅ **All personas are performing above threshold.**")
        else:
            lines.append(f"⚠️ **{len(weak)} persona(s) flagged for improvement:**")
            lines.append("")
            lines.append("| Persona | Engine | Avg Score | Outputs | Reason |")
            lines.append("|---------|--------|----------:|--------:|--------|")
            for wp in weak:
                lines.append(
                    f"| {wp['persona']} | {wp['engine']} | "
                    f"{wp['avg_score']:.3f} | {wp['output_count']} | {wp['weakness_reason']} |"
                )
        lines.append("")

        # --- Section 3: Improvement recommendations ---
        lines.append("## 3. Persona Improvement Recommendations")
        lines.append("")
        recommendations = self.recommend_persona_improvements()
        if not recommendations:
            lines.append("_No recommendations needed._")
        else:
            for rec in recommendations:
                emoji = "🔴" if rec["priority"] == "HIGH" else "🟡"
                lines.append(f"### {emoji} {rec['persona']} ({rec['engine']})")
                lines.append(f"- **Current score**: {rec['current_avg_score']:.3f}")
                lines.append(f"- **Weakest dimension**: {rec['lowest_dimension']} ({rec['lowest_dim_score']:.3f})")
                lines.append("- **Recommendations**:")
                for r in rec["recommendations"]:
                    lines.append(f"  - {r}")
                lines.append("")

        # --- Section 4: A/B test summary ---
        lines.append("## 4. A/B Test Summary")
        lines.append("")
        if not self._ab_tests:
            lines.append("_No A/B tests have been run yet._")
        else:
            lines.append(f"**Total tests**: {len(self._ab_tests)}")
            lines.append("")
            lines.append("| Test ID | Base WR | Variant WR | Recommendation | Confidence |")
            lines.append("|---------|--------:|-----------:|----------------|-----------:|")
            for tid, tdata in sorted(self._ab_tests.items(), key=lambda x: x[1].get("created_at", 0), reverse=True):
                total_a = tdata["wins_a"] + tdata["losses_a"]
                total_b = tdata["wins_b"] + tdata["losses_b"]
                wr_a = tdata["wins_a"] / total_a if total_a else 0.0
                wr_b = tdata["wins_b"] / total_b if total_b else 0.0
                lines.append(
                    f"| {tid[:20]}... | {wr_a:.3f} | {wr_b:.3f} | "
                    f"{tdata.get('recommendation', 'N/A')} | — |"
                )
        lines.append("")

        # --- Section 5: Improvement actions taken ---
        lines.append("## 5. Improvement Actions")
        lines.append("")
        if not self._skill_improvements:
            lines.append("_No improvements recorded yet._")
        else:
            lines.append(f"**Skills with recorded improvements**: {len(self._skill_improvements)}")
            for skill, changes in self._skill_improvements.items():
                lines.append(f"- `{skill}`: {len(changes)} improvement(s)")
        lines.append("")

        # --- Footer ---
        lines.append("---")
        lines.append(
            f"_Meta-review complete | Outputs: {len(self._output_log)} | "
            f"Personas: {len(self._personas)} | A/B tests: {len(self._ab_tests)}_"
        )
        lines.append("")

        report = "\n".join(lines)
        logger.info("Meta-review cycle complete | report length=%d chars", len(report))
        return report

    # -- Convenience methods for swarm engine integration --------------------

    def ingest_engine_output(self, engine: str, output: dict[str, Any]) -> dict[str, Any]:
        """Convenience wrapper to ingest an output from a named engine.

        Parameters
        ----------
        engine:
            One of the six swarm engine names.
        output:
            Raw output dict from the engine.

        Returns
        -------
        dict
            The scored output entry with ``scores`` and ``ingested_at`` added.
        """
        output["engine"] = engine
        idx = self._ingest_output(output)
        return self._output_log[idx]

    def get_ab_test_leaderboard(self) -> list[dict[str, Any]]:
        """Return a leaderboard of all prompt variants ranked by win-rate.

        Returns
        -------
        list[dict]
            Each entry has ``test_id``, ``variant`` (``"base"`` or ``"variant"``),
            ``win_rate``, and ``posterior_mode``.
        """
        leaderboard: list[dict[str, Any]] = []
        for tid, tdata in self._ab_tests.items():
            total_a = tdata["wins_a"] + tdata["losses_a"]
            total_b = tdata["wins_b"] + tdata["losses_b"]
            wr_a = tdata["wins_a"] / total_a if total_a else 0.0
            wr_b = tdata["wins_b"] / total_b if total_b else 0.0
            leaderboard.append({
                "test_id": tid,
                "variant": "base",
                "win_rate": round(wr_a, 4),
                "posterior_mode": tdata.get("post_mode_a", 0.0),
            })
            leaderboard.append({
                "test_id": tid,
                "variant": "variant",
                "win_rate": round(wr_b, 4),
                "posterior_mode": tdata.get("post_mode_b", 0.0),
            })
        leaderboard.sort(key=lambda e: e["win_rate"], reverse=True)
        return leaderboard

    def get_thompson_best_variant(self, test_id: str) -> str:
        """Use Thompson sampling to select the best variant for *test_id*.

        Returns ``"base"`` or ``"variant"`` based on a single posterior draw.
        This is the exploration/exploitation decision point: calling this
        method repeatedly will naturally explore both arms early on and
        converge to the better arm as data accumulates.

        Parameters
        ----------
        test_id:
            Identifier of a previously run A/B test.

        Returns
        -------
        str
            ``"base"`` or ``"variant"``.

        Raises
        ------
        KeyError
            If *test_id* does not exist.
        """
        if test_id not in self._ab_tests:
            raise KeyError(f"A/B test {test_id!r} not found")
        tdata = self._ab_tests[test_id]
        winner = _thompson_sample(
            tdata["wins_a"], tdata["losses_a"],
            tdata["wins_b"], tdata["losses_b"],
        )
        return "base" if winner == "A" else "variant"
