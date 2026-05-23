"""
Skill Evolution Tracker — PR-4 Meta-Improvement Swarm.

Tracks the effectiveness of skills and prompt-templates over time using a
pure-Python implementation.  Detects skill decay, computes rolling win-rates,
quality-score trends (linear regression), and generates actionable reports.

Typical usage::

    tracker = SkillEvolutionTracker(skills_dir="./skills", history_path="./skill_history.json")
    tracker.register_skill("code_review", {"owner": "PR-Review-Engine", "tags": ["review"]})
    tracker.record_skill_outcome("code_review", {"success": True, "quality_score": 0.85})
    print(tracker.generate_skill_report())
"""
from __future__ import annotations

import json
import logging
import math
import os
import time
from typing import Any

logger = logging.getLogger("swarm_v2.skills")


# ---------------------------------------------------------------------------
# Linear-regression helper (no numpy)
# ---------------------------------------------------------------------------

def _linear_regression_slope(x_vals: list[float], y_vals: list[float]) -> float:
    """Return the slope of a simple linear regression y ~ x.

    Returns ``0.0`` if there is insufficient variance in *x_vals*.
    """
    n = len(x_vals)
    if n < 2:
        return 0.0
    mean_x = sum(x_vals) / n
    mean_y = sum(y_vals) / n
    var_x = sum((x - mean_x) ** 2 for x in x_vals)
    if var_x == 0.0:
        return 0.0
    cov = sum((x_vals[i] - mean_x) * (y_vals[i] - mean_y) for i in range(n))
    return cov / var_x


# ---------------------------------------------------------------------------
# SkillEvolutionTracker
# ---------------------------------------------------------------------------

