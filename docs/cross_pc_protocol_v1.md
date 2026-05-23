# Cross-PC Protocol v1 (Debug-First)

This document defines the canonical envelope and transport behavior for cross-PC communication across Cursor, Claude peers, Freebuff-style workers, and CLI agents.

## Objectives

- Use one message envelope across WebSocket, HTTP fallback, Redis bridge, and MCP adapters.
- Make every message traceable and replayable for debugging.
- Support online realtime delivery and offline store-and-forward delivery.

## Runtime + Network Compatibility

Protocol behavior is independent of operator runtime:

- Claude/Cursor on Windows
- Hermes/Claude in WSL
- Freebuff/CLI workers on Linux/Windows

Network support:

- Same LAN: native WS/HTTP + optional UDP discovery
- Different networks: explicit endpoints over VPN/Tailscale, SSH tunnel, or controlled port forwarding

## Envelope (Canonical JSON)

```json
{
  "schema_version": "cross-pc/v1",
  "message_id": "8f73104f-f1f8-462f-9f67-c17b7c0d0671",
  "trace_id": "5f93c3e0d49548a59f9fd8d1f01a95f5",
  "causation_id": "be4b11bf-14a8-43f4-8cc7-9f6bcf91e4a2",
  "from": "cursor-main",
  "to": "claude-peer-2",
  "topic": "task.request",
  "ts_utc": "2026-05-07T11:30:00Z",
  "require_ack": true,
  "ttl_sec": 120,
  "payload": {
    "task": "summarize_changes",
    "path": "updates/"
  },
  "debug": {
    "transport": "ws",
    "attempt": 1,
    "source_host": "workstation-a"
  }
}
```

## Required Fields

- `schema_version`: Must be `cross-pc/v1`.
- `message_id`: UUID-like unique identifier used for idempotency and ACK matching.
- `trace_id`: Correlation identifier spanning all related messages in one logical flow.
- `from`: Sender peer ID.
- `topic`: Message topic (`task.request`, `event.status`, `ack`, `heartbeat`, `error`, etc).
- `ts_utc`: UTC timestamp in ISO format.
- `payload`: Object payload (can be empty object).

## Optional Fields

- `causation_id`: Parent message ID when a message is caused by a previous message.
- `to`: Target peer ID. If omitted, message is treated as broadcast.
- `require_ack`: If true, receiver or gateway should produce an `ack`.
- `ttl_sec`: Delivery validity window (default 300; max 3600 in gateway).
- `debug`: Debug metadata object.

## Envelope Validation Rules

1. Reject if `schema_version` is not `cross-pc/v1`.
2. Reject if required keys are missing.
3. Reject if `payload` is not an object.
4. Coerce missing optional fields to defaults:
   - `to = ""`
   - `causation_id = ""`
   - `require_ack = false`
   - `ttl_sec = 300`
   - `debug = {}`
5. Enforce `ttl_sec` bounds: `1 <= ttl_sec <= 3600`.

## Delivery Semantics

- **WebSocket is primary** for live peers.
- **HTTP fallback** is used when WS is unavailable.
- **Store-and-forward** queue retains messages for offline target peers.
- **Idempotency**: duplicate `message_id` values are accepted but not re-processed.
- **ACK behavior**:
  - `require_ack=true` messages enter pending state until ACK arrives or retries exhaust.
  - ACK topic uses envelope with `topic="ack"` and `payload.message_id=<original_message_id>`.

## Transport API

### WebSocket

- Endpoint: `/ws`
- Client should first send `peer.register` envelope.
- Server responses use canonical envelope.

### HTTP Fallback

- `POST /publish`: submit one envelope.
- `POST /ack`: acknowledge a message by `message_id`.
- `GET /poll?peer_id=<id>&limit=<n>`: retrieve queued messages for peer.
- `GET /replay?trace_id=<trace>`: fetch trace history from event log.
- `GET /health`: gateway and queue health.

### Endpoint selection rules

1. Attempt WS first.
2. On WS connection failure, use HTTP fallback.
3. Record selected transport in `debug.transport`.
4. Keep envelope identical across both transports.

## Logging and Replay

Every inbound envelope is written to JSONL event log with:

- `direction`: inbound/outbound
- `transport`: ws/http/redis
- `status`: accepted/routed/queued/duplicate/rejected/acked
- `gateway_ts_utc`
- full canonical envelope

This allows deterministic replay by `trace_id` and `message_id`.

## Backward Compatibility Bridge

Gateway mirrors accepted messages to:

- Redis pub/sub: `alpha_engine_bus`
- Redis durable list: `bus:alpha_engine_bus:log`
- Target inbox (if `to` set): `agent:<to>:inbox`

Bridge payload is the same canonical envelope, serialized as JSON.

## Security and Remote Operation Notes

- Prefer private networks (VPN/Tailscale/ZeroTier) for cross-network transport.
- If exposing ports publicly, enforce host firewall rules and restrict source ranges.
- Discovery is optional; use static endpoint configuration when cross-network routing is used.
