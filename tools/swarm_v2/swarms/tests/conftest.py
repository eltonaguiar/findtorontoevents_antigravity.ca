"""Shared pytest fixtures and import mocking for swarm tests."""

from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import MagicMock

# ── Mock heavy dependencies before any imports ──────────────────────

# Mock chromadb
_chromadb = ModuleType("chromadb")
_chromadb.config = ModuleType("chromadb.config")
_chromadb.config.Settings = MagicMock
sys.modules["chromadb"] = _chromadb
sys.modules["chromadb.config"] = _chromadb.config

# Mock sentence_transformers
_st = ModuleType("sentence_transformers")


class _FakeSentenceTransformer:
    def __init__(self, *args, **kwargs):
        pass

    def encode(self, text, **kwargs):
        import numpy as np
        return np.array([0.1] * 384)


_st.SentenceTransformer = _FakeSentenceTransformer
sys.modules["sentence_transformers"] = _st

# Mock chromadb Client
class _FakeCollection:
    def __init__(self):
        self._data = {"ids": [], "documents": [], "embeddings": [], "metadatas": []}

    def add(self, ids, documents, embeddings, metadatas):
        self._data["ids"].extend(ids)
        self._data["documents"].extend(documents)
        self._data["embeddings"].extend(embeddings)
        self._data["metadatas"].extend(metadatas)

    def query(self, query_embeddings=None, n_results=5, where=None):
        return {
            "ids": [["id1"]],
            "documents": [["test doc"]],
            "metadatas": [[{"source_swarm": "test", "tags": [], "created_at": "2024-01-01T00:00:00"}]],
            "distances": [[0.1]],
        }

    def get(self, where=None, limit=None):
        return {
            "ids": self._data["ids"][:limit],
            "documents": self._data["documents"][:limit],
            "metadatas": self._data["metadatas"][:limit],
        }

    def delete(self, ids):
        pass


class _FakeClient:
    def __init__(self, *args, **kwargs):
        pass

    def get_or_create_collection(self, name):
        return _FakeCollection()


_chromadb.Client = _FakeClient


# ── Now safe to import swarms modules ───────────────────────────────
