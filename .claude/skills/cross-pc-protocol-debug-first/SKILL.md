---
name: cross-pc-protocol-debug-first
description: Use when implementing, operating, or debugging the cross-PC communication protocol that bridges Cursor, Claude peers, and Freebuff-style CLI agents across machines. Covers WebSocket+HTTP transport, canonical envelope, ACK/retry, store-and-forward, replay, LAN discovery, Redis backward-compat bridge, and the JSONL inspector workflow. Aliases - cross-pc, xpc, protocol-debug, cross_pc_protocol
---

# Cross-PC Protocol (Debug-First)

Operate the cross-PC bus that lets Cursor / Claude / Freebuff agents on different machines exchange tasks and results. Designed so every message is traceable, replayable, and survives offline peers. Backward compatible with the existing Redis `alpha_engine_bus`.

## Runtime-agnostic operator prompt

Use this exact prompt when delegating to Claude, Hermes, or any CLI agent:

```text
Use cross-pc-protocol-debug-first and run this flow exactly:
1) Verify gateway health.
2) Send heartbeat from my peer_id.
3) Poll queue once.
4) Broadcast a short status message to all peers.
5) Return message_id, transport, queue depth, and whether fallback to HTTP occurred.
Environment may be Windows PowerShell, cmd.exe, bash, or WSL. Use shell-safe JSON quoting for that environment.
If WebSocket is down, auto-fallback to HTTP and report it explicitly.
```

## Files in scope

Source of truth — never duplicate logic outside these:

- `cross_pc_protocol/schema.py` — envelope dataclass + validators
- `cross_pc_protocol/gateway.py` — WS primary + HTTP `/publish /poll /ack /replay /health`
- `cross_pc_protocol/storage.py` — JSONL event log + per-peer store-and-forward queues
- `cross_pc_protocol/reliability.py` — idempotency, ACK + retry, TTL expiry
- `cross_pc_protocol/redis_bridge.py` — publish to `alpha_engine_bus`, append `bus:alpha_engine_bus:log`, enqueue `agent:<peer_id>:inbox`
- `cross_pc_protocol/lan_discovery.py` — UDP broadcast peer discovery
- `cross_pc_protocol/client.py` — shared client used by adapters
- `tools/protocol_gateway.py` — gateway daemon entry point
- `tools/protocol_inspect.py` — CLI inspector (`tail / trace / replay / health`)
- `tools/lan_discovery.py` — discovery CLI
- `tools/adapters/cursor_claude_adapter.py` — Cursor + Claude peer wrapper
- `tools/adapters/freebuff_adapter.py` — Freebuff/CLI wrapper
- `tests/test_cross_pc_protocol.py`
- `docs/cross_pc_protocol_v1.md` — canonical spec
- `docs/cross_pc_protocol_runbook.md` — incident runbook
- `updates/2026-05-07-cross-pc-protocol-debug-first.md` — change log entry

## Canonical envelope (single schema everywhere)

```json
{
  "schema_version": "cross-pc/v1",
  "message_id": "<uuid4>",
  "trace_id": "<hex32>",
  "causation_id": "<uuid4 or null>",
  "from": "<peer_id>",
  "to": "<peer_id or topic>",
  "topic": "<dotted.topic>",
  "ts_utc": "<RFC3339 Z>",
  "require_ack": true,
  "ttl_sec": 120,
  "payload": {},
  "debug": {"transport": "ws|http|redis", "hop": 0, "host": "<hostname>"}
}
```

Rules:
- `message_id` is the idempotency key. Receivers MUST drop duplicates.
- `trace_id` propagates unchanged across hops; `causation_id` chains request→response.
- TTL expiry purges from store-and-forward; expired messages emit `status=expired` log line.
- Same envelope on WS, HTTP, Redis bridge, and adapter shims — no transport-specific fields.

## Transport

- **Primary:** WebSocket (`ws://<host>:<port>/ws`).
- **Fallback:** HTTP — `/publish` (POST envelope), `/poll?peer_id=&limit=` (GET drain), `/ack` (POST `{message_id}`), `/replay?trace_id=|message_id=`, `/health`.
- **Discovery:** `tools/lan_discovery.py` — UDP broadcast on configured port; mDNS optional.
- Auto-fallback: client tries WS, on failure transparently switches to HTTP polling. Transport recorded in `debug.transport`.

