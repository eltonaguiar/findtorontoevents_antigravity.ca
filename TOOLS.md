# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

Add whatever helps you do your job. This is your cheat sheet.

## COMS (MQTT bus) — verified from laptop ELTON2026, 2026-11-25

- **Broker:** `192.168.2.52:1883`, anonymous, no TLS (trusted LAN only). This laptop is `192.168.2.51`, ~17ms rtt.
- **Client:** `tools/coms/coms.ps1` (from AGENT_FOLDERFRAMEWORK/COMMUNICATION/coms.ps1). Upstream guide: `_FORLAPTOPNOV252026.MD` on main.
- **Dependency:** `paho-mqtt` must be in whatever interpreter bare `python` resolves to. Here that is the hermes venv (`C:\Users\zerou\AppData\Local\hermes\hermes-agent\venv`). Use `python -m pip install paho-mqtt` — `--user` is rejected inside the venv.
- **My seat:** `inbox/elton2026/findtorontoevents_antigravity-ca/buffy-laptop` (role `buffy-laptop`, deliberately distinct from the Linux box's `buffy` seat).
- **Topics:** `inbox/<host>/<worktree>/<agent>`, `mentions/all` (broadcast everyone listens on), `notes/<slug>` (retained documents, 349+ live), `registry/<host>/<wt>/<agent>` (retained seats), `status/<host>`.
- **Commands:**
  ```bash
  powershell -ExecutionPolicy Bypass -NoProfile -File tools/coms/coms.ps1 roster
  powershell -ExecutionPolicy Bypass -NoProfile -File tools/coms/coms.ps1 check -Agent buffy-laptop --wait 5
  powershell -ExecutionPolicy Bypass -NoProfile -File tools/coms/coms.ps1 send mentions/all "message"
  powershell -ExecutionPolicy Bypass -NoProfile -File tools/coms/coms.ps1 send notes/<slug> "message" --retain
  ```
- **Gotchas:** plain `send` has no delivery guarantee (online subscribers only) — use `--retain` for async handoff. `--retain` into another agent's inbox is refused unless `-Force` (retained slots are last-writer-wins). Slugging rewrites dots, so the worktree segment is `findtorontoevents_antigravity-ca`, not `...ca` with the dot. Verify a send by reading the topic back with a raw paho subscriber, not by trusting the client's "sent" line.

## chrome-devtools (browser control) — verified 2026-11-25

- `chrome-devtools-mcp` is not an MCP tool here; use its CLI: `npm i -g chrome-devtools-mcp@latest`, then `chrome-devtools <tool> [args] --output-format=json`.
- **Attach to the user's live Chrome with `chrome-devtools start --autoConnect`** (Chrome 144+, requires the Remote debugging toggle on `chrome://inspect`). `--browserUrl http://127.0.0.1:9222` does NOT work: that toggle's server 404s on all `/json` endpoints and 403s WS upgrades.
- Re-attach after a wedge: `chrome-devtools status` → note `pid=`, `Stop-Process -Id <pid>`, then `start --autoConnect`.
- **Wedge hazard:** navigating a long-lived tab to a signed Azure blob URL (e.g. GitHub raw logs) can leave the load event pending forever and block every later command with exit 124. One throwaway tab per fetch + `close_page`, 60s per-call timeout. Recovery needs the tab closed or Chrome restarted — the daemon is attached to the user's real browser, so ask first.
- `evaluate_script` results come back as `{"message": "...```json\n<value>\n```"}`; parse `message` then JSON-decode the fenced block. CLI output is truncated near ~90 KB, so never ship big payloads through it — return a short value (e.g. `location.href`) and fetch the bytes separately.
- **Windows argv trap:** the `.cmd` shim goes through cmd.exe, which rewrites arguments — a multi-line JS payload gets chopped and `--pageId` is lost (`Error: specify either a pageId or a serviceWorkerId`). Call the package's real JS bin with node instead: `%APPDATA%/npm/node_modules/chrome-devtools-mcp/out/Default/gen/src/bin/chrome-devtools.js`.
