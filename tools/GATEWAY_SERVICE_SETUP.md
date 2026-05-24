# Cross-PC Gateway — service setup

One-time install so the gateway stops dying every time someone closes a shell or reboots.

## Architecture (one canonical bus, many clients)

```
┌─────────────────────────────────────────────────────────────────┐
│  Windows desktop (the host)                                     │
│  192.168.2.32:8788                                              │
│  ┌──────────────────────────────────────────────────────┐       │
│  │ cross-pc-gateway  (nssm service, auto-start on boot) │       │
│  │   python tools/protocol_gateway.py --host 0.0.0.0    │       │
│  └──────────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────┘
              ▲              ▲              ▲              ▲
              │              │              │              │
        register_peer.py  register_peer.py  ...        register_peer.py
        (Linux/WSL)       (Hermes laptop)              (Cursor desktop)
        peer_id=          peer_id=                     peer_id=
        claude-opus-4-7   hermes-wsl-laptop            cursor-desktop-08l...
```

There is exactly **ONE** gateway in the fleet. Every other peer is a heartbeat
client. Running a second gateway on a different host fragments the bus —
documented failure mode at `CHATBIBLE_FAILURE.MD` 2026-05-22T13:28Z.

## ⚠ Part 0 — If you have a Linux/WSL gateway service running, DISABLE IT FIRST

Verified on 2026-05-24: a well-intentioned commit (`64179783 fix(chatbible):
auto-start gateway via systemd user service`) installed
`~/.config/systemd/user/chatbible-gateway.service` on this Linux host. That
service starts a second `protocol_gateway.py` bound to `0.0.0.0:8788` on the
WSL machine's LAN IP (192.168.2.52). Its `peer_registry` is **empty** —
nobody connects to it because every real peer points at the canonical
192.168.2.32:8788 (Windows desktop). It is a silent-failure trap: any agent
that defaults to `127.0.0.1:8788` (the old CHATBIBLE default) now sends to
the wrong bus and gets back `ok: true`.

Disable it before continuing:

```bash
systemctl --user stop chatbible-gateway
systemctl --user disable chatbible-gateway
rm ~/.config/systemd/user/chatbible-gateway.service
systemctl --user daemon-reload
# Optional: revert the commit if it's still in your branch
# git revert 64179783
```

This is not a hypothetical — see CHATBIBLE_FAILURE.MD 2026-05-22T13:28Z
correction for the same trap from a previous session.

The right pattern is: **one** gateway on the desktop (Part 1) + **one
heartbeat client** on every other machine (Part 2). Never a second gateway.

## Part 1 — Install the gateway as a Windows service (desktop only)

Prerequisites:
- Windows desktop at 192.168.2.32
- Python 3.11+ on PATH
- [nssm](https://nssm.cc/download) installed (`choco install nssm` or download zip
  and add to PATH)
- Run PowerShell **as Administrator**

```powershell
cd E:\findtorontoevents_antigravity.ca
.\tools\install_gateway_service.ps1
```

Verify:

```powershell
nssm status cross-pc-gateway
# expected: SERVICE_RUNNING
Invoke-WebRequest http://192.168.2.32:8788/health -UseBasicParsing | Select -Expand Content
# expected: {"ok":true,"ts_utc":...,"peer_registry":{...}}
```

Survives reboots because `Start = SERVICE_AUTO_START`. Survives crashes because
`AppExit = Restart` with a 5-second delay.

Logs live at `<repo>\logs\cross_pc_gateway\stdout.log` and `stderr.log`, rotated
at 10 MB.

Reinstall after pulling new gateway code:

```powershell
.\tools\install_gateway_service.ps1 -Reinstall
```

## Part 2 — Install the heartbeat client (every other peer)

Each peer machine runs `tools/register_peer.py` as a long-lived daemon. It
publishes a `peer.heartbeat` envelope every 60 seconds so the gateway's
`peer_registry` accurately reflects who is online, and retries with capped
exponential backoff (5s → 300s) if the gateway is unreachable. After 5
consecutive failures it appends an entry to `CHATBIBLE_FAILURE.MD` so the
operator sees the gap.

### Linux / WSL (systemd user service)

```bash
mkdir -p ~/.config/systemd/user
cat > ~/.config/systemd/user/cross-pc-heartbeat.service <<'EOF'
[Unit]
Description=Cross-PC protocol heartbeat client
After=network-online.target

[Service]
Type=simple
WorkingDirectory=%h/findtorontoevents_antigravity.ca
ExecStart=/usr/bin/python3 tools/register_peer.py \
    --peer-id claude-opus-4-7-linux-wsl \
    --http-base http://192.168.2.32:8788 \
    --interval 60 \
    --capabilities ci-triage,memory,session-summary
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now cross-pc-heartbeat
systemctl --user status cross-pc-heartbeat
journalctl --user -u cross-pc-heartbeat -n 50 -f
```

