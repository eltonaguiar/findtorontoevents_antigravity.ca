"""ChromaDB vector store wrapper with sentence-transformers embeddings.

``chromadb`` and ``sentence-transformers`` are heavy optional dependencies
(the latter pulls in torch). When either is unavailable the store falls
back to an in-process implementation so the CLI still runs — keyword
search via :class:`HybridSearchIndex`'s BM25 half continues to work; only
the semantic-vector half degrades to a deterministic hash embedding.

HuggingFace fallback policy (avoids getting stuck on rate limits):
  1. If ``sentence-transformers`` installed AND (model is cached OR HF_TOKEN set):
     use ``all-MiniLM-L6-v2`` locally.
  2. Elif ``OLLAMA_CLOUD_KEY`` / ``OLLAMA_API_KEY`` set:
     call Ollama Cloud ``/v1/embeddings`` (nomic-embed-text).
  3. Elif ``DEEPSEEK_API`` / ``DEEPSEEK_API_KEY`` set:
     call DeepSeek ``/embeddings`` (deepseek-chat as proxy — uses last hidden state).
  4. Fall back to deterministic hash embedding (no semantics, never crashes).
"""

import hashlib
import json
import logging
import os
import struct
import urllib.error
import urllib.request
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

try:  # pragma: no cover - import-availability branch
    import chromadb
    from chromadb.config import Settings
    _HAS_CHROMA = True
except ImportError:  # pragma: no cover
    chromadb = None
    Settings = None
    _HAS_CHROMA = False

try:  # pragma: no cover - import-availability branch
    from sentence_transformers import SentenceTransformer
    _HAS_ST = True
except ImportError:  # pragma: no cover
    SentenceTransformer = None
    _HAS_ST = False

_EMBED_DIM = 384
_USER_AGENT = "Mozilla/5.0 swarm-v2/2.0"


def _st_model_is_cached() -> bool:
    """Return True if all-MiniLM-L6-v2 is already in the local ST cache."""
    import pathlib
    cache_roots = [
        os.environ.get("SENTENCE_TRANSFORMERS_HOME"),
        os.path.join(os.path.expanduser("~"), ".cache", "torch", "sentence_transformers"),
        os.path.join(os.path.expanduser("~"), ".cache", "huggingface", "hub"),
    ]
    for root in cache_roots:
        if root and pathlib.Path(root).exists():
            for child in pathlib.Path(root).iterdir():
                if "MiniLM" in child.name or "all-MiniLM" in child.name.lower():
                    return True
    return False


def _api_embed(text: str) -> Optional[list[float]]:
    """Try to embed via Ollama Cloud, then DeepSeek. Returns None on failure."""
    # --- Ollama Cloud (nomic-embed-text) ---
    ollama_key = os.environ.get("OLLAMA_CLOUD_KEY") or os.environ.get("OLLAMA_API_KEY")
    if ollama_key:
        try:
            body = json.dumps({"model": "nomic-embed-text", "input": text}).encode()
            req = urllib.request.Request(
                "https://ollama.com/v1/embeddings",
                data=body, method="POST",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {ollama_key}",
                    "User-Agent": _USER_AGENT,
                },
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
            vec = data["data"][0]["embedding"]
            # Resize to _EMBED_DIM if necessary
            if len(vec) != _EMBED_DIM:
                arr = np.array(vec, dtype=np.float32)
                if len(vec) > _EMBED_DIM:
                    arr = arr[:_EMBED_DIM]
                else:
                    arr = np.pad(arr, (0, _EMBED_DIM - len(arr)))
                norm = np.linalg.norm(arr)
                if norm > 0:
                    arr /= norm
                return arr.tolist()
            return vec
        except Exception as exc:  # noqa: BLE001
            logger.debug("Ollama embed failed: %s", exc)

    # --- DeepSeek (use chat endpoint to get last-token embedding proxy) ---
    deepseek_key = os.environ.get("DEEPSEEK_API") or os.environ.get("DEEPSEEK_API_KEY")
    if deepseek_key:
        try:
            body = json.dumps({
                "model": "deepseek-chat",
                "input": text,
                "encoding_format": "float",
            }).encode()
            req = urllib.request.Request(
                "https://api.deepseek.com/embeddings",
                data=body, method="POST",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {deepseek_key}",
                    "User-Agent": _USER_AGENT,
                },
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
            vec = data["data"][0]["embedding"]
            arr = np.array(vec[:_EMBED_DIM] if len(vec) > _EMBED_DIM else vec, dtype=np.float32)
            if len(arr) < _EMBED_DIM:
                arr = np.pad(arr, (0, _EMBED_DIM - len(arr)))
            norm = np.linalg.norm(arr)
            if norm > 0:
                arr /= norm
            return arr.tolist()
        except Exception as exc:  # noqa: BLE001
            logger.debug("DeepSeek embed failed: %s", exc)

    return None


