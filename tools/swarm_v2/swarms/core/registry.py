"""Agent registry for the multi-agent swarm system.

Maintains a mapping from ``agent_id`` to :class:`AgentConfig` and provides
lookup, filtering, and health-check utilities.
"""

from __future__ import annotations

import logging
from typing import Optional

from swarms.core.models import AgentConfig, AgentRole

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# AgentRegistry
# ---------------------------------------------------------------------------


class AgentRegistry:
    """Central registry for all agents participating in a swarm.

    The registry is **not** async-safe by design; it is intended to be
    mutated only during the setup phase (inside the orchestrator's
    ``create_agents``) and read concurrently thereafter.  If dynamic
    registration/unregistration is required at runtime, callers must
    provide their own synchronisation.
    """

    def __init__(self) -> None:
        """Create an empty registry."""
        self._agents: dict[str, AgentConfig] = {}

    # -- CRUD ---------------------------------------------------------------

    def register(self, agent_id: str, config: AgentConfig) -> None:
        """Add an agent to the registry.

        Parameters
        ----------
        agent_id:
            Unique identifier for the agent.
        config:
            Immutable-style configuration describing the agent.

        Raises
        ------
        ValueError
            If *agent_id* is already registered.
        """
        if agent_id in self._agents:
            raise ValueError(f"Agent '{agent_id}' is already registered.")
        self._agents[agent_id] = config
        logger.info("AgentRegistry: registered '%s' (role=%s)", agent_id, config.role.value)

    def unregister(self, agent_id: str) -> None:
        """Remove an agent from the registry.

        Silently succeeds if the agent does not exist.
        """
        if agent_id in self._agents:
            del self._agents[agent_id]
            logger.info("AgentRegistry: unregistered '%s'", agent_id)

    def get(self, agent_id: str) -> Optional[AgentConfig]:
        """Retrieve the configuration for *agent_id*, or ``None``."""
        return self._agents.get(agent_id)

    # -- queries ------------------------------------------------------------

    def find_by_role(self, role: AgentRole) -> list[tuple[str, AgentConfig]]:
        """Return all ``(agent_id, config)`` pairs where ``config.role == role``."""
        return [
            (aid, cfg) for aid, cfg in self._agents.items() if cfg.role == role
        ]

    def list_agents(self) -> list[tuple[str, AgentConfig]]:
        """Return a snapshot of every registered agent as ``(agent_id, config)``."""
        return list(self._agents.items())

    # -- health --------------------------------------------------------------

    def get_health(self) -> dict[str, str]:
        """Return a health status map for all registered agents.

        Each entry is ``agent_id -> "healthy"``.  In a future revision this
        could incorporate heartbeat timestamps or failure counters.
        """
        return {aid: "healthy" for aid in self._agents}

    # -- introspection ------------------------------------------------------

    def __len__(self) -> int:
        """Return the number of registered agents."""
        return len(self._agents)

    def __contains__(self, agent_id: str) -> bool:
        """Check whether *agent_id* is registered."""
        return agent_id in self._agents
