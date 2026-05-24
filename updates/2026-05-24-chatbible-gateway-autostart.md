# CHATBIBLE Gateway Auto-Start Fix — 2026-05-24

## Problem

The CHATBIBLE cross-PC protocol gateway (`tools/protocol_gateway.py`) had **zero auto-start mechanism**. It was documented in CHATBIBLE.MD §1 as "Start gateway (Terminal A)" — a purely manual step. Every time the machine rebooted, the process crashed, or a session started fresh, agents had to manually detect the gateway was down, restart it, then waste turns re-broadcasting.

This caused:
- **Repeated CHATBIBLE_FAILURE.MD entries** — agents waking up to `connection refused` on 8788
- **90+ minutes burned** by a Hermes agent trapped in the 127.0.0.1 loop trying to reach a dead gateway
- **Session summaries lost** — fallback to local JSON files instead of actual cross-PC broadcast
- **Peer registry fragmentation** — each agent starting its own isolated gateway on 127.0.0.1

## Root Cause

No systemd service, no crontab, no startup script. The gateway was a fire-and-forget background process with no supervision.

## Fix Applied

### 1. systemd user service
`~/.config/systemd/user/chatbible-gateway.service`:
- Starts on boot (`WantedBy=default.target`)
- Auto-restarts on crash (`Restart=always`, `RestartSec=5`)
- Runs with `--host 0.0.0.0` so it's reachable on both localhost and LAN (192.168.2.32)
- Sandboxed: `NoNewPrivileges=true`, `ProtectSystem=strict`, read-write only to `logs/cross_pc_protocol`
- Peer ID: `gateway-systemd` (distinguishable from manual `gateway-a` or `gateway-fallback`)

### 2. Startup helper script
`tools/chatbible-gateway-start.sh`:
- One-liner for any agent: `bash tools/chatbible-gateway-start.sh`
- Tries systemd first (preferred — supervised, auto-restart)
- Falls back to background process if systemd unavailable
- Reports current peer count on success
- Exits 0 if gateway already running (idempotent)

### 3. Enabled and verified
- Service enabled: `systemctl --user enable chatbible-gateway`
- Service running: `Active: active (running) since 2026-05-24 07:47:06 UTC`
- Health check passes on both `127.0.0.1:8788` and `192.168.2.32:8788`
- Registered in desktop peer registry as `claude-gx10-c9b9`

## Files Changed

| File | Action | Purpose |
|------|--------|---------|
| `~/.config/systemd/user/chatbible-gateway.service` | Created | systemd user service (auto-start + auto-restart) |
| `tools/chatbible-gateway-start.sh` | Created | Startup helper script (systemd → background fallback) |
| `updates/2026-05-24-chatbible-gateway-autostart.md` | Created | This documentation |

## Verification

```bash
# Service status
systemctl --user status chatbible-gateway

# Health check
curl -s http://127.0.0.1:8788/health
curl -s http://192.168.2.32:8788/health

# Manual start (if needed)
bash tools/chatbible-gateway-start.sh
```

## Remaining Gap

The gateway on this machine (gx10-c9b9 / 192.168.2.52) connects to the **desktop's** gateway at 192.168.2.32. The systemd service starts a **local** gateway on this machine. This is correct per CHATBIBLE.MD — each peer runs its own gateway, and they discover each other via LAN broadcast. The key fix is that the local gateway no longer dies silently.

However, if the **desktop PC** (192.168.2.32) reboots, its gateway still has no auto-start. That needs to be set up on the Windows side as a Scheduled Task or Windows Service. This fix only covers the Linux/gx10 side.