class SkillEvolutionTracker:
    """Tracks skill effectiveness over time with decay detection.

    Each *skill* is a prompt-template, persona configuration, or reusable
    strategy registered by name.  Outcomes are recorded as they occur; the
    tracker maintains rolling statistics and flags skills that are degrading
    or stale.

    Parameters
    ----------
    skills_dir:
        Directory where skill definitions (JSON files) are stored.  The
        tracker scans this directory on initialisation to discover existing
        skills.
    history_path:
        Path to a JSON file used for persistent storage of outcome history.
    """

    # Decay-detection constants
    ROLLING_WINDOW: int = 20
    DECAY_WR_THRESHOLD: float = 0.10  # 10% drop below baseline triggers review
    DEPRECATION_DAYS: int = 30        # Unused for 30 days → flag for deprecation

    def __init__(self, skills_dir: str, history_path: str) -> None:
        self.skills_dir: str = skills_dir
        self.history_path: str = history_path

        # skill_registry: {skill_name: {"registered_at": float, "metadata": dict, ...}}
        self._registry: dict[str, dict[str, Any]] = {}

        # outcome_history: {skill_name: [{"success": bool, "quality_score": float, "timestamp": float}, ...]}
        self._history: dict[str, list[dict[str, Any]]] = {}

        # baseline_win_rates: {skill_name: float} — established at registration
        self._baselines: dict[str, float] = {}

        self._load_or_init()
        self._scan_skills_dir()

        logger.info(
            "SkillEvolutionTracker initialised | skills_dir=%s | history=%s | %d skill(s) registered",
            skills_dir, history_path, len(self._registry),
        )

    # -- Internal helpers ----------------------------------------------------

    def _load_or_init(self) -> None:
        """Load persistent history from disk or start fresh."""
        if os.path.exists(self.history_path):
            try:
                with open(self.history_path, "r", encoding="utf-8") as fh:
                    payload = json.load(fh)
                self._registry = payload.get("registry", {})
                self._history = payload.get("history", {})
                self._baselines = payload.get("baselines", {})
                logger.debug(
                    "Loaded history from %s (%d skills, %d total outcomes)",
                    self.history_path,
                    len(self._registry),
                    sum(len(v) for v in self._history.values()),
                )
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Failed to load history from %s: %s — starting fresh", self.history_path, exc)
                self._registry = {}
                self._history = {}
                self._baselines = {}
        else:
            logger.debug("No history file at %s — starting fresh", self.history_path)

    def _persist(self) -> None:
        """Write current state to the JSON history file."""
        payload = {
            "registry": self._registry,
            "history": self._history,
            "baselines": self._baselines,
            "saved_at": time.time(),
        }
        os.makedirs(os.path.dirname(self.history_path), exist_ok=True) if os.path.dirname(self.history_path) else None
        with open(self.history_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, default=str)
        logger.debug("Persisted skill history to %s", self.history_path)

    def _scan_skills_dir(self) -> None:
        """Discover skill definitions on disk and auto-register any new ones."""
        if not os.path.isdir(self.skills_dir):
            logger.debug("Skills directory does not exist yet: %s", self.skills_dir)
            return
        for entry in os.listdir(self.skills_dir):
            if not entry.endswith(".json"):
                continue
            skill_name = entry[:-5]
            if skill_name not in self._registry:
                skill_path = os.path.join(self.skills_dir, entry)
                try:
                    with open(skill_path, "r", encoding="utf-8") as fh:
                        metadata = json.load(fh)
                except (json.JSONDecodeError, OSError) as exc:
                    logger.warning("Could not read skill file %s: %s", skill_path, exc)
                    metadata = {}
                self.register_skill(skill_name, metadata)
                logger.debug("Auto-registered skill %r from %s", skill_name, skill_path)

    # -- Public API ----------------------------------------------------------

    def register_skill(self, skill_name: str, metadata: dict[str, Any]) -> None:
        """Register a new skill for tracking.

        If the skill already exists its metadata is merged (new keys take
        precedence).

        Parameters
        ----------
        skill_name:
            Unique identifier for the skill.
        metadata:
            Arbitrary metadata dict (e.g. ``{"owner": "Coding-Engine", "tags": ["python"]}``).
        """
        now = time.time()
        if skill_name in self._registry:
            existing = self._registry[skill_name]
            existing["metadata"] = {**existing.get("metadata", {}), **metadata}
            existing["last_updated"] = now
            logger.debug("Updated metadata for skill %r", skill_name)
        else:
            self._registry[skill_name] = {
                "registered_at": now,
                "last_updated": now,
                "metadata": metadata,
            }
            self._history[skill_name] = []
            # Baseline will be set after first batch of outcomes
            self._baselines[skill_name] = 0.0
            logger.info("Registered new skill %r", skill_name)

        self._persist()

    def record_skill_outcome(self, skill_name: str, outcome: dict[str, Any]) -> None:
        """Record the result of applying a skill.

        Parameters
        ----------
        skill_name:
            Skill identifier (must have been :meth:`register_skill`-ed).
        outcome:
            Dict with at least these keys::

                {
                    "success": bool,      # Whether the skill produced a good result
                    "quality_score": float,  # 0.0 .. 1.0 (higher = better)
                    "timestamp": float,   # Optional; defaults to now
                }

        Raises
        ------
        KeyError
            If *skill_name* has not been registered.
        ValueError
            If *outcome* is missing required fields.
        """
        if skill_name not in self._registry:
            raise KeyError(f"Skill {skill_name!r} not registered — call register_skill() first")

        required = {"success", "quality_score"}
        missing = required - set(outcome.keys())
        if missing:
            raise ValueError(f"Outcome dict missing required keys: {missing}")

        # Normalise
        record: dict[str, Any] = {
            "success": bool(outcome["success"]),
            "quality_score": float(outcome["quality_score"]),
            "timestamp": float(outcome.get("timestamp", time.time())),
        }

        self._history[skill_name].append(record)
        self._registry[skill_name]["last_updated"] = time.time()

        # Establish baseline on first ROLLING_WINDOW outcomes
        history = self._history[skill_name]
        if len(history) == self.ROLLING_WINDOW and self._baselines.get(skill_name, 0.0) == 0.0:
            wr = sum(1 for r in history if r["success"]) / len(history)
            self._baselines[skill_name] = wr
            logger.info("Established baseline WR for %s: %.3f", skill_name, wr)

        logger.debug(
            "Recorded outcome for %s | success=%s score=%.3f",
            skill_name, record["success"], record["quality_score"],
        )
        self._persist()

    def compute_skill_effectiveness(self, skill_name: str) -> dict[str, Any]:
        """Compute effectiveness metrics for a skill.

        Returns
        -------
        dict
            ``{"skill_name": str, "total_attempts": int,
            "rolling_window": int, "rolling_wins": int, "rolling_attempts": int,
            "rolling_win_rate": float, "avg_quality_score": float,
            "quality_trend_slope": float, "usage_frequency": float,
            "baseline_wr": float}``
        """
        if skill_name not in self._registry:
            raise KeyError(f"Skill {skill_name!r} not registered")

        history = self._history.get(skill_name, [])
        total = len(history)

        # Rolling window (most recent)
        recent = history[-self.ROLLING_WINDOW:] if total >= self.ROLLING_WINDOW else history
        rolling_wins = sum(1 for r in recent if r["success"])
        rolling_attempts = len(recent)
        rolling_wr = rolling_wins / rolling_attempts if rolling_attempts > 0 else 0.0

        # Average quality score (rolling window)
        avg_quality = (
            sum(r["quality_score"] for r in recent) / rolling_attempts
            if rolling_attempts > 0
            else 0.0
        )

        # Quality trend (linear regression on rolling window)
        if rolling_attempts >= 2:
            x_vals = list(range(rolling_attempts))
            y_vals = [r["quality_score"] for r in recent]
            quality_slope = _linear_regression_slope(x_vals, y_vals)
        else:
            quality_slope = 0.0

        # Usage frequency: outcomes per day (over the full history)
        if total >= 2:
            first_ts = history[0]["timestamp"]
            last_ts = history[-1]["timestamp"]
            days = max((last_ts - first_ts) / 86400.0, 0.001)
            usage_freq = total / days
        else:
            usage_freq = 0.0

        return {
            "skill_name": skill_name,
            "total_attempts": total,
            "rolling_window": self.ROLLING_WINDOW,
            "rolling_wins": rolling_wins,
            "rolling_attempts": rolling_attempts,
            "rolling_win_rate": round(rolling_wr, 4),
            "avg_quality_score": round(avg_quality, 4),
            "quality_trend_slope": round(quality_slope, 6),
            "usage_frequency": round(usage_freq, 4),
            "baseline_wr": round(self._baselines.get(skill_name, 0.0), 4),
        }

    def detect_skill_decay(self, window: int = 20) -> list[dict[str, Any]]:
        """Detect skills that are declining in effectiveness.

        A skill is flagged when **any** of the following are true:

        1. Rolling win-rate has dropped > ``DECAY_WR_THRESHOLD`` (10%)
           below its baseline.
        2. Quality-score trend (linear regression slope) is negative.
        3. Skill has not been used for > ``DEPRECATION_DAYS`` (30) days.

        Parameters
        ----------
        window:
            Number of recent outcomes to examine (default 20).

        Returns
        -------
        list[dict]
            Each dict describes a flagged skill with ``skill_name``,
            ``flag_type``, ``details``, and ``recommended_action``.
        """
        flags: list[dict[str, Any]] = []
        now = time.time()

        for skill_name in self._registry:
            history = self._history.get(skill_name, [])
            if not history:
                # Unused since registration
                reg_at = self._registry[skill_name].get("registered_at", now)
                if (now - reg_at) / 86400.0 > self.DEPRECATION_DAYS:
                    flags.append({
                        "skill_name": skill_name,
                        "flag_type": "DEPRECATION_CANDIDATE",
                        "details": f"No outcomes recorded in {self.DEPRECATION_DAYS}+ days",
                        "recommended_action": "Consider removing or merging this skill",
                    })
                continue

            # Check staleness
            last_used = max(r["timestamp"] for r in history)
            days_since_use = (now - last_used) / 86400.0
            if days_since_use > self.DEPRECATION_DAYS:
                flags.append({
                    "skill_name": skill_name,
                    "flag_type": "STALE_SKILL",
                    "details": f"Last used {days_since_use:.1f} days ago (> {self.DEPRECATION_DAYS} threshold)",
                    "recommended_action": "Review for relevance; deprecate if no longer needed",
                })
                continue  # Don't pile on additional flags for stale skills

            # Need enough data for WR / quality checks
            if len(history) < window:
                continue

            recent = history[-window:]
            rolling_wr = sum(1 for r in recent if r["success"]) / len(recent)
            baseline = self._baselines.get(skill_name, rolling_wr)

            # Flag 1: WR drop
            if baseline > 0 and (baseline - rolling_wr) > self.DECAY_WR_THRESHOLD:
                flags.append({
                    "skill_name": skill_name,
                    "flag_type": "WIN_RATE_DECAY",
                    "details": (
                        f"Rolling WR {rolling_wr:.3f} dropped "
                        f"{baseline - rolling_wr:.3f} below baseline {baseline:.3f}"
                    ),
                    "recommended_action": "Re-tune prompt parameters or A/B test a variant",
                })

            # Flag 2: Negative quality trend
            x_vals = list(range(len(recent)))
            y_vals = [r["quality_score"] for r in recent]
            slope = _linear_regression_slope(x_vals, y_vals)
            if slope < 0:
                flags.append({
                    "skill_name": skill_name,
                    "flag_type": "QUALITY_TREND_NEGATIVE",
                    "details": f"Quality score decreasing (slope={slope:.6f})",
                    "recommended_action": "Refresh prompt with recent best-practice examples",
                })

        logger.info("Decay scan complete | %d skill(s) flagged out of %d", len(flags), len(self._registry))
        return flags

    def recommend_skill_updates(self) -> list[dict[str, Any]]:
        """Generate actionable update recommendations for all tracked skills.

        Combines decay detection with effectiveness rankings to produce a
        prioritised list of skills that need attention.

        Returns
        -------
        list[dict]
            Each recommendation contains ``skill_name``, ``priority``
            (``HIGH`` / ``MEDIUM`` / ``LOW``), ``reason``, and ``suggested_action``.
        """
        recommendations: list[dict[str, Any]] = []
        decay_flags = self.detect_skill_decay()

        # Group flags by skill
        flagged_skills: dict[str, list[dict[str, Any]]] = {}
        for flag in decay_flags:
            flagged_skills.setdefault(flag["skill_name"], []).append(flag)

        for skill_name, flags in flagged_skills.items():
            has_wr_decay = any(f["flag_type"] == "WIN_RATE_DECAY" for f in flags)
            has_quality_decay = any(f["flag_type"] == "QUALITY_TREND_NEGATIVE" for f in flags)
            is_stale = any(f["flag_type"] in ("STALE_SKILL", "DEPRECATION_CANDIDATE") for f in flags)

            if is_stale:
                priority = "LOW"
                reason = "Skill is stale / unused"
                action = "Deprecate or archive if confirmed unused"
            elif has_wr_decay and has_quality_decay:
                priority = "HIGH"
                reason = f"{len(flags)} decay signals: " + ", ".join(f["flag_type"] for f in flags)
                action = "Immediate A/B test with refreshed prompt variant"
            elif has_wr_decay or has_quality_decay:
                priority = "MEDIUM"
                reason = flags[0]["details"]
                action = flags[0]["recommended_action"]
            else:
                priority = "LOW"
                reason = flags[0]["details"]
                action = flags[0]["recommended_action"]

            recommendations.append({
                "skill_name": skill_name,
                "priority": priority,
                "reason": reason,
                "suggested_action": action,
            })

        # Sort: HIGH first, then MEDIUM, then LOW
        priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        recommendations.sort(key=lambda r: priority_order.get(r["priority"], 99))

        return recommendations

    def generate_skill_report(self) -> str:
        """Generate a markdown report of all tracked skills.

        Returns
        -------
        str
            Markdown-formatted skill evolution report.
        """
        lines: list[str] = [
            "# Skill Evolution Report",
            "",
            f"_Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}_",
            f"_Rolling window: {self.ROLLING_WINDOW} attempts | "
            f"Decay threshold: {self.DECAY_WR_THRESHOLD*100:.0f}% WR drop | "
            f"Deprecation: {self.DEPRECATION_DAYS} days unused_",
            "",
        ]

        if not self._registry:
            lines.append("_No skills registered yet._")
            return "\n".join(lines)

        # Summary table
        lines.append("## Summary")
        lines.append("")
        lines.append("| Skill | Total | Rolling WR | Avg Quality | Trend | Baseline | Status |")
        lines.append("|-------|-------|-----------:|------------:|------:|---------:|--------|")

        decay_flags = {f["skill_name"]: f["flag_type"] for f in self.detect_skill_decay()}

        for skill_name in sorted(self._registry.keys()):
            eff = self.compute_skill_effectiveness(skill_name)
            trend_icon = "📈" if eff["quality_trend_slope"] > 0.001 else "📉" if eff["quality_trend_slope"] < -0.001 else "➡️"
            status = "⚠️ " + decay_flags[skill_name] if skill_name in decay_flags else "✅ Healthy"
            lines.append(
                f"| {skill_name} | {eff['total_attempts']} | "
                f"{eff['rolling_win_rate']:.3f} | {eff['avg_quality_score']:.3f} | "
                f"{eff['quality_trend_slope']:+.4f} {trend_icon} | "
                f"{eff['baseline_wr']:.3f} | {status} |"
            )

        lines.append("")

        # Recommendations
        recommendations = self.recommend_skill_updates()
        if recommendations:
            lines.append("## Recommended Updates")
            lines.append("")
            for rec in recommendations:
                emoji = "🔴" if rec["priority"] == "HIGH" else "🟡" if rec["priority"] == "MEDIUM" else "🟢"
                lines.append(f"### {emoji} [{rec['priority']}] {rec['skill_name']}")
                lines.append(f"- **Reason**: {rec['reason']}")
                lines.append(f"- **Action**: {rec['suggested_action']}")
                lines.append("")
        else:
            lines.append("## Recommended Updates")
            lines.append("")
            lines.append("_No updates required — all skills are healthy._")
            lines.append("")

        lines.append("---")
        lines.append(f"_Tracking {len(self._registry)} skill(s) with {sum(len(v) for v in self._history.values())} total outcome(s)_")
        lines.append("")
        return "\n".join(lines)

    def export_skill_snapshots(self, output_dir: str) -> int:
        """Export a JSON snapshot of every skill's current effectiveness.

        Parameters
        ----------
        output_dir:
            Destination directory for the snapshot files.

        Returns
        -------
        int
            Number of snapshots written.
        """
        os.makedirs(output_dir, exist_ok=True)
        count = 0
        for skill_name in self._registry:
            eff = self.compute_skill_effectiveness(skill_name)
            snapshot = {
                **eff,
                "skill_metadata": self._registry[skill_name].get("metadata", {}),
                "exported_at": time.time(),
            }
            path = os.path.join(output_dir, f"{skill_name}_snapshot.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(snapshot, fh, indent=2, default=str)
            count += 1
        logger.info("Exported %d skill snapshots to %s", count, output_dir)
        return count
