"""Async message bus for inter-agent communication.

Implements a thread-safe, asynchronous publish/subscribe message bus with
in-memory history, broadcast support, and timeout-based response waiting.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any, Callable, Optional

from swarms.core.models import MessageType, SwarmMessage

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# MessageBus
# ---------------------------------------------------------------------------


class MessageBus:
    """Async pub/sub message bus for swarm agents.

    Each subscriber (identified by ``agent_id``) receives an independent
    :class:`asyncio.Queue`.  Messages are persisted in an in-memory history
    log and can be filtered by recipient or message type.

    All mutating operations are protected by :class:`asyncio.Lock` so the bus
    is safe to use from multiple concurrent agents.
    """

    def __init__(self) -> None:
        """Initialise the bus with empty subscriber mapping and history."""
        self._subscribers: dict[str, asyncio.Queue[SwarmMessage]] = {}
        self._history: list[SwarmMessage] = []
        self._lock: asyncio.Lock = asyncio.Lock()

    # -- subscription -------------------------------------------------------

    def subscribe(self, agent_id: str) -> asyncio.Queue[SwarmMessage]:
        """Register *agent_id* and return its dedicated message queue.

        If the agent is already subscribed, the existing queue is returned.
        """
        if agent_id in self._subscribers:
            logger.debug("MessageBus: agent '%s' re-subscribed (existing queue)", agent_id)
            return self._subscribers[agent_id]
        queue: asyncio.Queue[SwarmMessage] = asyncio.Queue()
        self._subscribers[agent_id] = queue
        logger.info("MessageBus: agent '%s' subscribed", agent_id)
        return queue

    # -- publish ------------------------------------------------------------

    async def publish(self, message: SwarmMessage) -> None:
        """Persist *message* and route it to relevant subscribers.

        The message is appended to the internal history log and then
        dispatched to every subscriber whose ``agent_id`` appears in
        ``message.recipients``.  When ``message.recipients`` contains the
        wildcard ``"*"`` the message is delivered to **all** subscribers.
        """
        async with self._lock:
            self._history.append(message)

            if "*" in message.recipients:
                targets = list(self._subscribers.keys())
            else:
                targets = [
                    rid for rid in message.recipients if rid in self._subscribers
                ]

            for target_id in targets:
                try:
                    self._subscribers[target_id].put_nowait(message)
                except Exception:
                    logger.exception("MessageBus: failed to deliver to '%s'", target_id)

            logger.debug(
                "MessageBus: published msg %s (type=%s) to %d recipient(s)",
                message.id,
                message.msg_type.value,
                len(targets),
            )

    # -- broadcast ----------------------------------------------------------

    async def broadcast(
        self,
        payload: dict[str, Any],
        sender: str,
        msg_type: MessageType,
    ) -> None:
        """Construct a :class:`SwarmMessage` and send it to **all** subscribers.

        Parameters
        ----------
        payload:
            Arbitrary JSON-serialisable data carried by the message.
        sender:
            ``agent_id`` of the broadcasting agent.
        msg_type:
            The :class:`MessageType` classification for the message.
        """
        message = SwarmMessage(
            id=uuid.uuid4().hex[:12],
            msg_type=msg_type,
            sender=sender,
            recipients=["*"],
            payload=payload,
            timestamp=datetime.utcnow(),
        )
        await self.publish(message)

    # -- history query ------------------------------------------------------

    def get_history(
        self,
        agent_id: Optional[str] = None,
        msg_type: Optional[MessageType] = None,
    ) -> list[SwarmMessage]:
        """Return a filtered view of the message history.

        Parameters
        ----------
        agent_id:
            If given, only messages where this agent is among the recipients.
        msg_type:
            If given, only messages matching this type.

        Returns
        -------
        list[SwarmMessage]
            Chronologically ordered list of matching messages.
        """
        results: list[SwarmMessage] = []
        for msg in self._history:
            if agent_id is not None and agent_id not in msg.recipients and "*" not in msg.recipients:
                continue
            if msg_type is not None and msg.msg_type != msg_type:
                continue
            results.append(msg)
        return results

    # -- blocking receive with timeout --------------------------------------

    async def wait_for_response(
        self,
        agent_id: str,
        timeout: float = 30.0,
    ) -> Optional[SwarmMessage]:
        """Asynchronously wait for the next message addressed to *agent_id*.

        The call blocks until either a message arrives or *timeout* seconds
        elapse.

        Parameters
        ----------
        agent_id:
            The subscriber to listen on.
        timeout:
            Maximum seconds to wait before returning ``None``.

        Returns
        -------
        SwarmMessage or None
            The next message for the agent, or ``None`` on timeout.
        """
        queue = self.subscribe(agent_id)
        try:
            message = await asyncio.wait_for(queue.get(), timeout=timeout)
            return message
        except asyncio.TimeoutError:
            logger.debug("MessageBus: timeout waiting for response to '%s'", agent_id)
            return None

    # -- introspection ------------------------------------------------------

    def subscriber_count(self) -> int:
        """Return the number of currently subscribed agents."""
        return len(self._subscribers)

    def history_size(self) -> int:
        """Return the total number of messages persisted in history."""
        return len(self._history)