## Reliability

- **Idempotency:** `reliability.py` keeps a bounded LRU of seen `message_id`s per peer.
- **ACK + retry:** if `require_ack=true`, gateway retries with exponential backoff (1s, 2s, 4s, 8s, 16s, cap 60s) until ACK or TTL.
- **Store-and-forward:** offline peers — queue persisted in JSONL under `cross_pc_protocol/queues/<peer_id>.jsonl`; flushed on next `/poll` or WS reconnect.
- **Replay:** `protocol_inspect.py replay --trace-id <id>` or `--message-id <id>` resends from event log without changing IDs.

## Debug-first observability

Structured JSONL event log at `cross_pc_protocol/logs/events.jsonl`. One line per send/recv/ack/expire/error:

```json
{"ts":"...","direction":"out|in","transport":"ws|http|redis","status":"sent|delivered|ack|retry|expired|drop_dup|error","peer":"...","message_id":"...","trace_id":"...","topic":"...","detail":"..."}
```

Inspector CLI:

```
python tools/protocol_inspect.py tail [--peer ID] [--topic T] [--follow]
python tools/protocol_inspect.py trace --trace-id <id>
python tools/protocol_inspect.py replay --message-id <id>
python tools/protocol_inspect.py health
```

Deterministic incident workflow:
1. `health` — confirm gateway up, peer registry, queue depths.
2. `tail --follow` — watch live traffic, filter by peer/topic.
3. `trace --trace-id <id>` — full causal chain end-to-end.
4. `replay` if a hop dropped a message; verify with `tail`.

## Redis backward-compat bridge

For every cross-PC message that targets a Redis-bus subscriber, `redis_bridge.py` does ALL of:
- `PUBLISH alpha_engine_bus <envelope_json>`
- `RPUSH bus:alpha_engine_bus:log <envelope_json>`
- `RPUSH agent:<peer_id>:inbox <envelope_json>` (per recipient)

Inverse: Redis-only senders get wrapped into a v1 envelope with `debug.transport="redis"` so they show up in trace/replay.

## Compatibility adapters

- `tools/adapters/cursor_claude_adapter.py` — wraps Cursor and Claude peer IDs, speaks WS/HTTP, mirrors to Redis.
- `tools/adapters/freebuff_adapter.py` — CLI-friendly polling adapter for Freebuff and other batch agents.

Both expose `send` / `poll` / `ack` subcommands and a shared `--peer-id` flag.

## Verification — always run

```
python -m pytest tests/test_cross_pc_protocol.py -q
python tools/protocol_gateway.py --help
python tools/protocol_inspect.py --help
python tools/adapters/cursor_claude_adapter.py --help
python tools/adapters/freebuff_adapter.py --help
python tools/lan_discovery.py --help
```

All six MUST exit 0. If any --help fails, the adapter is broken — fix before shipping.

## Quickstart (3-terminal flow)

Terminal 1 — gateway:
```
python tools/protocol_gateway.py --host 0.0.0.0 --ws-port 8787 --http-port 8788
```

Terminal 2 — Cursor/Claude peer A sends:
```
python tools/adapters/cursor_claude_adapter.py --peer-id cursor-a send --topic task.request --payload '{"summary":"hello"}' --to freebuff-b --require-ack
```

Terminal 3 — Freebuff peer B polls + inspector:
```
python tools/adapters/freebuff_adapter.py --peer-id freebuff-b poll --limit 10
python tools/protocol_inspect.py tail --follow
```

## Environment command matrix (same protocol, different shells)

- **PowerShell (Windows):**
```
python tools/adapters/cursor_claude_adapter.py --peer-id claude-win send --topic heartbeat --payload '{"status":"ready"}' --to gateway-a
```

- **cmd.exe (Windows):**
```
python tools/adapters/cursor_claude_adapter.py --peer-id claude-cmd send --topic heartbeat --payload "{\"status\":\"ready\"}" --to gateway-a
```

