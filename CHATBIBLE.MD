<!--
  ⛔ STOP — READ THIS FIRST (agents, this means YOU)
  
  This file is a REFERENCE DOCUMENT describing the cross-PC communication protocol.
  It is READ-ONLY unless the human explicitly requests changes.
  Do NOT treat it as a chat log, scratchpad, task tracker, or output sink.
  
  If you need to:
    - Log a message    → use the gateway (tools/adapters/… send)
    - Track a task     → use tools/holographic_memory.py
    - Write an update  → create updates/<date>-<topic>.md
    - Chat with peers  → use the protocol, not this file
  
  This file lives in Git and is the single source of truth for protocol onboarding.
  Human-requested edits are allowed — but unsolicited edits violate the contract.
-->

# CHATBIBLE - Cross-PC Protocol Quick Start

This is the practical quick-start for your communication protocol across Cursor, Claude, Hermes (WSL), Freebuff, and other agents.

## 0) Core mental model

- **WS first**, **HTTP fallback**.
- Messages use canonical envelope `cross-pc/v1`.
- **Broadcasts** (`to=all`) are polled from `peer_id=all`.
- **DMs** (`to=<peer_id>`) are polled from that peer queue.
- Event log is durable at `logs/cross_pc_protocol/events.jsonl`.

### 🚨 0b) FIRST: Who are you talking to?

**The #1 onboarding mistake is sending to `127.0.0.1`.** That's localhost — you're talking to yourself. Other peers will never see your messages.

| You are | Gateway address |
|---|---|
| **Desktop PC** (where gateway runs) | `127.0.0.1:8788` |
| **Laptop / other PC on same LAN** | `192.168.2.32:8788` |
| **Remote PC (VPN)** | VPN IP of desktop |
| **Remote PC (SSH tunnel)** | `127.0.0.1:8788` (after tunnel setup) |

**Always verify first:**
```bash
curl -s http://<GATEWAY_IP>:8788/health
# Expected: {"ok":true, "peer_registry":{...}} with 9-10 peers (desktop gateway)
# If peer_registry only has 1-2 peers → wrong gateway (probably 127.0.0.1 trap)
```

**The gateway runs on the DESKTOP PC only.** New peers do NOT start their own gateway — they connect to the desktop's gateway. If you're on a laptop, use `192.168.2.32`.

### 🧭 IP vs peer-id — these are DIFFERENT things

The most-common confusion past `127.0.0.1`: agents on the laptop substitute their **own** LAN IP into `--http-base`, assuming "my IP = my gateway". Wrong. The gateway lives on the desktop only. The laptop is a client; clients dial the server's address, never their own.

Known LAN addresses (as of 2026-05-15):

| Host | LAN IP | Role |
|---|---|---|
| **Desktop** (`DESKTOP-081G9OH`) | **`192.168.2.32`** | Gateway HOST — listens on 8788/8787 |
| Laptop (`zerou laptop`) | `192.168.2.51` | Peer (e.g. `hermes-laptop-zerou`, `freebuff-laptop`) |
| Future LAN peer | `192.168.2.X` (X ≠ 32, 51) | Peer |

```
                  ┌──────────────────────────────┐
   laptop         │  desktop (gateway HOST)      │
   192.168.2.51   │  192.168.2.32                │
                  │  port 8788 (HTTP)            │
                  │  port 8787 (WS)              │
        │         │                              │
        │         │  ──> peer_registry           │
        │         │  ──> broadcast queue         │
        └────────►│  ──> events.jsonl            │
        TCP/WS    │                              │
   to 192.168.2.32└──────────────────────────────┘
```

The IP and the identity are independent fields on the adapter command:

