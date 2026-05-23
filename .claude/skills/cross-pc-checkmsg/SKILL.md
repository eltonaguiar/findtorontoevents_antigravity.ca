---
name: cross-pc-checkmsg
description: Check messages on the cross-PC protocol gateway — poll your peer inbox, drain the broadcast queue (peer_id=all), and tail the durable JSONL event log. Use when the user says "check cross-pc msgs", "any peer messages", "/cross-pc-checkmsg", "what's in the bus", or wants to inspect inbound traffic. Aliases - xpc-check, cross-pc-poll, checkmsg.
---

# /cross-pc-checkmsg — Check cross-PC messages

Inspect three storage layers in this order:

1. **Per-peer offline queue** — DM-style messages addressed to `to=<peer_id>`. Drained via `GET /poll?peer_id=<id>`.
2. **Broadcast queue** — messages with `to=""` or `to="all"`. Drained via `GET /poll?peer_id=all`.
3. **Durable event log** — `logs/cross_pc_protocol/events.jsonl` (append-only). Survives gateway restart; the queues above do not.

Common gotcha: polling only `peer_id=<self>` misses broadcasts. Always check `all` too.

## When to use

- User says: "any peer messages?", "check cross-pc inbox", "/cross-pc-checkmsg", "what hit the bus", "tail the protocol log".
- Before starting work, to see if a peer dispatched something to you.

## Pre-flight — Core file existence

Before running any commands, verify the core protocol files exist. Missing files mean a broken install or wrong working directory.

```bash
MISSING=""
for f in \
  tools/adapters/cursor_claude_adapter.py \
  tools/protocol_inspect.py \
  cross_pc_protocol/client.py \
  cross_pc_protocol/storage.py \
  logs/cross_pc_protocol/events.jsonl; do
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

The `logs/cross_pc_protocol/events.jsonl` file may not exist on a fresh install — that's fine, the gateway creates it on first run. All others MUST exist.

## Identity

Pick your peer_id the same way `/cross-pc-sendmsg` does:
1. explicit arg, 2. `$CROSS_PC_PEER_ID`, 3. inferred `<runtime>-<hostname>`.

## Quick path — adapter + inspect CLIs

```bash
# my DM inbox (drains)
python tools/adapters/cursor_claude_adapter.py --runtime claude poll --limit 50

# tail event log live
python tools/protocol_inspect.py tail --follow

# filter by peer or topic
python tools/protocol_inspect.py tail --peer freebuff-b --topic CHATBIBLE

# trace replay
python tools/protocol_inspect.py trace --trace-id <TRACE>

# health
python tools/protocol_inspect.py health
```

For deeper diagnostics (broadcast queue, registry table, raw payloads), use the steps below.

## Gateway address (IMPORTANT)

**Always use `192.168.2.32:8788` on this desktop — not `127.0.0.1`.** The gateway runs bound to the LAN IP; loopback only works if the gateway was started in this exact shell.

## Step 1 — Gateway health + registered peers

```bash
curl.exe -s -m 3 http://192.168.2.32:8788/health | python -c "
import sys, json
d = json.load(sys.stdin)
print('ok:', d.get('ok'), 'pending_acks:', d.get('pending_acks'))
print('offline_queues:', d.get('offline_queues'))
print('peers:')
for k, v in (d.get('peer_registry') or {}).items():
    print(' ', k, v.get('last_seen_ts_utc'), v.get('last_topic'))
print('lan_peers:', d.get('lan_peers'))
"
```

`offline_queues` is a `{peer_id: depth}` dict. `all` = pending broadcasts. Anything else = pending DMs for that peer.

## Step 2 — Drain your DM inbox

```bash
python -c "
import os, json
from cross_pc_protocol.client import ProtocolClient
peer = os.environ.get('CROSS_PC_PEER_ID', 'claude-code-windows-desktop')
c = ProtocolClient(peer_id=peer)
res = c.poll(limit=50)
msgs = res.get('messages') or res.get('envelopes') or []
print(peer, 'count:', len(msgs))
for m in msgs:
    print(' ', m.get('topic'), 'from', m.get('from'), 'mid', m.get('message_id'))
    print('   payload:', json.dumps(m.get('payload'), ensure_ascii=True)[:240])
    if m.get('require_ack'):
        try: c.ack(m.get('message_id'))
        except Exception as e: print('   ack-err:', e)
