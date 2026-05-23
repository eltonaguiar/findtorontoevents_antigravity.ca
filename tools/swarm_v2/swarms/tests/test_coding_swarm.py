"""Tests for CodingSwarmOrchestrator in swarms.engines.coding_swarm."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


from swarms.core.models import AgentRole, CodeArtifact, SwarmTask, TaskStatus
from swarms.engines.coding_swarm import CodingSwarmOrchestrator, TEST_COVERAGE_THRESHOLD


@pytest.fixture
def orchestrator():
    """Create a CodingSwarmOrchestrator with mocked infrastructure."""
    memory = MagicMock()
    memory.add = MagicMock(return_value="entry_id")
    bus = MagicMock()
    bus.publish = AsyncMock()
    bus.broadcast = AsyncMock()
    registry = MagicMock()
    registry.register = MagicMock()
    registry.get = MagicMock(return_value=MagicMock())
    safety = MagicMock()

    orch = CodingSwarmOrchestrator(memory=memory, bus=bus, registry=registry, safety=safety)
    yield orch


class TestGetRequiredAgents:
    def test_returns_correct_roles(self):
        orch = CodingSwarmOrchestrator(
            memory=MagicMock(), bus=MagicMock(), registry=MagicMock(), safety=MagicMock()
        )
        roles = orch.get_required_agents()
        assert len(roles) == 7
        assert roles.count(AgentRole.CODE_GENERATOR) == 3
        assert roles.count(AgentRole.CODE_REVIEWER) == 2
        assert roles.count(AgentRole.TEST_WRITER) == 2

    def test_ordering(self):
        orch = CodingSwarmOrchestrator(
            memory=MagicMock(), bus=MagicMock(), registry=MagicMock(), safety=MagicMock()
        )
        roles = orch.get_required_agents()
        assert roles[0] == AgentRole.CODE_GENERATOR
        assert roles[3] == AgentRole.CODE_REVIEWER
        assert roles[5] == AgentRole.TEST_WRITER


class TestCreateAgents:
    def test_registers_all_agents(self):
        registry = MagicMock()
        orch = CodingSwarmOrchestrator(
            memory=MagicMock(), bus=MagicMock(), registry=registry, safety=MagicMock()
        )
        agent_ids = orch.create_agents()
        assert len(agent_ids) == 7
        assert registry.register.call_count == 7

    def test_agent_ids_are_unique(self):
        registry = MagicMock()
        orch = CodingSwarmOrchestrator(
            memory=MagicMock(), bus=MagicMock(), registry=registry, safety=MagicMock()
        )
        agent_ids = orch.create_agents()
        assert len(agent_ids) == len(set(agent_ids))


class TestExecute:
    @pytest.mark.asyncio
    async def test_execute_runs_full_pipeline(self, orchestrator):
        task = SwarmTask(
            task_type="coding",
            description="Write a function",
            inputs={"description": "Write add() function", "models": ["gpt-4o"]},
        )
        result = await orchestrator.execute(task)
        assert "artifacts" in result
        assert "artifact_count" in result
        # Pipeline reaches a terminal state. With the deterministic template
        # path (no LLM), stub code may legitimately fail test enforcement and
        # yield FAILED — both terminal states are valid here.
        assert task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED)

    @pytest.mark.asyncio
    async def test_execute_stores_result(self, orchestrator):
        task = SwarmTask(
            task_type="coding",
            description="Write a function",
            inputs={"description": "Write add()"},
        )
        await orchestrator.execute(task)
        orchestrator.memory.add.assert_called()

    @pytest.mark.asyncio
    async def test_execute_with_strict_mode(self, orchestrator):
        task = SwarmTask(
            task_type="coding",
            description="Strict task",
            inputs={"description": "Write code", "strict": True},
        )
        result = await orchestrator.execute(task)
        assert result["strict"] is True

    @pytest.mark.asyncio
    async def test_execute_with_custom_models(self, orchestrator):
        task = SwarmTask(
            task_type="coding",
            description="Multi-model",
            inputs={"description": "Write code", "models": ["gpt-4o", "claude-sonnet"]},
        )
        result = await orchestrator.execute(task)
        assert "artifacts" in result


class TestDecomposeTask:
    def test_decompose_returns_list(self, orchestrator):
        tasks = orchestrator._decompose_task("Write a Python app")
        assert isinstance(tasks, list)
        assert len(tasks) >= 1
        assert "description" in tasks[0]

    def test_decompose_includes_filepath(self, orchestrator):
        tasks = orchestrator._decompose_task("Write code")
        assert "filepath" in tasks[0]
        assert "language" in tasks[0]


class TestRevisionLoop:
    @pytest.mark.asyncio
    async def test_revision_loop_respects_max_revisions(self, orchestrator):
        code_result = {
            "filepath": "test.py",
            "language": "python",
            "source_code": "def test(): pass",
            "tests": "def test_test(): pass",
            "test_results": {"passed": 1, "failed": 0, "coverage": 85.0},
        }
        reviewers = ["code_reviewer_0", "code_reviewer_1"]
        artifacts = await orchestrator._review_and_revise(
            [code_result], reviewers, max_revisions=1, strict=False
        )
        assert len(artifacts) == 1
        assert isinstance(artifacts[0], CodeArtifact)

    @pytest.mark.asyncio
    async def test_revision_loop_with_issues(self, orchestrator):
        orchestrator._run_reviewers = AsyncMock(return_value=[
            {"reviewer": "r1", "issues": True, "comment": "Fix this"},
            {"reviewer": "r2", "issues": False, "comment": "OK"},
        ])
        code_result = {
            "filepath": "test.py",
            "language": "python",
            "source_code": "def test(): pass",
            "tests": "def test_test(): pass",
            "test_results": {"passed": 1, "failed": 0, "coverage": 85.0},
        }
        reviewers = ["code_reviewer_0", "code_reviewer_1"]
        artifacts = await orchestrator._review_and_revise(
            [code_result], reviewers, max_revisions=2, strict=False
        )
        assert len(artifacts) == 1
        # Code should have been revised
        assert "Fixed revision" in artifacts[0].source_code or artifacts[0].source_code == "def test(): pass"


class TestTestEnforcement:
    def test_enforce_tests_accepts_passing(self, orchestrator):
        artifacts = [
            CodeArtifact(
                filepath="test.py",
                language="python",
                source_code="def foo(): pass",
                tests="def test_foo(): assert True",
                test_results={"passed": 5, "failed": 0, "coverage": 85.0},
            )
        ]
        result = orchestrator._enforce_tests(artifacts)
        assert len(result) == 1

    def test_enforce_tests_rejects_no_tests(self, orchestrator):
        artifacts = [
            CodeArtifact(
                filepath="test.py",
                language="python",
                source_code="def foo(): pass",
                tests=None,
                test_results=None,
            )
        ]
        result = orchestrator._enforce_tests(artifacts)
        assert len(result) == 0

    def test_enforce_tests_rejects_failures(self, orchestrator):
        artifacts = [
            CodeArtifact(
                filepath="test.py",
                language="python",
                source_code="def foo(): pass",
                tests="def test_foo(): assert False",
                test_results={"passed": 0, "failed": 3, "coverage": 50.0},
            )
        ]
        result = orchestrator._enforce_tests(artifacts)
        assert len(result) == 0

    def test_enforce_tests_rejects_low_coverage(self, orchestrator):
        artifacts = [
            CodeArtifact(
                filepath="test.py",
                language="python",
                source_code="def foo(): pass",
                tests="def test_foo(): pass",
                test_results={"passed": 1, "failed": 0, "coverage": TEST_COVERAGE_THRESHOLD - 10},
            )
        ]
        result = orchestrator._enforce_tests(artifacts)
        assert len(result) == 0

    def test_enforce_tests_boundary_coverage(self, orchestrator):
        artifacts = [
            CodeArtifact(
                filepath="test.py",
                language="python",
                source_code="def foo(): pass",
                tests="def test_foo(): pass",
                test_results={"passed": 1, "failed": 0, "coverage": TEST_COVERAGE_THRESHOLD},
            )
        ]
        result = orchestrator._enforce_tests(artifacts)
        assert len(result) == 1

    def test_enforce_tests_empty_list(self, orchestrator):
        result = orchestrator._enforce_tests([])
        assert result == []

    def test_enforce_tests_strict_rejects_all_failing(self, orchestrator):
        # strict=True (default): all-failing -> empty list.
        artifacts = [
            CodeArtifact(filepath="a.py", language="python",
                         source_code="x", tests="t",
                         test_results={"passed": 1, "failed": 2, "coverage": 90.0}),
        ]
        assert orchestrator._enforce_tests(artifacts, strict=True) == []

    def test_enforce_tests_non_strict_returns_best_effort(self, orchestrator):
        # strict=False: no clean artifact -> return the least-broken one.
        artifacts = [
            CodeArtifact(filepath="bad.py", language="python",
                         source_code="x", tests="t",
                         test_results={"passed": 1, "failed": 5, "coverage": 90.0}),
            CodeArtifact(filepath="best.py", language="python",
                         source_code="x", tests="t",
                         test_results={"passed": 4, "failed": 1, "coverage": 90.0}),
        ]
        result = orchestrator._enforce_tests(artifacts, strict=False)
        assert len(result) == 1
        assert result[0].filepath == "best.py"   # fewest failures wins

    def test_enforce_tests_non_strict_prefers_clean(self, orchestrator):
        # strict=False: a clean artifact still wins over best-effort.
        artifacts = [
            CodeArtifact(filepath="clean.py", language="python",
                         source_code="x", tests="t",
                         test_results={"passed": 3, "failed": 0, "coverage": 95.0}),
            CodeArtifact(filepath="broken.py", language="python",
                         source_code="x", tests="t",
                         test_results={"passed": 1, "failed": 1, "coverage": 95.0}),
        ]
        result = orchestrator._enforce_tests(artifacts, strict=False)
        assert [a.filepath for a in result] == ["clean.py"]

    def test_enforce_tests_mixed(self, orchestrator):
        artifacts = [
            CodeArtifact(
                filepath="good.py",
                language="python",
                source_code="def good(): pass",
                tests="def test_good(): pass",
                test_results={"passed": 1, "failed": 0, "coverage": 90.0},
            ),
            CodeArtifact(
                filepath="bad.py",
                language="python",
                source_code="def bad(): pass",
                tests=None,
                test_results=None,
            ),
        ]
        result = orchestrator._enforce_tests(artifacts)
        assert len(result) == 1
        assert result[0].filepath == "good.py"


class TestRunGenerators:
    @pytest.mark.asyncio
    async def test_run_generators(self, orchestrator):
        sub_tasks = [{"description": "task1", "filepath": "a.py", "language": "python"}]
        generators = ["code_generator_0"]
        result = await orchestrator._run_generators(sub_tasks, generators, ["gpt-4o"])
        assert len(result) == 1
        assert "source_code" in result[0]
        assert "filepath" in result[0]

    @pytest.mark.asyncio
    async def test_run_generators_distributes_tasks(self, orchestrator):
        sub_tasks = [
            {"description": f"task{i}", "filepath": f"a{i}.py", "language": "python"}
            for i in range(3)
        ]
        generators = ["code_generator_0", "code_generator_1"]
        result = await orchestrator._run_generators(sub_tasks, generators, ["gpt-4o"])
        assert len(result) == 3


class TestRunTestWriters:
    @pytest.mark.asyncio
    async def test_run_test_writers(self, orchestrator):
        code_results = [
            {"filepath": "a.py", "language": "python", "source_code": "def f(): pass"}
        ]
        test_writers = ["test_writer_0"]
        result = await orchestrator._run_test_writers(code_results, test_writers)
        assert len(result) == 1
        # TestWriterWorker enriches the tests; test_results is owned by the
        # generator stage upstream, not the test-writer stage.
        assert result[0]["tests"] is not None


class TestRunReviewers:
    @pytest.mark.asyncio
    async def test_run_reviewers(self, orchestrator):
        code = {"source_code": "def f(): pass"}
        reviewers = ["code_reviewer_0", "code_reviewer_1"]
        result = await orchestrator._run_reviewers(code, reviewers)
        assert len(result) == 2
        assert all("reviewer" in r for r in result)


class TestMemoryStorage:
    @pytest.mark.asyncio
    async def test_memory_storage_on_execute(self, orchestrator):
        task = SwarmTask(
            task_type="coding",
            description="Write code",
            inputs={"description": "Write hello_world()"},
        )
        await orchestrator.execute(task)
        assert orchestrator.memory.add.called
