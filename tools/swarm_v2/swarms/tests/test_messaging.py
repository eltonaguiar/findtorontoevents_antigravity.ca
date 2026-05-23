"""Tests for MessageBus in swarms.core.messaging."""

from __future__ import annotations

import asyncio

import pytest


from swarms.core.messaging import MessageBus
from swarms.core.models import MessageType, SwarmMessage


@pytest.fixture
def bus():
    """Create a fresh MessageBus for each test."""
    return MessageBus()


class TestSubscribe:
    @pytest.mark.asyncio
    async def test_subscribe_creates_queue(self, bus):
        queue = bus.subscribe("agent_1")
        assert queue is not None
        assert bus.subscriber_count() == 1

    @pytest.mark.asyncio
    async def test_subscribe_returns_existing_queue(self, bus):
        q1 = bus.subscribe("agent_1")
        q2 = bus.subscribe("agent_1")
        assert q1 is q2
        assert bus.subscriber_count() == 1

    @pytest.mark.asyncio
    async def test_multiple_subscribers(self, bus):
        bus.subscribe("agent_1")
        bus.subscribe("agent_2")
        bus.subscribe("agent_3")
        assert bus.subscriber_count() == 3


class TestPublish:
    @pytest.mark.asyncio
    async def test_publish_routes_to_subscriber(self, bus):
        queue = bus.subscribe("agent_1")
        msg = SwarmMessage(
            msg_type=MessageType.TASK_ASSIGNMENT,
            sender="orch",
            recipients=["agent_1"],
            payload={"task": "test"},
        )
        await bus.publish(msg)
        received = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert received.id == msg.id
        assert received.msg_type == MessageType.TASK_ASSIGNMENT

    @pytest.mark.asyncio
    async def test_publish_does_not_route_to_unrelated(self, bus):
        queue1 = bus.subscribe("agent_1")
        bus.subscribe("agent_2")
        msg = SwarmMessage(
            msg_type=MessageType.TASK_ASSIGNMENT,
            sender="orch",
            recipients=["agent_1"],
            payload={"task": "test"},
        )
        await bus.publish(msg)
        # agent_1 should receive
        received = await asyncio.wait_for(queue1.get(), timeout=1.0)
        assert received is not None

    @pytest.mark.asyncio
    async def test_publish_history(self, bus):
        msg = SwarmMessage(
            msg_type=MessageType.TASK_ASSIGNMENT,
            sender="orch",
            recipients=["agent_1"],
            payload={"task": "test"},
        )
        await bus.publish(msg)
        assert bus.history_size() == 1

    @pytest.mark.asyncio
    async def test_publish_multiple_messages(self, bus):
        bus.subscribe("agent_1")
        for i in range(5):
            msg = SwarmMessage(
                msg_type=MessageType.TASK_ASSIGNMENT,
                sender="orch",
                recipients=["agent_1"],
                payload={"index": i},
            )
            await bus.publish(msg)
        assert bus.history_size() == 5


class TestBroadcast:
    @pytest.mark.asyncio
    async def test_broadcast_reaches_all(self, bus):
        q1 = bus.subscribe("agent_1")
        q2 = bus.subscribe("agent_2")
        q3 = bus.subscribe("agent_3")
        await bus.broadcast(
            payload={"announcement": "hello"},
            sender="orch",
            msg_type=MessageType.FINAL_OUTPUT,
        )
        r1 = await asyncio.wait_for(q1.get(), timeout=1.0)
        r2 = await asyncio.wait_for(q2.get(), timeout=1.0)
        r3 = await asyncio.wait_for(q3.get(), timeout=1.0)
        assert r1.payload == {"announcement": "hello"}
        assert r2.payload == {"announcement": "hello"}
        assert r3.payload == {"announcement": "hello"}

    @pytest.mark.asyncio
    async def test_broadcast_increments_history(self, bus):
        bus.subscribe("a")
        bus.subscribe("b")
        await bus.broadcast({}, "orch", MessageType.FINAL_OUTPUT)
        assert bus.history_size() == 1


