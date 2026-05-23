"""Tests for SwarmMemory in swarms.core.memory."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from swarms.core.memory import SwarmMemory
from swarms.core.models import ExportedSkill, MemoryEntry


@pytest.fixture
def mock_vector_store():
    """Create a mock VectorStore."""
    mock = MagicMock()
    mock.embed.return_value = [0.1, 0.2, 0.3]
    mock.add.return_value = None
    mock.search.return_value = []
    mock.search_by_vector.return_value = []
    mock.get_recent.return_value = []
    mock.delete.return_value = None
    mock.close.return_value = None
    return mock


@pytest.fixture
def memory(mock_vector_store):
    """Create a SwarmMemory with a mocked VectorStore."""
    with patch("swarms.core.memory.VectorStore", return_value=mock_vector_store):
        mem = SwarmMemory(collection_name="test", persist_dir="/tmp/test")
        yield mem


class TestAdd:
    def test_add_creates_entry_with_embedding(self, memory, mock_vector_store):
        entry = MemoryEntry(content="Hello world", source_swarm="coding")
        assert entry.embedding is None
        memory.add(entry)
        mock_vector_store.embed.assert_called_once_with("Hello world")
        assert entry.embedding == [0.1, 0.2, 0.3]

    def test_add_returns_entry_id(self, memory, mock_vector_store):
        entry = MemoryEntry(content="Test", source_swarm="test")
        result = memory.add(entry)
        assert result == entry.id

    def test_add_uses_existing_embedding(self, memory, mock_vector_store):
        entry = MemoryEntry(content="Test", source_swarm="test", embedding=[0.9, 0.8, 0.7])
        memory.add(entry)
        mock_vector_store.embed.assert_not_called()
        assert entry.embedding == [0.9, 0.8, 0.7]

    def test_add_calls_vector_store_add(self, memory, mock_vector_store):
        entry = MemoryEntry(content="Hello", source_swarm="coding")
        memory.add(entry)
        mock_vector_store.add.assert_called_once()
        call_kwargs = mock_vector_store.add.call_args.kwargs
        assert call_kwargs["id"] == entry.id
        assert call_kwargs["text"] == "Hello"
        assert "metadata" in call_kwargs


class TestSearch:
    def test_search_returns_entries(self, memory, mock_vector_store):
        mock_vector_store.search.return_value = [
            {
                "id": "abc123",
                "document": "Hello world",
                "metadata": {
                    "source_swarm": "coding",
                    "tags": ["python"],
                    "created_at": datetime.utcnow().isoformat(),
                },
                "distance": 0.1,
            }
        ]
        results = memory.search("hello", n_results=5)
        assert len(results) == 1
        assert results[0].id == "abc123"
        assert results[0].content == "Hello world"

    def test_search_passes_n_results(self, memory, mock_vector_store):
        mock_vector_store.search.return_value = []
        memory.search("test", n_results=10)
        mock_vector_store.search.assert_called_once()
        call_args = mock_vector_store.search.call_args
        assert call_args.kwargs.get("n_results") == 10

    def test_search_with_tags(self, memory, mock_vector_store):
        mock_vector_store.search.return_value = []
        memory.search("test", tags=["python", "code"])
        mock_vector_store.search.assert_called_once()
        call_kwargs = mock_vector_store.search.call_args.kwargs
        assert "where" in call_kwargs

    def test_search_empty_results(self, memory, mock_vector_store):
        mock_vector_store.search.return_value = []
        results = memory.search("nonexistent")
        assert results == []

    def test_search_returns_memory_entries(self, memory, mock_vector_store):
        mock_vector_store.search.return_value = [
            {
                "id": "id1",
                "document": "content1",
                "metadata": {
                    "source_swarm": "coding",
                    "tags": [],
                    "created_at": datetime.utcnow().isoformat(),
                },
            }
        ]
        results = memory.search("query")
        assert all(isinstance(r, MemoryEntry) for r in results)


class TestSearchByVector:
    def test_search_by_vector(self, memory, mock_vector_store):
        mock_vector_store.search_by_vector.return_value = [
            {
                "id": "id1",
                "document": "content",
                "metadata": {
                    "source_swarm": "test",
                    "tags": [],
                    "created_at": datetime.utcnow().isoformat(),
                },
            }
        ]
        results = memory.search_by_vector([0.1, 0.2, 0.3], n_results=3)
        assert len(results) == 1
        mock_vector_store.search_by_vector.assert_called_once_with([0.1, 0.2, 0.3], 3)

    def test_search_by_vector_empty(self, memory, mock_vector_store):
        mock_vector_store.search_by_vector.return_value = []
        results = memory.search_by_vector([0.0, 0.0], n_results=5)
        assert results == []


class TestGetRecent:
    def test_get_recent_returns_newest_first(self, memory, mock_vector_store):
        now = datetime.utcnow()
        mock_vector_store.get_recent.return_value = [
            {
                "id": "id1",
                "document": "newest",
                "metadata": {
                    "source_swarm": "coding",
                    "tags": [],
                    "created_at": now.isoformat(),
                },
            },
            {
                "id": "id2",
                "document": "older",
                "metadata": {
                    "source_swarm": "coding",
                    "tags": [],
                    "created_at": now.isoformat(),
                },
            },
        ]
        results = memory.get_recent(n=2)
        assert len(results) == 2
        assert results[0].content == "newest"

    def test_get_recent_with_swarm_type(self, memory, mock_vector_store):
        mock_vector_store.get_recent.return_value = []
        memory.get_recent(n=5, swarm_type="coding")
        mock_vector_store.get_recent.assert_called_once()
        call_kwargs = mock_vector_store.get_recent.call_args.kwargs
        assert "where" in call_kwargs

    def test_get_recent_empty(self, memory, mock_vector_store):
        mock_vector_store.get_recent.return_value = []
        results = memory.get_recent(n=10)
        assert results == []


class TestExportAsSkill:
    def test_export_as_skill_creates_exported_skill(self, memory, mock_vector_store):
        mock_vector_store.search.return_value = [
            {
                "id": "mem1",
                "document": "Python best practices",
                "metadata": {
                    "source_swarm": "coding",
                    "tags": ["python"],
                    "created_at": datetime.utcnow().isoformat(),
                },
            },
            {
                "id": "mem2",
                "document": "Testing guidelines",
                "metadata": {
                    "source_swarm": "coding",
                    "tags": ["testing"],
                    "created_at": datetime.utcnow().isoformat(),
                },
            },
        ]
        skill = memory.export_as_skill("python coding", "python-coding-skill")
        assert isinstance(skill, ExportedSkill)
        assert skill.name == "python-coding-skill"
        assert skill.swarm_type == "coding"
        assert len(skill.knowledge_base) == 2
        assert "mem1" in skill.knowledge_base
        assert "mem2" in skill.knowledge_base

    def test_export_as_skill_system_prompt(self, memory, mock_vector_store):
        mock_vector_store.search.return_value = [
            {
                "id": "mem1",
                "document": "Important concept",
                "metadata": {
                    "source_swarm": "research",
                    "tags": [],
                    "created_at": datetime.utcnow().isoformat(),
                },
            }
        ]
        skill = memory.export_as_skill("research topic", "research-skill")
        assert "Important concept" in skill.system_prompt
        assert skill.name == "research-skill"

    def test_export_as_skill_empty_memory(self, memory, mock_vector_store):
        mock_vector_store.search.return_value = []
        skill = memory.export_as_skill("nothing", "empty-skill")
        assert isinstance(skill, ExportedSkill)
        assert skill.knowledge_base == []
        assert skill.swarm_type == "general"

    def test_export_as_skill_description(self, memory, mock_vector_store):
        mock_vector_store.search.return_value = [
            {
                "id": "m1",
                "document": "c1",
                "metadata": {
                    "source_swarm": "coding",
                    "tags": [],
                    "created_at": datetime.utcnow().isoformat(),
                },
            }
        ]
        skill = memory.export_as_skill("query", "test-skill")
        assert "test-skill" in skill.description
        assert "1 relevant memories" in skill.description

    def test_export_as_skill_examples(self, memory, mock_vector_store):
        docs = []
        for i in range(6):
            docs.append({
                "id": f"m{i}",
                "document": f"content {i}",
                "metadata": {
                    "source_swarm": "coding",
                    "tags": [],
                    "created_at": datetime.utcnow().isoformat(),
                },
            })
        mock_vector_store.search.return_value = docs
        skill = memory.export_as_skill("query", "test-skill")
        assert len(skill.examples) <= 5  # capped at 5


class TestDelete:
    def test_delete_calls_vector_store(self, memory, mock_vector_store):
        memory.delete("entry_1")
        mock_vector_store.delete.assert_called_once_with("entry_1")


class TestClose:
    def test_close_calls_vector_store_close(self, memory, mock_vector_store):
        memory.close()
        mock_vector_store.close.assert_called_once()


class TestEntryToDoc:
    def test_entry_to_doc(self, memory):
        entry = MemoryEntry(
            content="Hello",
            source_swarm="coding",
            embedding=[0.1, 0.2],
            metadata={"key": "value"},
            tags=["python"],
        )
        doc = memory._entry_to_doc(entry)
        assert doc["id"] == entry.id
        assert doc["text"] == "Hello"
        assert doc["embedding"] == [0.1, 0.2]
        assert doc["metadata"]["source_swarm"] == "coding"
        assert doc["metadata"]["tags"] == ["python"]
        assert doc["metadata"]["key"] == "value"

    def test_doc_to_entry(self, memory):
        now = datetime.utcnow()
        doc = {
            "id": "abc123",
            "document": "Hello world",
            "embedding": [0.1, 0.2],
            "metadata": {
                "source_swarm": "coding",
                "tags": ["python"],
                "created_at": now.isoformat(),
            },
        }
        entry = memory._doc_to_entry(doc)
        assert entry.id == "abc123"
        assert entry.content == "Hello world"
        assert entry.embedding == [0.1, 0.2]
        assert entry.source_swarm == "coding"
        assert entry.tags == ["python"]

    def test_doc_to_entry_with_text_field(self, memory):
        now = datetime.utcnow()
        doc = {
            "id": "abc",
            "text": "Content",
            "metadata": {
                "source_swarm": "test",
                "tags": [],
                "created_at": now.isoformat(),
            },
        }
        entry = memory._doc_to_entry(doc)
        assert entry.content == "Content"

    def test_doc_to_entry_no_created_at(self, memory):
        doc = {
            "id": "abc",
            "document": "Content",
            "metadata": {
                "source_swarm": "test",
                "tags": [],
            },
        }
        entry = memory._doc_to_entry(doc)
        assert entry.content == "Content"
        assert entry.source_swarm == "test"
