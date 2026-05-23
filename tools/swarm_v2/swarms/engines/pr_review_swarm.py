"""PR review swarm engine.

This module implements :class:`PRReviewSwarmOrchestrator`, which reviews
open pull-requests with multi-agent impact analysis.

Pipeline
--------
1. Fetch PR data (title, description, files changed, diff)
2. Fan-out in parallel:
   a) impact_analyzer → affected modules, dependency graph, breaking change detection
   b) code_reviewer → code quality, patterns, security issues
   c) risk_controller → test coverage impact, rollback complexity
3. Collect all analyses
4. Aggregate into PRReviewResult:
   - impact_score = weighted average of all agent scores
   - risk_level = max(risk_controller.risk, impact_analyzer.risk)
   - approved = all agents approve AND impact_score > threshold
5. Store in memory
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Optional

from swarms.core.base_orchestrator import BaseOrchestrator
from swarms.core.llm_client import LLMClient
from swarms.core.memory import SwarmMemory
from swarms.core.messaging import MessageBus
from swarms.core.models import (
    AgentConfig,
    AgentRole,
    MemoryEntry,
    PRReviewResult,
    SwarmMessage,
    SwarmTask,
    TaskStatus,
)
from swarms.core.registry import AgentRegistry
from swarms.core.safety import SafetyEnforcer
from swarms.workers.code_reviewer import CodeReviewerWorker
from swarms.workers.impact_analyzer import ImpactAnalyzerWorker

logger = logging.getLogger(__name__)


class PRReviewSwarmOrchestrator(BaseOrchestrator):
    """Reviews open PRs with multi-agent impact analysis.

    Fetches PR data and fans-out to **impact_analyzer**, **code_reviewer**,
    and **risk_controller** agents in parallel.  Results are aggregated into
    a :class:`PRReviewResult` with a weighted impact score and a boolean
    approval decision.

    Parameters
    ----------
    memory :
        Persistent vector-store memory.
    bus :
        Async message bus.
    registry :
        Agent registry.
    safety :
        Safety enforcer.
    approval_threshold :
        Minimum impact score (0-100) required for approval.
    """

    def __init__(
        self,
        memory: SwarmMemory,
        bus: MessageBus,
        registry: AgentRegistry,
        safety: SafetyEnforcer,
        approval_threshold: float = 75.0,
        llm: Optional[LLMClient] = None,
    ) -> None:
        super().__init__(memory, bus, registry, safety)
        self.approval_threshold = approval_threshold
        self.llm: Optional[LLMClient] = llm

        # Worker references — populated by :meth:`create_agents`
        self._impact_analyzer: ImpactAnalyzerWorker | None = None
        self._code_reviewer: CodeReviewerWorker | None = None
        self._risk_controller: CodeReviewerWorker | None = None

    # ------------------------------------------------------------------
    # Agent lifecycle
    # ------------------------------------------------------------------

    def get_required_agents(self) -> list[AgentRole]:
        """Return required agent roles.

        One each of: ``IMPACT_ANALYZER``, ``CODE_REVIEWER``,
        ``RISK_CONTROLLER``.
        """
        return [
            AgentRole.IMPACT_ANALYZER,
            AgentRole.CODE_REVIEWER,
            AgentRole.RISK_CONTROLLER,
        ]

    def create_agents(self) -> list[str]:
        """Instantiate and register the three specialist agents.

        Returns
        -------
        list[str]
            ``agent_id``\\ s of the created agents.
        """
        agent_ids: list[str] = []

        # Impact analyzer
        ia_id = "impact_0"
        self.registry.register(
            ia_id,
            AgentConfig(role=AgentRole.IMPACT_ANALYZER, model="gpt-4o"),
        )
        self._impact_analyzer = ImpactAnalyzerWorker(
            ia_id, self.registry.get(ia_id), self.bus, llm=self.llm
        )
        agent_ids.append(ia_id)

        # Code reviewer
        cr_id = "review_0"
        self.registry.register(
            cr_id,
            AgentConfig(role=AgentRole.CODE_REVIEWER, model="claude-sonnet"),
        )
        self._code_reviewer = CodeReviewerWorker(
            cr_id, self.registry.get(cr_id), self.bus, llm=self.llm
        )
        agent_ids.append(cr_id)

        # Risk controller — uses the code_reviewer worker with a
        # risk-control system prompt
        rc_id = "risk_0"
        self.registry.register(
            rc_id,
            AgentConfig(
                role=AgentRole.RISK_CONTROLLER,
                model="gpt-4o",
                system_prompt="You are a risk controller. Assess test coverage impact and rollback complexity.",
            ),
        )
        # In the stub architecture the risk controller re-uses the
        # CodeReviewerWorker class but is configured with a different role.
        self._risk_controller = CodeReviewerWorker(
            rc_id, self.registry.get(rc_id), self.bus, llm=self.llm
        )
        agent_ids.append(rc_id)

        logger.info(
            "PRReviewSwarmOrchestrator created %d agents: %s",
            len(agent_ids),
            agent_ids,
        )
        return agent_ids

    # ------------------------------------------------------------------
    # Main execution
    # ------------------------------------------------------------------

    def _fetch_pr_data(self, repo: str, pr_number: int) -> dict[str, Any]:
        """Fetch PR data (mocked).

        Parameters
        ----------
        repo :
            Repository identifier (``owner/repo``).
        pr_number :
            Pull-request number.

        Returns
        -------
        dict[str, Any]
            Mock PR data with ``repo``, ``files_changed``, ``diff_summary``, etc.
        """
        return {
            "repo": repo,
            "pr_number": pr_number,
            "files_changed": ["src/main.py", "tests/test_main.py"],
            "diff_summary": f"Mock diff for PR #{pr_number} in {repo}",
            "title": f"PR #{pr_number}",
            "description": "Mock PR description",
            "author": "developer",
        }

    def _mock_analysis(
        self,
        agent_id: str,
        role: AgentRole,
        pr_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate a mock analysis from an agent (used when workers are unavailable).

        Parameters
        ----------
        agent_id :
            Identifier of the mock agent.
        role :
            Role of the agent.
        pr_data :
            PR data from :meth:`_fetch_pr_data`.

        Returns
        -------
        dict[str, Any]
            Structured mock analysis result.
        """
        role_str = role.value.lower()
        files = pr_data.get("files_changed", [])

        if role == AgentRole.IMPACT_ANALYZER:
            return {
                "agent_id": agent_id,
                "role": role_str,
                "impact_score": 75.0,
                "risk_level": "medium",
                "approved": True,
                "affected_modules": ["core"],
                "comments": ["Assessed impact on core modules"],
            }
        elif role == AgentRole.CODE_REVIEWER:
            return {
                "agent_id": agent_id,
                "role": role_str,
                "impact_score": 85.0,
                "risk_level": "low",
                "approved": True,
                "affected_modules": [],
                "comments": ["Code style looks good"],
            }
        else:  # RISK_CONTROLLER
            return {
                "agent_id": agent_id,
                "role": role_str,
                "impact_score": 65.0,
                "risk_level": "medium",
                "approved": True,
                "affected_modules": [],
                "comments": ["Risk within acceptable bounds"],
            }

    def _aggregate_reviews(
        self,
        analyses: list[dict[str, Any]],
        pr_number: int,
        pr_title: str,
        pr_data: dict[str, Any],
    ) -> PRReviewResult:
        """Aggregate individual agent analyses into a final PR review result.

        Parameters
        ----------
        analyses :
            List of analysis dicts from each agent.
        pr_number :
            Pull-request number.
        pr_title :
            Pull-request title.
        pr_data :
            PR data dict.

        Returns
        -------
        PRReviewResult
            Aggregated review result.
        """
        # Weighted impact score
        weights = {
            "impact_analyzer": 0.5,
            "code_reviewer": 0.3,
            "risk_controller": 0.2,
        }
        total_weight = 0.0
        weighted_score = 0.0

        risk_level_map = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        max_risk = 0

        all_approved = True
        all_comments: list[str] = []
        all_affected_modules: list[str] = []

        for analysis in analyses:
            role = analysis.get("role", "")
            score = analysis.get("impact_score", 50.0)
            weight = weights.get(role, 0.33)
            weighted_score += score * weight
            total_weight += weight

            risk = analysis.get("risk_level", "low")
            max_risk = max(max_risk, risk_level_map.get(risk, 0))

            if not analysis.get("approved", False):
                all_approved = False

            for comment in analysis.get("comments", []):
                if isinstance(comment, str):
                    all_comments.append(comment)

            all_affected_modules.extend(analysis.get("affected_modules", []))

        if total_weight > 0:
            impact_score = weighted_score / total_weight
        else:
            impact_score = 50.0

        reverse_risk_map = {0: "low", 1: "medium", 2: "high", 3: "critical"}
        risk_level = reverse_risk_map[max_risk]

        approved = all_approved and (impact_score >= self.approval_threshold)

        files_changed = pr_data.get("files_changed", [])
        affected_files = list(dict.fromkeys(files_changed + all_affected_modules))

        recommendations = list(dict.fromkeys(all_comments))

        return PRReviewResult(
            pr_number=pr_number,
            pr_title=pr_title,
            impact_score=round(impact_score, 1),
            risk_level=risk_level,  # type: ignore[arg-type]
            affected_files=affected_files,
            breaking_changes=[],
            test_coverage_impact="No explicit coverage impact",
            recommendations=recommendations,
            approved=approved,
        )

    async def execute(self, task: SwarmTask) -> dict[str, Any]:
        """Review a PR using multi-agent impact analysis.

        Parameters
        ----------
        task :
            A :class:`SwarmTask` with ``task_type == "pr_review"``.
            ``task.inputs`` must contain:

            - ``repo`` (*str*): repository identifier (``owner/repo``)
            - ``pr_number`` (*int*): pull-request number
            - ``pr_title`` (*str*, optional): PR title

        Returns
        -------
        dict[str, Any]
            Serialized :class:`PRReviewResult` under the ``review`` key,
            plus raw agent outputs under ``impact_analysis``,
            ``code_review``, and ``risk_assessment``.
        """
        task.status = TaskStatus.IN_PROGRESS
        logger.info("PRReviewSwarm: starting review for task %s", task.id)

        # -- Ensure agents exist ------------------------------------------------
        if self._impact_analyzer is None:
            self.create_agents()

        # -- Extract inputs -----------------------------------------------------
        repo: str = task.inputs.get("repo", "")
        pr_number: int = task.inputs.get("pr_number", 0)
        pr_title: str = task.inputs.get("pr_title", "")

        # Build pr_data dict for worker methods
        pr_data: dict[str, Any] = {
            "pr_number": pr_number,
            "title": pr_title,
            "repo": repo,
            "files_changed": [{"filename": f} for f in ["src/main.py", "tests/test_main.py"]],
            "diff": "mock diff",
        }

        # ------------------------------------------------------------------
        # Phase 1: Fan-out parallel analyses
        # ------------------------------------------------------------------
        impact_future = self._impact_analyzer.analyze_pr_impact(pr_data)
        review_future = self._code_reviewer.review_pr(pr_data)
        risk_future = self._risk_controller.review_pr(pr_data)

        impact_result, review_result, risk_result = await asyncio.gather(
            impact_future,
            review_future,
            risk_future,
            return_exceptions=True,
        )

        # Graceful error handling — log and substitute empty results
        results: list[dict[str, Any]] = []
        for label, raw in [
            ("impact", impact_result),
            ("review", review_result),
            ("risk", risk_result),
        ]:
            if isinstance(raw, Exception):
                logger.error("PRReviewSwarm: %s analysis failed: %s", label, raw)
                results.append({})
            else:
                results.append(raw if isinstance(raw, dict) else {})

        impact_analysis, code_review, risk_assessment = results

        logger.info("PRReviewSwarm: all parallel analyses collected")

        # ------------------------------------------------------------------
        # Phase 2: Aggregate into PRReviewResult
        # ------------------------------------------------------------------
        # Impact score — weighted average of review score (40%) and
        # impact analyzer risk inverse (30%) and risk score (30%)
        review_score = code_review.get("score", 50.0)
        impact_risk = impact_analysis.get("risk_score", 50.0)
        risk_score = risk_assessment.get("score", 50.0)

        impact_score = (
            0.4 * review_score
            + 0.3 * (100 - impact_risk)
            + 0.3 * risk_score
        )
        impact_score = max(0.0, min(100.0, impact_score))

        # Risk level — max across all agents
        impact_risk_level = impact_analysis.get("risk_level", "low")
        risk_risk_level = risk_assessment.get("risk_level", "low")
        risk_level_map = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        max_risk = max(
            risk_level_map.get(impact_risk_level, 0),
            risk_level_map.get(risk_risk_level, 0),
        )
        reverse_risk_map = {0: "low", 1: "medium", 2: "high", 3: "critical"}
        risk_level = reverse_risk_map[max_risk]

        # Approval — all agents must approve AND impact score must exceed
        # the configurable threshold
        all_approve = (
            code_review.get("approved", False)
            and risk_assessment.get("approved", True)
            and impact_risk < 80
        )
        approved = all_approve and (impact_score >= self.approval_threshold)

        # Build recommendations list
        recommendations: list[str] = []
        recommendations.extend(impact_analysis.get("recommendations", []))
        for comment in code_review.get("comments", []):
            if isinstance(comment, dict):
                msg = comment.get("message", "")
                if msg:
                    recommendations.append(f"[{comment.get('severity', 'info')}] {msg}")
            elif isinstance(comment, str):
                recommendations.append(comment)
        recommendations.extend(risk_assessment.get("recommendations", []))

        review_result_obj = PRReviewResult(
            pr_number=pr_number,
            pr_title=pr_title,
            impact_score=round(impact_score, 1),
            risk_level=risk_level,  # type: ignore[arg-type]
            affected_files=[f.get("filename", "") for f in pr_data.get("files_changed", [])],
            breaking_changes=impact_analysis.get("breaking_changes", []),
            test_coverage_impact=risk_assessment.get("issues", ["No explicit coverage impact"])[0]
            if risk_assessment.get("issues")
            else "No explicit coverage impact",
            recommendations=list(dict.fromkeys(recommendations)),  # dedupe
            approved=approved,
        )

        # ------------------------------------------------------------------
        # Phase 3: Store in memory
        # ------------------------------------------------------------------
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.utcnow()

        result = {
            "task_id": task.id,
            "pr_number": pr_number,
            "impact_score": round(impact_score, 1),
            "risk_level": risk_level,
            "approved": approved,
            "review": review_result_obj.model_dump(),
            "impact_analysis": impact_analysis,
            "code_review": code_review,
            "risk_assessment": risk_assessment,
        }
        self.store_result(task, result)

        # Also store the PR review as a separate memory entry
        entry = MemoryEntry(
            content=f"PR #{pr_number} review: {pr_title}\n"
            f"Score: {impact_score:.1f}, Risk: {risk_level}, Approved: {approved}",
            metadata={
                "task_id": task.id,
                "repo": repo,
                "pr_number": pr_number,
                "impact_score": impact_score,
                "risk_level": risk_level,
                "approved": approved,
            },
            tags=["pr_review", repo, f"pr_{pr_number}"],
            source_swarm="pr_review",
        )
        self.memory.add(entry)

        logger.info(
            "PRReviewSwarm: PR #%d review complete (score=%.1f, approved=%s)",
            pr_number,
            impact_score,
            approved,
        )
        return result