def _hash_embed(text: str) -> list[float]:
    """Deterministic fallback embedding when sentence-transformers is absent.

    Not semantically meaningful — it only gives the vector store a stable,
    correctly-shaped vector so callers do not crash. Real semantic ranking
    requires ``sentence-transformers``.
    """
    vec = np.zeros(_EMBED_DIM, dtype=np.float32)
    for i in range(_EMBED_DIM):
        h = hashlib.sha256(f"{i}:{text}".encode("utf-8")).digest()[:4]
        vec[i] = struct.unpack("<i", h)[0] / 2147483648.0
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec /= norm
    return vec.tolist()


class _InMemoryCollection:
    """Minimal in-process stand-in for a ChromaDB collection."""

    def __init__(self) -> None:
        self._d = {"ids": [], "documents": [], "embeddings": [], "metadatas": []}

    def add(self, ids, documents, embeddings, metadatas) -> None:
        self._d["ids"].extend(ids)
        self._d["documents"].extend(documents)
        self._d["embeddings"].extend(embeddings)
        self._d["metadatas"].extend(metadatas)

    def _match(self, meta, where) -> bool:
        if not where:
            return True
        return all(meta.get(k) == v for k, v in where.items())

    def query(self, query_embeddings=None, n_results=5, where=None):
        q = np.array(query_embeddings[0], dtype=np.float32)
        scored = []
        for i, emb in enumerate(self._d["embeddings"]):
            if not self._match(self._d["metadatas"][i], where):
                continue
            e = np.array(emb, dtype=np.float32)
            dist = float(np.linalg.norm(q - e))
            scored.append((dist, i))
        scored.sort(key=lambda x: x[0])
        scored = scored[:n_results]
        return {
            "ids": [[self._d["ids"][i] for _, i in scored]],
            "documents": [[self._d["documents"][i] for _, i in scored]],
            "metadatas": [[self._d["metadatas"][i] for _, i in scored]],
            "distances": [[d for d, _ in scored]],
        }

    def get(self, where=None, limit=None):
        idx = [i for i in range(len(self._d["ids"]))
               if self._match(self._d["metadatas"][i], where)]
        if limit is not None:
            idx = idx[:limit]
        return {
            "ids": [self._d["ids"][i] for i in idx],
            "documents": [self._d["documents"][i] for i in idx],
            "metadatas": [self._d["metadatas"][i] for i in idx],
        }

    def delete(self, ids) -> None:
        keep = [i for i, _id in enumerate(self._d["ids"]) if _id not in set(ids)]
        for key in self._d:
            self._d[key] = [self._d[key][i] for i in keep]


