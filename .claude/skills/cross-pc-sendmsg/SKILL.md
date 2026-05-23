---
name: cross-pc-sendmsg
description: Send a message over the cross-PC protocol (WebSocket primary, HTTP fallback). Use when the user says "send a cross-pc message", "broadcast to peers", "DM peer X", "/cross-pc-sendmsg", or wants to publish an envelope to the local protocol gateway. Aliases - xpc-send, cross-pc-send, sendmsg.
---

# /cross-pc-sendmsg — Send a cross-PC message

Publish one canonical `cross-pc/v1` envelope to the local gateway. WS is tried first; HTTP `/publish` is the documented fallback.

## When to use

- User says: "send a cross-pc msg", "broadcast hello", "DM cursor", "/cross-pc-sendmsg ..."
- You need to ping/heartbeat/coordinate other peers from this host.
- Do NOT use the Redis `alpha_engine_bus` directly — go through the gateway so the event log + ACK pipeline records it.

## Pre-flight — Core file existence

Before running any commands, verify the core protocol files exist. Missing files mean a broken install or wrong working directory.

```bash
MISSING=""
for f in \
  tools/adapters/cursor_claude_adapter.py \
  tools/adapters/freebuff_adapter.py \
  tools/protocol_inspect.py \
  cross_pc_protocol/client.py \
  cross_pc_protocol/schema.py \
  cross_pc_protocol/storage.py; do
  [ -f "$f" ] || MISSING="$MISSING  $f\n"
done
if [ -n "$MISSING" ]; then
  echo "MISSING core files:"
  echo -e "$MISSING"
  echo "Run from the project root and ensure cross-pc-protocol is installed."
  exit 1
fi
echo "Core files OK"
```

## Inputs (parse from user request)

