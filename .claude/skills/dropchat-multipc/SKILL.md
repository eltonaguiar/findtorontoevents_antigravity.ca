---
name: dropchat-multipc
description: Push the current session's transcript summary + open PRs + outstanding action items to the cross-PC protocol gateway so peer agents (Cursor, Hermes/WSL, Freebuff, Claude on laptop, etc.) can see what this instance just did. Then poll the broadcast + DM queues for any messages from those peers and surface them to the operator. Optionally revise + recommit work based on peer insights. Triggers — `/dropchat-multipc`, "drop chat to multi-pc", "broadcast session summary", "DROPCHATTOMULTIPC", "share with peers", "check peer inbox + sync". Aliases — dropchat, dctm, multipc-sync, peer-sync.
---

# dropchat-multipc

End-of-turn / end-of-session handoff for cross-PC agent coordination. Compresses the session's actual deliverables (commits, PRs, files written, decisions made) into one structured broadcast envelope, sends it via the gateway described in `CHATBIBLE.MD`, then drains the peer inbox so the operator can see what other agents have been doing in parallel.

## Why this exists

The user has 4+ agents running across Windows + WSL + multiple PCs (Cursor, Hermes, Claude Code, GH Copilot, Antigravity, Kilo, etc.). They have a shared cross-PC gateway (`tools/protocol_gateway.py`) but agents forget to use it after a heads-down work session. Result: duplicate work (e.g., Hermes + Kilo Code both audited the same blocklist), missed insights (e.g., Mercury2 finding a P0 bug that another agent could have fixed instantly), and stale handoffs.

This skill bundles the "broadcast what I did + see what others did + revise if needed" workflow into one command.

## When to use

- End of a long autonomous session (10+ tool calls, multiple PRs/commits)
- Before pausing work for the day
- When the user says "drop chat to multi-pc", "/dropchat-multipc", "share with peers", "DROPCHATTOMULTIPC"
- After landing any change that touches code another agent might be working on concurrently (gates, blocklists, dashboard, deploy scripts)
- Periodic mid-session sync if the session is generating a lot of artifacts (>3 PRs / >5 commits)

## Prerequisites

1. Cross-PC gateway must be running. **Always use `192.168.2.32:8788` on this desktop — never `127.0.0.1`.** The gateway is a background service bound to the LAN IP; loopback only works if the gateway was started in this exact shell session.

   ```bash
   curl.exe -s http://192.168.2.32:8788/health | python -m json.tool
   ```

   The `peer_registry` must show registered peers. If empty or connection refused, the gateway is down.

2. `tools/adapters/cursor_claude_adapter.py` + `tools/adapters/freebuff_adapter.py` + `tools/protocol_inspect.py` must exist. If missing, the cross-pc-protocol install is broken — fall back to writing to `logs/cross_pc_protocol/events.jsonl` directly and surface a warning.

3. Identify yourself. The user is "Claude Code on findtorontoevents desktop" by default. Use `--runtime claude` when calling the adapter so the peer_id is correctly stamped.

## Step 1 — Gather the session payload

Build a structured JSON payload from this turn's actual deliverables. Do NOT include the raw model-think narrative. Format:

```json
{
  "schema": "session-summary/v1",
  "agent": "claude-opus-4-7-desktop",
  "session_started_utc": "<UTC ISO timestamp>",
  "session_ended_utc": "<UTC ISO timestamp>",
  "branch_at_end": "<current git branch>",
  "commits_this_session": [
    {"sha": "<short_sha>", "subject": "<commit subject>", "branch": "<branch>", "files": <count>}
  ],
  "prs_opened_or_updated": [
    {"number": 1024, "title": "...", "state": "open|merged|closed", "url": "..."}
  ],
  "merged_to_main_this_session": ["<sha>", "..."],
  "files_written": ["<path>", "..."],
  "decisions": [
    "1-line decision summary, e.g. 'Unblocked CT=F (PF 10.94 winner) from Hermes blocklist after 4-engine swarm review'"
  ],
  "open_questions": [
    "1-line question, e.g. 'Should daily reconciliation job auto-close positions when source-system drops below filter?'"
  ],
  "follow_ups_for_other_agents": [
    {"to": "all|<peer_id>", "ask": "...", "priority": "P0|P1|P2"}
  ],
  "files_to_check": [
    "<paths peer agents should look at before their next session>"
  ]
}
```

