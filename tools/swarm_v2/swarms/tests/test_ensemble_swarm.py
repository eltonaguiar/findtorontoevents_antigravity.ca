"""Tests for EnsembleSwarmOrchestrator in swarms.engines.ensemble_swarm."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


from swarms.core.models import AgentRole, EnsembleResult, SwarmTask, TaskStatus, VoteResult
from swarms.engines.ensemble_swarm import EnsembleSwarmOrchestrator, CONFIDENCE_THRESHOLD


@pytest.fixture
def orchestrator():
    """Create an EnsembleSwarmOrchestrator with mocked infrastructure."""
    memory = MagicMock()
    memory.add = MagicMock(return_value="entry_id")
    bus = MagicMock()
    bus.publish = AsyncMock()
    registry = MagicMock()
    registry.register = MagicMock()
    safety = MagicMock()

    orch = EnsembleSwarmOrchestrator(memory=memory, bus=bus, registry=registry, safety=safety)
    yield orch


class TestGetRequiredAgents:
    def test_returns_five_tacticians(self):
        orch = EnsembleSwarmOrchestrator(
            memory=MagicMock(), bus=MagicMock(), registry=MagicMock(), safety=MagicMock()
        )
        roles = orch.get_required_agents()
        assert len(roles) == 5
        assert all(r == AgentRole.TACTICIAN for r in roles)


class TestCreateAgents:
    def test_registers_five_agents(self):
        registry = MagicMock()
        orch = EnsembleSwarmOrchestrator(
            memory=MagicMock(), bus=MagicMock(), registry=registry, safety=MagicMock()
        )
        agent_ids = orch.create_agents()
        assert len(agent_ids) == 5


class TestExecute:
    @pytest.mark.asyncio
    async def test_execute_returns_result(self, orchestrator):
        task = SwarmTask(
            task_type="ensemble",
            description="Predict",
            inputs={"prediction_task": "Market direction", "task_type": "classification"},
        )
        result = await orchestrator.execute(task)
        assert "aggregated_result" in result
        assert "confidence_interval" in result
        assert "predictions" in result
        assert "dissenting_opinions" in result
        assert task.status == TaskStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_execute_regression_task(self, orchestrator):
        task = SwarmTask(
            task_type="ensemble",
            description="Predict price",
            inputs={
                "prediction_task": "Stock price",
                "task_type": "regression",
                "confidence_threshold": 0.9,
            },
        )
        result = await orchestrator.execute(task)
        assert "aggregated_result" in result
        assert "confidence_interval" in result

    @pytest.mark.asyncio
    async def test_execute_stores_result(self, orchestrator):
        task = SwarmTask(
            task_type="ensemble",
            description="Predict",
            inputs={"prediction_task": "Direction"},
        )
        await orchestrator.execute(task)
        orchestrator.memory.add.assert_called()


class TestAggregateClassifications:
    def test_weighted_majority(self, orchestrator):
        votes = [
            VoteResult(agent_id="a0", vote="buy", confidence=0.9, reasoning="r"),
            VoteResult(agent_id="a1", vote="buy", confidence=0.7, reasoning="r"),
            VoteResult(agent_id="a2", vote="sell", confidence=0.5, reasoning="r"),
        ]
        result = orchestrator._aggregate_classifications(votes)
        # buy weight = 0.9 + 0.7 = 1.6; sell weight = 0.5
        assert result == "buy"

    def test_tie_breaking(self, orchestrator):
        votes = [
            VoteResult(agent_id="a0", vote="buy", confidence=0.5, reasoning="r"),
            VoteResult(agent_id="a1", vote="sell", confidence=0.5, reasoning="r"),
        ]
        result = orchestrator._aggregate_classifications(votes)
        assert result in ["buy", "sell"]

    def test_empty_votes(self, orchestrator):
        result = orchestrator._aggregate_classifications([])
        assert result is None

    def test_single_vote(self, orchestrator):
        votes = [
            VoteResult(agent_id="a0", vote="hold", confidence=0.9, reasoning="r"),
        ]
        result = orchestrator._aggregate_classifications(votes)
        assert result == "hold"


class TestAggregateRegressions:
    def test_weighted_average(self, orchestrator):
        votes = [
            VoteResult(agent_id="a0", vote=100.0, confidence=0.9, reasoning="r"),
            VoteResult(agent_id="a1", vote=200.0, confidence=0.1, reasoning="r"),
        ]
        result = orchestrator._aggregate_regressions(votes)
        # (100*0.9 + 200*0.1) / (0.9+0.1) = (90+20)/1 = 110.0
        assert result == 110.0

    def test_empty_votes(self, orchestrator):
        result = orchestrator._aggregate_regressions([])
        assert result == 0.0

    def test_single_vote(self, orchestrator):
        votes = [
            VoteResult(agent_id="a0", vote=50.0, confidence=0.8, reasoning="r"),
        ]
        result = orchestrator._aggregate_regressions(votes)
        assert result == 50.0

    def test_zero_confidence(self, orchestrator):
        votes = [
            VoteResult(agent_id="a0", vote=100.0, confidence=0.0, reasoning="r"),
            VoteResult(agent_id="a1", vote=200.0, confidence=0.0, reasoning="r"),
        ]
        result = orchestrator._aggregate_regressions(votes)
        assert result == 0.0


class TestConfidenceInterval:
    def test_calculation(self, orchestrator):
        votes = [
            VoteResult(agent_id="a0", vote="buy", confidence=0.9, reasoning="r"),
            VoteResult(agent_id="a1", vote="buy", confidence=0.7, reasoning="r"),
        ]
        ci = orchestrator._confidence_interval(votes)
        assert isinstance(ci, tuple)
        assert len(ci) == 2
        assert 0.0 <= ci[0] <= ci[1] <= 1.0

    def test_empty_votes(self, orchestrator):
        ci = orchestrator._confidence_interval([])
        assert ci == (0.0, 0.0)

    def test_single_vote(self, orchestrator):
        votes = [
            VoteResult(agent_id="a0", vote="buy", confidence=0.8, reasoning="r"),
        ]
        ci = orchestrator._confidence_interval(votes)
        assert ci[0] == ci[1]  # stdev=0 for single sample

    def test_bounds_within_zero_one(self, orchestrator):
        votes = [
            VoteResult(agent_id="a0", vote="buy", confidence=0.99, reasoning="r"),
            VoteResult(agent_id="a1", vote="buy", confidence=0.01, reasoning="r"),
        ]
        ci = orchestrator._confidence_interval(votes)
        assert ci[0] >= 0.0
        assert ci[1] <= 1.0


class TestLowConfidenceExpansion:
    @pytest.mark.asyncio
    async def test_low_confidence_triggers_expansion(self, orchestrator):
        # Override confidence interval to trigger expansion
        task = SwarmTask(
            task_type="ensemble",
            description="Predict",
            inputs={
                "prediction_task": "Direction",
                "confidence_threshold": 0.99,  # very high threshold
            },
        )
        result = await orchestrator.execute(task)
        # Should still complete with more predictions
        assert "aggregated_result" in result
        assert len(result["predictions"]) > 5  # expanded

    @pytest.mark.asyncio
    async def test_spawn_extra_agents(self, orchestrator):
        extra_ids = await orchestrator._spawn_extra_agents(2)
        assert len(extra_ids) == 2
        assert all("extra" in aid for aid in extra_ids)
        assert orchestrator.registry.register.call_count == 2


class TestCollectVotes:
    @pytest.mark.asyncio
    async def test_collects_all_votes(self, orchestrator):
        # Use pre-created agents from create_agents
        orchestrator.create_agents()
        agent_ids = orchestrator.registry.register.call_args_list
        # Mock registry.get to return proper config
        orchestrator.registry.get = MagicMock(return_value=MagicMock())
        votes = await orchestrator._collect_votes(["tactician_0", "tactician_1"], "task")
        assert len(votes) == 2
        assert all(isinstance(v, VoteResult) for v in votes)

    @pytest.mark.asyncio
    async def test_votes_have_confidence(self, orchestrator):
        orchestrator.registry.get = MagicMock(return_value=MagicMock())
        votes = await orchestrator._collect_votes(["tactician_0"], "task")
        assert 0.0 <= votes[0].confidence <= 1.0

    @pytest.mark.asyncio
    async def test_votes_have_reasoning(self, orchestrator):
        orchestrator.registry.get = MagicMock(return_value=MagicMock())
        votes = await orchestrator._collect_votes(["tactician_0"], "task")
        assert votes[0].reasoning != ""
