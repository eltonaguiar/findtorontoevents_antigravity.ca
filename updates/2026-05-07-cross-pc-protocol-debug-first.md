# 2026-05-07 - Cross-PC Communication Protocol (Debug-First)

## What was missing

The repo had multiple partial coordination approaches (Redis list/pubsub patterns, MCP peer messaging, and file-based fallback), but no single cross-PC protocol that unified:

- transport behavior (WS primary + HTTP fallback),
- envelope schema/versioning,
- idempotency + ACK/retry reliability,
- and deterministic replay debugging.

This made multi-agent communication hard to standardize across Cursor, Claude peers, and Freebuff-style workers.

## What changed

1. Added canonical protocol spec:
   - `docs/cross_pc_protocol_v1.md`

2. Added core protocol package:
   - `cross_pc_protocol/schema.py` (validation + canonical normalization)
   - `cross_pc_protocol/gateway.py` (WS + HTTP gateway)
   - `cross_pc_protocol/lan_discovery.py` (UDP LAN discovery)
   - `cross_pc_protocol/reliability.py` (idempotency, retry, offline queue)
   - `cross_pc_protocol/storage.py` (JSONL event store)
   - `cross_pc_protocol/redis_bridge.py` (legacy Redis compatibility)
   - `cross_pc_protocol/client.py` (WS-first client with HTTP fallback)

3. Added operator and integration tools:
   - `tools/protocol_gateway.py`
   - `tools/lan_discovery.py`
   - `tools/protocol_inspect.py`
   - `tools/adapters/cursor_claude_adapter.py`
   - `tools/adapters/freebuff_adapter.py`

4. Added tests:
   - `tests/test_cross_pc_protocol.py`

5. Added rollout/runbook:
   - `docs/cross_pc_protocol_runbook.md`

## Verification

- Executed targeted pytest for protocol module:
  - `pytest tests/test_cross_pc_protocol.py`
- Verified pass criteria:
  - canonical schema normalization,
  - schema rejection on invalid payload,
  - store-and-forward queue + ACK completion,
  - duplicate suppression by `message_id`.