Gather it from real sources, not fabrication:

```bash
git log --since="<session start UTC>" --oneline --all > /tmp/session_commits.txt
gh pr list --author=@me --json number,title,state,url --search "updated:>=<session start>" > /tmp/session_prs.json
```

If you can't compute a real session-start timestamp, use "the last 4 hours" as a conservative upper bound.

## Step 2 — Send the broadcast

One message, `topic=SESSION_SUMMARY`, `to=all`. Use the adapter (it handles identity correctly per CHATBIBLE §2):

```bash
python tools/adapters/cursor_claude_adapter.py --runtime claude \
  --http-base http://192.168.2.32:8788 \
  send --topic SESSION_SUMMARY \
  --payload @/tmp/session_summary_payload.json \
  --to all
```

If the adapter doesn't accept `@/path` syntax, inline the JSON via `--payload "$(cat /tmp/session_summary_payload.json)"` and watch for shell quoting issues.

For Hermes on WSL adjust path: `python3 tools/adapters/cursor_claude_adapter.py --runtime hermes ...`.

**Verify the send actually went out** — don't trust the adapter's exit code alone. Tail the event log:

```bash
python tools/protocol_inspect.py --http-base http://192.168.2.32:8788 tail --limit 5
```

You should see your envelope at the top. If you only see `direction=inbound` for OTHER peers, your send didn't land — check gateway IP per Step 0.

## Step 3 — Drain the inbox

Two pulls, mandatory:

```bash
# DMs addressed specifically to this peer
python tools/adapters/freebuff_adapter.py \
  --peer-id claude-desktop \
  --http-base http://192.168.2.32:8788 \
  poll --limit 50 > /tmp/inbox_dms.json

# Broadcasts that other peers have sent since last drain
python tools/adapters/freebuff_adapter.py \
  --peer-id all \
  --http-base http://192.168.2.32:8788 \
  poll --limit 50 > /tmp/inbox_broadcasts.json
```

**Polling is destructive** — once you drain, those messages pop off the queue. The durable copy lives at `logs/cross_pc_protocol/events.jsonl` (see `CHATBIBLE.MD §4`). For non-destructive peek, use `protocol_inspect tail` instead.

## Step 4 — Triage peer messages

For each message:

1. Classify by topic: `SESSION_SUMMARY`, `task.request`, `audit_finding`, `pick_proposal`, `block_proposal`, `bug_report`, `heartbeat`, etc.
2. If a peer reports a P0 bug or data-corruption claim that overlaps with your session's work — re-verify on disk before acting (memory: `project_hermes_phantom_work_2026-05-09`).
3. If a peer requests an `ack` (envelope has `require_ack=true`), POST `/ack` with their `message_id` after handling. Adapter does this when invoked with `--require-ack`.
4. For each task.request DM to you specifically, decide:
   - Accept and act (proceed to Step 5)
   - Defer with a reply DM containing rationale
   - Reject with a reply DM citing the reason (e.g., "scope-creep" or "blocked on <X>")

Anything received gets a one-line entry in `reports/peer_inbox_<UTC>.md` so the operator can review.

## Step 5 — Revise + re-commit (optional, only if peer insight changes decisions)

If a peer message reveals that a decision made earlier in your session was wrong (e.g., a blocklist row should have been a different symbol, a banner has a typo, a gate boundary is off-by-one):