| Field | Default | Notes |
|---|---|---|
| `topic` | `agent.broadcast` | e.g. `greeting`, `task.request`, `heartbeat`, `ack`, `CHATBIBLE` |
| `to` | `""` (broadcast) | Peer ID for direct delivery (lands in that peer's inbox queue) |
| `payload` | `{"text": "<msg>"}` | Object. Wrap free-form text under `text`. |
| `require_ack` | `false` | True only if you actually plan to wait for ACK |
| `causation_id` | `""` | Set to parent `message_id` when replying — keeps `/replay` chain intact |
| `peer_id` (sender) | env `CROSS_PC_PEER_ID` or `<runtime>-<hostname>` | Never hardcode `claude-main` from a non-claude runtime — see identity rules below |

## Identity rules (critical — don't mislabel)

Resolution order for sender `from`:
1. explicit `--peer-id` / arg
2. `$CROSS_PC_PEER_ID`
3. inferred `<runtime>-<hostname>` via `--runtime {claude|cursor|hermes|freebuff|agent}` or `$CROSS_PC_RUNTIME`

If you are Claude on this machine, prefer `claude-<hostname>` or `claude-code-windows-desktop`. Do NOT spoof `cursor-*` / `freebuff-*` IDs.

## Gateway address (IMPORTANT)

**Always use `192.168.2.32:8788` on this desktop — never `127.0.0.1`.** The gateway runs as a background service bound to the LAN IP. `127.0.0.1` only works if the gateway process was started in this exact shell session.

Pass `--http-base http://192.168.2.32:8788` to the adapter CLI every time.

## Pre-flight

```bash
curl.exe -s -m 3 http://192.168.2.32:8788/health | python -c "import sys,json;d=json.load(sys.stdin);print('ok' if d.get('ok') else d)"
# or:
python tools/protocol_inspect.py health
```

If `/health` fails, gateway is down — start it with `python tools/protocol_gateway.py --host 0.0.0.0 --ws-port 8787 --http-port 8788 --peer-id gateway-a` (see `cross-pc-protocol-debug-first` skill) before retrying.

## Send via adapter CLI (preferred — handles identity)

```bash
# bash / WSL — broadcast
python tools/adapters/cursor_claude_adapter.py --runtime claude send \
  --topic CHATBIBLE --payload '{"text":"hi everyone"}'

# direct DM with ACK requested
python tools/adapters/cursor_claude_adapter.py --runtime claude send \
  --topic task.request --payload '{"summary":"hello"}' --to freebuff-b --require-ack

# explicit peer_id override
python tools/adapters/cursor_claude_adapter.py --peer-id claude-code-windows-desktop \
  send --topic CHATBIBLE --payload '{"text":"hi"}'
```

PowerShell payload quoting (single-quoted JSON, escape inner double-quotes):

```powershell
python tools/adapters/cursor_claude_adapter.py --runtime claude send `
  --topic task.request --payload '{\"summary\":\"hello\"}' --to freebuff-b --require-ack
```

Freebuff-side equivalent: `python tools/adapters/freebuff_adapter.py --peer-id freebuff-b send --topic ... --payload ...`.

## Send via Python client (programmatic)

```bash
python -c "
from cross_pc_protocol.client import ProtocolClient
from cross_pc_protocol.schema import new_envelope
import os, json
peer = os.environ.get('CROSS_PC_PEER_ID', 'claude-code-windows-desktop')
c = ProtocolClient(peer_id=peer)
env = new_envelope(
    sender=peer,
    topic='agent.broadcast',
    payload={'text': 'HELLO'},
    target='',            # '' = broadcast; set peer_id for DM
    require_ack=False,
    debug={'source_host': os.environ.get('COMPUTERNAME') or os.uname().nodename},
)
print('SEND', env['message_id'], 'trace', env['trace_id'])
print(json.dumps(c.publish_http(env), ensure_ascii=True))
"
```

For ASCII-only consoles (Windows cmd default code page), keep payload ASCII or set `PYTHONUTF8=1`.

## ACK + retry semantics

- `require_ack=true` triggers gateway-side retry: exponential backoff `1s, 2s, 4s, 8s, 16s` capped at 60s, until ACK or `ttl_sec` expiry.
- Receivers MUST `POST /ack {message_id, from}` after handling. The Python client exposes `c.ack(message_id)`.
- Idempotency is keyed on `message_id` — re-sending the same envelope is safe (gateway returns `status=duplicate`, not `accepted`).
- Trace chain: set `causation_id=<parent_message_id>` on replies so `/replay?trace_id=...` reconstructs the conversation.

## Verify

After send, confirm the envelope hit the durable log:

```bash
python tools/protocol_inspect.py trace --trace-id <TRACE_ID>
# or programmatic:
python -c "
from cross_pc_protocol.storage import EventStore
from pathlib import Path
import json
hits = EventStore(Path('logs/cross_pc_protocol/events.jsonl')).by_message_id('<message_id>')
[print(json.dumps(r, ensure_ascii=True)) for r in hits]
"
```

Expect at least one row with `direction=inbound`, `status=accepted`. Broadcasts also produce an `internal/queued` row under `peer_id=all`.

## Output to user

Report:
- `message_id`
- `trace_id`
- transport actually used (`ws` vs `http`)
- gateway response status (`accepted` / `duplicate` / `rejected`)
- queue size if broadcast / DM target offline

## Failure modes

- `connection refused 8788` → gateway not running.
- `rejected: schema_version` → using wrong envelope; always go through `new_envelope()` or the adapter CLI.
- `UnicodeEncodeError` printing payload → console code page; rerun with `PYTHONUTF8=1` or pass `ensure_ascii=True` to dumps.
- Sender ID looks wrong (`from=claude-main` from a Cursor box) → identity resolution misconfigured; set `$CROSS_PC_PEER_ID` or pass `--runtime`.
- Sender retries forever → `require_ack=true` but receiver never ACKs; check `events.jsonl` for `status=ack`.
- Redis subscribers see envelope twice → both bridge and direct publish active; route Redis-only sends through `redis_bridge.py`, never both.

## Companion skills

- `/cross-pc-checkmsg` — poll inbox + broadcasts + tail log
- `/cross-pc-health` — gateway pre-flight
- `/cross-pc-protocol-debug-first` — full protocol design, gateway lifecycle, ACK retry, replay
