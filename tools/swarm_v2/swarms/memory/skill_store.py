"""Skill store for exporting swarm knowledge as reusable Claude skills."""

import json
import os
from datetime import datetime
from typing import TYPE_CHECKING, Optional

import yaml

from swarms.core.models import ExportedSkill, MemoryEntry

if TYPE_CHECKING:
    from swarms.core.memory import SwarmMemory


# ── Defaults derived from swarm configurations ───────────────────

_DEFAULT_SYSTEM_PROMPTS: dict[str, str] = {
    "coding": (
        "You are an expert software engineer. Write clean, well-tested code. "
        "Always include unit tests with any code you generate. Follow PEP 8 "
        "and provide docstrings for all public functions."
    ),
    "pr_review": (
        "You are a senior code reviewer. Analyze pull requests for impact, "
        "risk, and quality. Provide actionable recommendations."
    ),
    "gh_actions": (
        "You are a DevOps expert specializing in CI/CD pipeline analysis. "
        "Detect flaky tests, stale workflows, and resource issues."
    ),
    "research": (
        "You are a research analyst. Use epistemic triangulation: cross-verify "
        "findings across multiple sources, flag contradictions, and report "
        "confidence scores for every claim."
    ),
    "ensemble": (
        "You are a prediction aggregator. Combine multiple expert opinions "
        "using weighted voting based on each expert's confidence and track "
        "record."
    ),
    "hierarchical": (
        "You are a strategic decision-making system. Operate across three "
        "levels: strategic (macro signals), tactical (asset-specific "
        "predictions), and execution (position sizing and validation)."
    ),
}

_DEFAULT_DESCRIPTIONS: dict[str, str] = {
    "coding": "Generate production-ready code with mandatory tests.",
    "pr_review": "Analyze pull requests for impact, risk, and quality.",
    "gh_actions": "Monitor and diagnose GitHub Actions workflow issues.",
    "research": "Deep research with cross-source triangulation.",
    "ensemble": "Weighted ensemble aggregation across predictors.",
    "hierarchical": "Multi-layer strategic/tactical/execution decision system.",
}

_DEFAULT_PARAMETERS: dict[str, dict] = {
    "coding": {
        "test_framework": "pytest",
        "max_revision_loops": 3,
        "test_coverage_threshold": 80.0,
        "strict_mode": False,
    },
    "pr_review": {
        "impact_threshold": 50.0,
        "risk_weights": {"code": 0.4, "test": 0.3, "dependency": 0.3},
    },
    "gh_actions": {
        "analysis_window_days": 30,
        "max_runs": 100,
        "flakiness_threshold": 0.2,
    },
    "research": {
        "min_confidence": 0.7,
        "max_researchers": 5,
        "cross_verify": True,
    },
    "ensemble": {
        "aggregation": "weighted_majority",
        "confidence_threshold": 0.8,
        "spawn_extra_agents": True,
    },
    "hierarchical": {
        "strategist_count": 2,
        "tactician_count": 3,
        "risk_controller": True,
    },
}


