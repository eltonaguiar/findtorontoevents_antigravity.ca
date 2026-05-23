"""GitHub Actions monitoring swarm engine.

This module implements :class:`GitHubActionsSwarmOrchestrator`, which
monitors GitHub Actions workflows for failed, flaky, cancelled, and stale
jobs, then generates actionable recommendations.

Pipeline
--------
1. Fetch workflow runs via GitHub API (last N runs per workflow)
2. Analyze patterns:
   - Group by workflow name + job name
   - Detect: consecutive failures, intermittent failures (alternating pass/fail),
     cancellations, staleness
3. Fan-out: impact_analyzer per flaky job → assess blast radius
4. Generate recommendations:
   - For flaky: suggest retry logic, test isolation, dependency pinning
   - For stale: suggest workflow trigger audit, deprecation
   - For cancelled: suggest timeout/resource adjustments
5. Output GitHubActionsResult
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from swarms.core.base_orchestrator import BaseOrchestrator
from swarms.core.llm_client import LLMClient
from swarms.core.memory import SwarmMemory
from swarms.core.messaging import MessageBus
from swarms.core.models import (
    AgentConfig,
    AgentRole,
    GitHubActionsResult,
    MemoryEntry,
    SwarmMessage,
    SwarmTask,
    TaskStatus,
)
from swarms.core.registry import AgentRegistry
from swarms.core.safety import SafetyEnforcer
from swarms.workers.impact_analyzer import ImpactAnalyzerWorker

logger = logging.getLogger(__name__)


class GitHubActionsSwarmOrchestrator(BaseOrchestrator):
    """Monitors GitHub Actions for failed, flaky, cancelled, and stale jobs.

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
    analysis_window_days :
        Number of days to look back when detecting stale jobs.
    max_runs :
        Maximum number of workflow runs to fetch per workflow.
    """

    def __init__(
        self,
        memory: SwarmMemory,
        bus: MessageBus,
        registry: AgentRegistry,
        safety: SafetyEnforcer,
        analysis_window_days: int = 30,
        max_runs: int = 100,
        llm: Optional[LLMClient] = None,
    ) -> None:
        super().__init__(memory, bus, registry, safety)
        self.analysis_window_days = analysis_window_days
        self.max_runs = max_runs
        self.llm: Optional[LLMClient] = llm

        # Worker references — populated by :meth:`create_agents`
        self._impact_analyzers: list[ImpactAnalyzerWorker] = []

    # ------------------------------------------------------------------
    # Agent lifecycle
    # ------------------------------------------------------------------

    def get_required_agents(self) -> list[AgentRole]:
        """Return required agent roles.

        Two ``IMPACT_ANALYZER`` agents for parallel blast-radius
        assessment of flaky jobs.
        """
        return [AgentRole.IMPACT_ANALYZER, AgentRole.IMPACT_ANALYZER]

    def create_agents(self) -> list[str]:
        """Instantiate and register two impact-analyzer agents.

        Returns
        -------
        list[str]
            ``agent_id``\\ s of the created agents.
        """
        agent_ids: list[str] = []
        for i in range(2):
            aid = f"gha_impact_{i}"
            self.registry.register(
                aid,
                AgentConfig(role=AgentRole.IMPACT_ANALYZER, model="gpt-4o"),
            )
            self._impact_analyzers.append(
                ImpactAnalyzerWorker(
                    aid, self.registry.get(aid), self.bus, llm=self.llm
                )
            )
            agent_ids.append(aid)

        logger.info(
            "GitHubActionsSwarmOrchestrator created %d agents",
            len(agent_ids),
        )
        return agent_ids

    # ------------------------------------------------------------------
    # Detection helpers
    # ------------------------------------------------------------------

    def _detect_flaky_jobs(self, runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Detect intermittently failing jobs (alternating pass/fail pattern).

        Groups *runs* by ``(workflow_name, job_name)`` and flags groups
        whose last 5 conclusions alternate between ``success`` and
        ``failure``.
        """
        # Group by workflow + job
        groups: dict[str, list[dict[str, Any]]] = {}
        for run in runs:
            key = f"{run.get('workflow_name', 'unknown')}/{run.get('job_name', 'unknown')}"
            groups.setdefault(key, []).append(run)

        flaky: list[dict[str, Any]] = []
        for key, job_runs in groups.items():
            if len(job_runs) < 3:
                continue

            # Sort by run number descending (most recent first)
            job_runs_sorted = sorted(
                job_runs, key=lambda r: r.get("run_number", 0), reverse=True
            )

            # Check last 5 for alternating pattern
            recent = job_runs_sorted[:5]
            conclusions = [r.get("conclusion", "") for r in recent]

            # Alternating pattern: at least 2 successes AND 2 failures
            # with no two consecutive same conclusions
            success_count = sum(1 for c in conclusions if c == "success")
            failure_count = sum(1 for c in conclusions if c == "failure")

            if success_count >= 2 and failure_count >= 2:
                # More strict: check if they actually alternate
                alternates = any(
                    conclusions[i] != conclusions[i + 1]
                    for i in range(len(conclusions) - 1)
                )
                if alternates:
                    wf_name, job_name = key.split("/", 1)
                    flaky.append(
                        {
                            "workflow_name": wf_name,
                            "job_name": job_name,
                            "alternating_pattern": conclusions,
                            "recent_runs": [
                                {
                                    "run_number": r.get("run_number"),
                                    "conclusion": r.get("conclusion"),
                                    "run_url": r.get("run_url"),
                                    "started_at": r.get("started_at"),
                                }
                                for r in recent
                            ],
                            "failure_rate": failure_count / len(conclusions),
                        }
                    )

        logger.info("Detected %d flaky jobs", len(flaky))
        return flaky

    def _detect_stale_jobs(self, runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Detect jobs not run in more than ``analysis_window_days`` days.

        Groups *runs* by ``(workflow_name, job_name)`` and flags groups
        whose most recent run is older than the threshold.
        """
        cutoff = datetime.utcnow() - timedelta(days=self.analysis_window_days)

        # Group by workflow + job
        groups: dict[str, list[dict[str, Any]]] = {}
        for run in runs:
            key = f"{run.get('workflow_name', 'unknown')}/{run.get('job_name', 'unknown')}"
            groups.setdefault(key, []).append(run)

        stale: list[dict[str, Any]] = []
        for key, job_runs in groups.items():
            if not job_runs:
                continue

            most_recent = max(
                job_runs,
                key=lambda r: r.get("run_number", 0),
            )
            started_at_str = most_recent.get("started_at", "")
            try:
                started_at = (
                    datetime.fromisoformat(started_at_str.replace("Z", "+00:00"))
                    if started_at_str
                    else datetime.utcnow()
                )
            except (ValueError, AttributeError):
                started_at = datetime.utcnow()

            if started_at < cutoff:
                wf_name, job_name = key.split("/", 1)
                stale.append(
                    {
                        "workflow_name": wf_name,
                        "job_name": job_name,
                        "last_run_at": started_at_str,
                        "days_since_last_run": (datetime.utcnow() - started_at).days,
                        "run_url": most_recent.get("run_url"),
                    }
                )

        logger.info("Detected %d stale jobs", len(stale))
        return stale

    def _detect_cancelled_jobs(self, runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Detect frequently cancelled jobs.

        Groups *runs* by ``(workflow_name, job_name)`` and flags groups
        where at least 30%% of recent runs were cancelled.
        """
        # Group by workflow + job
        groups: dict[str, list[dict[str, Any]]] = {}
        for run in runs:
            key = f"{run.get('workflow_name', 'unknown')}/{run.get('job_name', 'unknown')}"
            groups.setdefault(key, []).append(run)

        cancelled: list[dict[str, Any]] = []
        for key, job_runs in groups.items():
            if len(job_runs) < 3:
                continue

            cancelled_runs = [r for r in job_runs if r.get("conclusion") == "cancelled"]
            rate = len(cancelled_runs) / len(job_runs)

            if rate >= 0.3:
                wf_name, job_name = key.split("/", 1)
                most_recent_cancelled = max(
                    cancelled_runs,
                    key=lambda r: r.get("run_number", 0),
                    default={},
                )
                cancelled.append(
                    {
                        "workflow_name": wf_name,
                        "job_name": job_name,
                        "cancellation_rate": round(rate, 2),
                        "cancelled_count": len(cancelled_runs),
                        "total_runs": len(job_runs),
                        "recent_cancelled_url": most_recent_cancelled.get("run_url"),
                    }
                )

        logger.info("Detected %d cancelled jobs", len(cancelled))
        return cancelled

    def _detect_failed_jobs(self, runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Extract jobs whose most recent conclusion is ``failure``.

        Groups *runs* by ``(workflow_name, job_name)`` and flags groups
        where the latest run failed.
        """
        groups: dict[str, list[dict[str, Any]]] = {}
        for run in runs:
            key = f"{run.get('workflow_name', 'unknown')}/{run.get('job_name', 'unknown')}"
            groups.setdefault(key, []).append(run)

        failed: list[dict[str, Any]] = []
        for key, job_runs in groups.items():
            if not job_runs:
                continue

            most_recent = max(
                job_runs,
                key=lambda r: r.get("run_number", 0),
            )

            if most_recent.get("conclusion") == "failure":
                # Count consecutive failures
                sorted_runs = sorted(
                    job_runs, key=lambda r: r.get("run_number", 0), reverse=True
                )
                consecutive = 0
                for r in sorted_runs:
                    if r.get("conclusion") == "failure":
                        consecutive += 1
                    else:
                        break

                wf_name, job_name = key.split("/", 1)
                failed.append(
                    {
                        "workflow_name": wf_name,
                        "job_name": job_name,
                        "conclusion": "failure",
                        "consecutive_failures": consecutive,
                        "run_url": most_recent.get("run_url"),
                        "failed_since": sorted_runs[consecutive - 1].get("started_at")
                        if consecutive <= len(sorted_runs)
                        else None,
                    }
                )

        logger.info("Detected %d failed jobs", len(failed))
        return failed

    def _generate_recommendations(
        self,
        flaky_jobs: list[dict[str, Any]],
        stale_jobs: list[dict[str, Any]],
        cancelled_jobs: list[dict[str, Any]],
        failed_jobs: list[dict[str, Any]],
    ) -> list[str]:
        """Generate actionable recommendations from detected issues.

        Parameters
        ----------
        flaky_jobs :
            Jobs detected as flaky (alternating pass/fail).
        stale_jobs :
            Jobs not run recently.
        cancelled_jobs :
            Frequently cancelled jobs.
        failed_jobs :
            Currently failing jobs.

        Returns
        -------
        list[str]
            Human-readable recommendation strings.
        """
        recommendations: list[str] = []

        for job in flaky_jobs:
            recommendations.append(
                f"[FLAKY] Job '{job['workflow_name']}/{job['job_name']}': "
                "Add retry logic with exponential backoff, isolate flaky tests, "
                "and pin dependencies."
            )

        for job in stale_jobs:
            recommendations.append(
                f"[STALE] Job '{job['workflow_name']}/{job['job_name']}': "
                f"Last run {job['days_since_last_run']} days ago. "
                "Audit workflow triggers or deprecate."
            )

        for job in cancelled_jobs:
            recommendations.append(
                f"[CANCELLED] Job '{job['workflow_name']}/{job['job_name']}': "
                f"Cancellation rate {job['cancellation_rate']*100:.0f}%. "
                "Review timeout settings and resource limits."
            )

        for job in failed_jobs:
            if job["consecutive_failures"] >= 3:
                recommendations.append(
                    f"[FAILED] Job '{job['workflow_name']}/{job['job_name']}': "
                    f"{job['consecutive_failures']} consecutive failures. "
                    "Investigate immediately."
                )
            else:
                recommendations.append(
                    f"[FAILED] Job '{job['workflow_name']}/{job['job_name']}': "
                    f"Recent failure. Check logs."
                )

        if not any([flaky_jobs, stale_jobs, cancelled_jobs, failed_jobs]):
            recommendations.append("All workflows are healthy — no issues detected.")

        return recommendations

    # ------------------------------------------------------------------
    # GitHub API helpers (mocked)
    # ------------------------------------------------------------------

    async def _fetch_workflow_runs(
        self,
        repo: str,
        token: str | None = None,
        workflows: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch the last *max_runs* workflow runs for *repo*.

        This is a **mocked** implementation that returns deterministic
        placeholder data.  In production this would call the GitHub API.
        """
        await asyncio.sleep(0.05)  # simulate API latency

        # Deterministic mock data
        mock_workflows = workflows or ["ci.yml", "test.yml", "deploy.yml"]
        mock_jobs = ["unit-tests", "integration-tests", "lint", "build"]

        runs: list[dict[str, Any]] = []
        run_number = 1000

        # Generate enough runs to demonstrate all patterns
        for wf_idx, wf_name in enumerate(mock_workflows):
            for job_idx, job_name in enumerate(mock_jobs):
                for i in range(min(10, self.max_runs // len(mock_workflows) // len(mock_jobs) + 1)):
                    # Create interesting patterns:
                    # - Some jobs alternate (flaky)
                    # - Some are consistently failing
                    # - Some are cancelled frequently
                    # - Some are stale (old dates)

                    base_offset = wf_idx * 100 + job_idx * 10 + i

                    # Stale pattern: very old dates for certain jobs
                    if job_name == "lint" and wf_name == "deploy.yml":
                        started = (
                            datetime.utcnow()
                            - timedelta(days=self.analysis_window_days + 5)
                        ).isoformat()
                        conclusion = "success"
                    # Flaky pattern: alternating
                    elif job_name == "integration-tests" and wf_name == "ci.yml":
                        started = (
                            datetime.utcnow() - timedelta(hours=base_offset * 2)
                        ).isoformat()
                        conclusion = "success" if i % 2 == 0 else "failure"
                    # Cancelled pattern
                    elif job_name == "build" and wf_name == "test.yml":
                        started = (
                            datetime.utcnow() - timedelta(hours=base_offset * 3)
                        ).isoformat()
                        conclusion = "cancelled" if i % 3 == 0 else "success"
                    # Failed pattern
                    elif job_name == "unit-tests" and wf_name == "ci.yml":
                        started = (
                            datetime.utcnow() - timedelta(hours=base_offset)
                        ).isoformat()
                        conclusion = "failure" if i < 5 else "success"
                    else:
                        started = (
                            datetime.utcnow() - timedelta(hours=base_offset)
                        ).isoformat()
                        conclusion = "success"

                    runs.append(
                        {
                            "run_number": run_number - base_offset,
                            "workflow_name": wf_name,
                            "job_name": job_name,
                            "conclusion": conclusion,
                            "run_url": f"https://github.com/{repo}/actions/runs/{run_number - base_offset}",
                            "started_at": started,
                            "repo": repo,
                        }
                    )

        logger.info(
            "Fetched %d workflow runs for %s",
            len(runs),
            repo,
        )
        return runs

    # ------------------------------------------------------------------
    # Main execution
    # ------------------------------------------------------------------

    async def execute(self, task: SwarmTask) -> dict[str, Any]:
        """Monitor GitHub Actions and generate recommendations.

        Parameters
        ----------
        task :
            A :class:`SwarmTask` with ``task_type == "gh_actions"``.
            ``task.inputs`` must contain:

            - ``repo`` (*str*): repository identifier (``owner/repo``)
            - ``token`` (*Optional[str]*): GitHub API token
            - ``workflows`` (*Optional[list]*): workflow names to filter

        Returns
        -------
        dict[str, Any]
            Serialized :class:`GitHubActionsResult` under the
            ``analysis`` key, plus the raw ``runs`` list.
        """
        task.status = TaskStatus.IN_PROGRESS
        logger.info("GitHubActionsSwarm: starting analysis for task %s", task.id)

        # -- Ensure agents exist ------------------------------------------------
        if not self._impact_analyzers:
            self.create_agents()

        # -- Extract inputs -----------------------------------------------------
        repo: str = task.inputs.get("repo", "")
        token: str | None = task.inputs.get("token")
        workflows: list[str] | None = task.inputs.get("workflows")

        # ------------------------------------------------------------------
        # Phase 1: Fetch workflow runs
        # ------------------------------------------------------------------
        runs = await self._fetch_workflow_runs(repo, token, workflows)

        # ------------------------------------------------------------------
        # Phase 2: Analyze patterns
        # ------------------------------------------------------------------
        flaky_jobs = self._detect_flaky_jobs(runs)
        stale_jobs = self._detect_stale_jobs(runs)
        cancelled_jobs = self._detect_cancelled_jobs(runs)
        failed_jobs = self._detect_failed_jobs(runs)

        # ------------------------------------------------------------------
        # Phase 3: Fan-out impact analysis per flaky job
        # ------------------------------------------------------------------
        blast_radius_results: list[dict[str, Any]] = []
        if flaky_jobs:
            blast_tasks = [
                self._impact_analyzers[i % len(self._impact_analyzers)].analyze_blast_radius(
                    job_name=f"{job['workflow_name']}/{job['job_name']}",
                    failure_pattern=f"Alternating pass/fail: {job['alternating_pattern']}",
                    repo=repo,
                )
                for i, job in enumerate(flaky_jobs)
            ]
            blast_raw = await asyncio.gather(*blast_tasks, return_exceptions=True)
            for raw in blast_raw:
                if isinstance(raw, Exception):
                    logger.error("Blast-radius analysis failed: %s", raw)
                else:
                    blast_radius_results.append(raw)

        # ------------------------------------------------------------------
        # Phase 4: Generate recommendations
        # ------------------------------------------------------------------
        recommendations: list[str] = []

        # Flaky job recommendations
        for job in flaky_jobs:
            recommendations.append(
                f"[FLAKY] Job '{job['workflow_name']}/{job['job_name']}': "
                "Add retry logic with exponential backoff, isolate flaky tests, "
                "and pin dependencies."
            )

        # Stale job recommendations
        for job in stale_jobs:
            recommendations.append(
                f"[STALE] Job '{job['workflow_name']}/{job['job_name']}': "
                f"Last run {job['days_since_last_run']} days ago. "
                "Audit workflow triggers or deprecate."
            )

        # Cancelled job recommendations
        for job in cancelled_jobs:
            recommendations.append(
                f"[CANCELLED] Job '{job['workflow_name']}/{job['job_name']}': "
                f"Cancellation rate {job['cancellation_rate']*100:.0f}%. "
                "Review timeout settings and resource limits."
            )

        # Failed job recommendations
        for job in failed_jobs:
            if job["consecutive_failures"] >= 3:
                recommendations.append(
                    f"[FAILED] Job '{job['workflow_name']}/{job['job_name']}': "
                    f"{job['consecutive_failures']} consecutive failures. "
                    "Investigate immediately."
                )
            else:
                recommendations.append(
                    f"[FAILED] Job '{job['workflow_name']}/{job['job_name']}': "
                    f"Recent failure. Check logs."
                )

        # Add blast-radius recommendations
        for br in blast_radius_results:
            recommendations.extend(br.get("recommendations", []))

        result_obj = GitHubActionsResult(
            repo=repo,
            failed_jobs=failed_jobs,
            flaky_jobs=flaky_jobs,
            stale_jobs=stale_jobs,
            cancelled_jobs=cancelled_jobs,
            recommendations=list(dict.fromkeys(recommendations)),
        )

        # ------------------------------------------------------------------
        # Phase 5: Store in memory
        # ------------------------------------------------------------------
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.utcnow()

        result = {
            "task_id": task.id,
            "analysis": result_obj.model_dump(),
            "total_runs_analyzed": len(runs),
            "blast_radius_count": len(blast_radius_results),
        }
        self.store_result(task, result)

        # Store summary in memory
        entry = MemoryEntry(
            content=f"GitHub Actions analysis for {repo}: "
            f"{len(failed_jobs)} failed, {len(flaky_jobs)} flaky, "
            f"{len(stale_jobs)} stale, {len(cancelled_jobs)} cancelled jobs. "
            f"Recommendations: {len(recommendations)}",
            metadata={
                "task_id": task.id,
                "repo": repo,
                "failed_jobs": len(failed_jobs),
                "flaky_jobs": len(flaky_jobs),
                "stale_jobs": len(stale_jobs),
                "cancelled_jobs": len(cancelled_jobs),
            },
            tags=["gh_actions", repo],
            source_swarm="gh_actions",
        )
        self.memory.add(entry)

        logger.info(
            "GitHubActionsSwarm: analysis complete for %s "
            "(failed=%d, flaky=%d, stale=%d, cancelled=%d)",
            repo,
            len(failed_jobs),
            len(flaky_jobs),
            len(stale_jobs),
            len(cancelled_jobs),
        )
        return result
