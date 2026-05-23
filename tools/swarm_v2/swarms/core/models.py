"""Core Pydantic data models for the multi-agent swarm system.

This module defines all typed data structures used across swarm engines,
including agent configuration, messages, tasks, results, memory entries,
and exported skills.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


# ─── Agent Identity ──────────────────────────────────────────────


class AgentRole(str, Enum):
    """Enumeration of predefined agent roles within a swarm.

    Each role maps to a specific responsibility in the multi-agent pipeline.
    """

    CODE_GENERATOR = "code_generator"
    CODE_REVIEWER = "code_reviewer"
    TEST_WRITER = "test_writer"
    IMPACT_ANALYZER = "impact_analyzer"
    RESEARCHER = "researcher"
    RISK_CONTROLLER = "risk_controller"
    STRATEGIST = "strategist"
    TACTICIAN = "tactician"


class AgentConfig(BaseModel):
    """Configuration schema for an individual swarm agent.

    Parameters
    ----------
    role :
        The functional role this agent plays in the swarm.
    model :
        The LLM model identifier (e.g. ``"gpt-4o"``, ``"claude-sonnet"``).
    temperature :
        Sampling temperature for the model.
    max_tokens :
        Maximum tokens to generate per request.
    system_prompt :
        System-level prompt that defines agent behavior.
    tools_allowed :
        Names of tools the agent is permitted to invoke.
    read_only :
        When ``True`` the agent is restricted to read-only operations.
    """

    role: AgentRole
    model: str  # e.g. "gpt-4o", "claude-sonnet"
    temperature: float = 0.7
    max_tokens: int = 4096
    system_prompt: str = ""
    tools_allowed: list[str] = Field(default_factory=list)
    read_only: bool = True  # safety default


# ─── Messages ────────────────────────────────────────────────────


class MessageType(str, Enum):
    """Enumeration of message types used on the swarm message bus."""

    TASK_ASSIGNMENT = "task_assignment"
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    TEST_RESULT = "test_result"
    IMPACT_ANALYSIS = "impact_analysis"
    RESEARCH_FINDING = "research_finding"
    VOTE = "vote"
    CONSENSUS = "consensus"
    ERROR = "error"
    FINAL_OUTPUT = "final_output"


class SwarmMessage(BaseModel):
    r"""A single message exchanged between agents on the message bus.

    Parameters
    ----------
    id :
        Unique message identifier (12-char hex).
    msg_type :
        Semantic category of the message.
    sender :
        ``agent_id`` of the originating agent.
    recipients :
        List of target ``agent_id``\ s; ``["*"]`` means broadcast.
    payload :
        Arbitrary key-value data carried by the message.
    timestamp :
        UTC timestamp of message creation.
    parent_id :
        Reference to a parent message for threaded conversations.
    """

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    msg_type: MessageType
    sender: str  # agent_id
    recipients: list[str]  # agent_ids; ["*"] = broadcast
    payload: dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    parent_id: Optional[str] = None  # for threading


# ─── Task Definitions ────────────────────────────────────────────


class TaskStatus(str, Enum):
    """Lifecycle states for a :class:`SwarmTask`."""

    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_REVISION = "needs_revision"


class SwarmTask(BaseModel):
    r"""Represents a unit of work dispatched to the swarm.

    Parameters
    ----------
    id :
        Unique task identifier (12-char hex).
    task_type :
        Swarm category — e.g. ``"coding"``, ``"pr_review"``, ``"gh_actions"``.
    description :
        Human-readable summary of the task.
    inputs :
        Task-specific input parameters.
    status :
        Current lifecycle state of the task.
    priority :
        Priority level — ``1`` = high, ``2`` = medium, ``3`` = low.
    assigned_agents :
        ``agent_id``\ s currently working on this task.
    results :
        Accumulated outputs from agents.
    created_at :
        UTC timestamp when the task was created.
    completed_at :
        UTC timestamp when the task finished (``None`` until then).
    """

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    task_type: str  # "coding", "pr_review", "gh_actions", ...
    description: str
    inputs: dict[str, Any]  # task-specific inputs
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 1  # 1=high, 2=med, 3=low
    assigned_agents: list[str] = Field(default_factory=list)
    results: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


# ─── Swarm Results ───────────────────────────────────────────────


class CodeArtifact(BaseModel):
    """A generated code file together with tests and review metadata.

    Parameters
    ----------
    filepath :
        Relative path where the code should be written.
    language :
        Programming language identifier.
    source_code :
        The generated source text.
    tests :
        Optional accompanying test code.
    test_results :
        Structured test-run summary (passed, failed, coverage).
    review_comments :
        Structured feedback from code-review agents.
    """

    filepath: str
    language: str
    source_code: str
    tests: Optional[str] = None
    test_results: Optional[dict] = None  # {passed: int, failed: int, coverage: float}
    review_comments: list[dict] = Field(default_factory=list)


class PRReviewResult(BaseModel):
    """Aggregated output of a PR review swarm run.

    Parameters
    ----------
    pr_number :
        GitHub pull-request number.
    pr_title :
        Title of the pull request.
    impact_score :
        Numeric impact score ranging from ``0`` to ``100``.
    risk_level :
        Qualitative risk assessment.
    affected_files :
        List of file paths touched by the PR.
    breaking_changes :
        Descriptions of potentially breaking modifications.
    test_coverage_impact :
        Human-readable summary of coverage changes.
    recommendations :
        Actionable suggestions from the review agents.
    approved :
        ``True`` when all agents approve and the impact score exceeds the threshold.
    """

    pr_number: int
    pr_title: str
    impact_score: float  # 0-100
    risk_level: Literal["low", "medium", "high", "critical"]
    affected_files: list[str]
    breaking_changes: list[str]
    test_coverage_impact: str
    recommendations: list[str]
    approved: bool = False


class GitHubActionsResult(BaseModel):
    """Result of analysing GitHub Actions workflow runs.

    Parameters
    ----------
    repo :
        Repository identifier (``owner/repo``).
    failed_jobs :
        Jobs whose most recent conclusion is ``failure``.
    flaky_jobs :
        Jobs with an intermittent pass/fail pattern.
    stale_jobs :
        Jobs not run in a configurable number of days.
    cancelled_jobs :
        Jobs explicitly cancelled.
    recommendations :
        Actionable remediation suggestions.
    """

    repo: str
    failed_jobs: list[dict]  # [{name, conclusion, run_url, failed_since}]
    flaky_jobs: list[dict]  # intermittently failing
    stale_jobs: list[dict]  # not run in > N days
    cancelled_jobs: list[dict]
    recommendations: list[str]


class ResearchFinding(BaseModel):
    """A single finding produced by a research agent.

    Parameters
    ----------
    source :
        Origin of the claim (e.g. URL, paper title).
    confidence :
        Confidence score between ``0`` and ``1``.
    claim :
        The factual assertion.
    evidence :
        Supporting data points or references.
    contradictions :
        Known counter-evidence or conflicting claims.
    """

    source: str
    confidence: float  # 0-1
    claim: str
    evidence: list[str]
    contradictions: list[str] = Field(default_factory=list)


class ResearchResult(BaseModel):
    """Aggregated output of a research swarm run.

    Parameters
    ----------
    topic :
        The research topic or question.
    findings :
        Individual findings from all research agents.
    consensus_claims :
        Claims backed by multiple agents without contradiction.
    disputed_claims :
        Claims where agents disagree.
    gaps :
        Areas where no evidence was found.
    sources :
        Unique list of all sources consulted.
    """

    topic: str
    findings: list[ResearchFinding]
    consensus_claims: list[str]
    disputed_claims: list[str]
    gaps: list[str]
    sources: list[str]


class VoteResult(BaseModel):
    """A single vote cast by an ensemble agent.

    Parameters
    ----------
    agent_id :
        The voting agent's identifier.
    vote :
        The vote payload (type varies by ensemble task).
    confidence :
        Agent's confidence in its vote (``0`` to ``1``).
    reasoning :
        Explanation supporting the vote.
    """

    agent_id: str
    vote: Any
    confidence: float
    reasoning: str


class EnsembleResult(BaseModel):
    """Aggregated result of an ensemble prediction swarm.

    Parameters
    ----------
    predictions :
        Individual votes from all ensemble agents.
    aggregated_result :
        Final blended prediction.
    confidence_interval :
        Lower and upper bounds of aggregate confidence.
    dissenting_opinions :
        Reasoning from agents whose votes diverged from the majority.
    """

    predictions: list[VoteResult]
    aggregated_result: Any
    confidence_interval: tuple[float, float]
    dissenting_opinions: list[str]


class HierarchicalSignal(BaseModel):
    """A signal emitted by a hierarchical swarm agent.

    Parameters
    ----------
    level :
        Layer in the hierarchy — ``"strategic"``, ``"tactical"``, or ``"execution"``.
    agent_id :
        The emitting agent's identifier.
    signal_type :
        Semantic category — e.g. ``"trend"``, ``"regime"``, ``"entry"``.
    payload :
        Arbitrary signal data.
    confidence :
        Confidence score (``0`` to ``1``).
    timestamp :
        UTC timestamp of signal creation.
    """

    level: Literal["strategic", "tactical", "execution"]
    agent_id: str
    signal_type: str  # e.g. "trend", "regime", "entry"
    payload: dict[str, Any]
    confidence: float
    timestamp: datetime


# ─── Memory / Skill ──────────────────────────────────────────────


class MemoryEntry(BaseModel):
    """A persisted memory item in the swarm's vector store.

    Parameters
    ----------
    id :
        Unique memory identifier (12-char hex).
    content :
        Textual information to remember.
    embedding :
        Optional pre-computed vector embedding.
    metadata :
        Arbitrary key-value metadata.
    tags :
        Categorical labels for filtering.
    source_swarm :
        Name of the swarm that produced this entry.
    created_at :
        UTC timestamp of persistence.
    """

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    content: str  # text to remember
    embedding: Optional[list[float]] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    source_swarm: str  # which swarm produced this
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ExportedSkill(BaseModel):
    r"""A reusable skill package derived from swarm memory and configuration.

    Parameters
    ----------
    name :
        Human-readable skill name.
    description :
        Short summary of what the skill does.
    version :
        Semantic version string.
    swarm_type :
        Swarm category this skill originates from.
    parameters :
        Tunable parameters for the skill.
    examples :
        Usage examples for few-shot prompting.
    system_prompt :
        System prompt derived from swarm configuration.
    knowledge_base :
        ``MemoryEntry.id``\ s that form the skill's knowledge.
    created_at :
        UTC timestamp of skill creation.
    """

    name: str
    description: str
    version: str = "1.0.0"
    swarm_type: str
    parameters: dict[str, Any]  # tunable params
    examples: list[dict[str, Any]]  # usage examples
    system_prompt: str  # derived from swarm config
    knowledge_base: list[str]  # memory entry IDs
    created_at: datetime = Field(default_factory=datetime.utcnow)
