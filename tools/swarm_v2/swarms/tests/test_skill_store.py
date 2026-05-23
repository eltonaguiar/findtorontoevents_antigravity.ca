"""Tests for SkillStore in swarms.memory.skill_store."""

from __future__ import annotations

import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from swarms.core.models import ExportedSkill, MemoryEntry
from swarms.memory.skill_store import SkillStore


@pytest.fixture
def mock_memory():
    """Create a mock SwarmMemory."""
    memory = MagicMock()
    memory.search.return_value = [
        MemoryEntry(
            id="mem1",
            content="Python coding best practices",
            source_swarm="coding",
            tags=["python"],
        ),
        MemoryEntry(
            id="mem2",
            content="Testing patterns",
            source_swarm="coding",
            tags=["testing"],
        ),
    ]
    return memory


@pytest.fixture
def skill_store(mock_memory):
    """Create a SkillStore with a temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = SkillStore(memory=mock_memory, output_dir=tmpdir)
        yield store


class TestCreateSkillFromSwarm:
    def test_produces_exported_skill(self, skill_store, mock_memory):
        skill = skill_store.create_skill_from_swarm(
            swarm_type="coding",
            skill_name="python-expert",
            examples=[{"input": "Write a function", "output": "def func(): pass"}],
        )
        assert isinstance(skill, ExportedSkill)
        assert skill.name == "python-expert"
        assert skill.swarm_type == "coding"

    def test_knowledge_base_populated(self, skill_store, mock_memory):
        skill = skill_store.create_skill_from_swarm(
            swarm_type="coding",
            skill_name="test-skill",
            examples=[],
        )
        assert len(skill.knowledge_base) == 2
        assert "mem1" in skill.knowledge_base
        assert "mem2" in skill.knowledge_base

    def test_system_prompt_populated(self, skill_store, mock_memory):
        skill = skill_store.create_skill_from_swarm(
            swarm_type="coding",
            skill_name="test-skill",
            examples=[],
        )
        assert "software engineer" in skill.system_prompt.lower() or skill.system_prompt != ""

    def test_parameters_populated(self, skill_store, mock_memory):
        skill = skill_store.create_skill_from_swarm(
            swarm_type="coding",
            skill_name="test-skill",
            examples=[],
        )
        assert "test_framework" in skill.parameters
        assert skill.parameters["test_framework"] == "pytest"

    def test_description_populated(self, skill_store, mock_memory):
        skill = skill_store.create_skill_from_swarm(
            swarm_type="coding",
            skill_name="test-skill",
            examples=[],
        )
        assert "code" in skill.description.lower()

    def test_examples_preserved(self, skill_store, mock_memory):
        examples = [{"input": "Q1", "output": "A1"}]
        skill = skill_store.create_skill_from_swarm(
            swarm_type="coding",
            skill_name="test-skill",
            examples=examples,
        )
        assert skill.examples == examples

    def test_unknown_swarm_type(self, skill_store, mock_memory):
        skill = skill_store.create_skill_from_swarm(
            swarm_type="unknown_type",
            skill_name="test-skill",
            examples=[],
        )
        assert skill.swarm_type == "unknown_type"
        assert skill.system_prompt == "You are a helpful AI assistant."

    def test_memory_search_called(self, skill_store, mock_memory):
        skill_store.create_skill_from_swarm("coding", "test", [])
        mock_memory.search.assert_called_once_with("test", n_results=10)


class TestExportToClaudeSkill:
    def test_creates_markdown_file(self, skill_store):
        skill = ExportedSkill(
            name="Python Expert",
            description="Python coding skill",
            swarm_type="coding",
            parameters={},
            examples=[{"input": "Q", "output": "A"}],
            system_prompt="You are a Python expert.",
            knowledge_base=[],
        )
        path = skill_store.export_to_claude_skill(skill)
        assert os.path.exists(path)
        assert path.endswith("_claude_skill.md")

    def test_contains_yaml_frontmatter(self, skill_store):
        skill = ExportedSkill(
            name="Test Skill",
            description="A test",
            swarm_type="coding",
            parameters={},
            examples=[],
            system_prompt="You are a test.",
            knowledge_base=[],
        )
        path = skill_store.export_to_claude_skill(skill)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert content.startswith("---")
        assert "name: Test Skill" in content
        assert "swarm_type: coding" in content

    def test_contains_system_prompt(self, skill_store):
        skill = ExportedSkill(
            name="Test",
            description="D",
            swarm_type="coding",
            parameters={},
            examples=[],
            system_prompt="You are an expert.",
            knowledge_base=[],
        )
        path = skill_store.export_to_claude_skill(skill)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "You are an expert." in content

    def test_contains_examples(self, skill_store):
        skill = ExportedSkill(
            name="Test",
            description="D",
            swarm_type="coding",
            parameters={},
            examples=[{"input": "Q1", "output": "A1"}],
            system_prompt="SP",
            knowledge_base=[],
        )
        path = skill_store.export_to_claude_skill(skill)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "Example 1" in content


class TestExportToClaudeProject:
    def test_creates_json_file(self, skill_store):
        skill = ExportedSkill(
            name="Python Expert",
            description="Python coding skill",
            swarm_type="coding",
            parameters={},
            examples=[{"input": "Q", "output": "A"}],
            system_prompt="You are a Python expert.",
            knowledge_base=[],
        )
        path = skill_store.export_to_claude_project(skill)
        assert os.path.exists(path)
        assert path.endswith("_claude_project.json")

    def test_valid_json(self, skill_store):
        skill = ExportedSkill(
            name="Test",
            description="D",
            swarm_type="coding",
            parameters={},
            examples=[],
            system_prompt="SP",
            knowledge_base=[],
        )
        path = skill_store.export_to_claude_project(skill)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["name"] == "Test"
        assert data["system_prompt"] == "SP"
        assert "example_conversations" in data

    def test_example_conversations_structure(self, skill_store):
        skill = ExportedSkill(
            name="Test",
            description="D",
            swarm_type="coding",
            parameters={},
            examples=[{"input": "Q1", "output": "A1"}],
            system_prompt="SP",
            knowledge_base=[],
        )
        path = skill_store.export_to_claude_project(skill)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert len(data["example_conversations"]) == 1
        messages = data["example_conversations"][0]["messages"]
        assert any(m["role"] == "user" for m in messages)
        assert any(m["role"] == "assistant" for m in messages)


class TestSaveAndLoadSkill:
    def test_save_skill_creates_file(self, skill_store):
        skill = ExportedSkill(
            name="SaveTest",
            description="Test saving",
            swarm_type="coding",
            parameters={},
            examples=[],
            system_prompt="SP",
            knowledge_base=[],
        )
        path = skill_store.save_skill(skill)
        assert os.path.exists(path)

    def test_load_skill_retrieves(self, skill_store):
        skill = ExportedSkill(
            name="LoadTest",
            description="Test loading",
            swarm_type="coding",
            parameters={},
            examples=[{"input": "Q", "output": "A"}],
            system_prompt="SP",
            knowledge_base=[],
        )
        skill_store.save_skill(skill)
        loaded = skill_store.load_skill("LoadTest")
        assert loaded is not None
        assert loaded.name == "LoadTest"
        assert loaded.description == "Test loading"

    def test_load_skill_not_found(self, skill_store):
        loaded = skill_store.load_skill("NonExistent")
        assert loaded is None

    def test_save_and_load_roundtrip(self, skill_store):
        original = ExportedSkill(
            name="RoundTrip",
            description="Test",
            version="2.0.0",
            swarm_type="research",
            parameters={"depth": 5},
            examples=[{"input": "Q1", "output": "A1", "extra": "data"}],
            system_prompt="SP",
            knowledge_base=["mem1", "mem2"],
        )
        skill_store.save_skill(original)
        loaded = skill_store.load_skill("RoundTrip")
        assert loaded.version == "2.0.0"
        assert loaded.swarm_type == "research"
        assert loaded.parameters == {"depth": 5}
        assert loaded.knowledge_base == ["mem1", "mem2"]


class TestSearchSkills:
    def test_finds_by_name(self, skill_store):
        skill = ExportedSkill(
            name="Python Coding",
            description="Python skill",
            swarm_type="coding",
            parameters={},
            examples=[],
            system_prompt="SP",
            knowledge_base=[],
        )
        skill_store.save_skill(skill)
        results = skill_store.search_skills("python")
        assert len(results) == 1
        assert results[0].name == "Python Coding"

    def test_finds_by_description(self, skill_store):
        skill = ExportedSkill(
            name="Test",
            description="Machine learning patterns",
            swarm_type="research",
            parameters={},
            examples=[],
            system_prompt="SP",
            knowledge_base=[],
        )
        skill_store.save_skill(skill)
        results = skill_store.search_skills("machine learning")
        assert len(results) == 1

    def test_no_match(self, skill_store):
        skill = ExportedSkill(
            name="Test",
            description="D",
            swarm_type="coding",
            parameters={},
            examples=[],
            system_prompt="SP",
            knowledge_base=[],
        )
        skill_store.save_skill(skill)
        results = skill_store.search_skills("nonexistent xyz")
        assert results == []

    def test_case_insensitive(self, skill_store):
        skill = ExportedSkill(
            name="UPPERCASE",
            description="DESC",
            swarm_type="coding",
            parameters={},
            examples=[],
            system_prompt="SP",
            knowledge_base=[],
        )
        skill_store.save_skill(skill)
        results = skill_store.search_skills("uppercase")
        assert len(results) == 1

    def test_empty_output_dir(self, skill_store):
        # Use a fresh empty directory
        with tempfile.TemporaryDirectory() as tmpdir:
            empty_store = SkillStore(memory=MagicMock(), output_dir=tmpdir)
            results = empty_store.search_skills("anything")
            assert results == []

    def test_ignores_non_json_files(self, skill_store):
        # Create a non-json file
        other_path = os.path.join(skill_store.output_dir, "readme.txt")
        with open(other_path, "w") as f:
            f.write("hello")
        results = skill_store.search_skills("anything")