---
name: tv-cdp-launch
description: Launch TradingView Desktop with Chrome DevTools Protocol so the tradingview-desktop MCP can drive the UI. Handles the WindowsApps install path (which the MCP's tv_launch can't auto-find), the non-default-port problem (MCP defaults to 9222 but TV is often bound to 9223), and the loopback-only listen behavior. Aliases — tv-launch, tv-up, tv-cdp.
---

# tv-cdp-launch

> **MCP server:** [tradesdontlie/tradingview-mcp](https://github.com/tradesdontlie/tradingview-mcp) — the `mcp__tradingview-desktop__*` tool family.

Bring TradingView Desktop up with `--remote-debugging-port` and make sure the `mcp__tradingview-desktop__*` tool family can reach it.

## When to use

- Any other `tv-*` skill returns `cdp_connected: false` or `CDP connection failed after 5 attempts`.
- User says "launch TV", "TV is down", "MCP can't see TradingView", "open tradingview with debug".
- First step of every paper-trading or position-management workflow.

## Constraints (read before launching)

1. **WindowsApps install is invisible to `mcp__tradingview-desktop__tv_launch`.** The MCP only searches `%LOCALAPPDATA%\TradingView\…`, `Program Files\TradingView\…`, and `Program Files (x86)\TradingView\…`. Store-installed TV lives at `C:\Program Files\WindowsApps\TradingView.Desktop_<ver>_x64__<hash>\TradingView.exe` and must be launched manually.
2. **MCP CDP port is hard-coded to 9222.** `tv_health_check` and friends take no port argument. If TV is bound to a different port (9223, 9224, …) you must proxy 9222 → real_port.
3. **CDP binds to 127.0.0.1 only.** Don't probe via `localhost` only — explicit `127.0.0.1`.
4. **`netsh interface portproxy` needs admin.** If you don't have elevation, use the userland Python TCP forwarder pattern below.

## Step 1 — Find the exe

```powershell
Get-ChildItem "C:\Program Files\WindowsApps\TradingView.Desktop_*\TradingView.exe" -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName
```

If the WindowsApps folder is ACL-locked, try AppX:

```powershell
(Get-AppxPackage -Name "*TradingView*").InstallLocation
```

## Step 2 — Kill stale instances + launch

```powershell
Get-Process -Name TradingView -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2
Start-Process "C:\Program Files\WindowsApps\TradingView.Desktop_<ver>_x64__<hash>\TradingView.exe" `
  -ArgumentList "--remote-debugging-port=9222","--remote-allow-origins=*"
Start-Sleep -Seconds 8
```

Prefer port **9222** so the MCP works out of the box. If user already launched on 9223, jump to Step 4.

## Step 3 — Verify port listen + CDP responds

```powershell
Get-NetTCPConnection -State Listen |
  Where-Object { $_.LocalPort -in 9222,9223,9224 } |
  Select-Object LocalAddress, LocalPort, OwningProcess
try {
  (Invoke-WebRequest -Uri "http://127.0.0.1:9222/json/version" -TimeoutSec 5 -UseBasicParsing).Content
} catch { "fail: $_" }
```

A successful response includes `"Browser": "Chrome/…"` and a `webSocketDebuggerUrl`. Now call:

```
mcp__tradingview-desktop__tv_health_check
```

Expect `cdp_connected: true` and a `target_url` of `https://www.tradingview.com/chart/...`.

## Step 4 — Port bridge (TV on 9223, MCP wants 9222)

Two options. Use whichever you have permissions for.

### 4a. netsh portproxy (needs admin)

```powershell
netsh interface portproxy add v4tov4 listenaddress=127.0.0.1 listenport=9222 connectaddress=127.0.0.1 connectport=9223
# verify
netsh interface portproxy show v4tov4
# teardown when done
# netsh interface portproxy delete v4tov4 listenaddress=127.0.0.1 listenport=9222
```

If `netsh` returns `The requested operation requires elevation`, fall through to 4b.

### 4b. Userland Python TCP forwarder (no admin)

Save once, run in background:

```python
# tools/tv_cdp_proxy.py
import socket, threading
def pipe(a, b):
    try:
        while True:
            d = a.recv(65536)
            if not d:
                break
            b.sendall(d)
    except Exception:
        pass
    finally:
        for s in (a, b):
            try: s.close()
            except: pass

def handle(client, target_port):
    upstream = socket.socket()
    upstream.connect(("127.0.0.1", target_port))
    threading.Thread(target=pipe, args=(client, upstream), daemon=True).start()
    pipe(upstream, client)

def main(listen=9222, forward=9223):
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("127.0.0.1", listen))
    s.listen(50)
    print(f"LISTEN {listen} -> {forward}", flush=True)
    while True:
        c, _ = s.accept()
        threading.Thread(target=handle, args=(c, forward), daemon=True).start()

if __name__ == "__main__":
    import sys
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 9222,
         int(sys.argv[2]) if len(sys.argv) > 2 else 9223)
```

Launch the forwarder in the background (Bash tool, `run_in_background: true`):

```bash
python tools/tv_cdp_proxy.py 9222 9223 &
sleep 2
curl -s -m 3 http://127.0.0.1:9222/json/version | head -c 200
```

The forwarder is socket-level. CDP works over WebSocket, which tunnels fine through this. The MCP will see 9222 normally.

## Step 5 — Confirm MCP can drive the page

```
mcp__tradingview-desktop__tv_health_check
```

Returned `success: true` + `cdp_connected: true` = ready. If `cdp_connected: false`:
- Re-check Step 3 (CDP responds on the listen port)
- Re-check Step 4 (forwarder alive — `Get-Process python` should show your forwarder PID)
- Re-check no other process has stolen 9222 (`Get-NetTCPConnection -LocalPort 9222`)

## Cleanup

If you started the Python forwarder in background, leave it running for the session. To stop:

```bash
# find pid
ss -ltnp 2>/dev/null | grep ':9222'    # WSL
# or via PowerShell
Get-NetTCPConnection -LocalPort 9222 | Select-Object OwningProcess
Stop-Process -Id <pid>
```

## Known failure modes

| Symptom | Cause | Fix |
|---|---|---|
| `tv_launch` returns "TradingView not found on win32" | WindowsApps path not searched | Manual launch via Step 2 |
| `tv_health_check` returns `cdp_connected: false` after manual launch | TV launched without `--remote-debugging-port` | Re-launch with the flag; kill all TV procs first |
| CDP responds on 9223 but MCP says fail | Port mismatch | Step 4 bridge |
| `netsh portproxy` says "requires elevation" | No admin | Use 4b (Python forwarder) |
| `Invoke-WebRequest 9222` says "actively refused" but port is in `Get-NetTCPConnection` | TV CDP still booting | Wait 5–10s and retry |
| Multiple TradingView.exe processes (8+) but no listener | Renderer subprocesses only — main proc crashed | `Stop-Process -Name TradingView -Force`, relaunch |
| `--remote-allow-origins=*` rejected | TV >= 3.x sometimes requires this for MCP WS handshake | Keep the flag; do not drop it |

## Companion skills

- `tv-account-switch` — once CDP is up, switch between paper accounts
- `tv-positions-read` — read open positions table
- `tv-paper-trade` — place trades with TP/SL (existing skill)
- `tv-debug` — debugging matrix for everything else