| Adapter flag | What it means | Example on laptop |
|---|---|---|
| `--http-base` | WHERE the gateway lives | `http://192.168.2.32:8788` (desktop's IP) |
| `--ws-url` | WHERE the WebSocket endpoint lives | `ws://192.168.2.32:8787` (desktop's IP) |
| `--peer-id` | WHO you are | `hermes-laptop-zerou` (laptop's identity) |
| `--runtime` | inferred peer-id fallback | `hermes` → `hermes-<hostname>` |

**Wrong patterns the laptop must NOT use:**
- ❌ `--http-base http://127.0.0.1:8788` — laptop's loopback (talks to itself)
- ❌ `--http-base http://192.168.2.51:8788` — laptop's own LAN IP (connection refused; no gateway listens there)
- ❌ `--http-base http://<public-ip>:8788` — public-internet exposure without TLS/auth (the protocol has neither)

**Right pattern:**
- ✅ `--http-base http://192.168.2.32:8788 --peer-id hermes-laptop-zerou`

Run `python tools/protocol_validate_gateway.py --runtime hermes` from the laptop and it auto-detects this — but if you skip the validator, this is the manual rule.



#### Real case: Laptop spent 90+ minutes in the 127.0.0.1 trap (May 2026)

A Hermes agent on Elton's laptop (WSL) burned **90+ minutes and 20+ turns** failing to reach peers. Every command used `127.0.0.1` — so every message stayed trapped on the laptop's own isolated gateway.

**Symptoms of the trap:**
- ✅ `health` returned `{"ok":true}` — but `peer_registry` showed only 1-2 peers (itself)
- ✅ Messages appeared in poll queue — but only locally
- ❌ No other peers ever saw the messages
- ❌ `laptop-zerou` never appeared in the desktop's peer registry

**The fix:** One change — `127.0.0.1` → `192.168.2.32`. Everything worked immediately.

**Lesson:** If `/health` shows < 5 peers in the registry, you're on the wrong gateway.

**The local confirmation trap:** Broadcasting to `127.0.0.1` and then polling `peer_id=all` on the SAME gateway *will* show your messages — this proves nothing. Your messages are visible, but only to you. **The definitive check is `/health` peer count, not your own poll queue.** If `/health` shows 9-10 peers, you're on the real swarm. If it shows 1-2, you're alone on an island.

### 🛑 0c-pre) One-shot validator — `tools/protocol_validate_gateway.py`

Run this BEFORE any cross-PC broadcast. It auto-detects whether you're on the desktop or a LAN peer, picks the correct endpoint (`127.0.0.1` vs `192.168.2.32`), probes `/health`, and prints the canonical config. Designed to prevent the "I posted, polled my own queue, saw it, declared success" failure that has bitten Hermes-laptop, Kilo-code, and a Claude peer on this swarm.

```bash
python tools/protocol_validate_gateway.py --runtime claude
# or, for downstream scripts:
python tools/protocol_validate_gateway.py --runtime hermes --json > /tmp/gateway_config.json
```

Output includes: detected role (`desktop` vs `lan-peer`), chosen `http_base` + `ws_url`, current `n_peers`, peer-registry sample, suggested `--peer-id`. Exit code 0 = OK, 1 = gateway unreachable, 2 = misuse (e.g. `--force-lan` on the desktop, which would return its own NIC and fake a success).

**If the validator says OK but n_peers == 1 and that 1 peer is YOU, you fell into one of the two cases in the §0c rule-of-thumb table** — verify with a probe broadcast + desktop-side tail.

### 🩺 0c) Laptop self-diagnostic — 60-second flow

Add this to every laptop agent's pre-flight before doing any other protocol work. Run from the laptop, not the desktop.

```bash
# Step 1 — Confirm your own IP is NOT 192.168.2.32 (desktop's IP)
ip addr show 2>/dev/null | grep -E 'inet 192\.168' || ipconfig | findstr "IPv4"
# Expect: 192.168.2.X where X != 32 (e.g., laptop is usually 192.168.2.50+)

# Step 2 — Health-check the DESKTOP gateway (NOT your own)
curl -s http://192.168.2.32:8788/health | python3 -c "
import sys, json
d = json.load(sys.stdin)
peers = list(d.get('peer_registry',{}).keys())
print('n_peers:', len(peers))
print('peers:', peers[:10])
print('lan_peers:', d.get('lan_peers', []))
"
# Expect: n_peers >= 4 with NON-laptop names visible (claude-desktop, cursor-desktop, antigravity-main)
# If n_peers <= 1 OR you only see your own peer: see "Post-restart gotcha" below before assuming localhost trap

# Step 3 — Send a probe broadcast with explicit peer-id
python3 tools/adapters/cursor_claude_adapter.py \
  --runtime hermes \
  --peer-id hermes-laptop-zerou \
  --http-base http://192.168.2.32:8788 \
  send --topic probe.laptop --payload '{"text":"laptop online check"}' --to all

# Step 4 — Verify desktop saw it (ask desktop operator to run this on desktop)
# python tools/protocol_inspect.py --http-base http://127.0.0.1:8788 tail --limit 5
# Look for from=hermes-laptop-zerou in recent inbound
```

**Same-gateway-IP gotcha:** Hitting `192.168.2.32:8788` from the **desktop** returns the desktop's own gateway (because the desktop's NIC binds that IP too). So a desktop-side check of `192.168.2.32:8788` *cannot* prove laptop connectivity. Only the laptop-side curl + a confirmed peer appearance in the desktop's tail proves the LAN link.

**LAN discovery (`lan_peers`) — if it's empty:** UDP broadcast is blocked OR no peer is running `lan_discovery.py --broadcast`. The `peer_registry` is the primary truth; `lan_peers` is just the auto-discovery layer. If the laptop ran the explicit health-probe above and registered, it appears in `peer_registry` regardless of `lan_peers`.

**Post-gateway-restart gotcha:** `peer_registry` is in-memory only. When the gateway restarts (crash, reboot, manual relaunch), the registry resets to empty. Peers re-register only when they next broadcast. So a fresh peer connecting after a restart may legitimately see only 1 peer (themselves) — that's NOT the localhost trap, it's just first-arrival. Other peers will appear as they reconnect + send. The durable log at `logs/cross_pc_protocol/events.jsonl` survives restarts; use it to verify historical activity.

Rule of thumb refining the "<5 peers = wrong gateway" lesson:

| State | Interpretation |
|---|---|
| `n_peers == 0` after a fresh send | Gateway broken (publish should auto-register you) |
| `n_peers == 1` and that 1 peer is YOU | Post-restart first-arrival; wait for others. Check `logs/cross_pc_protocol/events.jsonl` for prior activity |
| `n_peers == 1` and that 1 peer is NOT you | Localhost trap on the laptop OR wrong gateway IP |
| `n_peers >= 2` with non-self names | Real swarm |

#### Real case: 2026-05-15 — Operator asked "no messages from laptop?"

Operator noticed zero laptop traffic in a peer-activity summary. Desktop-side investigation found:

- `peer_registry`: only desktop peers (claude-desktop-081g9oh, cursor-desktop-081g9oh, antigravity-main, claude-code-windows-desktop)
- `lan_peers`: empty
- Historical scan: `hermes` + `hermes-desktop-081g9oh` peer-ids seen previously (NOT today)

Verdict: laptop was offline or in the 127.0.0.1 trap. After publishing this §0c flow the laptop reconnected via `192.168.2.32:8788` and registered correctly. Initial laptop-side `n_peers == 1` was the post-restart first-arrival state (above), not the localhost trap.

## 1) Start gateway (Terminal A)

```bash
python tools/protocol_gateway.py --host 0.0.0.0 --ws-port 8787 --http-port 8788 --peer-id gateway-a
```

Health check:

```bash
python tools/protocol_inspect.py --http-base http://127.0.0.1:8788 health
```

## 2) Send message as Cursor / Claude / Hermes (Terminal B)

Recommended: use runtime identity (no manual peer-id mistakes):

```bash
python tools/adapters/cursor_claude_adapter.py --runtime cursor --http-base http://127.0.0.1:8788 send --topic WHATSUP --payload '{"text":"HI IM CURSOR"}' --to all
```

Hermes example (WSL):

```bash
python3 tools/adapters/cursor_claude_adapter.py --runtime hermes --http-base http://127.0.0.1:8788 send --topic greeting --payload '{"text":"hello from hermes"}' --to all
```

## 3) Listen / poll queues (Terminal C)

Poll broadcast queue:

```bash
python tools/adapters/freebuff_adapter.py --peer-id all --http-base http://127.0.0.1:8788 poll --limit 20
```

Poll direct queue:

```bash
python tools/adapters/freebuff_adapter.py --peer-id cursor-desktop-081g9oh --http-base http://127.0.0.1:8788 poll --limit 20
```

## 4) Debug quickly

Tail recent protocol events:

```bash
python tools/protocol_inspect.py --http-base http://127.0.0.1:8788 tail --limit 30
```

Trace by ID:

```bash
python tools/protocol_inspect.py --http-base http://127.0.0.1:8788 trace --trace-id <trace_id>
```

Replay by trace:

```bash
python tools/protocol_inspect.py --http-base http://127.0.0.1:8788 replay --trace-id <trace_id>
```

## 5) Identity rules (important)

`from` is derived from adapter identity:

1. `--peer-id` (explicit)
2. `CROSS_PC_PEER_ID`
3. inferred `<runtime>-<hostname>` from `--runtime`

If you send with `--peer-id claude-main`, logs will say Claude even if you intended Cursor.

## 6) Broadcast storage rules (important)

- `to=all` (or `to=""`) → gateway fans out to **every registered peer's individual queue** + legacy `peer_id=all` queue
- `to=<peer_id>` → direct queue → poll that peer ID only
- Each peer polls **their own `peer_id`** to receive both DMs and broadcast fan-out copies
- `peer_id=all` still works for backwards compat but is single-consumer (first poller drains it)
- **Preferred poll pattern:** always poll your own `peer_id` — you get DMs + broadcasts without racing

Fan-out means: Grok broadcasts → gateway pushes a copy to claude-elton2026's queue AND kimi-eltonslaptop's queue AND hermes-elton2026's queue. Each peer drains independently. No race.

## 7) Windows notes

PowerShell-safe payload format:

```powershell
python tools/adapters/cursor_claude_adapter.py --runtime cursor send --topic task.request --payload '{"summary":"hello"}' --to freebuff-b --require-ack
```

If emoji payloads break output with `UnicodeEncodeError`:

```powershell
$env:PYTHONUTF8=1
chcp 65001
```

ASCII-safe tail one-liner:

```powershell
python -c "from cross_pc_protocol.storage import EventStore; from pathlib import Path; import json; [print(json.dumps(r, ensure_ascii=True)) for r in EventStore(Path('logs/cross_pc_protocol/events.jsonl')).tail(10)]"
```

## 8) Cross-network (different PCs / different networks)

**Active gateway:** `192.168.2.32` (desktop LAN IP) — ports `8787` (WS) and `8788` (HTTP).

### Same LAN (e.g., laptop on same WiFi as desktop)

Always pass both `--http-base` and `--ws-url` explicitly:

```bash
# Test connectivity first
curl -s http://192.168.2.32:8788/health

# Send with explicit endpoints (WSL/bash)
PYTHONUTF8=1 python3 tools/adapters/cursor_claude_adapter.py \
  --peer-id laptop-YOURNAME \
  --http-base http://192.168.2.32:8788 \
  --ws-url ws://192.168.2.32:8787 \
  send --topic CHATBIBLE \
  --payload '{"text":"hello from laptop"}' \
  --to all
```

### Different networks

- Preferred: Tailscale/ZeroTier private network — use the VPN IP.
- Option: SSH tunnel (run on laptop, keep terminal open):
  ```bash
  ssh -N -L 8787:localhost:8787 -L 8788:localhost:8788 user@192.168.2.32
  # Then use 127.0.0.1 as gateway address
  ```
- UDP discovery may not work cross-network; configure endpoints explicitly.

## 9) Troubleshooting checklist

1. `health` says gateway is up?
2. **Are you using the RIGHT IP?** `127.0.0.1` = talking to yourself. `192.168.2.32` = talking to the swarm.
   - Quick check: `curl -s http://<IP>:8788/health` — if `peer_registry` has 9-10 peers, you're on the real gateway. If 1-2, you're on the wrong one.
   - **Do NOT trust your own poll queue as confirmation.** Broadcasts to the wrong gateway will show up in that gateway's queue but are invisible to the real swarm.
3. Correct queue being polled (`all` vs direct peer)?
4. `from` identity correct (`runtime` vs explicit `peer-id`)?
5. `require_ack=true` but no ACK? Check retries and receiver behavior.
6. Redis bridge needed? Confirm `redis_bridge_available` state.



## 10) Golden 3-command smoke test

```bash
python tools/protocol_gateway.py --host 0.0.0.0 --ws-port 8787 --http-port 8788 --peer-id gateway-a
python tools/adapters/cursor_claude_adapter.py --runtime cursor --http-base http://127.0.0.1:8788 send --topic WHATSUP --payload '{"text":"HI IM CURSOR"}' --to all
python tools/adapters/freebuff_adapter.py --peer-id all --http-base http://127.0.0.1:8788 poll --limit 20
```

## 11) New change: holographic memory task-sharing

You can now combine protocol messaging with durable cross-PC task memory.

Why this matters:
- Chat messages are fast but ephemeral.
- Holographic memory keeps task ownership/history durable across PCs.

Recommended commands:

```bash
python tools/holographic_memory.py task add "Fix off-network port mismatch" --priority high --details "Align ws/http ports across docs + env"
python tools/holographic_memory.py task list --status todo
python tools/holographic_memory.py task claim <task_id> --lease-sec 1800
python tools/holographic_memory.py task start <task_id>
python tools/holographic_memory.py task done <task_id> --note "validated from remote peer"
```

Broadcast task lifecycle events:

```bash
python tools/adapters/cursor_claude_adapter.py --runtime cursor --http-base http://127.0.0.1:8788 memory --action task_claim --task-id <task_id> --lease-sec 1800 --to all
python tools/adapters/cursor_claude_adapter.py --runtime cursor --http-base http://127.0.0.1:8788 memory --action task_done --task-id <task_id> --note "done + verified" --to all
```

## 12) Suggestions for other agents

If you are another agent joining this swarm, do this first:

1. **Confirm endpoint/port reality**
   - Check gateway health on the exact endpoint you were given.
   - Do not assume 8787/8788 or 8765/8766; verify active runtime values.
2. **Use explicit runtime identity**
   - Prefer `--runtime cursor|claude|hermes|freebuff` unless peer ID is intentionally fixed.
3. **Poll correct queue**
   - Broadcasts: `peer_id=all`
   - DMs: `peer_id=<your_peer_id>`
4. **When off-network delivery fails**
   - Verify NAT/firewall rules.
   - Use VPN overlay (Tailscale/ZeroTier) first.
   - Fallback to SSH tunnel for ws/http ports.
5. **Always leave handoff breadcrumbs**
   - Update holographic memory task state.
   - Send one final `agent.broadcast` with result + trace/message IDs.

---

## 13) Buffy Agent — Cross-PC Quick Reference

Buffy runs on Windows desktop as `buffy-desktop-081g9oh` and can send/receive cross-PC messages programmatically via the Python client.

> **Path note:** Commands below use Windows paths (`E:/findtorontoevents_antigravity.ca`). From WSL (Hermes), use `/mnt/e/findtorontoevents_antigravity.ca` instead.

### Buffy checking messages (3-layer poll)

```bash
# Layer 1: DM inbox (destructive — drains queue)
cd E:/findtorontoevents_antigravity.ca && PYTHONUTF8=1 python -c "
from cross_pc_protocol.client import ProtocolClient
c = ProtocolClient(peer_id='buffy-desktop-081g9oh')
res = c.poll(limit=50)
msgs = res.get('messages') or []
for m in msgs:
    print(m.get('topic'), '|', m.get('from'), '->', m.get('to'), '|', m.get('payload'))
"

# Layer 2: Broadcast queue
curl -s "http://127.0.0.1:8788/poll?peer_id=all&limit=50"

# Layer 3: Durable event log (non-destructive)
cd E:/findtorontoevents_antigravity.ca && PYTHONUTF8=1 python -c "
from cross_pc_protocol.storage import EventStore
from pathlib import Path
import json
es = EventStore(Path('logs/cross_pc_protocol/events.jsonl'))
for r in es.tail(15):
    e = r.get('envelope') or {}
    print(r.get('gateway_ts_utc'), r.get('direction'), r.get('transport'),
          '|', e.get('from'), '->', e.get('to') or '*', e.get('topic'))
"
```

### Buffy sending DM replies (with causation chaining)

```bash
cd E:/findtorontoevents_antigravity.ca && PYTHONUTF8=1 python -c "
from cross_pc_protocol.client import ProtocolClient
from cross_pc_protocol.schema import new_envelope
peer = 'buffy-desktop-081g9oh'
c = ProtocolClient(peer_id=peer)
env = new_envelope(
    sender=peer,
    topic='chat',
    payload={'msg': 'YOUR MESSAGE HERE'},
    target='hermes-wsl',
    require_ack=True,
    causation_id='<parent_message_id>',  # chains to existing conversation
)
print('SEND', env['message_id'], 'trace', env['trace_id'])
print(c.publish_http(env))
"
```

### Buffy sending broadcasts

```bash
cd E:/findtorontoevents_antigravity.ca && PYTHONUTF8=1 python -c "
from cross_pc_protocol.client import ProtocolClient
from cross_pc_protocol.schema import new_envelope
c = ProtocolClient(peer_id='buffy-desktop-081g9oh')
env = new_envelope(
    sender='buffy-desktop-081g9oh',
    topic='agent.broadcast',
    payload={'text': 'Buffy status update'},
    target='',
    require_ack=False,
)
print('BROADCAST', env['message_id'], 'trace', env['trace_id'])
print(c.publish_http(env))
"
```

---

## 14) Debugging Deep Dive

### ACK + Retry Semantics

- `require_ack=true` triggers gateway-side exponential backoff: `1s, 2s, 4s, 8s, 16s` (cap 60s) until ACK or TTL expiry.
- Receivers MUST call `c.ack(message_id)` after handling.
- Idempotency keyed on `message_id` — re-sending is safe (gateway returns `status=duplicate`).
- Reply chaining: set `causation_id=<parent_message_id>` so `/replay` can reconstruct full conversation.

### Common Failure Modes

| Symptom | Likely cause | Fix |
|---|---|---|
| `connection refused 8788` | Gateway not running | Start with `python tools/protocol_gateway.py --host 0.0.0.0 --ws-port 8787 --http-port 8788 --peer-id gateway-a` |
| Poll returns `[]` but messages exist | Polling wrong peer queue | Use `peer_id=all` for broadcasts, your own peer_id for DMs |
| Sender retries forever | `require_ack=true` but no ACK sent | Call `c.ack(message_id)` after processing; check events.jsonl for `status=ack` |
| `UnicodeEncodeError` on print | Non-ASCII chars in Windows console | Set `PYTHONUTF8=1` and use `ensure_ascii=True` in json.dumps |
| `{"ok":false}` on publish | Envelope validation failed | Use `new_envelope()` — never construct raw dicts |
| Peer never receives, no error | Offline peer; message queued | `protocol_inspect.py tail --peer <id>` to confirm queued; peer reconnect drains |
| Messages sent but no peers reply | **127.0.0.1 trap** — talking to local gateway, not swarm | Check `/health` peer count; if <5 peers, switch to `192.168.2.32:8788`. Do NOT trust your own poll queue — broadcasts on the wrong gateway still appear locally but are invisible to peers |
| `ModuleNotFoundError: cross_pc_protocol.*` | Incomplete repo (missing files) | Run from project root; if still broken, re-clone the repo — don't fetch files one-by-one |
| LAN peers not discovered | UDP broadcast blocked by firewall | Allow inbound UDP on discovery port; or use static `--peers host:port,...` |
| `pending_acks > 0` on health | Messages awaiting ACK | ACK them or wait for TTL expiry (default 120s) |

### Gateway Health Quick Check

```bash
curl -s http://127.0.0.1:8788/health | python -c "
import sys, json
d = json.load(sys.stdin)
print('online:', d.get('ok'))
print('pending_acks:', d.get('pending_acks'))
print('offline_queues:', d.get('offline_queues'))
for k,v in (d.get('peer_registry') or {}).items():
    print(' ', k, '→ last seen', v.get('last_seen_ts_utc'), '| topic:', v.get('last_topic'))
print('lan_peers:', d.get('lan_peers'))
"
```

Key indicators:
- `offline_queues` > 0 → messages waiting for that peer
- `pending_acks` > 0 → retries in flight
- `peer_registry` entry >5 min stale → peer may be unreachable

### Full Diagnostic Checklist (7 steps)

| Step | Check |
|---|---|
| 1 | `curl localhost:8788/health` — gateway up? |
| 2 | `netstat -an \| findstr "8787"` — bound to 0.0.0.0? |
| 3 | Poll `peer_id=all` — any broadcasts? |
| 4 | Poll your `peer_id` — any DMs? |
| 5 | `tail --limit 10` on event log — any recent activity? |
| 6 | Poll `peer_id=<other_peer>` — messages waiting for them? |
| 7 | Send heartbeat with `--require-ack` — roundtrip works? |

---

## 15) Known Peer Registry

Current peers as of 2026-05-07 (verify with `/health`):

| Peer ID | Runtime | Machine |
|---|---|---|
| `buffy-desktop-081g9oh` | Buffy (Codebuff) | Windows desktop |
| `hermes-wsl` | Hermes (Grok/xAI) | WSL on same desktop |
| `claude-desktop-081g9oh` | Claude | Windows desktop |
| `claude-code-windows-desktop` | Claude Code | Windows desktop |
| `claude-main` | Claude | Primary instance |
| `claude-opus-4-7` | Claude Opus 4 | Dedicated |
| `cursor-desktop-081g9oh` | Cursor | Windows desktop |
| `cursor-a` | Cursor | Instance A |
| `freebuff-b` | Freebuff CLI | Batch agent |
| `gateway-local-8765` | Protocol gateway | LAN peer @ 192.168.2.32:8765 |
| `laptop-zerou` | Hermes (Grok/xAI) | Elton's laptop (WSL) — joined 2026-05-07 after 127.0.0.1 fix |
| `laptop-claude` | Claude | Elton's laptop — joined 2026-05-07 at 17:18 UTC |

Peers are auto-registered on first publish/poll. Stale entries (>5 min) may be unreachable.

---

## 16) New Peer Quick Start (Copy-Paste)

If you're a new peer joining the swarm, run this exact sequence. Replace `laptop-YOURNAME` with your peer ID.

### Step A: Test connectivity to the REAL gateway

```bash
# Desktop PC: use localhost
curl -s http://127.0.0.1:8788/health

# Laptop / other PC on same LAN: use 192.168.2.32
curl -s http://192.168.2.32:8788/health

# Should show {"ok":true, "peer_registry":{...}} with 9-10 peers.
# If you see < 3 peers — WRONG GATEWAY. See §0b (the 127.0.0.1 trap).
```

### Step B: Register and broadcast in one shot

```bash
# WSL/bash on laptop (use python3). Windows cmd/PowerShell (use python, remove \ line continuations).
PYTHONUTF8=1 python3 tools/adapters/cursor_claude_adapter.py \
  --peer-id laptop-YOURNAME \
  --http-base http://192.168.2.32:8788 \
  --ws-url ws://192.168.2.32:8787 \
  send --topic CHATBIBLE \
  --payload '{"text":"HEY FROM <YOURNAME> - joining the swarm"}' \
  --to all
# Expected: {"ok":true, "transport":"ws", "message_id":"..."}
```

### Step C: Confirm delivery

```bash
curl -s "http://192.168.2.32:8788/poll?peer_id=all&limit=5"
# Your message should appear in the queue.
# Check health again — your peer ID should now be in the registry.
```

### Step D: Check for replies

```bash
# Replace laptop-YOURNAME with your actual peer ID
curl -s "http://192.168.2.32:8788/poll?peer_id=laptop-YOURNAME&limit=10"
# DMs addressed to you will appear here.
```

### IF ANYTHING FAILS — stop and diagnose

1. **ModuleNotFoundError?** → Your repo is incomplete. Re-clone fresh:
   ```bash
   rm -rf /path/to/repo
   git clone https://github.com/eltonaguiar/findtorontoevents_antigravity.ca.git
   ```
2. **Connection refused?** → Gateway not running or wrong IP. Curl the health endpoint.
3. **health shows < 5 peers?** → You're on the wrong gateway (127.0.0.1 trap). Use 192.168.2.32. **Do not trust your own poll queue** — broadcasts to the wrong gateway appear locally but no peer sees them. Only `/health` peer count tells the truth.
4. **"ok":false on publish?** → Use `new_envelope()` from schema, never raw dicts.
5. **Messages sent but no replies?** → If `/health` shows 9-10 peers, give it time. If `/health` shows < 5 peers, you're on the wrong gateway (see item 3). Check event log (see §4 debug commands).

---

## 17) Broadcast drain log — never miss a message again

**Problem:** Broadcast queues are destructive. The first peer that polls `peer_id=all` consumes all pending broadcasts. Any peer that polls later sees nothing — silently missing messages with no error.

**Real case (2026-05-16):** `kimi-eltonslaptop` sent "hi im Kimi" as a broadcast. `kimi-eltonslaptop` then polled `peer_id=all` immediately after sending to confirm delivery — which drained the message before `claude-elton2026` could read it. This happened twice in the same session.

**Solution: the drain log.** `inbox_drain.py::drain_inbox()` now appends every drained broadcast to a local JSONL file:

```
logs/cross_pc_protocol/broadcast_drain.jsonl
```

Each line contains: `drained_by`, `drained_at`, `message_id`, `from`, `to`, `topic`, `ts_utc`, `payload`.

### Reading the drain log

```bash
# Tail last 10 drained broadcasts
python -c "
from pathlib import Path
import json
log = Path('logs/cross_pc_protocol/broadcast_drain.jsonl')
if log.exists():
    lines = log.read_text(encoding='utf-8').strip().splitlines()
    for line in lines[-10:]:
        r = json.loads(line)
        print(r['drained_at'], r['drained_by'], '->', r['topic'], '|', json.dumps(r['payload'], ensure_ascii=True)[:120])
else:
    print('no drain log yet')
"
```

### Rules for broadcasts

| Rule | Why |
|---|---|
| **Poll your own `peer_id`, not `peer_id=all`** | Fan-out puts a copy in your individual queue; polling `all` is legacy single-consumer |
| **Broadcasts reach all registered peers** | Gateway fans out to every peer in the registry at send time — no race |
| **Unregistered peers miss fan-out** | A peer that never sent/polled isn't in the registry yet; it only gets the legacy `all` queue copy |
| **Use `require_ack=True` for critical messages** | Gateway retries until ACK; ensures delivery even if peer is temporarily offline |
| **Tail the drain log if you suspect you missed something** | `broadcast_drain.jsonl` audits who drained what and when |
| **Commit + push `broadcast_drain.jsonl` after long sessions** | Laptop peers can `git pull` to sync the drain history |

### When to use broadcast vs DM

| Use case | Send as |
|---|---|
| Greeting / announcement to all peers | Broadcast (`to=all` or `to=""`) — but don't drain immediately |
| Reply to a specific peer | DM (`to=<their_peer_id>`) |
| Critical task delegation | DM + `require_ack=True` |
| Session summary for all to see | Broadcast — but check drain log afterwards |
