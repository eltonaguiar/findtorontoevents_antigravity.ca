"""Tests for all Pydantic models in swarms.core.models."""

from __future__ import annotations

import uuid
from datetime import datetime

import pytest
from pydantic import ValidationError

from swarms.core.models import (
    AgentConfig,
    AgentRole,
    CodeArtifact,
    EnsembleResult,
    ExportedSkill,
    GitHubActionsResult,
    HierarchicalSignal,
    MemoryEntry,
    MessageType,
    PRReviewResult,
    ResearchFinding,
    ResearchResult,
    SwarmMessage,
    SwarmTask,
    TaskStatus,
    VoteResult,
)


# ─── AgentConfig ─────────────────────────────────────────────────────


class TestAgentConfig:
    def test_creation_with_defaults(self):
        config = AgentConfig(role=AgentRole.CODE_GENERATOR, model="gpt-4o")
        assert config.role == AgentRole.CODE_GENERATOR
        assert config.model == "gpt-4o"
        assert config.temperature == 0.7
        assert config.max_tokens == 4096
        assert config.system_prompt == ""
        assert config.tools_allowed == []
        assert config.read_only is True

    def test_creation_with_custom_values(self):
        config = AgentConfig(
            role=AgentRole.STRATEGIST,
            model="claude-sonnet",
            temperature=0.9,
            max_tokens=8192,
            system_prompt="You are a strategist.",
            tools_allowed=["read", "search"],
            read_only=False,
        )
        assert config.temperature == 0.9
        assert config.max_tokens == 8192
        assert config.system_prompt == "You are a strategist."
        assert config.tools_allowed == ["read", "search"]
        assert config.read_only is False

    def test_all_roles(self):
        for role in AgentRole:
            config = AgentConfig(role=role, model="gpt-4o")
            assert config.role == role

    def test_temperature_high_value(self):
        # pydantic v2 does not auto-bound floats; just verify high value accepted
        config = AgentConfig(role=AgentRole.CODE_GENERATOR, model="gpt-4o", temperature=2.5)
        assert config.temperature == 2.5


# ─── SwarmMessage ────────────────────────────────────────────────────


class TestSwarmMessage:
    def test_creation(self):
        msg = SwarmMessage(
            msg_type=MessageType.TASK_ASSIGNMENT,
            sender="agent_1",
            recipients=["agent_2"],
            payload={"task": "write code"},
        )
        assert msg.msg_type == MessageType.TASK_ASSIGNMENT
        assert msg.sender == "agent_1"
        assert msg.recipients == ["agent_2"]
        assert msg.payload == {"task": "write code"}
        assert msg.parent_id is None

    def test_timestamp_auto_populated(self):
        before = datetime.utcnow()
        msg = SwarmMessage(
            msg_type=MessageType.CODE_GENERATION,
            sender="a",
            recipients=["*"],
            payload={},
        )
        after = datetime.utcnow()
        assert before <= msg.timestamp <= after

    def test_id_auto_generated(self):
        msg = SwarmMessage(
            msg_type=MessageType.CODE_REVIEW,
            sender="a",
            recipients=["b"],
            payload={},
        )
        assert len(msg.id) == 12
        assert all(c in "0123456789abcdef" for c in msg.id)

    def test_parent_id(self):
        msg = SwarmMessage(
            msg_type=MessageType.CODE_REVIEW,
            sender="a",
            recipients=["b"],
            payload={},
            parent_id="abc123",
        )
        assert msg.parent_id == "abc123"

    def test_broadcast_recipients(self):
        msg = SwarmMessage(
            msg_type=MessageType.FINAL_OUTPUT,
            sender="orch",
            recipients=["*"],
            payload={"result": "done"},
        )
        assert "*" in msg.recipients


# ─── SwarmTask ───────────────────────────────────────────────────────


class TestSwarmTask:
    def test_creation_defaults(self):
        task = SwarmTask(task_type="coding", description="Write a function", inputs={})
        assert task.status == TaskStatus.PENDING
        assert task.priority == 1
        assert task.assigned_agents == []
        assert task.results == {}
        assert task.completed_at is None

    def test_status_transitions(self):
        task = SwarmTask(task_type="coding", description="test", inputs={})
        assert task.status == TaskStatus.PENDING
        task.status = TaskStatus.IN_PROGRESS
        assert task.status == TaskStatus.IN_PROGRESS
        task.status = TaskStatus.COMPLETED
        assert task.status == TaskStatus.COMPLETED
        task.status = TaskStatus.FAILED
        assert task.status == TaskStatus.FAILED
        task.status = TaskStatus.NEEDS_REVISION
        assert task.status == TaskStatus.NEEDS_REVISION

    def test_priority_levels(self):
        task = SwarmTask(task_type="coding", description="test", inputs={}, priority=2)
        assert task.priority == 2

    def test_all_task_statuses(self):
        for status in TaskStatus:
            task = SwarmTask(task_type="coding", description="test", inputs={}, status=status)
            assert task.status == status

    def test_assigned_agents(self):
        task = SwarmTask(
            task_type="coding",
            description="test",
            inputs={},
            assigned_agents=["agent_1", "agent_2"],
        )
        assert task.assigned_agents == ["agent_1", "agent_2"]

    def test_results_storage(self):
        task = SwarmTask(
            task_type="coding",
            description="test",
            inputs={},
            results={"output": "code"},
        )
        assert task.results == {"output": "code"}

    def test_timestamp_fields(self):
        before = datetime.utcnow()
        task = SwarmTask(task_type="coding", description="test", inputs={})
        after = datetime.utcnow()
        assert before <= task.created_at <= after
        assert task.completed_at is None


