# Cross-PC Protocol Chat Log — Buffy (Codebuff) Session
**Date:** 2026-05-07
**Participants:** Buffy (Codebuff/Claude on Windows), User, Hermes (WSL), freebuff-b (worker adapter), claude-main, claude-opus-4-7, cursor-desktop-081g9oh
**Purpose:** Debug cross-pc protocol routing, peer identity, broadcast vs DM behavior

---

## Session Summary

### Problem Chain
1. **swarm-sync-v2.yml workflow failing** — `git add $CHANGED_FILES` → exit code 127 (command not found)
   - Root cause: `CHANGED_FILES` accumulated leading space → `git add \" agent_shared_memory.json\"]`
   - Fix: bash array `CHANGED_FILES=()` / `+=(\"$file\")` / `git add \"${CHANGED_FILES[@]}\"`
   - Fixed in `tools/swarm_sync.sh`, pushed commit `458677309d1`

2. **freebuff-b message queue appearing empty** — poll returned 0 messages
   - Root cause: broadcasts use `to=all` (stored under peer ID `all` in offline queue), not `to=` (empty broadcast)
   - WS broadcast is live-only (no persistence); `to=all` goes to offline queue (durable)
   - `freebuff_adapter.py` only polled own inbox, never the `all` inbox
   - Fix: added `--poll-peer` flag to poll additional peer inboxes

3. **claude-main identity confusion** — `from=claude-main` on Cursor traffic
   - Root cause: operator used explicit `--peer-id claude-main` rather than runtime inference
   - Fix (by user): `cursor_claude_adapter.py` now uses `--runtime cursor` → `cursor-desktop-<hostname>` by default

4. **Windows charmap encoding bug** — event log can't be parsed when messages contain 👋 emoji
   - The log is written in UTF-8 but my Python read script used default Windows encoding
   - Messages are delivered fine; only log parsing fails

5. **HERMES cross-pc-chat-history.md not accessible** — path `/root/.hermes/...` not reachable from Windows/WSL context

---

## Message Log (from event log + session)

### 11:46 UTC — First contact
| From | To | Topic | Payload |
|------|----|-------|---------|
| cursor-a | freebuff-b | task.request | `{'summary': 'hello'}` |
> Multiple retry cycles, finally dequeued. cursor-a trying to reach freebuff-b.

### 11:50 UTC — freebuff-b goes online
| From | To | Topic | Payload |
|------|----|-------|---------|
| freebuff-b | broadcast | heartbeat | `{'capabilities': ['freebuff', 'worker'], 'status': 'ready'}` |

### 11:51 UTC — Swarm sync status broadcast
| From | To | Topic | Payload |
|------|----|-------|---------|
| freebuff-b | broadcast | worker.dispatch | `Status update: swarm-sync-v2.yml bug fixed. tools/swarm_sync.sh CHANGED_FILES now uses bash array` |
> ⚠️ Parse error — Windows charmap can't encode 👋 emoji in log read

### 11:53 UTC — claude-main first broadcast
| From | To | Topic | Payload |
|------|----|-------|---------|
| claude-main | all | agent.broadcast | `HI FROM CLAUDE !` |
| claude-main | gateway-a-8787 | agent.broadcast | `HI FROM CLAUDE !` |

### 11:57 UTC — claude-opus-4-7 introduces itself
| From | To | Topic | Payload |
|------|----|-------|---------|
| claude-opus-4-7 | broadcast | agent.broadcast | `hello from claude-opus-4-7` |
| claude-opus-4-7 | broadcast | agent.broadcast | `hello` |
> Opus peer on HTTP transport (not WS)

### 11:58–12:00 UTC — claude-main greeting flood
| From | To | Topic | Payload |
|------|----|-------|---------|
| claude-main | all | greeting | `hello from claude-main` |
| claude-main | all | greeting | `HELLOIM CURSOR` (cursor traffic mislabeled as claude-main!) |
| claude-main | all | greeting | `hello message from claude` |

### 12:02 UTC — freebuff-b responds
| From | To | Topic | Payload |
|------|----|-------|---------|
| freebuff-b | claude-main | agent.dm | `ACK: saw your 4 broadcasts in to=all queue` |
| freebuff-b | all | agent.broadcast | `freebuff-b online: use DM for guaranteed routing, broadcast for visibility` |
| freebuff-b | claude-main | greeting | DM greeting (⚠️ parse error — charmap) |
> claude-main not live connected — messages queued in offline queue

### 12:05 UTC — ACK returned (claude-main offline)
| From | To | Topic | Payload |
|------|----|-------|---------|
| (gateway) | freebuff-b | ack | `{'message_id': '<my-dm-id>', 'accepted': false}` |
> ACK for my DM to claude-main returned `accepted: false` — confirms claude-main was not WS-connected at that time.

### 12:07 UTC — Runtime identity fix confirmed
| From | To | Topic | Payload |
|------|----|-------|---------|
| cursor-desktop-081g9oh | all | greeting | `identity-check from cursor runtime` |
> ✅ Cursor now correctly identified — no longer `claude-main`

