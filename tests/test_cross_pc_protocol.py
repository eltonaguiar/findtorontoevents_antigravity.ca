from __future__ import annotations

import asyncio
import uuid

from cross_pc_protocol.gateway import ProtocolGateway
from cross_pc_protocol.schema import ProtocolValidationError, normalize_envelope, utc_now_iso


def _base_message(**overrides):
    payload = {
        "schema_version": "cross-pc/v1",
        "message_id": str(uuid.uuid4()),
        "trace_id": uuid.uuid4().hex,
        "causation_id": "",
        "from": "peer-a",
        "to": "peer-b",
        "topic": "task.request",
        "ts_utc": utc_now_iso(),
        "require_ack": True,
        "ttl_sec": 120,
        "payload": {"summary": "hello"},
        "debug": {"transport": "test"},
    }
    payload.update(overrides)
    return payload


def test_normalize_envelope_success():
    message = _base_message()
    normalized = normalize_envelope(message)
    assert normalized["schema_version"] == "cross-pc/v1"
    assert normalized["from"] == "peer-a"
    assert normalized["payload"]["summary"] == "hello"


def test_normalize_envelope_rejects_invalid_payload():
    message = _base_message(payload="oops")
    try:
        normalize_envelope(message)
        assert False, "Expected ProtocolValidationError"
    except ProtocolValidationError:
        assert True


def test_gateway_store_forward_and_poll(tmp_path):
    gateway = ProtocolGateway(
        ws_port=0,
        http_port=0,
        peer_id="test-gateway",
        event_log_path=str(tmp_path / "events.jsonl"),
    )

    async def _run():
        result = await gateway.process_inbound(_base_message(), transport="http")
        assert result["ok"] is True
        polled = gateway.poll("peer-b", limit=10)
        assert polled["ok"] is True
        assert len(polled["messages"]) == 1
        pending_before = gateway.retry_tracker.pending_count()
        assert pending_before == 1
        ack = await gateway.register_ack(polled["messages"][0]["message_id"], from_peer="peer-b")
        assert ack["ok"] is True
        assert gateway.retry_tracker.pending_count() == 0

    asyncio.run(_run())


def test_gateway_deduplicates_message_ids(tmp_path):
    gateway = ProtocolGateway(
        ws_port=0,
        http_port=0,
        peer_id="test-gateway",
        event_log_path=str(tmp_path / "events.jsonl"),
    )
    message = _base_message()

    async def _run():
        first = await gateway.process_inbound(message, transport="http")
        second = await gateway.process_inbound(message, transport="http")
        assert first["status"] == "accepted"
        assert second["status"] == "duplicate"

    asyncio.run(_run())