# ─── CodeArtifact ────────────────────────────────────────────────────


class TestCodeArtifact:
    def test_creation_minimal(self):
        art = CodeArtifact(
            filepath="src/main.py",
            language="python",
            source_code="def main(): pass",
        )
        assert art.tests is None
        assert art.test_results is None
        assert art.review_comments == []

    def test_creation_with_tests(self):
        art = CodeArtifact(
            filepath="src/main.py",
            language="python",
            source_code="def main(): pass",
            tests="def test_main(): pass",
            test_results={"passed": 10, "failed": 0, "coverage": 95.0},
            review_comments=[{"reviewer": "r1", "comment": "LGTM"}],
        )
        assert art.tests == "def test_main(): pass"
        assert art.test_results == {"passed": 10, "failed": 0, "coverage": 95.0}
        assert len(art.review_comments) == 1

    def test_test_results_structure(self):
        art = CodeArtifact(
            filepath="x.py",
            language="python",
            source_code="",
            test_results={"passed": 5, "failed": 2, "coverage": 60.0},
        )
        assert art.test_results["passed"] == 5
        assert art.test_results["failed"] == 2
        assert art.test_results["coverage"] == 60.0


# ─── PRReviewResult ──────────────────────────────────────────────────


class TestPRReviewResult:
    def test_creation(self):
        result = PRReviewResult(
            pr_number=123,
            pr_title="Add feature",
            impact_score=75.0,
            risk_level="medium",
            affected_files=["src/a.py"],
            breaking_changes=[],
            test_coverage_impact="+5%",
            recommendations=["Add more tests"],
        )
        assert result.approved is False  # default

    def test_risk_levels(self):
        for level in ["low", "medium", "high", "critical"]:
            result = PRReviewResult(
                pr_number=1,
                pr_title="test",
                impact_score=50.0,
                risk_level=level,
                affected_files=[],
                breaking_changes=[],
                test_coverage_impact="",
                recommendations=[],
            )
            assert result.risk_level == level

    def test_invalid_risk_level(self):
        with pytest.raises(ValidationError):
            PRReviewResult(
                pr_number=1,
                pr_title="test",
                impact_score=50.0,
                risk_level="extreme",  # invalid
                affected_files=[],
                breaking_changes=[],
                test_coverage_impact="",
                recommendations=[],
            )

    def test_approved_when_true(self):
        result = PRReviewResult(
            pr_number=1,
            pr_title="test",
            impact_score=85.0,
            risk_level="low",
            affected_files=[],
            breaking_changes=[],
            test_coverage_impact="+10%",
            recommendations=[],
            approved=True,
        )
        assert result.approved is True


# ─── GitHubActionsResult ─────────────────────────────────────────────


class TestGitHubActionsResult:
    def test_creation(self):
        result = GitHubActionsResult(
            repo="owner/repo",
            failed_jobs=[{"name": "test", "conclusion": "failure"}],
            flaky_jobs=[],
            stale_jobs=[],
            cancelled_jobs=[],
            recommendations=["Fix tests"],
        )
        assert result.repo == "owner/repo"
        assert len(result.failed_jobs) == 1

    def test_all_lists_empty(self):
        result = GitHubActionsResult(
            repo="x/y",
            failed_jobs=[],
            flaky_jobs=[],
            stale_jobs=[],
            cancelled_jobs=[],
            recommendations=[],
        )
        assert all(
            [
                result.failed_jobs == [],
                result.flaky_jobs == [],
                result.stale_jobs == [],
                result.cancelled_jobs == [],
            ]
        )


# ─── ResearchFinding ─────────────────────────────────────────────────


class TestResearchFinding:
    def test_creation(self):
        finding = ResearchFinding(
            source="https://example.com",
            confidence=0.85,
            claim="Python is popular",
            evidence=["TIOBE index", "GitHub stats"],
        )
        assert finding.source == "https://example.com"
        assert finding.confidence == 0.85
        assert finding.contradictions == []

    def test_confidence_bounds_valid(self):
        for conf in [0.0, 0.5, 1.0]:
            finding = ResearchFinding(
                source="s",
                confidence=conf,
                claim="test",
                evidence=[],
            )
            assert finding.confidence == conf

    def test_with_contradictions(self):
        finding = ResearchFinding(
            source="s",
            confidence=0.5,
            claim="test",
            evidence=[],
            contradictions=["counter claim"],
        )
        assert finding.contradictions == ["counter claim"]


# ─── ResearchResult ──────────────────────────────────────────────────


