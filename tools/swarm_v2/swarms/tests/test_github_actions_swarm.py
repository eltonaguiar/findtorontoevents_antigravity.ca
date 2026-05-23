"""Tests for GitHubActionsSwarmOrchestrator in swarms.engines.github_actions_swarm."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


from swarms.core.models import AgentRole, GitHubActionsResult, SwarmTask, TaskStatus
from swarms.engines.github_actions_swarm import GitHubActionsSwarmOrchestrator

# Internal constants for testing
_FLAKY_ALTERNATIONS = 3


def _make_run(name, conclusion, run_number=1, **kwargs):
    """Helper to build a run dict with the keys the engine expects."""
    run = {
        "workflow_name": kwargs.get("workflow_name", "ci.yml"),
        "job_name": name,
        "conclusion": conclusion,
        "run_number": run_number,
        "run_url": f"https://github.com/test/actions/runs/{run_number}",
        "started_at": kwargs.get("started_at", datetime.utcnow().isoformat()),
    }
    run.update(kwargs)
    return run


@pytest.fixture
def orchestrator():
    """Create a GitHubActionsSwarmOrchestrator with mocked infrastructure."""
    memory = MagicMock()
    memory.add = MagicMock(return_value="entry_id")
    bus = MagicMock()
    bus.publish = AsyncMock()
    registry = MagicMock()
    registry.register = MagicMock()
    registry.get = MagicMock(return_value=MagicMock())
    safety = MagicMock()

    orch = GitHubActionsSwarmOrchestrator(memory=memory, bus=bus, registry=registry, safety=safety)
    yield orch


class TestGetRequiredAgents:
    def test_returns_two_impact_analyzers(self):
        orch = GitHubActionsSwarmOrchestrator(
            memory=MagicMock(), bus=MagicMock(), registry=MagicMock(), safety=MagicMock()
        )
        roles = orch.get_required_agents()
        assert len(roles) == 2
        assert all(r == AgentRole.IMPACT_ANALYZER for r in roles)


class TestCreateAgents:
    def test_registers_two_agents(self):
        registry = MagicMock()
        registry.get = MagicMock(return_value=MagicMock())
        orch = GitHubActionsSwarmOrchestrator(
            memory=MagicMock(), bus=MagicMock(), registry=registry, safety=MagicMock()
        )
        agent_ids = orch.create_agents()
        assert len(agent_ids) == 2


class TestExecute:
    @pytest.mark.asyncio
    async def test_execute_returns_result(self, orchestrator):
        orchestrator.create_agents()
        for ia in orchestrator._impact_analyzers:
            ia.analyze_blast_radius = AsyncMock(return_value={"recommendations": []})

        task = SwarmTask(
            task_type="gh_actions",
            description="Monitor actions",
            inputs={"repo": "owner/repo", "since_days": 30},
        )
        result = await orchestrator.execute(task)
        assert "analysis" in result
        assert "repo" in result["analysis"]
        assert task.status == TaskStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_execute_stores_result(self, orchestrator):
        orchestrator.create_agents()
        for ia in orchestrator._impact_analyzers:
            ia.analyze_blast_radius = AsyncMock(return_value={"recommendations": []})

        task = SwarmTask(
            task_type="gh_actions",
            description="Monitor",
            inputs={"repo": "owner/repo"},
        )
        await orchestrator.execute(task)
        orchestrator.memory.add.assert_called()

    @pytest.mark.asyncio
    async def test_execute_custom_since_days(self, orchestrator):
        orchestrator.create_agents()
        for ia in orchestrator._impact_analyzers:
            ia.analyze_blast_radius = AsyncMock(return_value={"recommendations": []})

        task = SwarmTask(
            task_type="gh_actions",
            description="Monitor",
            inputs={"repo": "x/y", "since_days": 7},
        )
        result = await orchestrator.execute(task)
        assert result["analysis"]["repo"] == "x/y"


class TestDetectFlakyJobs:
    def test_finds_alternating_pattern(self, orchestrator):
        runs = [
            _make_run("test-job", "success", run_number=4),
            _make_run("test-job", "failure", run_number=3),
            _make_run("test-job", "success", run_number=2),
            _make_run("test-job", "failure", run_number=1),
        ]
        flaky = orchestrator._detect_flaky_jobs(runs)
        assert len(flaky) == 1
        assert flaky[0]["job_name"] == "test-job"

    def test_no_false_positives(self, orchestrator):
        runs = [
            _make_run("test-job", "success", run_number=3),
            _make_run("test-job", "success", run_number=2),
            _make_run("other-job", "failure", run_number=1),
        ]
        flaky = orchestrator._detect_flaky_jobs(runs)
        assert len(flaky) == 0

    def test_empty_runs(self, orchestrator):
        flaky = orchestrator._detect_flaky_jobs([])
        assert flaky == []

    def test_respects_flaky_threshold(self, orchestrator):
        # Only 2 alternations (below threshold of 3)
        runs = [
            _make_run("test", "success", run_number=3),
            _make_run("test", "failure", run_number=2),
            _make_run("test", "success", run_number=1),
        ]
        flaky = orchestrator._detect_flaky_jobs(runs)
        if _FLAKY_ALTERNATIONS <= 2:
            assert len(flaky) == 1
        else:
            assert len(flaky) == 0

    def test_multiple_jobs(self, orchestrator):
        runs = [
            _make_run("flaky", "success", run_number=4),
            _make_run("flaky", "failure", run_number=3),
            _make_run("flaky", "success", run_number=2),
            _make_run("flaky", "failure", run_number=1),
            _make_run("stable", "success", run_number=2),
            _make_run("stable", "success", run_number=1),
        ]
        flaky = orchestrator._detect_flaky_jobs(runs)
        assert len(flaky) >= 1
        assert all(f["job_name"] == "flaky" for f in flaky)


class TestDetectStaleJobs:
    def test_finds_old_jobs(self, orchestrator):
        old_date = (datetime.utcnow() - timedelta(days=60)).isoformat()
        runs = [
            _make_run("old-job", "success", run_number=1, started_at=old_date),
        ]
        stale = orchestrator._detect_stale_jobs(runs)
        assert len(stale) == 1
        assert stale[0]["job_name"] == "old-job"

    def test_no_false_positives(self, orchestrator):
        recent = datetime.utcnow().isoformat()
        runs = [
            _make_run("recent-job", "success", run_number=1, started_at=recent),
        ]
        stale = orchestrator._detect_stale_jobs(runs)
        assert len(stale) == 0

    def test_empty_runs(self, orchestrator):
        stale = orchestrator._detect_stale_jobs([])
        assert stale == []

    def test_uses_max_date_per_job(self, orchestrator):
        recent = datetime.utcnow().isoformat()
        old = (datetime.utcnow() - timedelta(days=60)).isoformat()
        runs = [
            _make_run("job", "success", run_number=1, started_at=old),
            _make_run("job", "success", run_number=2, started_at=recent),
        ]
        stale = orchestrator._detect_stale_jobs(runs)
        # Most recent is within window
        assert len(stale) == 0


class TestDetectCancelledJobs:
    def test_finds_cancelled(self, orchestrator):
        runs = [
            _make_run("job1", "cancelled", run_number=3),
            _make_run("job1", "cancelled", run_number=2),
            _make_run("job1", "success", run_number=1),
            _make_run("job2", "success", run_number=1),
        ]
        cancelled = orchestrator._detect_cancelled_jobs(runs)
        assert len(cancelled) == 1
        assert cancelled[0]["job_name"] == "job1"

    def test_empty(self, orchestrator):
        assert orchestrator._detect_cancelled_jobs([]) == []

    def test_only_cancelled(self, orchestrator):
        runs = [
            _make_run("a", "cancelled", run_number=3),
            _make_run("a", "cancelled", run_number=2),
            _make_run("a", "cancelled", run_number=1),
            _make_run("b", "cancelled", run_number=3),
            _make_run("b", "cancelled", run_number=2),
            _make_run("b", "cancelled", run_number=1),
        ]
        cancelled = orchestrator._detect_cancelled_jobs(runs)
        assert len(cancelled) == 2


class TestDetectFailedJobs:
    def test_finds_failed(self, orchestrator):
        runs = [
            _make_run("job1", "failure", run_number=2),
            _make_run("job2", "success", run_number=1),
        ]
        failed = orchestrator._detect_failed_jobs(runs)
        assert len(failed) == 1
        assert failed[0]["job_name"] == "job1"

    def test_includes_failed_since(self, orchestrator):
        dt = datetime.utcnow().isoformat()
        runs = [
            _make_run("job1", "failure", run_number=1, started_at=dt),
        ]
        failed = orchestrator._detect_failed_jobs(runs)
        assert "failed_since" in failed[0]

    def test_empty(self, orchestrator):
        assert orchestrator._detect_failed_jobs([]) == []


class TestGenerateRecommendations:
    def test_flaky_recommendations(self, orchestrator):
        flaky = [{"workflow_name": "ci", "job_name": "test", "alternating_pattern": ["success", "failure"], "failure_rate": 0.5, "recent_runs": []}]
        recs = orchestrator._generate_recommendations(flaky, [], [], [])
        assert any("retry" in r.lower() for r in recs)
        assert any("dependenc" in r.lower() for r in recs)

    def test_stale_recommendations(self, orchestrator):
        stale = [{"workflow_name": "ci", "job_name": "lint", "last_run_at": "2024-01-01", "days_since_last_run": 30, "run_url": ""}]
        recs = orchestrator._generate_recommendations([], stale, [], [])
        assert any("audit" in r.lower() for r in recs)

    def test_cancelled_recommendations(self, orchestrator):
        cancelled = [{"workflow_name": "ci", "job_name": "build", "cancellation_rate": 0.5, "cancelled_count": 2, "total_runs": 4, "recent_cancelled_url": ""}]
        recs = orchestrator._generate_recommendations([], [], cancelled, [])
        assert any("timeout" in r.lower() or "resource" in r.lower() for r in recs)

    def test_failed_recommendations(self, orchestrator):
        failed = [{"workflow_name": "ci", "job_name": "deploy", "conclusion": "failure", "consecutive_failures": 1, "run_url": "", "failed_since": None}]
        recs = orchestrator._generate_recommendations([], [], [], failed)
        assert any("fix" in r.lower() or "logs" in r.lower() for r in recs)

    def test_healthy_recommendation(self, orchestrator):
        recs = orchestrator._generate_recommendations([], [], [], [])
        assert len(recs) == 1
        assert "healthy" in recs[0].lower()

    def test_all_categories(self, orchestrator):
        flaky = [{"workflow_name": "ci", "job_name": "f", "alternating_pattern": [], "failure_rate": 0.5, "recent_runs": []}]
        stale = [{"workflow_name": "ci", "job_name": "s", "last_run_at": "", "days_since_last_run": 30, "run_url": ""}]
        cancelled = [{"workflow_name": "ci", "job_name": "c", "cancellation_rate": 0.5, "cancelled_count": 1, "total_runs": 2, "recent_cancelled_url": ""}]
        failed = [{"workflow_name": "ci", "job_name": "f2", "conclusion": "failure", "consecutive_failures": 1, "run_url": "", "failed_since": None}]
        recs = orchestrator._generate_recommendations(flaky, stale, cancelled, failed)
        assert len(recs) >= 4