class TestGetHistory:
    @pytest.mark.asyncio
    async def test_get_history_returns_all(self, bus):
        bus.subscribe("agent_1")
        for i in range(3):
            msg = SwarmMessage(
                msg_type=MessageType.TASK_ASSIGNMENT,
                sender="orch",
                recipients=["agent_1"],
                payload={"i": i},
            )
            await bus.publish(msg)
        history = bus.get_history()
        assert len(history) == 3

    @pytest.mark.asyncio
    async def test_get_history_filters_by_agent_id(self, bus):
        bus.subscribe("agent_1")
        bus.subscribe("agent_2")
        msg1 = SwarmMessage(
            msg_type=MessageType.TASK_ASSIGNMENT,
            sender="orch",
            recipients=["agent_1"],
            payload={},
        )
        msg2 = SwarmMessage(
            msg_type=MessageType.CODE_REVIEW,
            sender="orch",
            recipients=["agent_2"],
            payload={},
        )
        await bus.publish(msg1)
        await bus.publish(msg2)
        history = bus.get_history(agent_id="agent_1")
        assert len(history) == 1
        assert history[0].recipients == ["agent_1"]

    @pytest.mark.asyncio
    async def test_get_history_filters_by_msg_type(self, bus):
        bus.subscribe("agent_1")
        msg1 = SwarmMessage(
            msg_type=MessageType.TASK_ASSIGNMENT,
            sender="orch",
            recipients=["agent_1"],
            payload={},
        )
        msg2 = SwarmMessage(
            msg_type=MessageType.CODE_REVIEW,
            sender="orch",
            recipients=["agent_1"],
            payload={},
        )
        await bus.publish(msg1)
        await bus.publish(msg2)
        history = bus.get_history(msg_type=MessageType.CODE_REVIEW)
        assert len(history) == 1
        assert history[0].msg_type == MessageType.CODE_REVIEW

    @pytest.mark.asyncio
    async def test_get_history_combined_filter(self, bus):
        bus.subscribe("agent_1")
        bus.subscribe("agent_2")
        msg1 = SwarmMessage(
            msg_type=MessageType.TASK_ASSIGNMENT,
            sender="orch",
            recipients=["agent_1"],
            payload={},
        )
        msg2 = SwarmMessage(
            msg_type=MessageType.TASK_ASSIGNMENT,
            sender="orch",
            recipients=["agent_2"],
            payload={},
        )
        msg3 = SwarmMessage(
            msg_type=MessageType.CODE_REVIEW,
            sender="orch",
            recipients=["agent_1"],
            payload={},
        )
        await bus.publish(msg1)
        await bus.publish(msg2)
        await bus.publish(msg3)
        history = bus.get_history(agent_id="agent_1", msg_type=MessageType.TASK_ASSIGNMENT)
        assert len(history) == 1
        assert history[0].recipients == ["agent_1"]
        assert history[0].msg_type == MessageType.TASK_ASSIGNMENT

    @pytest.mark.asyncio
    async def test_get_history_wildcard_recipient(self, bus):
        bus.subscribe("agent_1")
        bus.subscribe("agent_2")
        msg = SwarmMessage(
            msg_type=MessageType.FINAL_OUTPUT,
            sender="orch",
            recipients=["*"],
            payload={"announce": "all"},
        )
        await bus.publish(msg)
        history1 = bus.get_history(agent_id="agent_1")
        history2 = bus.get_history(agent_id="agent_2")
        assert len(history1) == 1
        assert len(history2) == 1


class TestWaitForResponse:
    @pytest.mark.asyncio
    async def test_wait_for_response_returns_message(self, bus):
        queue = bus.subscribe("agent_1")
        msg = SwarmMessage(
            msg_type=MessageType.TASK_ASSIGNMENT,
            sender="orch",
            recipients=["agent_1"],
            payload={"task": "test"},
        )
        # Publish after a short delay
        async def _send_delayed():
            await asyncio.sleep(0.05)
            await bus.publish(msg)

        asyncio.create_task(_send_delayed())
        received = await bus.wait_for_response("agent_1", timeout=2.0)
        assert received is not None
        assert received.id == msg.id

    @pytest.mark.asyncio
    async def test_wait_for_response_times_out(self, bus):
        bus.subscribe("agent_1")
        received = await bus.wait_for_response("agent_1", timeout=0.1)
        assert received is None

    @pytest.mark.asyncio
    async def test_wait_for_response_creates_subscription(self, bus):
        # agent not pre-subscribed
        msg = SwarmMessage(
            msg_type=MessageType.TASK_ASSIGNMENT,
            sender="orch",
            recipients=["new_agent"],
            payload={"task": "test"},
        )
        asyncio.create_task(bus.publish(msg))
        received = await bus.wait_for_response("new_agent", timeout=1.0)
        assert received is not None
        assert received.payload == {"task": "test"}


class TestIntrospection:
    @pytest.mark.asyncio
    async def test_subscriber_count_empty(self, bus):
        assert bus.subscriber_count() == 0

    @pytest.mark.asyncio
    async def test_history_size_empty(self, bus):
        assert bus.history_size() == 0

    @pytest.mark.asyncio
    async def test_subscriber_count_after_subscribe(self, bus):
        bus.subscribe("a")
        bus.subscribe("b")
        assert bus.subscriber_count() == 2

    @pytest.mark.asyncio
    async def test_history_size_tracks_messages(self, bus):
        bus.subscribe("a")
        msg = SwarmMessage(
            msg_type=MessageType.TASK_ASSIGNMENT,
            sender="orch",
            recipients=["a"],
            payload={},
        )
        await bus.publish(msg)
        await bus.publish(msg)
        assert bus.history_size() == 2