1. Make the smallest surgical fix — separate commit, separate one-line message that cites the peer message_id as the source.
2. If the fix touches an already-pushed PR branch, push the fix as an amendment commit. Do NOT force-push.
3. Update `reports/peer_inbox_<UTC>.md` with the action taken (Accepted-and-fixed / Deferred / Rejected).
4. If no peer insight changes anything: skip Step 5. Don't generate make-work to look productive.

## Step 6 — Reply with a closing broadcast

Optional but recommended:

```bash
python tools/adapters/cursor_claude_adapter.py --runtime claude \
  send --topic SESSION_CLOSED \
  --payload "$(echo '{"peer":"claude-desktop","drained_n":<count>,"acted_on":<count>,"next_session_eta":"<ISO>"}')" \
  --to all
```

This lets peers know they don't need to retry pinging you for the rest of the session.

## Output to operator

A compact 6-line summary:

```
[dropchat-multipc] 2026-05-15T01:32Z
broadcast: SESSION_SUMMARY → all (message_id=<id>, n_commits=N, n_prs=N)
inbox: <n> DMs, <m> broadcasts pulled
peers reachable: <count from /health>
revised: <0|N files touched per peer feedback>
follow-ups posted: <count>
```

## Failure logging (MANDATORY — user directive 2026-05-15)

If at ANY point in Steps 1-6 you cannot get a message onto the protocol bus (gateway unreachable, adapter missing, peer-id refusal, send returns non-accepted, etc.), you MUST append a structured entry to `CHATBIBLE_FAILURE.MD` at repo root and commit + push that file to `main` so the operator can see the gap.

### Failure entry format

Append (do not overwrite) one block per failure:

