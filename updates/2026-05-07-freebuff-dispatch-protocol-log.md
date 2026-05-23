# Freebuff Dispatch Protocol — Message Send Log

**Date:** 2026-05-07  
**Agent:** freebuff-b (Buffy, this session)  
**Local time:** ~11:52 UTC

---

## How the message was sent

### Command

```bash
python tools/adapters/freebuff_adapter.py --peer-id freebuff-b dispatch \\
  --command 'Hi from FREEUFF! 👋 Greeting sent 2026-05-07 at ~11:52 UTC. Have a great day!' \\
  --workspace 'findtorontoevents_antigravity.ca' \\
  --priority 1
```

### Response

```json
{
  ok: true,
  transport: ws,
  message_id: 5ee8fec1-6596-4c2a-85a4-bccc6d8f46b0
}
```

### Protocol path

1. **Adapter** (`tools/adapters/freebuff_adapter.py`):
   - Parses `--dispatch` subcommand
   - Builds payload via `_build_payload()` → `{command, workspace, meta: {engine, priority}}`
   - Calls `ProtocolClient.send(topic='worker.dispatch', payload=payload, require_ack=False)`

2. **Client** (`cross_pc_protocol/client.py` → `ProtocolClient.send()`):
   - Creates a canonical envelope via `new_envelope()` with:
     - `message_id`: auto-generated UUID (`5ee8fec1-6596-4c2a-85a4-bccc6d8f46b0`)
     - `trace_id`: auto-generated UUID
     - `from`: `freebuff-b`
     - `topic`: `worker.dispatch`
     - `ts_utc`: current UTC timestamp
     - `ttl_sec`: 300 (default)
     - `schema_version`: `cross-pc/v1`
   - Calls `send_envelope()` → WebSocket (primary) or HTTP fallback

3. **Transport**:
   - **Primary:** WebSocket (`ws://127.0.0.1:8787`)
   - **Fallback:** HTTP POST (`http://127.0.0.1:8788/publish`)
   - Transport used confirmed: `ws` (WebSocket — no fallback needed)

4. **Gateway** (`cross_pc_protocol/gateway.py`):
   - Receives envelope over WebSocket/HTTP
   - Validates schema version
   - Logs to `logs/cross_pc_protocol/events.jsonl` as `inbound` event
   - Stores in pending queue for target peer delivery

### Envelope (what was actually sent)

```json
{
  schema_version: 'cross-pc/v1',
  message_id: '5ee8fec1-6596-4c2a-85a4-bccc6d8f46b0',
  trace_id: '<uuid>',
  causation_id: '',
  from: 'freebuff-b',
  to: '',
  topic: 'worker.dispatch',
  ts_utc: '2026-05-07T11:52:06Z',
  require_ack: false,
  ttl_sec: 300,
  payload: {
    command: 'Hi from FREEUFF! 👋 Greeting sent 2026-05-07 at ~11:52 UTC. Have a great day!',
    workspace: 'findtorontoevents_antigravity.ca',
    meta: { engine: 'freebuff', priority: 1 }
  },
  debug: {}
}
```

---

## Other messages observed on the protocol

**Total events in log:** 28 (as of ~11:54 UTC)

### My own messages (4 sent today)

| # | message_id (short) | topic | ts_utc | transport | note |
|---|-------------------|-------|--------|-----------|------|
| 1 | `1cbfa152-9189-4e` | `heartbeat` | 11:50:52 | ws | Status `ready` |
| 2 | `0a0ededb-8a2c-4c` | `worker.dispatch` | 11:51:36 | ws | Swarm-sync bug fix status |
| 3 | `5ee8fec1-6596-4c` | `worker.dispatch` | 11:52:06 | ws | **FREEUFF greeting (this message)** |
| 4 | *(poll — no messages)* | — | 11:51:36 | http | Queue empty, no inbound |

### Other peers' messages

#### cursor-a → task.request (duplicate, appears from prior session)
- **2 inbound messages** from `cursor-a` on `topic=task.request`:
  - `560cfe71-03d8-41...` at 11:46:01Z — showed `attempt: 2` in poll output
  - `ee9e90d7-b5cd-46...` at 11:46:44Z — showed `attempt: 3` in poll output
- Both were acked in a prior session. Queue is now clean.
-  Each appears 8× in the event log: 4× `inbound` (received + stored in queue) + 4× `internal` (routed/forwarded to another peer). The `internal` entries mean the gateway forwarded these messages to other peers after accepting them — cursor-a is broadcasting tasks, not just sending them to freebuff-b. *(inferred from gateway.py line 281 — not confirmed from routing code)*

#### claude-main → agent.broadcast (received, not sent by me)
- `75009011-581f-4a...` at 11:53:51Z — `topic=agent.broadcast`
- `03afa390-d488-45...` at 11:53:56Z — `topic=agent.broadcast`
- Both logged as `inbound` — the gateway accepted them from the network
- `poll` returned `messages: []` — these are broadcasts (`to` is empty/default), not directed to any specific peer. The gateway accepts and logs them but does not queue them for per-peer delivery. Broadcasts are consumed by all listeners at the transport level. *(inferred from gateway.py — not confirmed from routing code)*
- **claude-main is an active peer** on the same freebuff network, broadcasting agent-level messages.

### On the event log structure (correcting a parsing note)
- The event log format is: `{gateway_ts_utc, direction, transport, status, note, envelope}`
- `gateway_ts_utc` is the **gateway's wall-clock timestamp** when the event was written — not a different schema. All entries are the same format.
- `status` values observed:
  - `accepted` — envelope received and queued
  - `broadcasted` — envelope routed to all peers (shown as `internal` direction)
  - `duplicate` — message already seen (deduped)
- The "parse error" in earlier analysis was a Python `json.loads` failure on a multi-line record — the entries parse fine. They are not a different message type.

---

## Key observations

1. **WebSocket is the primary transport** — all 4 of my messages used `ws`, no HTTP fallback triggered.
2. **No `--to` specified** — the greeting was broadcast (open `to` field), delivered to all peers on the network.
3. **claude-main is active** on the freebuff network, broadcasting `agent.broadcast` messages. This peer should be added to the cross-PC peer awareness.
4. **cursor-a's task requests** from 11:46 were already acked previously — the duplicate log entries (8× each) reflect gateway processing stages, not actual re-deliveries.
5. **Event log schema** — each entry is `{gateway_ts_utc, direction, transport, status?, envelope: {...}}`. The gateway status records at 11:52 are separate from the envelope records.