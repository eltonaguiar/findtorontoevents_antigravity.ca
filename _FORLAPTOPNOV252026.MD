# COMS on a laptop (Windows, C: drive only) — quick guide

COMS is a tiny MQTT message bus. The broker lives on the Linux box at
`192.168.2.52:1883`. Your laptop only needs a single client script + Python.

## 1. Get the client script (no git needed)

```powershell
$dir = "$env:USERPROFILE\coms"; New-Item -ItemType Directory -Force -Path $dir | Out-Null
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/eltonaguiar/AGENT_FOLDERFRAMEWORK/main/COMMUNICATION/coms.ps1" -OutFile "$dir\coms.ps1"
```

(Or clone the whole framework: `git clone https://github.com/eltonaguiar/AGENT_FOLDERFRAMEWORK $env:USERPROFILE\AGENT_FOLDERFRAMEWORK`)

## 2. Install the only runtime dependency

```powershell
pip install paho-mqtt
python -c "import paho.mqtt.client; print('paho ok')"
```

No mosquitto binaries needed on Windows.

## 3. Check connectivity

```powershell
Test-NetConnection 192.168.2.52 -Port 1883   # TcpTestSucceeded must be True
powershell -ExecutionPolicy Bypass -File $env:USERPROFILE\coms\coms.ps1 learn
```

## 4. Register a unique seat on this laptop

If your laptop's computer name might collide with another PC, set a unique host:

```powershell
$env:COMS_HOST = "laptop-<yourname>"      # e.g. laptop-elton
$env:COMS_WORKTREE = "agent-folderframework"   # optional, pins worktree segment
powershell -ExecutionPolicy Bypass -File $env:USERPROFILE\coms\coms.ps1 register -Agent claude
```

## 5. Send / receive

From the laptop:
```powershell
powershell -ExecutionPolicy Bypass -File $env:USERPROFILE\coms\coms.ps1 check -Agent claude
powershell -ExecutionPolicy Bypass -File $env:USERPROFILE\coms\coms.ps1 send mentions/all "hello from laptop"
```

From Linux/desktop to this laptop (use the exact inbox topic from register output):
```bash
COMS send inbox/laptop-<yourname>/<worktree>/claude "ping from desktop"
```
Then on the laptop: `coms.ps1 check -Agent claude` should show the ping.

## Notes

- Non-retained messages only reach online subscribers; use `send --retain` or `mentions/all` for async handoffs.
- `coms.ps1` is self-contained for all core commands; it only needs the framework folder for the optional `prompt` command.
- If two PCs share a computer name, use `$env:COMS_HOST` to avoid colliding inboxes.
- Broker is anonymous on the LAN (no TLS) — fine on a trusted network, do not expose to the internet.