```markdown
---
- **timestamp_utc:** 2026-05-15T01:32:11Z
- **agent_runtime:** claude-code | cursor | hermes-agent | gh-copilot | kilo-code | windsurf | aider | codex | <other>
- **provider/model:** anthropic/claude-opus-4-7 | openrouter/deepseek-reasoner | nous/hermes-3 | openai/gpt-5 | <other>
- **ide / surface:** claude-desktop | cursor-desktop-081g9oh | hermes-wsl-laptop | vscode-copilot | terminal | <other>
- **host:** desktop-zerou | laptop-zerou | <other>
- **stage_that_failed:** health-check | broadcast | inbox-drain | ack-roundtrip | revise-commit
- **error_observed:** `connection refused 127.0.0.1:8788` (verbatim error text, no paraphrase)
- **gateway_endpoint_tried:** `http://192.168.2.32:8788` | `http://192.168.2.32:8788`
- **peer_id_used:** claude-desktop | cursor-desktop-081g9oh | hermes-wsl-laptop | <other>
- **what_i_was_trying_to_send:** topic + 1-line payload summary, e.g. "SESSION_SUMMARY: closed 3 PRs, opened #1026"
- **fallback_used:** none | wrote to logs/cross_pc_protocol/events.jsonl directly | DM via Slack | none-just-this-file
- **next_action:** human-must-restart-gateway | retry-on-next-session | escalate-to-Elton
```

### Commit + push

After appending, commit:

```bash
git add CHATBIBLE_FAILURE.MD
git commit -m "log: CHATBIBLE protocol failure $(date -u +%Y-%m-%dT%H:%M:%SZ) — <agent_runtime> @ <ide>"
# Push directly to main (single-line append, low-risk):
git push origin HEAD:main
```

If push to main is blocked by branch protection, push to a `chat-failure-<utc>` branch and open a PR titled `chore: CHATBIBLE failure log <utc>`.

### Why mandatory

Silent failures of the protocol are how multi-agent sessions diverge. If 3 agents on 3 PCs are all hitting `127.0.0.1` and none can see each other, NOBODY notices unless someone logs the failure. This file is the single canonical surface where every agent admits to a missed sync. The operator scans it daily to spot recurring gateway / network / install issues.

### What does NOT need to go in CHATBIBLE_FAILURE.MD

- Routine inbox-empty events (drain returned `messages: []`) — that's a successful poll, not a failure.
- Adapter sub-tool warnings that recover (e.g., HTTP fallback after WS timeout — the message still got through).
- Operator-canceled sends.

Only true unreachable-bus events.

## Windows / PowerShell quick tips

Several agents (Kilo Code 2026-05-15 — see `CHATBIBLE_FAILURE.MD`) hit Bash-vs-PowerShell mismatches. CHATBIBLE.MD commands are Bash-flavoured. PowerShell equivalents:

| Bash idiom | PowerShell idiom |
|---|---|
| `curl -s url 2>/dev/null` | `try { (Invoke-WebRequest -Uri url -TimeoutSec 3 -UseBasicParsing).Content } catch { 'fail' }` (or `curl.exe -s url 2>$null`) |
| `netstat -an \| grep 8788` | `Get-NetTCPConnection -LocalPort 8788` |
| `python script.py &` | `Start-Process -NoNewWindow -PassThru -FilePath python -ArgumentList "script.py"` (PS `&` is the call operator) |
| `2>/dev/null` | `2>$null` — `/dev/null` is read by PowerShell as path `E:\dev\null` |
| `ss -an` | not available; use `Get-NetTCPConnection` |

The Bash tool in Claude Code does work with the Bash idioms; this section is for agents driving raw PowerShell terminals.

## Failure modes

| Symptom | Cause | Fix |
|---|---|---|
| `/health` shows 1-2 peers | localhost trap | Switch to `192.168.2.32:8788` per CHATBIBLE §0b |
| connection refused on 8788 | gateway not running | Start per CHATBIBLE §1, or coordinate with the desktop operator |
| my SESSION_SUMMARY doesn't appear in peers' inbox | my poll-bias: I drained `peer_id=all` and consumed my own broadcast | the durable copy still lives at `events.jsonl`; peers can read from there. Avoid draining `all` immediately after broadcasting |
| identity stamp wrong (`from=claude-main` from cursor box) | `--runtime` flag missing or env override | Always pass `--runtime claude` and verify the stamped `from` field in `protocol_inspect tail` |
| Payload too large | event log truncation at 1MB | Trim `files_written` to deltas + summary, don't paste full diffs |
| `UnicodeEncodeError` on Windows | console code page | `set PYTHONUTF8=1` or `chcp 65001` |
| Receiver claims they never got it | possibly retried before the gateway log flushed | Trace via `protocol_inspect trace --trace-id <id>` — if status=accepted there but receiver poll shows nothing, suspect a peer-id mismatch |

## Anti-patterns

- Do NOT post the raw chat transcript (model-think narrative). Always summarize to the structured payload.
- Do NOT broadcast on every tool call. This skill fires once per session OR when explicitly invoked.
- Do NOT use this for inter-thread coordination within the same Claude session. Use TodoWrite or peer skills for that.
- Do NOT delete `logs/cross_pc_protocol/events.jsonl` to "clean up". It's the durable replay log.
- Do NOT amend an existing peer's broadcast envelope. Always send a fresh envelope referencing their `causation_id`.

## Companion skills

- `/cross-pc-health` — pre-flight gateway check (CHATBIBLE §0b)
- `/cross-pc-sendmsg` — manual send (when you only need one message, not the full session summary bundle)
- `/cross-pc-checkmsg` — manual poll (when you just want to read, not broadcast)
- `/cross-pc-protocol-debug-first` — full protocol reference

## Reference

- Protocol overview: [CHATBIBLE.MD](../../../CHATBIBLE.MD)
- Adapter code: `tools/adapters/cursor_claude_adapter.py`
- Gateway: `tools/protocol_gateway.py`
- Inspector: `tools/protocol_inspect.py`
- Durable log: `logs/cross_pc_protocol/events.jsonl`
