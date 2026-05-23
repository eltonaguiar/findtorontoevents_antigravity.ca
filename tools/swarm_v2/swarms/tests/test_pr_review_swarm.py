"""Tests for PRReviewSwarmOrchestrator in swarms.engines.pr_review_swarm."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


from swarms.core.models import AgentRole, PRReviewResult, SwarmTask, TaskStatus
from swarms.engines.pr_review_swarm import PRReviewSwarmOrchestrator

# Internal constant value for testing
_APPROVAL_THRESHOLD = 70.0


@pytest.fixture
def orchestrator():
    """Create a PRReviewSwarmOrchestrator with mocked infrastructure."""
    memory = MagicMock()
    memory.add = MagicMock(return_value="entry_id")
    bus = MagicMock()
    bus.publish = AsyncMock()
    bus.broadcast = AsyncMock()
    registry = MagicMock()
    registry.register = MagicMock()
    registry.get = MagicMock(return_value=MagicMock())
    safety = MagicMock()

    orch = PRReviewSwarmOrchestrator(memory=memory, bus=bus, registry=registry, safety=safety)
    yield orch


class TestGetRequiredAgents:
    def test_returns_three_roles(self):
        orch = PRReviewSwarmOrchestrator(
            memory=MagicMock(), bus=MagicMock(), registry=MagicMock(), safety=MagicMock()
        )
        roles = orch.get_required_agents()
        assert len(roles) == 3

    def test_roles_correct(self):
        orch = PRReviewSwarmOrchestrator(
            memory=MagicMock(), bus=MagicMock(), registry=MagicMock(), safety=MagicMock()
        )
        roles = orch.get_required_agents()
        assert AgentRole.IMPACT_ANALYZER in roles
        assert AgentRole.CODE_REVIEWER in roles
        assert AgentRole.RISK_CONTROLLER in roles

    def test_exact_roles(self):
        orch = PRReviewSwarmOrchestrator(
            memory=MagicMock(), bus=MagicMock(), registry=MagicMock(), safety=MagicMock()
        )
        roles = orch.get_required_agents()
        assert roles == [AgentRole.IMPACT_ANALYZER, AgentRole.CODE_REVIEWER, AgentRole.RISK_CONTROLLER]


class TestCreateAgents:
    def test_registers_three_agents(self):
        registry = MagicMock()
        registry.get = MagicMock(return_value=MagicMock())
        orch = PRReviewSwarmOrchestrator(
            memory=MagicMock(), bus=MagicMock(), registry=registry, safety=MagicMock()
        )
        agent_ids = orch.create_agents()
        assert len(agent_ids) == 3
        assert registry.register.call_count == 3


class TestExecute:
    @pytest.mark.asyncio
    async def test_execute_returns_result(self, orchestrator):
        orchestrator.create_agents()
        orchestrator._impact_analyzer.analyze_pr_impact = AsyncMock(
            return_value={"risk_score": 50.0, "risk_level": "low", "recommendations": [], "breaking_changes": []}
        )
        orchestrator._code_reviewer.review_pr = AsyncMock(
            return_value={"approved": True, "score": 85.0, "comments": [], "issues_found": 0}
        )
        orchestrator._risk_controller.review_pr = AsyncMock(
            return_value={"approved": True, "score": 70.0, "comments": [], "issues_found": 0, "risk_level": "low", "recommendations": []}
        )

        task = SwarmTask(
            task_type="pr_review",
            description="Review PR",
            inputs={"repo": "owner/repo", "pr_number": 123, "pr_title": "Add feature"},
        )
        result = await orchestrator.execute(task)
        assert "pr_number" in result
        assert "impact_score" in result
        assert "risk_level" in result
        assert "approved" in result
        assert task.status == TaskStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_execute_stores_result(self, orchestrator):
        orchestrator.create_agents()
        orchestrator._impact_analyzer.analyze_pr_impact = AsyncMock(
            return_value={"risk_score": 50.0, "risk_level": "low", "recommendations": [], "breaking_changes": []}
        )
        orchestrator._code_reviewer.review_pr = AsyncMock(
            return_value={"approved": True, "score": 85.0, "comments": [], "issues_found": 0}
        )
        orchestrator._risk_controller.review_pr = AsyncMock(
            return_value={"approved": True, "score": 70.0, "comments": [], "issues_found": 0, "risk_level": "low", "recommendations": []}
        )

        task = SwarmTask(
            task_type="pr_review",
            description="Review PR",
            inputs={"repo": "owner/repo", "pr_number": 42},
        )
        await orchestrator.execute(task)
        orchestrator.memory.add.assert_called()

    @pytest.mark.asyncio
    async def test_execute_correct_pr_number(self, orchestrator):
        orchestrator.create_agents()
        orchestrator._impact_analyzer.analyze_pr_impact = AsyncMock(
            return_value={"risk_score": 50.0, "risk_level": "low", "recommendations": [], "breaking_changes": []}
        )
        orchestrator._code_reviewer.review_pr = AsyncMock(
            return_value={"approved": True, "score": 85.0, "comments": [], "issues_found": 0}
        )
        orchestrator._risk_controller.review_pr = AsyncMock(
            return_value={"approved": True, "score": 70.0, "comments": [], "issues_found": 0, "risk_level": "low", "recommendations": []}
        )

        task = SwarmTask(
            task_type="pr_review",
            description="Review PR",
            inputs={"repo": "owner/repo", "pr_number": 999, "pr_title": "Fix bug"},
        )
        result = await orchestrator.execute(task)
        assert result["pr_number"] == 999


class TestMockAnalysis:
    def test_mock_analysis_impact_analyzer(self, orchestrator):
        analysis = orchestrator._mock_analysis(
            "impact_analyzer_0", AgentRole.IMPACT_ANALYZER, {"files_changed": ["a.py"]}
        )
        assert analysis["role"] == "impact_analyzer"
        assert "impact_score" in analysis
        assert "approved" in analysis

    def test_mock_analysis_code_reviewer(self, orchestrator):
        analysis = orchestrator._mock_analysis(
            "code_reviewer_0", AgentRole.CODE_REVIEWER, {"files_changed": ["b.py"]}
        )
        assert analysis["role"] == "code_reviewer"

    def test_mock_analysis_risk_controller(self, orchestrator):
        analysis = orchestrator._mock_analysis(
            "risk_controller_0", AgentRole.RISK_CONTROLLER, {"files_changed": ["c.py"]}
        )
        assert analysis["role"] == "risk_controller"


class TestAggregateReviews:
    def test_impact_score_weighted_average(self, orchestrator):
        analyses = [
            {"agent_id": "a1", "role": "impact_analyzer", "impact_score": 80.0, "risk_level": "medium", "approved": True, "affected_modules": [], "comments": ["c1"]},
            {"agent_id": "a2", "role": "code_reviewer", "impact_score": 90.0, "risk_level": "low", "approved": True, "affected_modules": [], "comments": ["c2"]},
            {"agent_id": "a3", "role": "risk_controller", "impact_score": 70.0, "risk_level": "medium", "approved": True, "affected_modules": [], "comments": ["c3"]},
        ]
        result = orchestrator._aggregate_reviews(analyses, 1, "test", {"files_changed": ["a.py"]})
        assert isinstance(result, PRReviewResult)
        # Weighted: 80*0.5 + 90*0.3 + 70*0.2 = 40 + 27 + 14 = 81.0
        assert result.impact_score == 81.0

    def test_risk_level_is_max(self, orchestrator):
        analyses = [
            {"agent_id": "a1", "role": "impact_analyzer", "impact_score": 80.0, "risk_level": "medium", "approved": True, "affected_modules": [], "comments": []},
            {"agent_id": "a2", "role": "code_reviewer", "impact_score": 90.0, "risk_level": "low", "approved": True, "affected_modules": [], "comments": []},
            {"agent_id": "a3", "role": "risk_controller", "impact_score": 70.0, "risk_level": "high", "approved": True, "affected_modules": [], "comments": []},
        ]
        result = orchestrator._aggregate_reviews(analyses, 1, "test", {"files_changed": []})
        assert result.risk_level == "high"

    def test_approved_requires_all_approval(self, orchestrator):
        analyses = [
            {"agent_id": "a1", "role": "impact_analyzer", "impact_score": 80.0, "risk_level": "low", "approved": True, "affected_modules": [], "comments": []},
            {"agent_id": "a2", "role": "code_reviewer", "impact_score": 90.0, "risk_level": "low", "approved": False, "affected_modules": [], "comments": []},
            {"agent_id": "a3", "role": "risk_controller", "impact_score": 85.0, "risk_level": "low", "approved": True, "affected_modules": [], "comments": []},
        ]
        result = orchestrator._aggregate_reviews(analyses, 1, "test", {"files_changed": []})
        assert result.approved is False

    def test_approved_requires_impact_threshold(self, orchestrator):
        analyses = [
            {"agent_id": "a1", "role": "impact_analyzer", "impact_score": 50.0, "risk_level": "low", "approved": True, "affected_modules": [], "comments": []},
            {"agent_id": "a2", "role": "code_reviewer", "impact_score": 55.0, "risk_level": "low", "approved": True, "affected_modules": [], "comments": []},
            {"agent_id": "a3", "role": "risk_controller", "impact_score": 60.0, "risk_level": "low", "approved": True, "affected_modules": [], "comments": []},
        ]
        result = orchestrator._aggregate_reviews(analyses, 1, "test", {"files_changed": []})
        # impact_score = 50*0.5 + 55*0.3 + 60*0.2 = 25 + 16.5 + 12 = 53.5 < 70
        assert result.impact_score < _APPROVAL_THRESHOLD
        assert result.approved is False

    def test_affected_files_preserved(self, orchestrator):
        analyses = [
            {"agent_id": "a1", "role": "impact_analyzer", "impact_score": 80.0, "risk_level": "low", "approved": True, "affected_modules": ["src/a.py"], "comments": []},
        ]
        pr_data = {"files_changed": ["src/a.py", "tests/test_a.py"]}
        result = orchestrator._aggregate_reviews(analyses, 1, "test", pr_data)
        assert "src/a.py" in result.affected_files
        assert "tests/test_a.py" in result.affected_files

    def test_recommendations_collected(self, orchestrator):
        analyses = [
            {"agent_id": "a1", "role": "impact_analyzer", "impact_score": 80.0, "risk_level": "low", "approved": True, "affected_modules": [], "comments": ["Add tests"]},
            {"agent_id": "a2", "role": "code_reviewer", "impact_score": 90.0, "risk_level": "low", "approved": True, "affected_modules": [], "comments": ["Fix naming"]},
        ]
        result = orchestrator._aggregate_reviews(analyses, 1, "test", {"files_changed": []})
        assert "Add tests" in result.recommendations
        assert "Fix naming" in result.recommendations


class TestFetchPRData:
    def test_fetch_pr_data(self, orchestrator):
        data = orchestrator._fetch_pr_data("owner/repo", 123)
        assert data["repo"] == "owner/repo"
        assert "files_changed" in data
        assert "diff_summary" in data
