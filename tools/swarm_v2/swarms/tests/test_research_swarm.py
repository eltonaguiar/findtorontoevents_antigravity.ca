"""Tests for ResearchSwarmOrchestrator in swarms.engines.research_swarm."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


from swarms.core.models import (
    AgentRole,
    ResearchFinding,
    ResearchResult,
    SwarmTask,
    TaskStatus,
)
from swarms.engines.research_swarm import ResearchSwarmOrchestrator, MIN_CONFIDENCE


@pytest.fixture
def orchestrator():
    """Create a ResearchSwarmOrchestrator with mocked infrastructure."""
    memory = MagicMock()
    memory.add = MagicMock(return_value="entry_id")
    memory.search = MagicMock(return_value=[])
    bus = MagicMock()
    bus.publish = AsyncMock()
    bus.broadcast = AsyncMock()
    registry = MagicMock()
    registry.register = MagicMock()
    registry.get = MagicMock(return_value=MagicMock())
    safety = MagicMock()

    orch = ResearchSwarmOrchestrator(memory=memory, bus=bus, registry=registry, safety=safety)
    yield orch


class TestGetRequiredAgents:
    def test_returns_four_researchers(self):
        orch = ResearchSwarmOrchestrator(
            memory=MagicMock(), bus=MagicMock(), registry=MagicMock(), safety=MagicMock()
        )
        roles = orch.get_required_agents()
        assert len(roles) == 4
        assert all(r == AgentRole.RESEARCHER for r in roles)


class TestCreateAgents:
    def test_registers_four_agents(self):
        registry = MagicMock()
        orch = ResearchSwarmOrchestrator(
            memory=MagicMock(), bus=MagicMock(), registry=registry, safety=MagicMock()
        )
        agent_ids = orch.create_agents()
        assert len(agent_ids) == 4


class TestExecute:
    @pytest.mark.asyncio
    async def test_execute_returns_result(self, orchestrator):
        task = SwarmTask(
            task_type="research",
            description="Research Python",
            inputs={"topic": "Python programming", "depth": 3},
        )
        result = await orchestrator.execute(task)
        assert "topic" in result
        assert "findings" in result
        assert "consensus_claims" in result
        assert "disputed_claims" in result
        assert "gaps" in result
        assert "sources" in result
        assert task.status == TaskStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_execute_stores_findings_in_memory(self, orchestrator):
        task = SwarmTask(
            task_type="research",
            description="Research topic",
            inputs={"topic": "AI"},
        )
        await orchestrator.execute(task)
        assert orchestrator.memory.add.called

    @pytest.mark.asyncio
    async def test_execute_correct_topic(self, orchestrator):
        task = SwarmTask(
            task_type="research",
            description="Research",
            inputs={"topic": "Machine Learning"},
        )
        result = await orchestrator.execute(task)
        assert result["topic"] == "Machine Learning"


class TestDecomposeTopic:
    def test_returns_sub_questions(self, orchestrator):
        questions = orchestrator._decompose_topic("Python", depth=3)
        assert isinstance(questions, list)
        assert len(questions) == 3
        assert all("Python" in q for q in questions)

    def test_depth_bounds_at_5(self, orchestrator):
        questions = orchestrator._decompose_topic("X", depth=10)
        assert len(questions) <= 5

    def test_different_questions(self, orchestrator):
        questions = orchestrator._decompose_topic("AI", depth=4)
        assert len(set(questions)) == len(questions)  # all unique

    def test_each_question_contains_topic(self, orchestrator):
        questions = orchestrator._decompose_topic("Blockchain", depth=3)
        for q in questions:
            assert "Blockchain" in q


class TestRunResearch:
    @pytest.mark.asyncio
    async def test_returns_findings(self, orchestrator):
        questions = ["What is Python?", "Why use Python?"]
        researchers = ["researcher_0", "researcher_1"]
        findings = await orchestrator._run_research("Python", questions, researchers)
        assert len(findings) == 2
        assert all(isinstance(f, ResearchFinding) for f in findings)

    @pytest.mark.asyncio
    async def test_findings_have_content(self, orchestrator):
        questions = ["Q1?"]
        researchers = ["researcher_0"]
        findings = await orchestrator._run_research("Python", questions, researchers)
        assert findings[0].claim != ""
        assert findings[0].source != ""
        assert len(findings[0].evidence) > 0

    @pytest.mark.asyncio
    async def test_distributed_to_researchers(self, orchestrator):
        questions = ["Q1?", "Q2?", "Q3?"]
        researchers = ["researcher_0", "researcher_1"]
        findings = await orchestrator._run_research("Python", questions, researchers)
        assert len(findings) == 3


class TestCrossVerify:
    def test_detects_contradictions(self, orchestrator):
        findings = [
            ResearchFinding(source="s1", confidence=0.9, claim="A is good", evidence=["e1"]),
            ResearchFinding(source="s2", confidence=0.5, claim="A is bad", evidence=["e2"]),
        ]
        contradictions = orchestrator._cross_verify(findings)
        assert len(contradictions) > 0
        assert findings[0].contradictions  # should be populated
        assert findings[1].contradictions  # should be populated

    def test_no_contradictions_when_similar_confidence(self, orchestrator):
        findings = [
            ResearchFinding(source="s1", confidence=0.8, claim="A is good", evidence=["e1"]),
            ResearchFinding(source="s2", confidence=0.85, claim="A is good too", evidence=["e2"]),
        ]
        contradictions = orchestrator._cross_verify(findings)
        assert len(contradictions) == 0

    def test_empty_findings(self, orchestrator):
        contradictions = orchestrator._cross_verify([])
        assert contradictions == []

    def test_single_finding_no_contradiction(self, orchestrator):
        findings = [
            ResearchFinding(source="s1", confidence=0.5, claim="X", evidence=[]),
        ]
        contradictions = orchestrator._cross_verify(findings)
        assert contradictions == []


class TestSynthesize:
    def test_research_result_structure(self, orchestrator):
        findings = [
            ResearchFinding(source="s1", confidence=0.9, claim="C1", evidence=["e1"]),
            ResearchFinding(source="s2", confidence=0.8, claim="C2", evidence=["e2"]),
        ]
        result = orchestrator._synthesize("Topic", findings, [], ["Q1?"])
        assert isinstance(result, ResearchResult)
        assert result.topic == "Topic"
        assert len(result.findings) == 2

    def test_consensus_claims_high_confidence_no_contradiction(self, orchestrator):
        findings = [
            ResearchFinding(source="s1", confidence=0.9, claim="C1", evidence=["e1"], contradictions=[]),
        ]
        result = orchestrator._synthesize("T", findings, [], ["Q?"])
        assert "C1" in result.consensus_claims

    def test_disputed_claims_from_contradictions(self, orchestrator):
        findings = [
            ResearchFinding(source="s1", confidence=0.9, claim="C1", evidence=["e1"]),
            ResearchFinding(source="s2", confidence=0.5, claim="C2", evidence=["e2"]),
        ]
        contradictions = [("C1", "C2")]
        result = orchestrator._synthesize("T", findings, contradictions, ["Q?"])
        assert len(result.disputed_claims) > 0

    def test_gaps_for_unanswered_questions(self, orchestrator):
        findings = [
            ResearchFinding(source="s1", confidence=0.9, claim="Other", evidence=[]),
        ]
        result = orchestrator._synthesize("T", findings, [], ["What is T?", "Unrelated?"])
        # "What is T?" should be in gaps since finding claim "Other" doesn't match
        assert len(result.gaps) >= 1

    def test_sources_unique(self, orchestrator):
        findings = [
            ResearchFinding(source="s1", confidence=0.9, claim="C1", evidence=[]),
            ResearchFinding(source="s2", confidence=0.8, claim="C2", evidence=[]),
        ]
        result = orchestrator._synthesize("T", findings, [], ["Q?"])
        assert set(result.sources) == {"s1", "s2"}

    def test_findings_stored_in_memory_on_execute(self, orchestrator):
        # This is tested at the execute level
        pass