- **bash / WSL (Hermes or Claude):**
```
python3 tools/adapters/cursor_claude_adapter.py --peer-id hermes-wsl send --topic heartbeat --payload '{"status":"ready"}' --to gateway-a
```

- **Freebuff CLI peer (any OS):**
```
python tools/adapters/freebuff_adapter.py --peer-id freebuff-b heartbeat --status ready
```

## Cross-network guidance (beyond LAN)

- **Same LAN:** use `--host 0.0.0.0` on gateway and connect peers with `--ws-url ws://<LAN_IP>:<ws_port>` and `--http-base http://<LAN_IP>:<http_port>`.
- **Different networks:** use one of:
  - VPN overlay (recommended): Tailscale/ZeroTier private IPs.
  - SSH tunnel:
    - Receiver machine: `ssh -N -L 8787:localhost:8787 -L 8788:localhost:8788 user@gateway-host`
    - Peer connects to `localhost` ports.
  - Port-forward with firewall allow rules (only if you control both sides).
- **If UDP discovery is blocked or routed networks are involved:** skip LAN discovery and use explicit gateway endpoint config.

## PowerShell-safe usage examples (verbatim)

```
python tools/adapters/cursor_claude_adapter.py --peer-id cursor-a send --topic task.request --payload '{"summary":"hello"}' --to freebuff-b --require-ack
python tools/adapters/freebuff_adapter.py --peer-id freebuff-b poll --limit 10
python tools/protocol_inspect.py health
```

PowerShell quoting note: single-quoted JSON above works in pwsh 7+. For cmd.exe use double quotes with escaped inner: `"{\"summary\":\"hello\"}"`. For bash leave as-is.

## Common failure modes and fixes

| Symptom | Likely cause | Fix |
|---|---|---|
| `JSONDecodeError` from adapter `send` | shell ate quotes around `--payload` | Use single quotes in pwsh/bash; in cmd.exe escape inner double quotes |
| Peer never receives, no error | offline peer, message queued | `protocol_inspect.py tail --peer <id>` — confirm queued; peer reconnect drains |
| Sender retries forever | `require_ack=true` but receiver never ACKs | check receiver ACKs after handling; inspect `events.jsonl` for `status=ack` |
| Duplicate handler invocations | downstream not respecting idempotency | dedupe on `message_id` in app code; never on `payload` hash |
| `replay` returns nothing | log rotated or trace_id wrong | verify with `tail` first; rotated logs live under `cross_pc_protocol/logs/events.<date>.jsonl` |
| Redis subscribers see envelope twice | both bridge and direct publish active | route Redis-only sends through `redis_bridge.py`, never both |
| LAN peers not discovered | UDP broadcast blocked by Windows Firewall | allow inbound UDP on discovery port; or use static `--peers host:port,...` list |
| Works on LAN but not remote network | NAT/firewall blocks WS/HTTP ports | use VPN/Tailscale or SSH tunnel; verify with `protocol_inspect.py health` over remote base URL |
| Hermes/WSL can send locally but desktop peer misses traffic | wrong host binding or wrong endpoint | start gateway with `--host 0.0.0.0`, then use explicit `--ws-url` and `--http-base` on peers |

## Hard rules

- No placeholder/fake data in production logic. Adapters MUST refuse to send if envelope fails schema validation.
- Never bypass `redis_bridge.py` for Redis backward-compat — duplicates corrupt `bus:alpha_engine_bus:log` ordering.
- Every new transport or topic added MUST land tests in `tests/test_cross_pc_protocol.py` and a line in `docs/cross_pc_protocol_v1.md`.
- Log lines are append-only JSONL — never edit, only rotate.

## When to use this skill

- Any work touching `cross_pc_protocol/`, `tools/protocol_*`, `tools/adapters/`, or `tools/lan_discovery.py`.
- Debugging a missing/duplicate/late message between Cursor / Claude / Freebuff peers.
- Adding a new agent type — wrap it via an adapter, do not invent a parallel transport.
- Investigating Redis bus drift vs cross-PC traffic.
