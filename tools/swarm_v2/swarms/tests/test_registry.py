"""Tests for AgentRegistry in swarms.core.registry."""

from __future__ import annotations

import pytest

from swarms.core.models import AgentConfig, AgentRole
from swarms.core.registry import AgentRegistry


@pytest.fixture
def registry():
    """Create a fresh AgentRegistry."""
    return AgentRegistry()


@pytest.fixture
def sample_config():
    """Create a sample AgentConfig."""
    return AgentConfig(role=AgentRole.CODE_GENERATOR, model="gpt-4o")


class TestRegister:
    def test_register_adds_agent(self, registry, sample_config):
        registry.register("agent_1", sample_config)
        assert "agent_1" in registry
        assert len(registry) == 1

    def test_register_multiple(self, registry, sample_config):
        registry.register("agent_1", sample_config)
        registry.register(
            "agent_2",
            AgentConfig(role=AgentRole.CODE_REVIEWER, model="claude"),
        )
        assert len(registry) == 2
        assert "agent_1" in registry
        assert "agent_2" in registry

    def test_register_duplicate_raises(self, registry, sample_config):
        registry.register("agent_1", sample_config)
        with pytest.raises(ValueError, match="already registered"):
            registry.register("agent_1", sample_config)

    def test_register_all_roles(self, registry):
        for i, role in enumerate(AgentRole):
            config = AgentConfig(role=role, model="gpt-4o")
            registry.register(f"agent_{i}", config)
        assert len(registry) == len(AgentRole)


class TestUnregister:
    def test_unregister_removes_agent(self, registry, sample_config):
        registry.register("agent_1", sample_config)
        registry.unregister("agent_1")
        assert "agent_1" not in registry
        assert len(registry) == 0

    def test_unregister_silent_missing(self, registry):
        # Should not raise
        registry.unregister("nonexistent")
        assert len(registry) == 0

    def test_unregister_one_of_many(self, registry, sample_config):
        registry.register("a", sample_config)
        registry.register("b", sample_config)
        registry.unregister("a")
        assert "a" not in registry
        assert "b" in registry
        assert len(registry) == 1


class TestGet:
    def test_get_returns_correct_config(self, registry, sample_config):
        registry.register("agent_1", sample_config)
        result = registry.get("agent_1")
        assert result is not None
        assert result.role == AgentRole.CODE_GENERATOR
        assert result.model == "gpt-4o"

    def test_get_returns_none_for_missing(self, registry):
        result = registry.get("nonexistent")
        assert result is None

    def test_get_returns_copy_not_reference(self, registry, sample_config):
        registry.register("agent_1", sample_config)
        result = registry.get("agent_1")
        assert result is not None
        assert result == sample_config


class TestFindByRole:
    def test_find_by_role_filters(self, registry):
        registry.register("a1", AgentConfig(role=AgentRole.CODE_GENERATOR, model="gpt-4o"))
        registry.register("a2", AgentConfig(role=AgentRole.CODE_GENERATOR, model="gpt-4"))
        registry.register("a3", AgentConfig(role=AgentRole.CODE_REVIEWER, model="claude"))
        generators = registry.find_by_role(AgentRole.CODE_GENERATOR)
        assert len(generators) == 2
        for aid, cfg in generators:
            assert cfg.role == AgentRole.CODE_GENERATOR

    def test_find_by_role_no_match(self, registry):
        registry.register("a1", AgentConfig(role=AgentRole.CODE_GENERATOR, model="gpt-4o"))
        result = registry.find_by_role(AgentRole.STRATEGIST)
        assert result == []

    def test_find_by_role_returns_tuples(self, registry):
        registry.register("a1", AgentConfig(role=AgentRole.CODE_GENERATOR, model="gpt-4o"))
        results = registry.find_by_role(AgentRole.CODE_GENERATOR)
        assert len(results) == 1
        assert isinstance(results[0], tuple)
        assert results[0][0] == "a1"
        assert isinstance(results[0][1], AgentConfig)

    def test_find_by_role_all_roles(self, registry):
        for role in AgentRole:
            registry.register(f"agent_{role.value}", AgentConfig(role=role, model="gpt-4o"))
        for role in AgentRole:
            results = registry.find_by_role(role)
            assert len(results) == 1
            assert results[0][1].role == role


class TestListAgents:
    def test_list_agents_empty(self, registry):
        assert registry.list_agents() == []

    def test_list_agents_returns_all(self, registry):
        registry.register("a1", AgentConfig(role=AgentRole.CODE_GENERATOR, model="gpt-4o"))
        registry.register("a2", AgentConfig(role=AgentRole.CODE_REVIEWER, model="claude"))
        agents = registry.list_agents()
        assert len(agents) == 2
        ids = [aid for aid, _ in agents]
        assert "a1" in ids
        assert "a2" in ids

    def test_list_agents_snapshot(self, registry):
        registry.register("a1", AgentConfig(role=AgentRole.CODE_GENERATOR, model="gpt-4o"))
        agents = registry.list_agents()
        # Adding after list should not affect the snapshot
        registry.register("a2", AgentConfig(role=AgentRole.CODE_REVIEWER, model="claude"))
        assert len(agents) == 1


class TestGetHealth:
    def test_get_health_all_healthy(self, registry, sample_config):
        registry.register("a1", sample_config)
        registry.register("a2", sample_config)
        health = registry.get_health()
        assert health == {"a1": "healthy", "a2": "healthy"}

    def test_get_health_empty(self, registry):
        assert registry.get_health() == {}

    def test_get_health_after_unregister(self, registry, sample_config):
        registry.register("a1", sample_config)
        registry.register("a2", sample_config)
        registry.unregister("a1")
        health = registry.get_health()
        assert "a1" not in health
        assert "a2" in health
        assert health["a2"] == "healthy"


class TestDunderMethods:
    def test_len(self, registry, sample_config):
        assert len(registry) == 0
        registry.register("a1", sample_config)
        assert len(registry) == 1
        registry.register("a2", sample_config)
        assert len(registry) == 2

    def test_contains(self, registry, sample_config):
        registry.register("a1", sample_config)
        assert "a1" in registry
        assert "a2" not in registry
