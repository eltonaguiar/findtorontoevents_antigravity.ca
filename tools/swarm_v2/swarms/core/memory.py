"""Persistent memory layer for swarm agents."""

import logging
from datetime import datetime
from typing import Optional

from swarms.core.models import ExportedSkill, MemoryEntry
from swarms.memory.vector_store import VectorStore

logger = logging.getLogger(__name__)


class SwarmMemory:
    """Persistent memory layer backed by ChromaDB + sentence-transformers.

    ``SwarmMemory`` is the primary interface used by orchestrators and
    skill stores.  It converts :class:`MemoryEntry` objects to/from the
    raw document format used by :class:`VectorStore` and provides
    high-level operations for search, recent-entry retrieval, and skill
    export.
    """

    def __init__(
        self,
        collection_name: str = "swarm_memory",
        persist_dir: str = "./memory_store",
    ) -> None:
        """Initialise the memory layer.

        Args:
            collection_name: ChromaDB collection name.
            persist_dir: Directory for ChromaDB persistence.
        """
        self.vector_store = VectorStore(
            collection_name=collection_name,
            persist_dir=persist_dir,
        )

    # ── MemoryEntry ↔ VectorStore conversion ───────────────────────

    @staticmethod
    def _entry_to_doc(entry: MemoryEntry) -> dict:
        """Convert a :class:`MemoryEntry` to the dict format expected by
        :class:`VectorStore`.
        """
        metadata = dict(entry.metadata)
        metadata.update(
            {
                "source_swarm": entry.source_swarm,
                "tags": entry.tags,
                "created_at": entry.created_at.isoformat(),
            }
        )
        return {
            "id": entry.id,
            "text": entry.content,
            "metadata": metadata,
            "embedding": entry.embedding,
        }

    @staticmethod
    def _doc_to_entry(doc: dict) -> MemoryEntry:
        """Convert a raw document dict back to a :class:`MemoryEntry`."""
        metadata = dict(doc.get("metadata", {}))
        tags = metadata.pop("tags", [])
        source_swarm = metadata.pop("source_swarm", "unknown")
        created_at_str = metadata.pop("created_at", None)

        created_at = (
            datetime.fromisoformat(created_at_str)
            if created_at_str
            else datetime.utcnow()
        )

        return MemoryEntry(
            id=doc["id"],
            content=doc.get("document", doc.get("text", "")),
            embedding=doc.get("embedding"),
            metadata=metadata,
            tags=tags if isinstance(tags, list) else [],
            source_swarm=source_swarm,
            created_at=created_at,
        )

    # ── Core operations ────────────────────────────────────────────

    def add(self, entry: MemoryEntry) -> str:
        """Add a :class:`MemoryEntry` to persistent memory.

        If the entry does not have an embedding it is auto-generated.

        Args:
            entry: The memory entry to store.

        Returns:
            The entry ID.
        """
        doc = self._entry_to_doc(entry)
        if doc["embedding"] is None:
            doc["embedding"] = self.vector_store.embed(doc["text"])
            entry.embedding = doc["embedding"]
        self.vector_store.add(
            id=doc["id"],
            text=doc["text"],
            metadata=doc["metadata"],
            embedding=doc["embedding"],
        )
        logger.debug("SwarmMemory: added entry %s", entry.id)
        return entry.id

    def search(
        self,
        query: str,
        n_results: int = 5,
        tags: Optional[list[str]] = None,
    ) -> list[MemoryEntry]:
        """Search memory by free-text *query*.

        Args:
            query: Free-text query string.
            n_results: Maximum number of results to return.
            tags: Optional list of tags to filter on.  Only entries
                tagged with at least one of the supplied tags are
                considered.

        Returns:
            List of :class:`MemoryEntry` objects, ranked by relevance.
        """
        where: Optional[dict] = None
        if tags:
            where = {"tags": {"$contains_any": tags}}

        results = self.vector_store.search(query, n_results=n_results, where=where)
        return [self._doc_to_entry(r) for r in results]

    def search_by_vector(
        self,
        embedding: list[float],
        n_results: int = 5,
    ) -> list[MemoryEntry]:
        """Search memory using a pre-computed embedding vector.

        Args:
            embedding: Dense embedding vector.
            n_results: Maximum number of results.

        Returns:
            List of :class:`MemoryEntry` objects.
        """
        results = self.vector_store.search_by_vector(embedding, n_results)
        return [self._doc_to_entry(r) for r in results]

    def get_recent(
        self,
        n: int = 10,
        swarm_type: Optional[str] = None,
    ) -> list[MemoryEntry]:
        """Return the *n* most recent memory entries.

        Entries are ordered by ``created_at`` descending (newest first).

        Args:
            n: Maximum number of entries.
            swarm_type: If given, only return entries produced by that
                swarm type (matched against ``source_swarm``).

        Returns:
            List of :class:`MemoryEntry` objects.
        """
        where: Optional[dict] = None
        if swarm_type:
            where = {"source_swarm": swarm_type}

        results = self.vector_store.get_recent(n, where=where)
        return [self._doc_to_entry(r) for r in results]

    def delete(self, entry_id: str) -> None:
        """Remove the entry identified by *entry_id* from memory."""
        self.vector_store.delete(entry_id)
        logger.debug("SwarmMemory: deleted entry %s", entry_id)

    # ── Skill export ───────────────────────────────────────────────

    def export_as_skill(
        self,
        query: str,
        skill_name: str,
    ) -> ExportedSkill:
        """Aggregate relevant memories into a structured skill.

        The top-*k* memories matching *query* are collected and used to
        populate the ``knowledge_base`` and ``examples`` fields of an
        :class:`ExportedSkill`.

        Args:
            query: Query used to find relevant memories.
            skill_name: Human-readable name for the exported skill.

        Returns:
            A populated :class:`ExportedSkill`.
        """
        memories = self.search(query, n_results=20)
        knowledge_base = [m.id for m in memories]

        examples: list[dict] = []
        for mem in memories[:5]:
            ex = {
                "input": query,
                "output": mem.content,
                "source": mem.source_swarm,
                "metadata": mem.metadata,
            }
            examples.append(ex)

        # Derive swarm type from the dominant source in results
        swarm_counts: dict[str, int] = {}
        for m in memories:
            swarm_counts[m.source_swarm] = swarm_counts.get(
                m.source_swarm, 0
            ) + 1
        dominant_swarm = max(swarm_counts, key=swarm_counts.get) if swarm_counts else "general"

        description = (
            f"Skill '{skill_name}' exported from swarm memory. "
            f"Based on {len(memories)} relevant memories, primarily "
            f"from '{dominant_swarm}' swarm runs."
        )

        # Build a system prompt from the memory content
        system_prompt_lines: list[str] = [
            f"You are a specialized assistant for: {skill_name}.",
            "",
            "Your knowledge is grounded in the following context:",
        ]
        for mem in memories[:10]:
            system_prompt_lines.append(f"- {mem.content[:200]}")
        system_prompt = "\n".join(system_prompt_lines)

        return ExportedSkill(
            name=skill_name,
            description=description,
            swarm_type=dominant_swarm,
            parameters={},
            examples=examples,
            system_prompt=system_prompt,
            knowledge_base=knowledge_base,
        )

    # ── Lifecycle ──────────────────────────────────────────────────

    def close(self) -> None:
        """Release resources held by the memory layer."""
        self.vector_store.close()
