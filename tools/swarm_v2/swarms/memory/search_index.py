"""Hybrid search combining BM25 keyword search with vector similarity."""

import logging
from typing import Optional

import numpy as np
from rank_bm25 import BM25Okapi

from swarms.memory.vector_store import VectorStore

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────

_RRF_K = 60  # Reciprocal Rank Fusion constant — standard value


class HybridSearchIndex:
    """Combines BM25 keyword search with vector similarity for best results.

    This index maintains an in-memory BM25 corpus alongside a
    :class:`VectorStore`.  At query time it fetches results from both
    sub-systems and merges them using Reciprocal Rank Fusion (RRF).

    The BM25 component gives exact keyword matches high weight, while
    the vector component captures semantic similarity.  The fusion
    step produces a single ranked list that outperforms either method
    alone on most queries.
    """

    def __init__(self, vector_store: VectorStore) -> None:
        """Initialise the hybrid index.

        Args:
            vector_store: A configured :class:`VectorStore` instance.
        """
        self.vector_store = vector_store
        self.bm25_index: Optional[BM25Okapi] = None
        self.corpus: list[dict] = []
        self._doc_id_to_index: dict[str, int] = {}

    # ── Indexing ───────────────────────────────────────────────────

    def build_index(self, documents: list[dict]) -> None:
        """Build the BM25 index from *documents*.

        Each document dict must contain at least:

        - ``id`` (str): Unique identifier.
        - ``text`` (str): The document body.
        - ``metadata`` (dict): Optional metadata (stored but not indexed).

        This also rebuilds the internal ``doc_id → index`` map used
        during result merging.

        Args:
            documents: List of document dictionaries.
        """
        self.corpus = documents
        self._doc_id_to_index = {}

        if not documents:
            self.bm25_index = None
            logger.warning("HybridSearchIndex: empty document set")
            return

        tokenized_corpus: list[list[str]] = []
        for idx, doc in enumerate(documents):
            text = doc.get("text", "")
            tokens = text.lower().split()
            tokenized_corpus.append(tokens)
            self._doc_id_to_index[doc["id"]] = idx

        self.bm25_index = BM25Okapi(tokenized_corpus)
        logger.info(
            "HybridSearchIndex: BM25 index built with %d documents",
            len(documents),
        )

    def add_document(self, doc: dict) -> None:
        """Add a single document and rebuild the index.

        Args:
            doc: Document dict with ``id``, ``text``, and ``metadata``.
        """
        self.corpus.append(doc)
        self.build_index(self.corpus)

    # ── Search ─────────────────────────────────────────────────────

    def search(
        self,
        query: str,
        n_results: int = 5,
        tags: Optional[list[str]] = None,
    ) -> list[dict]:
        """Run a hybrid search and return merged results.

        The algorithm:

        1. Execute BM25 keyword search over the local corpus.
        2. Execute vector search via :class:`VectorStore`.
        3. Combine with Reciprocal Rank Fusion (RRF).
        4. Return the top-*n_results* hits.

        Args:
            query: Free-text query.
            n_results: Maximum number of results to return.
            tags: Optional list of tags to filter the vector search.

        Returns:
            List of merged result dicts with ``id``, ``document``,
            ``metadata``, ``bm25_score``, ``vector_distance``,
            ``rrf_score``.
        """
        # 1. BM25 keyword search
        bm25_results = self._bm25_search(query, n_results * 3)

        # 2. Vector search
        where = {"tags": {"$contains_any": tags}} if tags else None
        vector_results = self.vector_store.search(
            query,
            n_results=n_results * 3,
            where=where,
        )

        # 3. Reciprocal Rank Fusion
        rrf_scores: dict[str, float] = {}
        result_meta: dict[str, dict] = {}

        # BM25 ranks (higher score = better → lower rank number)
        bm25_sorted = sorted(
            bm25_results,
            key=lambda x: x["score"],
            reverse=True,
        )
        for rank, hit in enumerate(bm25_sorted, start=1):
            doc_id = hit["id"]
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1.0 / (_RRF_K + rank)
            if doc_id not in result_meta:
                result_meta[doc_id] = {
                    "document": hit.get("text", ""),
                    "metadata": hit.get("metadata", {}),
                    "bm25_score": hit["score"],
                }

        # Vector ranks (lower distance = better → lower rank number)
        for rank, hit in enumerate(vector_results, start=1):
            doc_id = hit["id"]
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1.0 / (
                _RRF_K + rank
            )
            if doc_id not in result_meta:
                result_meta[doc_id] = {
                    "document": hit.get("document", ""),
                    "metadata": hit.get("metadata", {}),
                    "vector_distance": hit.get("distance", 0.0),
                }
            else:
                result_meta[doc_id]["vector_distance"] = hit.get("distance", 0.0)

        # 4. Sort by fused score and package
        sorted_ids = sorted(
            rrf_scores.keys(),
            key=lambda d: rrf_scores[d],
            reverse=True,
        )[:n_results]

        final: list[dict] = []
        for doc_id in sorted_ids:
            meta = result_meta.get(doc_id, {})
            final.append(
                {
                    "id": doc_id,
                    "document": meta.get("document", ""),
                    "metadata": meta.get("metadata", {}),
                    "bm25_score": meta.get("bm25_score", 0.0),
                    "vector_distance": meta.get("vector_distance", 0.0),
                    "rrf_score": rrf_scores[doc_id],
                }
            )
        return final

    def _bm25_search(self, query: str, n_results: int) -> list[dict]:
        """Run BM25 keyword search over the local corpus.

        Args:
            query: Free-text query string.
            n_results: Maximum number of results.

        Returns:
            List of dicts with ``id``, ``text``, ``metadata``, ``score``.
        """
        if not self.bm25_index or not self.corpus:
            return []

        tokens = query.lower().split()
        scores = self.bm25_index.get_scores(tokens)
        top_n = min(n_results, len(self.corpus))
        top_indices = np.argsort(scores)[::-1][:top_n]

        results: list[dict] = []
        for idx in top_indices:
            if scores[idx] <= 0:
                continue
            doc = self.corpus[idx]
            results.append(
                {
                    "id": doc["id"],
                    "text": doc.get("text", ""),
                    "metadata": doc.get("metadata", {}),
                    "score": float(scores[idx]),
                }
            )
        return results