WSL note: systemd user services need `systemd=true` under `[boot]` in
`/etc/wsl.conf`. If your distro doesn't have systemd, fall back to a `cron
@reboot` line or a `nohup ... &` in `.bashrc`.

### Windows (nssm again, on every Windows peer that isn't the gateway host)

```powershell
$repo = "E:\findtorontoevents_antigravity.ca"
$py   = (Get-Command python.exe).Source
nssm install cross-pc-heartbeat $py `
    "$repo\tools\register_peer.py --peer-id cursor-desktop-08l9oh --http-base http://192.168.2.32:8788 --interval 60"
nssm set cross-pc-heartbeat AppDirectory $repo
nssm set cross-pc-heartbeat AppStdout "$repo\logs\cross_pc_heartbeat\stdout.log"
nssm set cross-pc-heartbeat AppStderr "$repo\logs\cross_pc_heartbeat\stderr.log"
nssm set cross-pc-heartbeat Start SERVICE_AUTO_START
nssm set cross-pc-heartbeat AppExit Default Restart
nssm start cross-pc-heartbeat
```

### Pick a stable peer_id

Use a name that is unique across machines AND identifies the runtime, so
peer_registry stays readable. Examples already in use:
- `claude-desktop-081g9oh` (Copilot/GPT-5.3-Codex on Windows desktop)
- `claude-opus-4-7-linux-wsl` (this Linux env)
- `hermes-wsl-laptop` (Hermes on laptop)
- `cursor-desktop-<short-hostname>`

Avoid bare `claude` / `claude-code` — overlaps between machines and the
gateway can't distinguish them.

### Smoke-test before installing as a service

```bash
python3 tools/register_peer.py \
    --peer-id <your-id> \
    --http-base http://192.168.2.32:8788 \
    --once
# expected: {"ok": true, "status": "accepted", ...}
curl -s http://192.168.2.32:8788/health | python3 -m json.tool
# expected: your peer_id appears under peer_registry with a recent last_seen_ts_utc
```

## Part 3 — Verify the bus is healthy

```bash
curl -s http://192.168.2.32:8788/health | python3 -m json.tool
```

Healthy output:
- `ok: true`
- `peer_registry` contains every peer you expect, with `last_seen_ts_utc`
  within the last 2× heartbeat interval (≤120s for the default 60s interval)
- `pending_acks: 0` (anything >0 means a peer didn't ACK something it should
  have)

Stale peer (last_seen older than 5min) means the heartbeat daemon on that
machine died — investigate via that machine's service logs, NOT by restarting
the gateway.

## Part 4 — Failure modes after this lands

| Symptom | Real cause | Fix |
|---|---|---|
| `/health` from a peer returns connection-refused | Gateway service on the desktop is stopped/crashed | `nssm status cross-pc-gateway`; if not running, `nssm start cross-pc-gateway` and check `stderr.log` |
| One peer missing from `peer_registry` | That peer's `register_peer.py` daemon died | `systemctl --user status cross-pc-heartbeat` (or nssm) on that peer; check daemon logs |
| `CHATBIBLE_FAILURE.MD` getting new entries from `register_peer.py` | Gateway is down or unreachable from that peer's network | Check gateway service first; if up, check that peer's network route to `192.168.2.32` |
| Two peer_ids look the same | Stable-peer-id rule wasn't followed | Edit the offending peer's daemon config, restart |

The "human-must-restart-gateway" entries in `CHATBIBLE_FAILURE.MD` should
**stop appearing** after Part 1 lands. If they keep appearing the service
either wasn't installed (run `nssm status cross-pc-gateway`) or is
crashlooping (check `logs\cross_pc_gateway\stderr.log`).

## What this fixes vs. doesn't

**Fixes:**
- Gateway dies on shell-close / reboot / log-off — Windows service auto-starts and auto-restarts.
- Peers don't reconnect after a temporary outage — heartbeat daemon retries with backoff.
- Operator doesn't know the gateway is down until the next manual `/dropchat-multipc` — daemon writes to `CHATBIBLE_FAILURE.MD` after 5 missed heartbeats (~10 minutes at default interval).
- `peer_registry` is stale (a peer hasn't published in hours so it looks alive when it's not) — heartbeats refresh `last_seen_ts_utc` every 60s.

**Does NOT fix:**
- Gateway host machine is fully offline (desktop unplugged, network down). The bus is single-host by design; that's a separate "multi-host gateway" project, not in scope here.
- Heartbeat daemon falls behind under heavy network packet loss — current timeout is 10s per heartbeat, exponential backoff caps at 5 minutes. Acceptable for the current fleet size.
- The Linux/WSL env still has loopback-only constraint — register_peer.py from this env reaches the desktop gateway over LAN (`192.168.2.32:8788`), but the desktop must be powered on and on the same network.
