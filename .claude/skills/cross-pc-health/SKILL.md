---
name: cross-pc-health
description: Quick health check of the local cross-PC protocol gateway — confirms /health, lists registered peers, queue depths, pending ACKs, LAN-discovered peers. Use when the user says "is the gateway up", "/cross-pc-health", "cross-pc status", or you need a pre-flight before sending. Aliases - xpc-health, cross-pc-status.
---

# /cross-pc-health — Cross-PC gateway health

One-shot diagnostic. No state mutation. Safe to run before every send.

## Pre-flight — Core file existence

Before running any commands, verify the core protocol files exist. Missing files mean the protocol tooling isn't installed or you're in the wrong directory.

```bash
MISSING=""
for f in \
  tools/protocol_inspect.py \
  tools/lan_discovery.py; do
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

## Quick path — inspect CLI

```bash
python tools/protocol_inspect.py health
```

## Gateway address (IMPORTANT)

**This desktop's gateway binds on the LAN IP, not loopback.**
Always use `192.168.2.32:8788` as the primary address. `127.0.0.1:8788` only works if the gateway process is running *in this exact shell session* — it is not reliable and will silently fail when the gateway is running as a background service.

| Context | Address to use |
|---------|---------------|
| This desktop (primary) | `http://192.168.2.32:8788` |
| Laptop / other LAN peer reaching this desktop | `http://192.168.2.32:8788` |
| Loopback (only if gateway started in same shell) | `http://127.0.0.1:8788` |

## Raw HTTP probe

```bash
curl.exe -s -m 3 http://192.168.2.32:8788/health | python -c "
import sys, json
d = json.load(sys.stdin)
print('ok           :', d.get('ok'))
print('ts_utc       :', d.get('ts_utc'))
print('ws_port      :', d.get('ws_port'))
print('http_port    :', d.get('http_port'))
print('redis_bridge :', d.get('redis_bridge_available'))
print('pending_acks :', d.get('pending_acks'))
print('offline_queues:', d.get('offline_queues'))
print('peers:')
for k, v in (d.get('peer_registry') or {}).items():
    print(' ', k, '| last_seen', v.get('last_seen_ts_utc'),
          '| transport', v.get('last_transport'),
          '| topic', v.get('last_topic'),
          '| caps', v.get('capabilities') or [])
print('lan_peers    :')
for p in (d.get('lan_peers') or []):
    print(' ', p.get('peer_id'), p.get('ip'), 'port', p.get('gateway_port'))
"
```

PowerShell-safe one-liner (no curl heredoc issues):

```powershell
python tools/protocol_inspect.py health
```

## Interpretation

- `ok=False` or curl fails → first retry with `192.168.2.32:8788` before concluding gateway is down. If both fail, start: `python tools/protocol_gateway.py --host 0.0.0.0 --ws-port 8787 --http-port 8788 --peer-id gateway-a` (see `cross-pc-protocol-debug-first`).
- `pending_acks > 0` → some `require_ack=true` DM still retrying (backoff 1s,2s,4s,8s,16s, cap 60s, until TTL). Check log for the message_id; ACK or let it expire.
- `offline_queues.all > 0` → unread broadcasts; `/cross-pc-checkmsg` drains.
- `offline_queues.<peer> > 0` → DMs queued for an offline peer.
- `redis_bridge=False` → backward-compat mirror to `alpha_engine_bus` is disabled (fine for pure cross-pc/v1 traffic).
- Peer with `last_seen` >5 min stale → not actively connected; DM will queue.

## LAN discovery (when peer missing from registry)

```bash
python tools/lan_discovery.py --broadcast
python tools/lan_discovery.py --listen --timeout 10
```

Windows Firewall can block UDP broadcast — allow inbound on the discovery port or use static `--peers host:port,...`.

## Companion skills

- `/cross-pc-sendmsg` — send / broadcast / DM
- `/cross-pc-checkmsg` — poll inbox + broadcasts + tail log
- `/cross-pc-protocol-debug-first` — full protocol design, gateway lifecycle, ACK retry, replay