"
```

Polling is **destructive** — messages pop out of the queue. Re-running shows 0. The durable log (step 4) keeps a copy.

## Step 3 — Drain the broadcast queue

```bash
curl.exe -s "http://192.168.2.32:8788/poll?peer_id=all&limit=50" | python -c "
import sys, json
d = json.load(sys.stdin)
msgs = d.get('messages') or []
print('broadcasts:', len(msgs))
for m in msgs:
    print(' ', m.get('ts_utc'), m.get('from'), '->', m.get('to') or '*', m.get('topic'))
    print('   payload:', json.dumps(m.get('payload'), ensure_ascii=True)[:240])
"
```

Anyone running `/cross-pc-checkmsg` will drain these. If you want to peek without draining, use Step 4 instead.

## Step 4 — Tail durable event log (non-destructive)

```bash
python -c "
from cross_pc_protocol.storage import EventStore
from pathlib import Path
es = EventStore(Path('logs/cross_pc_protocol/events.jsonl'))
for r in es.tail(20):
    e = r.get('envelope') or {}
    print(r.get('gateway_ts_utc'), r.get('direction'), r.get('transport'), r.get('status'),
          '|', e.get('from'), '->', e.get('to') or '*', e.get('topic'),
          'mid', e.get('message_id'))
"
```

Always wrap with `ensure_ascii=True` when re-printing payloads — Windows console blows up on emoji otherwise. Or set `PYTHONUTF8=1`.

## Step 5 — Replay one trace

When a peer references a `trace_id`, fetch the full conversation:

```bash
curl.exe -s "http://192.168.2.32:8788/replay?trace_id=<TRACE_ID>" | python -m json.tool
# or via inspect CLI:
python tools/protocol_inspect.py trace --trace-id <TRACE_ID>
# or programmatic:
python -c "
from cross_pc_protocol.storage import EventStore
from pathlib import Path
import json, sys
es = EventStore(Path('logs/cross_pc_protocol/events.jsonl'))
[print(json.dumps(r, ensure_ascii=True)) for r in es.by_trace_id(sys.argv[1])]
" <TRACE_ID>
```

## LAN discovery

If a peer isn't in `/health` `peer_registry`, check LAN broadcast:

```bash
python tools/lan_discovery.py --broadcast      # announce + listen
python tools/lan_discovery.py --listen --timeout 10
```

UDP-broadcast may be blocked by Windows Firewall — allow inbound on the discovery port, or fall back to a static `--peers host:port,...` list.

## Output to user

Summarize as a short table:
- DMs to me: `<count>` (per-topic breakdown if >1)
- Broadcasts pending: `<count>`
- Last 5 events from log (ts, from→to, topic)
- Peers registered + last_seen drift (stale = >5 min)
- `pending_acks` — non-zero means retries in flight

If nothing: explicit "no inbound on any layer" — don't claim activity that isn't there.

## Failure modes

- `connection refused 8788` → gateway down. Don't fabricate "no messages" — say gateway is offline.
- `UnicodeEncodeError` on print → use `ensure_ascii=True` or set `PYTHONUTF8=1`.
- Drained broadcasts surprise another peer → coordinate via `pending_acks` and the durable log; do not blind-drain `peer_id=all` if multiple consumers exist.
- Stale `peer_registry` entry — registration but no recent traffic; don't assume that peer will receive your DM (it'll just queue).
- `replay` returns nothing → log rotated or trace_id wrong; verify with `tail` first.

## Companion skills

- `/cross-pc-sendmsg` — send / broadcast / DM
- `/cross-pc-health` — gateway pre-flight
- `/cross-pc-protocol-debug-first` — full protocol, ACK retry semantics, gateway lifecycle, Redis bridge
