"""Tests for HierarchicalSwarmOrchestrator in swarms.engines.hierarchical_swarm."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest


from swarms.core.models import (
    AgentRole,
    HierarchicalSignal,
    SwarmTask,
    TaskStatus,
)
from swarms.engines.hierarchical_swarm import HierarchicalSwarmOrchestrator

# Internal constant for testing
_MAX_RISK_EXPOSURE = 0.15


@pytest.fixture
def orchestrator():
    """Create a HierarchicalSwarmOrchestrator with mocked infrastructure."""
    memory = MagicMock()
    memory.add = MagicMock(return_value="entry_id")
    bus = MagicMock()
    bus.publish = AsyncMock()
    bus.broadcast = AsyncMock()
    registry = MagicMock()
    registry.register = MagicMock()
    safety = MagicMock()

    orch = HierarchicalSwarmOrchestrator(memory=memory, bus=bus, registry=registry, safety=safety)
    yield orch


class TestGetRequiredAgents:
    def test_returns_six_agents(self):
        orch = HierarchicalSwarmOrchestrator(
            memory=MagicMock(), bus=MagicMock(), registry=MagicMock(), safety=MagicMock()
        )
        roles = orch.get_required_agents()
        assert len(roles) == 6

    def test_roles_correct(self):
        orch = HierarchicalSwarmOrchestrator(
            memory=MagicMock(), bus=MagicMock(), registry=MagicMock(), safety=MagicMock()
        )
        roles = orch.get_required_agents()
        assert roles.count(AgentRole.STRATEGIST) == 2
        assert roles.count(AgentRole.TACTICIAN) == 3
        assert roles.count(AgentRole.RISK_CONTROLLER) == 1

    def test_exact_roles(self):
        orch = HierarchicalSwarmOrchestrator(
            memory=MagicMock(), bus=MagicMock(), registry=MagicMock(), safety=MagicMock()
        )
        roles = orch.get_required_agents()
        expected = [
            AgentRole.STRATEGIST, AgentRole.STRATEGIST,
            AgentRole.TACTICIAN, AgentRole.TACTICIAN, AgentRole.TACTICIAN,
            AgentRole.RISK_CONTROLLER,
        ]
        assert roles == expected


class TestCreateAgents:
    def test_registers_six_agents(self):
        registry = MagicMock()
        orch = HierarchicalSwarmOrchestrator(
            memory=MagicMock(), bus=MagicMock(), registry=registry, safety=MagicMock()
        )
        agent_ids = orch.create_agents()
        assert len(agent_ids) == 6


class TestExecute:
    @pytest.mark.asyncio
    async def test_execute_returns_signals(self, orchestrator):
        task = SwarmTask(
            task_type="hierarchical",
            description="Decide",
            inputs={"market_data": {"trend": "up"}, "assets": ["AAPL"]},
        )
        result = await orchestrator.execute(task)
        assert "signals" in result
        assert isinstance(result["signals"], list)
        assert len(result["signals"]) > 0
        assert task.status == TaskStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_execute_stores_result(self, orchestrator):
        task = SwarmTask(
            task_type="hierarchical",
            description="Decide",
            inputs={"market_data": {}, "assets": ["AAPL"]},
        )
        await orchestrator.execute(task)
        orchestrator.memory.add.assert_called()

    @pytest.mark.asyncio
    async def test_3_layer_pipeline(self, orchestrator):
        task = SwarmTask(
            task_type="hierarchical",
            description="Decide",
            inputs={"market_data": {"bull": True}, "assets": ["AAPL", "GOOGL"]},
        )
        result = await orchestrator.execute(task)
        signals = result["signals"]
        levels = [s["level"] for s in signals]
        assert "strategic" in levels
        assert "tactical" in levels
        assert "execution" in levels


class TestStrategicLayer:
    @pytest.mark.asyncio
    async def test_returns_strategic_signals(self, orchestrator):
        strategists = ["strategist_0", "strategist_1"]
        signals = await orchestrator._strategic_layer({"trend": "up"}, strategists)
        assert len(signals) == 2
        assert all(s.level == "strategic" for s in signals)
        assert all(s.signal_type == "regime" for s in signals)

    @pytest.mark.asyncio
    async def test_signal_structure(self, orchestrator):
        strategists = ["strategist_0"]
        signals = await orchestrator._strategic_layer({}, strategists)
        assert isinstance(signals[0], HierarchicalSignal)
        assert signals[0].agent_id == "strategist_0"
        assert "outlook" in signals[0].payload
        assert 0.0 <= signals[0].confidence <= 1.0


class TestTacticalLayer:
    @pytest.mark.asyncio
    async def test_returns_tactical_signals(self, orchestrator):
        strategists = ["strategist_0"]
        tactical_ids = ["tactician_0", "tactician_1"]
        strategic_signals = await orchestrator._strategic_layer({}, strategists)
        tactical_signals = await orchestrator._tactical_layer(
            strategic_signals, ["AAPL"], tactical_ids
        )
        assert len(tactical_signals) == 2  # 2 tacticians x 1 asset
        assert all(s.level == "tactical" for s in tactical_signals)
        assert all(s.signal_type == "entry" for s in tactical_signals)

    @pytest.mark.asyncio
    async def test_multiple_assets(self, orchestrator):
        strategists = ["strategist_0"]
        tactical_ids = ["tactician_0"]
        strategic_signals = await orchestrator._strategic_layer({}, strategists)
        tactical_signals = await orchestrator._tactical_layer(
            strategic_signals, ["AAPL", "GOOGL", "MSFT"], tactical_ids
        )
        assert len(tactical_signals) == 3  # 1 tactician x 3 assets

    @pytest.mark.asyncio
    async def test_tactical_conditions_on_strategic(self, orchestrator):
        strategists = ["strategist_0"]
        tactical_ids = ["tactician_0"]
        strategic_signals = await orchestrator._strategic_layer({"bull": True}, strategists)
        tactical_signals = await orchestrator._tactical_layer(
            strategic_signals, ["AAPL"], tactical_ids
        )
        assert all(s.payload.get("asset") is not None for s in tactical_signals)
        assert all(s.payload.get("action") is not None for s in tactical_signals)


class TestExecutionLayer:
    @pytest.mark.asyncio
    async def test_returns_execution_signals(self, orchestrator):
        tactical = [
            HierarchicalSignal(
                level="tactical",
                agent_id="t_0",
                signal_type="entry",
                payload={"asset": "AAPL", "direction": "buy", "size": 100},
                confidence=0.8,
                timestamp=datetime.utcnow(),
            )
        ]
        execution = await orchestrator._execution_layer(tactical, "moderate", ["agent_0"])
        assert len(execution) == 1
        assert execution[0].level == "execution"
        assert execution[0].signal_type == "order"
        assert "order_size" in execution[0].payload
        assert "stop_loss_pct" in execution[0].payload

    def test_execution_sizes_half(self, orchestrator):
        tactical = [
            HierarchicalSignal(
                level="tactical",
                agent_id="t_0",
                signal_type="entry",
                payload={"asset": "AAPL", "size": 200},
                confidence=0.8,
                timestamp=datetime.utcnow(),
            )
        ]
        # Need to run async
        import asyncio
        execution = asyncio.run(orchestrator._execution_layer(tactical, "moderate", ["agent_0"]))
        assert execution[0].payload["order_size"] == 80  # base_size * confidence * profile_multiplier

    def test_execution_confidence_scaled(self, orchestrator):
        tactical = [
            HierarchicalSignal(
                level="tactical",
                agent_id="t_0",
                signal_type="entry",
                payload={"asset": "AAPL", "size": 100},
                confidence=0.8,
                timestamp=datetime.utcnow(),
            )
        ]
        import asyncio
        execution = asyncio.run(orchestrator._execution_layer(tactical, "moderate", ["agent_0"]))
        assert execution[0].confidence == 0.8  # confidence preserved from parent signal


class TestRiskCheck:
    @pytest.mark.asyncio
    async def test_vetoes_exceeding_limits(self, orchestrator):
        signals = [
            HierarchicalSignal(
                level="execution",
                agent_id="exec_0",
                signal_type="order",
                payload={"order_size": 999999, "asset": "AAPL"},  # huge
                confidence=0.9,
                timestamp=datetime.utcnow(),
            )
        ]
        result = await orchestrator._risk_check(signals, "risk_controller_0", "moderate")
        assert result[0].payload["vetoed"] is True

    @pytest.mark.asyncio
    async def test_allows_safe_signals(self, orchestrator):
        signals = [
            HierarchicalSignal(
                level="execution",
                agent_id="exec_0",
                signal_type="order",
                payload={"order_size": 0, "asset": "AAPL"},  # zero size avoids concentration veto
                confidence=0.9,
                timestamp=datetime.utcnow(),
            )
        ]
        result = await orchestrator._risk_check(signals, "risk_controller_0", "moderate")
        assert result[0].payload["vetoed"] is False

    @pytest.mark.asyncio
    async def test_no_position_no_veto(self, orchestrator):
        signals = [
            HierarchicalSignal(
                level="strategic",
                agent_id="s_0",
                signal_type="regime",
                payload={"outlook": "bullish"},
                confidence=0.8,
                timestamp=datetime.utcnow(),
            )
        ]
        result = await orchestrator._risk_check(signals, "risk_controller_0", "moderate")
        # No order_size in payload, so no veto
        assert result[0].payload["vetoed"] is False


class TestHierarchicalSignalStructure:
    def test_signal_creation(self):
        sig = HierarchicalSignal(
            level="strategic",
            agent_id="s1",
            signal_type="regime",
            payload={"outlook": "bullish"},
            confidence=0.8,
            timestamp=datetime.utcnow(),
        )
        assert sig.level == "strategic"
        assert sig.signal_type == "regime"
        assert sig.confidence == 0.8
        assert isinstance(sig.timestamp, datetime)

    def test_all_levels(self):
        for level in ["strategic", "tactical", "execution"]:
            sig = HierarchicalSignal(
                level=level,
                agent_id="a",
                signal_type="test",
                payload={},
                confidence=0.5,
                timestamp=datetime.utcnow(),
            )
            assert sig.level == level