class SkillStore:
    """Manages the creation, persistence, and export of swarm skills.

    A *skill* is a reusable package of swarm knowledge: system prompts,
    tunable parameters, usage examples, and references to the memory
    entries that informed it.  ``SkillStore`` can persist skills locally
    and export them to formats compatible with Claude (markdown with
    YAML frontmatter) and Claude Projects (JSON).
    """

    def __init__(
        self,
        memory: "SwarmMemory",
        output_dir: str = "./skills",
    ) -> None:
        """Initialise the skill store.

        Args:
            memory: The swarm memory instance used to search and
                retrieve knowledge entries.
            output_dir: Directory where exported skill files are written.
        """
        self.memory = memory
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    # ── Skill lifecycle ────────────────────────────────────────────

    def create_skill_from_swarm(
        self,
        swarm_type: str,
        skill_name: str,
        examples: list[dict],
    ) -> ExportedSkill:
        """Create a new :class:`ExportedSkill` from a swarm configuration.

        Args:
            swarm_type: One of the swarm type keys (e.g. ``"coding"``,
                ``"research"``).
            skill_name: Human-readable name for the skill.
            examples: List of usage-example dicts.  Each dict should
                contain at least an ``input`` and ``output`` key.

        Returns:
            A populated :class:`ExportedSkill` instance.
        """
        description = _DEFAULT_DESCRIPTIONS.get(
            swarm_type,
            f"Swarm skill for {swarm_type} tasks.",
        )
        system_prompt = _DEFAULT_SYSTEM_PROMPTS.get(
            swarm_type,
            "You are a helpful AI assistant.",
        )
        parameters = _DEFAULT_PARAMETERS.get(swarm_type, {})

        # Retrieve relevant memory entries to seed the knowledge base
        memories = self.memory.search(skill_name, n_results=10)
        knowledge_base = [m.id for m in memories]

        return ExportedSkill(
            name=skill_name,
            description=description,
            swarm_type=swarm_type,
            parameters=parameters,
            examples=examples,
            system_prompt=system_prompt,
            knowledge_base=knowledge_base,
        )

    # ── Local persistence ──────────────────────────────────────────

    def _skill_path(self, skill_name: str) -> str:
        """Return the on-disk path for *skill_name*."""
        safe_name = skill_name.replace(" ", "_").lower()
        return os.path.join(self.output_dir, f"{safe_name}.json")

    def save_skill(self, skill: ExportedSkill) -> str:
        """Persist *skill* to disk as JSON.

        Returns:
            The path to the written file.
        """
        path = self._skill_path(skill.name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(skill.model_dump_json(indent=2))
        return path

    def load_skill(self, skill_name: str) -> Optional[ExportedSkill]:
        """Load a skill from disk.

        Args:
            skill_name: The human-readable skill name.

        Returns:
            The loaded :class:`ExportedSkill`, or ``None`` if not found.
        """
        path = self._skill_path(skill_name)
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return ExportedSkill.model_validate(data)

    def search_skills(self, query: str) -> list[ExportedSkill]:
        """Search stored skills by *query* (matches name or description).

        This is a simple filename-based scan; for heavy use consider
        indexing skills in the vector store.

        Args:
            query: Substring to match against skill names.

        Returns:
            List of matching :class:`ExportedSkill` instances.
        """
        query_lower = query.lower()
        matches: list[ExportedSkill] = []
        if not os.path.isdir(self.output_dir):
            return matches
        for fname in os.listdir(self.output_dir):
            if not fname.endswith(".json"):
                continue
            path = os.path.join(self.output_dir, fname)
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            skill = ExportedSkill.model_validate(data)
            if query_lower in skill.name.lower() or query_lower in skill.description.lower():
                matches.append(skill)
        return matches

    # ── Claude Skill export (Markdown + YAML frontmatter) ──────────

    def export_to_claude_skill(self, skill: ExportedSkill) -> str:
        """Export *skill* to a Claude-compatible markdown file.

        The file contains YAML frontmatter followed by a markdown body
        that includes the system prompt and usage examples.

        Args:
            skill: The skill to export.

        Returns:
            Absolute path to the generated ``.md`` file.
        """
        safe_name = skill.name.replace(" ", "_").lower()
        path = os.path.join(self.output_dir, f"{safe_name}_claude_skill.md")

        frontmatter = {
            "name": skill.name,
            "description": skill.description,
            "version": skill.version,
            "swarm_type": skill.swarm_type,
            "tools": list(skill.parameters.get("tools_allowed", [])),
            "parameters": skill.parameters,
        }

        lines: list[str] = []
        lines.append("---")
        lines.append(yaml.dump(frontmatter, sort_keys=False))
        lines.append("---")
        lines.append("")
        lines.append(f"# {skill.name}")
        lines.append("")
        lines.append(f"{skill.description}")
        lines.append("")
        lines.append("## System Prompt")
        lines.append("")
        lines.append(skill.system_prompt)
        lines.append("")
        lines.append("## Examples")
        lines.append("")
        for idx, ex in enumerate(skill.examples, start=1):
            lines.append(f"### Example {idx}")
            lines.append("")
            lines.append("**Input:**")
            lines.append("```")
            lines.append(json.dumps(ex.get("input", ""), indent=2))
            lines.append("```")
            lines.append("")
            lines.append("**Output:**")
            lines.append("```")
            lines.append(json.dumps(ex.get("output", ""), indent=2))
            lines.append("```")
            lines.append("")
        lines.append("## Knowledge Base")
        lines.append("")
        lines.append(
            f"This skill is informed by **{len(skill.knowledge_base)}** "
            "memory entries from swarm runs."
        )
        if skill.knowledge_base:
            lines.append("")
            lines.append("Referenced memory IDs:")
            lines.append("")
            for mem_id in skill.knowledge_base:
                lines.append(f"- `{mem_id}`")

        with open(path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))

        return os.path.abspath(path)

    # ── Claude Project export (JSON) ───────────────────────────────

    def export_to_claude_project(self, skill: ExportedSkill) -> str:
        """Export *skill* to a Claude Project-compatible JSON file.

        The JSON contains a ``system_prompt`` field and an
        ``example_conversations`` array suitable for Claude Projects.

        Args:
            skill: The skill to export.

        Returns:
            Absolute path to the generated ``.json`` file.
        """
        safe_name = skill.name.replace(" ", "_").lower()
        path = os.path.join(self.output_dir, f"{safe_name}_claude_project.json")

        example_conversations: list[dict] = []
        for ex in skill.examples:
            messages: list[dict] = []
            user_input = ex.get("input", "")
            assistant_output = ex.get("output", "")
            if user_input:
                messages.append({"role": "user", "content": str(user_input)})
            if assistant_output:
                messages.append(
                    {"role": "assistant", "content": str(assistant_output)}
                )
            example_conversations.append({"messages": messages})

        payload = {
            "name": skill.name,
            "description": skill.description,
            "version": skill.version,
            "system_prompt": skill.system_prompt,
            "example_conversations": example_conversations,
            "parameters": skill.parameters,
            "knowledge_base_ids": skill.knowledge_base,
        }

        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)

        return os.path.abspath(path)
