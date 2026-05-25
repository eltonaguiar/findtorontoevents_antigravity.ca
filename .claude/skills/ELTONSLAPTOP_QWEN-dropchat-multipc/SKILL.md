---
name: ELTONSLAPTOP_QWEN-dropchat-multipc
description: Push session summary to cross-PC gateway with peer ID "ELTONSLAPTOP_QWEN". Triggers — /dropchat-multipc, "drop chat to multi-pc", "broadcast session summary". Aliases — dropchat, dctm, multipc-sync, peer-sync.
---

# /dropchat-multipc — Qwen edition (Peer ID: ELTONSLAPTOP_QWEN)

End-of-session handoff for cross-PC agent coordination. Compresses session deliverables into structured broadcast, sends via gateway, drains peer inbox.

**Peer ID**: `ELTONSLAPTOP_QWEN`

## When to use

- End of long autonomous session (10+ tool calls)
- Before pausing work for the day
- User says "/dropchat-multipc", "drop chat to multi-pc", "share with peers"
- After landing changes touching code another agent might modify

## Prerequisites

### Gateway health check
**Always use `192.168.2.32:8788` — never `127.0.0.1`.**

```bash
curl.exe -s -m 5 http://192.168.2.32:8788/health | python -m json.tool
```

### Core files exist
```powershell
if (Test-Path 'tools\adapters\cursor_claude_adapter.py') { echo "adapter OK" } else { echo "adapter MISSING" }
if (Test-Path 'tools\protocol_inspect.py') { echo "inspect OK" } else { echo "inspect MISSING" }
```

## Step 1 — Gather payload

Build structured JSON from real deliverables:

```json
{
  "schema": "session-summary/v1",
  "agent": "qwen-code-desktop",
  "peer_id": "ELTONSLAPTOP_QWEN",
  "branch_at_end": "<current git branch>",
  "commits_this_session": [{"sha": "<short>", "subject": "..."}],
  "files_written_or_modified": ["<path>", ...],
  "decisions": ["1-line decision summary"],
  "open_questions": ["1-line question"],
  "follow_ups_for_other_agents": [
    {"to": "all", "ask": "...", "priority": "P0|P1|P2"}
  ]
}
```

## Step 2 — Send broadcast

```bash
python tools/adapters/cursor_claude_adapter.py \
  --peer-id ELTONSLAPTOP_QWEN \
  --http-base http://192.168.2.32:8788 \
  send --topic SESSION_SUMMARY \
  --payload <your-JSON-payload> \
  --to all
```

## Step 3 — Verify send

```bash
python tools/protocol_inspect.py tail --limit 5
```

Should see your envelope near top.

## Step 4 — Drain inbox

Two pulls:

```bash
# DMs addressed to this peer
python tools/adapters/cursor_claude_adapter.py \
  --peer-id ELTONSLAPTOP_QWEN \
  --http-base http://192.168.2.32:8788 \
  poll --limit 50 > /tmp/inbox_dms.json

# Broadcasts from other peers
python tools/adapters/cursor_claude_adapter.py \
  --peer-id all \
  --http-base http://192.168.2.32:8788 \
  poll --limit 50 > /tmp/inbox_broadcasts.json
```

Polling is destructive — messages pop off queue. Durable copy at `logs/cross_pc_protocol/events.jsonl`.

## Step 5 — Triage peer messages

For each message:
1. Classify by topic (`SESSION_SUMMARY`, `task.request`, `audit_finding`, etc.)
2. If P0 bug overlapping your session's work → re-verify on disk before acting
3. If `require_ack=true` → POST `/ack` after handling
4. Log to `reports/peer_inbox_<UTC>.md`

## Step 6 — Closing broadcast (optional)

```bash
python tools/adapters/cursor_claude_adapter.py \
  --peer-id ELTONSLAPTOP_QWEN \
  --http-base http://192.168.2.32:8788 \
  send --topic SESSION_CLOSED \
  --payload '{"peer":"ELTONSLAPTOP_QWEN","drained_n":<count>,"acted_on":<count>}' \
  --to all
```

## Output format

Compact summary:
```
[dropchat-multipc] <timestamp UTC>
broadcast: SESSION_SUMMARY → all (message_id=<id>)
inbox: <n> DMs, <m> broadcasts pulled
peers reachable: <count from /health>
revised: 0
```

## Failure logging

If bus unreachable at any point:
1. Append entry to `CHATBIBLE_FAILURE.MD`
2. Commit + push `CHATBIBLE_FAILURE.MD` to `main`

Silent failures cause multi-agent divergence. Log every true unreachable-bus event.

## Anti-patterns

- Do NOT post raw chat transcripts — summarize to structured payloads
- Do NOT broadcast on every tool call — once per session or when invoked
- Do NOT delete `logs/cross_pc_protocol/events.jsonl` — replay log
- Do NOT use `127.0.0.1` — always use `192.168.2.32` on this desktop
