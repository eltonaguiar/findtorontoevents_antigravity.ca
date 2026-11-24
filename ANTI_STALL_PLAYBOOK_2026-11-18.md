# ANTI-STALL PLAYBOOK — GH Actions Health Check swarm

**Author:** coordinator (absorbed from @stall-postmortem, whose executor failed at 01:22Z with `pre-invocation hook: context summarization: no messages fit within the context token budget` — a worker cannot be revived when its inherited trajectory is too large to summarize).
**Date:** 2026-11-18
**Applies to:** any coordinator running a long-lived multi-agent swarm on this board.

---

## 1. Observed failure modes (real incidents, Nov 17–18)

| # | Failure mode | Evidence |
|---|---|---|
| F1 | GO issued, zero worker conversion for hours | 09:04Z dispatch → 12.6 h silence; board head frozen |
| F2 | Worker parked `waiting` with `last_read_seq` == the GO seq, never replies | `bonds-profiler`, `dash-auditor-2`, `pm-feed-implementer-3` at #621 |
| F3 | Deliverable written to brain/artifact dir instead of repo root | recurring; only 1 of 10 named files existed at root |
| F4 | "Missing file" report filed before the file landed | #617 vs #618 contradiction |
| F5 | `.py` source written into a `.md` deliverable; trailing log claims success | `equities_db_profile.md` = bonds script text |
| F6 | Untouched placeholder shipped as an answer | empty results table in `BONDS_EDGE_VERDICT` |
| F7 | Worker dies on pre-invocation context summarization | `stall-postmortem`, 01:22Z |

## 2. Rules (non-negotiable)

1. **Never `swarm_wait(mentions_only:true)` for background waits.** Use `mentions_only:false`, or a short `DurationSeconds` timer, or a cron heartbeat. A mentions-only wait parks the coordinator and stops all GO issuance.
2. **Always post a one-line status, even when blocked.** Format: (a) last deliverable + path, (b) complete? Y/N, (c) blocker or NONE. Silence is not a valid reply.
3. **Verify with `ls`, never trust a worker's claim.** Worker self-reports are treated as unverified until the coordinator runs `ls -la` at the repo root. Byte size > 1 KB and "is it really markdown?" are both checks.
4. **Reject stubs and wrong-content files as non-deliverables.** A 575 B profile with "Describe why…" bullet placeholders is a STUB. A `.md` whose first line is `#!/usr/bin/env python3` is WRONG-OUTPUT. Re-GO immediately, name the exact path.
5. **Write deliverables to the repo root**, `/home/eaguiar2015/findtorontoevents_antigravity.ca/<FILE>`, never to brain artifact dirs.
6. **Brief subagents scoped and bounded.** One artifact per brief, explicit source path + destination path, explicit "do not commit/push".
7. **Cron heartbeat, not sleep loops.** One cron every 20 min: read board, `swarm status`, `ls` the root, re-GO workers whose `last_post` > 90 min with an outstanding GO, post landed/missing list.
8. **Escalate to the user if board head has not advanced in 3 h.**
9. **Re-go only live workers.** If a worker declares itself idle/genuinely done, release it (`kill`) rather than re-GOing into a parking lot.
10. **A worker that errors on invocation is not retryable by name** — its trajectory is poisoned. Absorb its deliverable at the coordinator level and `kill` it.

## 3. Coordinator heartbeat checklist

```
read_board since=<head>
swarm status                      # note state + last_post per member
ls -la <repo root> | grep <deliverable names>
for each missing deliverable:
    find owning worker; if last_post > 90 min -> post one-line GO w/ exact path
if head - prev_head == 0 for 3h -> escalate to user
```

## 4. Definition of done (per deliverable)

- File exists at repo root, byte size consistent with real content (> 1 KB unless explicitly tiny).
- Content is the right artifact type (markdown is markdown, not Python source).
- No placeholder sentences ("Describe why…", "Check for timestamps…").
- Explicit raw counts or an explicit "query returned zero rows".
- Any external blocker (e.g. MySQL 1045) named in the file, not silently omitted.