class TestResearchResult:
    def test_creation(self):
        finding = ResearchFinding(
            source="s", confidence=0.9, claim="c", evidence=["e"]
        )
        result = ResearchResult(
            topic="Python",
            findings=[finding],
            consensus_claims=["c"],
            disputed_claims=[],
            gaps=[],
            sources=["s"],
        )
        assert result.topic == "Python"
        assert len(result.findings) == 1

    def test_empty_result(self):
        result = ResearchResult(
            topic="X",
            findings=[],
            consensus_claims=[],
            disputed_claims=[],
            gaps=["No data"],
            sources=[],
        )
        assert result.gaps == ["No data"]


# ─── VoteResult ──────────────────────────────────────────────────────


class TestVoteResult:
    def test_creation(self):
        vote = VoteResult(
            agent_id="agent_1",
            vote="buy",
            confidence=0.9,
            reasoning="Technical indicators are bullish",
        )
        assert vote.agent_id == "agent_1"
        assert vote.vote == "buy"
        assert vote.confidence == 0.9
        assert vote.reasoning == "Technical indicators are bullish"

    def test_vote_types(self):
        for v in ["buy", "sell", "hold", 42, 3.14, True]:
            vote = VoteResult(agent_id="a", vote=v, confidence=0.5, reasoning="r")
            assert vote.vote == v


# ─── EnsembleResult ──────────────────────────────────────────────────


class TestEnsembleResult:
    def test_creation(self):
        votes = [
            VoteResult(agent_id="a1", vote="buy", confidence=0.9, reasoning="r1"),
            VoteResult(agent_id="a2", vote="buy", confidence=0.7, reasoning="r2"),
        ]
        result = EnsembleResult(
            predictions=votes,
            aggregated_result="buy",
            confidence_interval=(0.6, 1.0),
            dissenting_opinions=[],
        )
        assert result.aggregated_result == "buy"
        assert result.confidence_interval == (0.6, 1.0)

    def test_with_dissent(self):
        result = EnsembleResult(
            predictions=[],
            aggregated_result=None,
            confidence_interval=(0.0, 0.0),
            dissenting_opinions=["Agent a3 disagrees"],
        )
        assert len(result.dissenting_opinions) == 1


# ─── HierarchicalSignal ──────────────────────────────────────────────


class TestHierarchicalSignal:
    def test_creation(self):
        sig = HierarchicalSignal(
            level="strategic",
            agent_id="strategist_0",
            signal_type="regime",
            payload={"outlook": "bullish"},
            confidence=0.8,
            timestamp=datetime.utcnow(),
        )
        assert sig.level == "strategic"
        assert sig.agent_id == "strategist_0"
        assert sig.signal_type == "regime"

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

    def test_invalid_level(self):
        with pytest.raises(ValidationError):
            HierarchicalSignal(
                level="invalid",
                agent_id="a",
                signal_type="test",
                payload={},
                confidence=0.5,
                timestamp=datetime.utcnow(),
            )


# ─── MemoryEntry ─────────────────────────────────────────────────────


class TestMemoryEntry:
    def test_creation_defaults(self):
        entry = MemoryEntry(content="Hello world", source_swarm="coding")
        assert entry.embedding is None
        assert entry.metadata == {}
        assert entry.tags == []
        assert len(entry.id) == 12

    def test_creation_full(self):
        entry = MemoryEntry(
            content="Hello",
            embedding=[0.1, 0.2, 0.3],
            metadata={"key": "value"},
            tags=["python", "code"],
            source_swarm="coding",
        )
        assert entry.embedding == [0.1, 0.2, 0.3]
        assert entry.metadata == {"key": "value"}
        assert entry.tags == ["python", "code"]

    def test_timestamp_auto(self):
        before = datetime.utcnow()
        entry = MemoryEntry(content="test", source_swarm="test")
        after = datetime.utcnow()
        assert before <= entry.created_at <= after


# ─── ExportedSkill ───────────────────────────────────────────────────


class TestExportedSkill:
    def test_creation_defaults(self):
        skill = ExportedSkill(
            name="python-coding",
            description="Python coding skill",
            swarm_type="coding",
            parameters={},
            examples=[],
            system_prompt="You are a Python expert.",
            knowledge_base=[],
        )
        assert skill.version == "1.0.0"

    def test_creation_full(self):
        skill = ExportedSkill(
            name="test-skill",
            description="A test skill",
            version="2.0.0",
            swarm_type="research",
            parameters={"depth": 3},
            examples=[{"input": "q", "output": "a"}],
            system_prompt="You are a researcher.",
            knowledge_base=["mem_1", "mem_2"],
        )
        assert skill.version == "2.0.0"
        assert skill.parameters == {"depth": 3}
        assert len(skill.examples) == 1
        assert skill.knowledge_base == ["mem_1", "mem_2"]

    def test_timestamp_auto(self):
        before = datetime.utcnow()
        skill = ExportedSkill(
            name="test",
            description="d",
            swarm_type="coding",
            parameters={},
            examples=[],
            system_prompt="s",
            knowledge_base=[],
        )
        after = datetime.utcnow()
        assert before <= skill.created_at <= after
