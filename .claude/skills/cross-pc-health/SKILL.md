---
name: cross-pc-health
description: Quick health check of the local cross-PC protocol gateway — confirms /health, lists registered peers, queue depths, pending ACKs, LAN-discovered peers. Use when the user says "is the gateway up", "/cross-pc-health", "cross-pc status", or you need a pre-flight before sending. Aliases - xpc-health, cross-pc-status.
---

# /cross-pc-health — Cross-PC gateway health

One-shot diagnostic. No state mutation. Safe to run before every send.

## ⛔ ANTI-PATTERNS — read first (these caused every false "gateway down" in CHATBIBLE_FAILURE.MD)

1. **NEVER use `curl.exe` on Linux/macOS.** `curl.exe` is a Windows-only binary. On any non-Windows host (incl. WSL and Remote-SSH peers like `gx10-c9b9`) it does not exist → silent empty output → you will wrongly conclude "gateway down." Use the portable probe below (`python tools/protocol_inspect.py health`), or plain `curl` (no `.exe`) only on Linux/macOS.
2. **NEVER judge a REMOTE gateway with a LOCAL listener check.** `ss -tlnp | grep 8788`, `netstat | findstr 8788`, `Get-NetTCPConnection -LocalPort 8788` all check **the host you are running on**. If the gateway lives on another machine (or you are SSH'd into a peer), a local "no listener" result is meaningless — it does NOT mean the gateway is down. Probe the gateway's **HTTP endpoint** instead.
3. **Know which host you are on before diagnosing.** Run `uname -s 2>/dev/null || echo Windows` and `hostname`. If you are on a peer (gx10, a laptop, WSL), the gateway is the *desktop* — you must reach it over the LAN, not via loopback or local ports.
4. **A failed probe is NOT proof the gateway is down.** Before logging a failure or restarting: confirm you used a tool that exists on your OS, that you hit the gateway's HTTP endpoint (not a local port scan), and that your host can route to the gateway IP. Restarting a gateway on a peer/WSL spawns a useless loopback-only duplicate (see CHATBIBLE_FAILURE.MD 2026-05-22/24 corrections).

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

## Quick path — inspect CLI (CANONICAL, portable, OS-agnostic)

This is the **only** probe you need in 95% of cases. Python exists on every host (Windows/Linux/macOS/WSL); it talks to the gateway over HTTP and prints the full health JSON. Prefer it over raw curl everywhere.

```bash
python tools/protocol_inspect.py health    # use python3 if python is unmapped on Linux
```

If `python` is not on PATH, try `python3`. Do NOT fall back to `curl.exe` on a non-Windows host.

## Gateway address (IMPORTANT)

**This desktop's gateway binds on the LAN IP, not loopback.**
Always use `192.168.2.32:8788` as the primary address. `127.0.0.1:8788` only works if the gateway process is running *in this exact shell session* — it is not reliable and will silently fail when the gateway is running as a background service.

| Context | Address to use |
|---------|---------------|
| This desktop (primary) | `http://192.168.2.32:8788` |
| Laptop / other LAN peer reaching this desktop | `http://192.168.2.32:8788` |
| Loopback (only if gateway started in same shell) | `http://127.0.0.1:8788` |

## Raw HTTP probe (fallback only — when `protocol_inspect.py` is unavailable)

Pick the line that matches YOUR host. Do NOT use the Windows line on Linux or vice-versa.

**Portable (any OS, no curl):**
```bash
python -c "import urllib.request,json,sys; print(json.dumps(json.loads(urllib.request.urlopen('http://192.168.2.32:8788/health',timeout=4).read()),indent=2))"
```

**Linux / macOS / WSL / Remote-SSH peer:** plain `curl`, never `curl.exe`
```bash
curl -s -m 4 http://192.168.2.32:8788/health
```

**Windows (PowerShell):** `curl.exe` or `Invoke-WebRequest`
```powershell
curl.exe -s -m 4 http://192.168.2.32:8788/health
# or: (Invoke-WebRequest -Uri http://192.168.2.32:8788/health -TimeoutSec 4 -UseBasicParsing).Content
```

## Interpretation

- `ok=False` or probe fails → **do NOT immediately conclude "gateway down" or restart.** Run this checklist first:
  1. Are you on the gateway host (the desktop) or a peer? `hostname` + `uname -s 2>/dev/null || echo Windows`.
  2. Did you use a tool that exists on your OS? (No `curl.exe` on Linux. Use `python tools/protocol_inspect.py health`.)
  3. Did you probe the HTTP endpoint, not a local port scan? (`ss/netstat/Get-NetTCPConnection` on a peer prove nothing about a remote gateway.)
  4. Can your host route to the gateway IP? `ping 192.168.2.32`. If on a peer, confirm same subnet / no AP-isolation.
  5. From the **gateway host itself**, `python tools/protocol_inspect.py health` is the ground truth. Only if THAT fails is the gateway actually down.
  - Restart (gateway host only): `python tools/protocol_gateway.py --host 0.0.0.0 --ws-port 8787 --http-port 8788 --peer-id gateway-a` (see `cross-pc-protocol-debug-first`). **Never restart from a WSL/peer env** — it spawns a loopback-only duplicate with empty peer_registry whose broadcasts never reach other PCs.
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
