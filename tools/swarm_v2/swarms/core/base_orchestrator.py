"""Abstract base orchestrator for all swarm types.

Concrete orchestrators (coding, pr-review, research, ensemble,
hierarchical) inherit from :class:`BaseOrchestrator` and implement
the swarm-specific execution logic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from swarms.core.memory import SwarmMemory
from swarms.core.messaging import MessageBus
from swarms.core.models import (
    AgentConfig,
    AgentRole,
    ExportedSkill,
    MemoryEntry,
    SwarmTask,
)
from swarms.core.registry import AgentRegistry
from swarms.core.safety import SafetyEnforcer


class BaseOrchestrator(ABC):
    """Abstract base class that every swarm orchestrator must extend.

    Parameters
    ----------
    memory :
        Persistent vector-store memory shared across the swarm.
    bus :
        Message bus for inter-agent communication.
    registry :
        Agent registry for config lookup and health monitoring.
    safety :
        Safety enforcer that governs tool and file access.

    Attributes
    ----------
    task_history :
        Ordered list of all tasks processed by this orchestrator instance.
    """

    def __init__(
        self,
        memory: SwarmMemory,
        bus: MessageBus,
        registry: AgentRegistry,
        safety: SafetyEnforcer,
    ) -> None:
        self.memory = memory
        self.bus = bus
        self.registry = registry
        self.safety = safety
        self.task_history: list[SwarmTask] = []

    # ─── Abstract interface ──────────────────────────────────────────

    @abstractmethod
    async def execute(self, task: SwarmTask) -> dict[str, Any]:
        """Execute *task* through the swarm pipeline.

        Parameters
        ----------
        task :
            The task to execute.

        Returns
        -------
        dict[str, Any]
            Execution results keyed by agent or stage name.
        """
        ...

    @abstractmethod
    def get_required_agents(self) -> list[AgentRole]:
        """Return the ordered list of agent roles required by this swarm.

        Returns
        -------
        list[AgentRole]
            One entry per agent slot (duplicates are allowed when multiple
            agents of the same role are needed).
        """
        ...

    # ─── Concrete helpers ────────────────────────────────────────────

    def create_agents(self) -> list[str]:
        r"""Instantiate and register agents per :meth:`get_required_agents`.

        Each role in the required list triggers creation of one agent
        with a default :class:`AgentConfig`.  Agents are registered on
        the orchestrator's :attr:`registry`.

        Returns
        -------
        list[str]
            ``agent_id``\ s of the newly created agents.
        """
        agent_ids: list[str] = []
        for role in self.get_required_agents():
            agent_id = f"{role.value}_{len(agent_ids)}"
            config = AgentConfig(
                role=role,
                model="gpt-4o",  # default model
                system_prompt=f"You are a {role.value} agent.",
            )
            self.registry.register(agent_id, config)
            agent_ids.append(agent_id)
        return agent_ids

    def store_result(self, task: SwarmTask, result: Any) -> None:
        """Persist *task* and its *result* to memory and task history.

        Parameters
        ----------
        task :
            The completed (or failed) task.
        result :
            The output produced by the swarm.
        """
        task.results["output"] = result
        self.task_history.append(task)
        entry = MemoryEntry(
            content=str(result),
            metadata={
                "task_id": task.id,
                "task_type": task.task_type,
                "status": task.status.value,
            },
            tags=[task.task_type, task.status.value],
            source_swarm=task.task_type,
        )
        self.memory.add(entry)

    def search_memory(self, query: str) -> list[MemoryEntry]:
        """Search the shared memory store.

        Parameters
        ----------
        query :
            Free-text query string.

        Returns
        -------
        list[MemoryEntry]
            Matching memory entries ordered by relevance.
        """
        return self.memory.search(query)

    def export_skill(self, skill_name: str) -> ExportedSkill:
        """Export swarm knowledge as a reusable skill.

        Parameters
        ----------
        skill_name :
            Name for the exported skill.

        Returns
        -------
        ExportedSkill
            Structured skill package ready for serialization.
        """
        return self.memory.export_as_skill(
            query=skill_name,
            skill_name=skill_name,
        )