class VectorStore:
    """Manages embedding generation and vector storage using ChromaDB.

    This class handles the lifecycle of embeddings — from generation via
    sentence-transformers to storage/retrieval via ChromaDB. It supports
    both text-based and vector-based search, as well as tag-filtered
    recent-entry retrieval.
    """

    def __init__(
        self,
        collection_name: str = "swarm_memory",
        persist_dir: str = "./memory_store",
    ) -> None:
        """Initialise the vector store.

        Args:
            collection_name: Name of the ChromaDB collection to use.
            persist_dir: Directory where ChromaDB persists its data.
        """
        self.persist_dir = persist_dir
        os.makedirs(persist_dir, exist_ok=True)

        self.client = None
        self.collection = None
        if _HAS_CHROMA:
            # Modern chromadb (>=0.5) uses PersistentClient; the legacy
            # Settings(chroma_db_impl="duckdb+parquet", ...) API raises a
            # deprecation ValueError. Fall back to in-memory on any failure.
            try:
                self.client = chromadb.PersistentClient(path=persist_dir)
                self.collection = self.client.get_or_create_collection(
                    collection_name
                )
            except Exception as exc:  # noqa: BLE001 - degrade, never crash
                logger.warning(
                    "chromadb init failed (%s) — VectorStore using in-memory "
                    "fallback.",
                    exc,
                )
                self.client = None
                self.collection = None
        if self.collection is None:
            if not _HAS_CHROMA:
                logger.warning(
                    "chromadb unavailable — VectorStore using in-memory "
                    "fallback (no cross-run persistence)."
                )
            self.collection = _InMemoryCollection()

        self.model = None
        self._use_api_embed = False

        if _HAS_ST:
            hf_token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")
            cached = _st_model_is_cached()
            if hf_token or cached:
                try:
                    # Suppress the unauthenticated-requests warning when loading
                    import warnings
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        self.model = SentenceTransformer("all-MiniLM-L6-v2")
                    logger.info("VectorStore: using SentenceTransformer (all-MiniLM-L6-v2)")
                except Exception as exc:
                    logger.warning("SentenceTransformer load failed (%s) — trying API embed", exc)
            else:
                logger.info(
                    "VectorStore: no HF_TOKEN and model not cached — "
                    "skipping HuggingFace download to avoid rate limits. "
                    "Trying API-based embeddings (Ollama/DeepSeek)."
                )

        if self.model is None:
            # Check if API embedding is available
            has_ollama = bool(os.environ.get("OLLAMA_CLOUD_KEY") or os.environ.get("OLLAMA_API_KEY"))
            has_deepseek = bool(os.environ.get("DEEPSEEK_API") or os.environ.get("DEEPSEEK_API_KEY"))
            if has_ollama or has_deepseek:
                self._use_api_embed = True
                provider = "Ollama Cloud" if has_ollama else "DeepSeek"
                logger.info("VectorStore: using %s API embeddings", provider)
            else:
                logger.warning(
                    "VectorStore: no embedding backend available "
                    "(no HF_TOKEN, no cached model, no OLLAMA_CLOUD_KEY/DEEPSEEK_API_KEY). "
                    "Using deterministic hash embedding — semantic ranking disabled. "
                    "Set HF_TOKEN or OLLAMA_CLOUD_KEY to enable real embeddings."
                )

    # ── Embedding ──────────────────────────────────────────────────

    def embed(self, text: str) -> list[float]:
        """Generate a dense embedding for *text*.

        Backend priority:
          1. SentenceTransformer (local, ``all-MiniLM-L6-v2``) — if loaded.
          2. API embedding (Ollama Cloud → DeepSeek) — if ``_use_api_embed``.
          3. Deterministic hash embedding — always available, never fails.

        Args:
            text: The input text to encode.

        Returns:
            A 384-dimensional floating-point vector.
        """
        if self.model is not None:
            return self.model.encode(text, convert_to_numpy=True).tolist()
        if self._use_api_embed:
            result = _api_embed(text)
            if result is not None:
                return result
            # API failed this call — log once and fall through to hash
            logger.debug("VectorStore: API embed returned None — using hash fallback for this call")
        return _hash_embed(text)

    # ── CRUD ───────────────────────────────────────────────────────

    def add(
        self,
        id: str,
        text: str,
        metadata: dict,
        embedding: Optional[list[float]] = None,
    ) -> None:
        """Add a document to the store.

        If *embedding* is not provided it is computed automatically from
        *text*.

        Args:
            id: Unique identifier for the document.
            text: The document body.
            metadata: Arbitrary key/value pairs to store alongside.
            embedding: Optional pre-computed embedding vector.
        """
        emb = embedding or self.embed(text)
        self.collection.add(
            ids=[id],
            documents=[text],
            embeddings=[emb],
            metadatas=[metadata],
        )

    def delete(self, id: str) -> None:
        """Remove the document identified by *id*."""
        self.collection.delete(ids=[id])

    # ── Search ─────────────────────────────────────────────────────

    def search(
        self,
        query: str,
        n_results: int = 5,
        where: Optional[dict] = None,
    ) -> list[dict]:
        """Search by query text.

        Args:
            query: The free-text query.
            n_results: Maximum number of hits to return.
            where: Optional ChromaDB metadata filter dictionary.

        Returns:
            List of dicts with keys ``id``, ``document``, ``metadata``,
            ``distance``.
        """
        query_embedding = self.embed(query)
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
        )
        return self._format_results(results)

    def search_by_vector(
        self,
        embedding: list[float],
        n_results: int = 5,
        where: Optional[dict] = None,
    ) -> list[dict]:
        """Search by a pre-computed embedding vector.

        Args:
            embedding: Dense vector from :meth:`embed` or another source.
            n_results: Maximum number of hits to return.
            where: Optional ChromaDB metadata filter dictionary.

        Returns:
            Same shape as :meth:`search`.
        """
        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=n_results,
            where=where,
        )
        return self._format_results(results)

    def get_recent(
        self,
        n: int = 10,
        where: Optional[dict] = None,
    ) -> list[dict]:
        """Return the *n* most recent entries, sorted by ``created_at``.

        This method over-fetches from ChromaDB and performs client-side
        sorting because ChromaDB does not natively support ordering by
        metadata fields.

        Args:
            n: Maximum number of entries to return.
            where: Optional metadata filter.

        Returns:
            List of raw documents (no distance field).
        """
        results = self.collection.get(where=where, limit=n * 3)
        if not results or not results["ids"]:
            return []
        items = self._format_get_results(results)
        items.sort(
            key=lambda x: x.get("metadata", {}).get("created_at", ""),
            reverse=True,
        )
        return items[:n]

    # ── Result formatting ──────────────────────────────────────────

    def _format_results(self, results) -> list[dict]:
        """Format ChromaDB *query* results into a plain list of dicts."""
        formatted: list[dict] = []
        if not results or not results["ids"]:
            return formatted
        for i in range(len(results["ids"][0])):
            formatted.append(
                {
                    "id": results["ids"][0][i],
                    "document": (
                        results["documents"][0][i]
                        if results["documents"]
                        else ""
                    ),
                    "metadata": (
                        results["metadatas"][0][i]
                        if results["metadatas"]
                        else {}
                    ),
                    "distance": (
                        results["distances"][0][i]
                        if results.get("distances")
                        else 0.0
                    ),
                }
            )
        return formatted

    def _format_get_results(self, results) -> list[dict]:
        """Format ChromaDB *get* results into a plain list of dicts."""
        formatted: list[dict] = []
        if not results or not results["ids"]:
            return formatted
        for i in range(len(results["ids"])):
            formatted.append(
                {
                    "id": results["ids"][i],
                    "document": (
                        results["documents"][i]
                        if results["documents"]
                        else ""
                    ),
                    "metadata": (
                        results["metadatas"][i]
                        if results["metadatas"]
                        else {}
                    ),
                }
            )
        return formatted

    # ── Lifecycle ──────────────────────────────────────────────────

    def close(self) -> None:
        """Close the store.

        ChromaDB with the DuckDB+Parquet backend auto-persists on every
        write, so this is currently a no-op.  Subclasses may override it
        if they need explicit teardown.
        """