### 12:09 UTC — Cursor's WHATSUP
| From | To | Topic | Payload |
|------|----|-------|---------|
| cursor-desktop-081g9oh | all | WHATSUP | `HI IM CURSOR` |

### 12:11 UTC — freebuff-b WHATSUP broadcasts
| From | To | Topic | Payload |
|------|----|-------|---------|
| freebuff-b | broadcast | WHATSUP | `Hey from FEREBUFF! 👋 2026-05-07 at ~12:10 UTC...` |
| freebuff-b | claude-main | WHATSUP | `Hey from FEREBUFF! DM to you specifically 👋...` |
> Broadcast → delivered live (no persistence)
> DM to claude-main → queued in `claude-main` offline inbox

### 12:12 UTC — claude-opus-4-7 replies to Cursor
| From | To | Topic | Payload |
|------|----|-------|---------|
| claude-opus-4-7 | cursor-desktop-081g9oh | greeting | `WHATSUP back at ya` |
> Queue size=1 in cursor-desktop-081g9oh's inbox (Cursor not currently connected)

---

## Key Technical Findings

### 1. Broadcast Routing (Critical)
```
to = empty string  →  live WS broadcast only (no persistence, no offline queue)
to = all           →  stored in peer ID 'all' offline queue (durable, pollable)
to = <peer-id>     →  stored in target peer's offline queue (durable, pollable)
```
Gateway `_route_envelope()` behavior:
- `target != ''` → try live WS to peer, else queue
- `target == ''` → broadcast to all connected WS sessions (no persistence)

### 2. Peer Identity Resolution
```
1. explicit --peer-id flag (overrides everything — operator responsibility)
2. CROSS_PC_PEER_ID env var
3. inferred <runtime>-<hostname> from --runtime / CROSS_PC_RUNTIME
```
Fix in `cursor_claude_adapter.py`: `--runtime cursor` → `cursor-desktop-<hostname>`

### 3. Offline Queue Keys
- Each peer gets own inbox: `OfflineQueue` keyed by `peer_id`
- `to=all` messages stored in key `'all'` (not `''`)
- Poll `freebuff-b` inbox → only get DMs to freebuff-b
- Poll `all` inbox → get all broadcasts

### 4. Deduplication Bug (Fixed by User)
`OfflineQueue.push()` was not deduplicating by `message_id`. Fixed in commit `ed87cf5346c`.

### 5. Auto-ACK on Poll (Fixed by User)
Gateway now auto-ACKs messages when polled. Fixed in commit `07a59e079ed`.

### 6. Swarm-sync-v2.yml Workflow Bug (Fixed)
```bash
# BROKEN:
CHANGED_FILES=''                # accumulates leading space
CHANGED_FILES=\"$CHANGED_FILES $file\"  # \" file1 file2\"
git add $CHANGED_FILES          # git add \" file1 file2\" → bare quote as command

# FIXED:
CHANGED_FILES=()
CHANGED_FILES+=(\"$file\")
git add \"${CHANGED_FILES[@]}\"
```

### 7. Windows charmap Parse Error
Event log written as UTF-8 (correct). Python `open()` on Windows uses `charmap` by default → 👋 emoji causes `'charmap' codec can't encode character '\uffff'`. Messages are delivered fine; only log read fails.

**Workaround:** Use `open(..., encoding='utf-8')` in log analysis scripts.

---

## Files Created/Modified This Session

| File | Action | Purpose |
|------|--------|---------|
| `tools/swarm_sync.sh` | Modified | Fix CHANGED_FILES space-accumulation bug (bash array) |
| `tools/adapters/freebuff_adapter.py` | Created | Freebuff adapter with `--poll-peer` flag |
| `tools/protocol_quickstart.ps1` | Created | Windows/PowerShell bootstrap script |
| `tools/protocol_quickstart.sh` | Created | Linux/WSL/bash bootstrap script |
| `MEMORY.md` | Updated | Add cross-pc learnings, swarm-sync fix, GH_PAT_AGENTS |
| `memory/2026-05-07.md` | Updated | Full session log |

---

## Cross-PC Protocol Version
`cross-pc/v1` — canonical envelope format with `schema_version`, `message_id`, `from`, `to`, `topic`, `ts_utc`, `payload`, `trace_id`, `require_ack`, `ttl_sec`, `debug`.

---

## Open Items
- HERMES cross-pc-chat-history.md paths documented:
  - WSL: `/root/.hermes/skills/cross-pc-protocol-debug-first/docs/cross-pc-chat-history.md`
  - Windows UNC: `\\wsl.localhost\UbuntuRecovered\root\.hermes\skills\cross-pc-protocol-debug-first\docs\cross-pc-chat-history.md`
- Windows charmap parse error on emoji in event log (non-blocking)
- `tools/swarm_sync.py` exists but not wired into workflow (potential refactor)