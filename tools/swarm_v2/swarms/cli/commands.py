"""Click commands for the swarm CLI."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime

import click

from swarms.core.llm_client import LLMClient
from swarms.core.memory import SwarmMemory
from swarms.core.messaging import MessageBus
from swarms.core.models import (
    AgentConfig,
    AgentRole,
    ExportedSkill,
    MemoryEntry,
    SwarmTask,
)
from swarms.core.registry import AgentRegistry
from swarms.core.safety import SafetyEnforcer

logger = logging.getLogger(__name__)


def _setup_infrastructure() -> tuple[SwarmMemory, MessageBus, AgentRegistry, SafetyEnforcer]:
    """Create shared infrastructure for all swarm commands."""
    memory = SwarmMemory(collection_name="cli_memory", persist_dir="./cli_memory_store")
    bus = MessageBus()
    registry = AgentRegistry()
    safety = SafetyEnforcer(read_only=True)
    return memory, bus, registry, safety


def _print_table(headers: list[str], rows: list[list[str]]) -> None:
    """Print a formatted ASCII table."""
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))

    sep = "+-" + "-+-".join("-" * w for w in col_widths) + "-+"
    header_line = "| " + " | ".join(h.ljust(w) for h, w in zip(headers, col_widths)) + " |"
    click.echo(sep)
    click.echo(header_line)
    click.echo(sep)
    for row in rows:
        row_line = "| " + " | ".join(str(cell).ljust(w) for cell, w in zip(row, col_widths)) + " |"
        click.echo(row_line)
    click.echo(sep)


def _print_json(data) -> None:
    """Print data as formatted JSON."""
    click.echo(json.dumps(data, indent=2, default=str))


# ─── Swarm Commands ──────────────────────────────────────────────────


@click.command()
@click.argument("task_file", type=click.Path(exists=True))
@click.option("--agents", default=3, help="Number of code generator agents")
@click.option("--models", default="gpt-4o", help="Comma-separated model list")
@click.option("--strict", is_flag=True, help="Enable strict mode")
@click.pass_context
def coding_command(ctx, task_file, agents, models, strict):
    """Run the coding swarm on a task file."""
    with open(task_file, "r", encoding="utf-8") as fh:
        description = fh.read()

    memory, bus, registry, safety = _setup_infrastructure()

    async def _run():
        from swarms.engines.coding_swarm import CodingSwarmOrchestrator
        orch = CodingSwarmOrchestrator(
            memory=memory, bus=bus, registry=registry, safety=safety, llm=LLMClient()
        )
        task = SwarmTask(
            task_type="coding",
            description=description,
            inputs={
                "description": description,
                "num_agents": agents,
                "models": models.split(","),
                "strict": strict,
                "max_revisions": 3,
            },
        )
        return await orch.execute(task)

    result = asyncio.run(_run())
    click.echo(f"Generated {result.get('artifact_count', 0)} code artifacts")
    for art in result.get("artifacts", []):
        click.echo(f"  - {art['filepath']} ({art['language']})")
    memory.close()


@click.command()
@click.argument("repo")
@click.option("--pr", type=int, default=None, help="PR number to review")
@click.option("--all-open", is_flag=True, help="Review all open PRs")
@click.pass_context
def pr_review_command(ctx, repo, pr, all_open):
    """Run the PR review swarm on a repository."""
    memory, bus, registry, safety = _setup_infrastructure()

    async def _run():
        from swarms.engines.pr_review_swarm import PRReviewSwarmOrchestrator
        orch = PRReviewSwarmOrchestrator(
            memory=memory, bus=bus, registry=registry, safety=safety, llm=LLMClient()
        )
        task = SwarmTask(
            task_type="pr_review",
            description=f"Review PR in {repo}",
            inputs={
                "repo": repo,
                "pr_number": pr or 0,
                "pr_title": f"PR #{pr}" if pr else "All Open PRs",
                "all_open": all_open,
            },
        )
        return await orch.execute(task)

    result = asyncio.run(_run())
    click.echo(f"PR #{result.get('pr_number', 'N/A')}: {result.get('pr_title', '')}")
    click.echo(f"Impact Score: {result.get('impact_score', 0):.1f}/100")
    click.echo(f"Risk Level: {result.get('risk_level', 'unknown')}")
    click.echo(f"Approved: {result.get('approved', False)}")
    if result.get("recommendations"):
        click.echo("Recommendations:")
        for rec in result["recommendations"]:
            click.echo(f"  - {rec}")
    memory.close()


@click.command()
@click.argument("repo")
@click.option("--since", default="30d", help="Analysis window (e.g. 30d)")
@click.option("--notify", is_flag=True, help="Send notifications")
@click.pass_context
def actions_command(ctx, repo, since, notify):
    """Monitor GitHub Actions for a repository."""
    memory, bus, registry, safety = _setup_infrastructure()

    since_days = int(since.replace("d", ""))

    async def _run():
        from swarms.engines.github_actions_swarm import GitHubActionsSwarmOrchestrator
        orch = GitHubActionsSwarmOrchestrator(
            memory=memory, bus=bus, registry=registry, safety=safety, llm=LLMClient()
        )
        task = SwarmTask(
            task_type="gh_actions",
            description=f"Monitor GitHub Actions for {repo}",
            inputs={
                "repo": repo,
                "since_days": since_days,
                "notify": notify,
            },
        )
        return await orch.execute(task)

    result = asyncio.run(_run())
    click.echo(f"Repository: {result.get('repo', repo)}")
    click.echo(f"Failed jobs: {len(result.get('failed_jobs', []))}")
    click.echo(f"Flaky jobs: {len(result.get('flaky_jobs', []))}")
    click.echo(f"Stale jobs: {len(result.get('stale_jobs', []))}")
    click.echo(f"Cancelled jobs: {len(result.get('cancelled_jobs', []))}")
    if result.get("recommendations"):
        click.echo("Recommendations:")
        for rec in result["recommendations"]:
            click.echo(f"  - {rec}")
    if notify:
        click.echo("Notifications sent.")
    memory.close()


@click.command()
@click.argument("topic")
@click.option("--depth", type=int, default=3, help="Research depth (1-5)")
@click.option("--route", type=click.Choice(["A", "B", "C", "D"]), default="A", help="Research route")
@click.pass_context
def research_command(ctx, topic, depth, route):
    """Run the research swarm on a topic."""
    memory, bus, registry, safety = _setup_infrastructure()

    depth = max(1, min(5, depth))

    async def _run():
        from swarms.engines.research_swarm import ResearchSwarmOrchestrator
        orch = ResearchSwarmOrchestrator(
            memory=memory, bus=bus, registry=registry, safety=safety, llm=LLMClient()
        )
        task = SwarmTask(
            task_type="research",
            description=f"Research: {topic}",
            inputs={
                "topic": topic,
                "depth": depth,
                "route": route,
            },
        )
        return await orch.execute(task)

    result = asyncio.run(_run())
    click.echo(f"Topic: {result.get('topic', topic)}")
    click.echo(f"Findings: {len(result.get('findings', []))}")
    click.echo(f"Consensus claims: {len(result.get('consensus_claims', []))}")
    click.echo(f"Disputed claims: {len(result.get('disputed_claims', []))}")
    if result.get("gaps"):
        click.echo(f"Research gaps: {len(result['gaps'])}")
    memory.close()


@click.command()
@click.argument("task")
@click.option("--agents", default=5, help="Number of prediction agents")
@click.option("--confidence-threshold", type=float, default=0.8, help="Confidence threshold")
@click.pass_context
def ensemble_command(ctx, task, agents, confidence_threshold):
    """Run the ensemble swarm for prediction tasks."""
    memory, bus, registry, safety = _setup_infrastructure()

    async def _run():
        from swarms.engines.ensemble_swarm import EnsembleSwarmOrchestrator
        orch = EnsembleSwarmOrchestrator(memory=memory, bus=bus, registry=registry, safety=safety)
        swarm_task = SwarmTask(
            task_type="ensemble",
            description=f"Ensemble prediction: {task}",
            inputs={
                "prediction_task": task,
                "num_agents": agents,
                "confidence_threshold": confidence_threshold,
                "task_type": "classification",
            },
        )
        return await orch.execute(swarm_task)

    result = asyncio.run(_run())
    click.echo(f"Aggregated result: {result.get('aggregated_result')}")
    ci = result.get("confidence_interval", [0, 0])
    click.echo(f"Confidence interval: [{ci[0]:.3f}, {ci[1]:.3f}]")
    click.echo(f"Predictions: {len(result.get('predictions', []))}")
    if result.get("dissenting_opinions"):
        click.echo(f"Dissenting opinions: {len(result['dissenting_opinions'])}")
    memory.close()


@click.command()
@click.argument("task")
@click.option("--strategists", default=2, help="Number of strategist agents")
@click.option("--tacticians", default=3, help="Number of tactician agents")
@click.pass_context
def hierarchical_command(ctx, task, strategists, tacticians):
    """Run the hierarchical swarm for decision making."""
    memory, bus, registry, safety = _setup_infrastructure()

    async def _run():
        from swarms.engines.hierarchical_swarm import HierarchicalSwarmOrchestrator
        orch = HierarchicalSwarmOrchestrator(memory=memory, bus=bus, registry=registry, safety=safety)
        swarm_task = SwarmTask(
            task_type="hierarchical",
            description=f"Hierarchical decision: {task}",
            inputs={
                "task": task,
                "strategist_count": strategists,
                "tactician_count": tacticians,
                "assets": ["AAPL", "GOOGL", "MSFT"],
            },
        )
        return await orch.execute(swarm_task)

    result = asyncio.run(_run())
    click.echo(f"Signals generated: {result.get('signal_count', 0)}")
    click.echo(f"Vetoed: {result.get('vetoed', False)}")
    for sig in result.get("signals", [])[:5]:
        click.echo(f"  [{sig['level']}] {sig['signal_type']} from {sig['agent_id']} (conf={sig['confidence']:.2f})")
    memory.close()


# ─── Memory Commands ─────────────────────────────────────────────────


@click.group()
def memory_command():
    """Search and manage swarm memory."""


@memory_command.command(name="search")
@click.argument("query")
@click.option("--tags", multiple=True, help="Filter by tags")
@click.pass_context
def memory_search(ctx, query, tags):
    """Search memory by query."""
    memory = SwarmMemory(collection_name="cli_memory", persist_dir="./cli_memory_store")
    results = memory.search(query, n_results=10, tags=list(tags) if tags else None)
    click.echo(f"Found {len(results)} results for '{query}':")
    for entry in results:
        click.echo(f"  [{entry.id}] {entry.content[:80]}...")
    memory.close()


@memory_command.command(name="export-skill")
@click.argument("query")
@click.argument("skill_name")
@click.pass_context
def memory_export_skill(ctx, query, skill_name):
    """Export memory entries as a skill."""
    memory = SwarmMemory(collection_name="cli_memory", persist_dir="./cli_memory_store")
    skill = memory.export_as_skill(query, skill_name)
    click.echo(f"Exported skill: {skill.name}")
    click.echo(f"Description: {skill.description}")
    click.echo(f"Knowledge base entries: {len(skill.knowledge_base)}")
    memory.close()


# ─── Skill Commands ──────────────────────────────────────────────────


@click.group()
def skill_command():
    """List and export swarm skills."""


@skill_command.command(name="list")
@click.pass_context
def skill_list(ctx):
    """List all exported skills."""
    from swarms.memory.skill_store import SkillStore
    memory = SwarmMemory(collection_name="cli_memory", persist_dir="./cli_memory_store")
    store = SkillStore(memory=memory, output_dir="./skills")
    skills = []
    if os.path.isdir("./skills"):
        for fname in os.listdir("./skills"):
            if fname.endswith(".json"):
                import json as _json
                with open(os.path.join("./skills", fname), "r", encoding="utf-8") as fh:
                    data = _json.load(fh)
                skills.append((data.get("name", fname), data.get("description", "")))
    if skills:
        _print_table(["Name", "Description"], skills)
    else:
        click.echo("No skills found.")
    memory.close()


@skill_command.command(name="export")
@click.argument("skill_name")
@click.option("--format", "fmt", type=click.Choice(["claude-md", "claude-json", "openai"]), default="claude-md")
@click.pass_context
def skill_export(ctx, skill_name, fmt):
    """Export a skill to a specific format."""
    from swarms.memory.skill_store import SkillStore
    memory = SwarmMemory(collection_name="cli_memory", persist_dir="./cli_memory_store")
    store = SkillStore(memory=memory, output_dir="./skills")
    skill = store.load_skill(skill_name)
    if skill is None:
        click.echo(f"Skill '{skill_name}' not found. Creating from memory...")
        skill = store.create_skill_from_swarm("coding", skill_name, examples=[])
        store.save_skill(skill)

    if fmt == "claude-md":
        path = store.export_to_claude_skill(skill)
    elif fmt == "claude-json":
        path = store.export_to_claude_project(skill)
    elif fmt == "openai":
        # OpenAI format: JSON with function-calling style
        path = store.export_to_claude_project(skill)
        click.echo("Note: openai format uses JSON project export as base.")
    else:
        path = store.export_to_claude_skill(skill)

    click.echo(f"Exported to: {path}")
    memory.close()
