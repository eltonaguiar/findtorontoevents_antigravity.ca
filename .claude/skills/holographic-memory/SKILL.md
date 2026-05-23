---
name: holographic-memory
description: Read from and write to the shared Hermes/Grok holographic memory (agent_shared_memory.json). Use when the user says "/holographic-memory", "holo-mem", "check holographic memory", "write to holographic memory", or "what does hermes remember". Manages the cross-session/cross-PC agent continuity layer separate from personal MEMORY.md.
---

# /holographic-memory — Shared Agent Holographic Memory

Manages `agent_shared_memory.json` — the shared continuity layer read by Hermes Agent, Grok, Claude Code, and all other peers across PCs and sessions. This is NOT your personal memory (MEMORY.md). It is the swarm-wide blackboard.

**File:** `C:\findtorontoevents_antigravity.ca\agent_shared_memory.json`  
**Tool:** `tools/holographic_memory.py` (always use the tool, never edit JSON directly)

---

## Parse arguments

- **empty / `dump` / `status`** → Show full current state (facts, decisions, learnings, swarm phase)
- **`decisions`** → Show active decisions
- **`learnings [--tag <tag>]`** → Show learnings, optionally filtered by tag
- **`fact get <key>`** → Get a specific fact
- **`fact set <key> <value>`** → Set a fact (use for session state you want peers to see)
- **`write-decision <id> <text>`** → Record a decision into holographic memory
- **`write-learning <text> [--tag <tag>]`** → Record a learning

---

## Step 1 — Verify the tool exists

```bash
python tools/holographic_memory.py dump 2>&1 | head -5
```

If `ModuleNotFoundError` or `FileNotFoundError`: the tool or the JSON file is missing. Check:
```bash
ls tools/holographic_memory.py
ls agent_shared_memory.json
```

---

## Step 2 — Read operations

### Full dump (default action)
```bash
python tools/holographic_memory.py dump
```

### Active decisions only
```bash
python tools/holographic_memory.py decisions --active
```

### Learnings (optionally by tag)
```bash
python tools/holographic_memory.py learnings
python tools/holographic_memory.py learnings --tag asset_edge
python tools/holographic_memory.py learnings --tag crypto
```

### Get a specific fact
```bash
python tools/holographic_memory.py fact get asset_class_health_2026-05-16
python tools/holographic_memory.py fact get swarm_phase
```

---

## Step 3 — Write operations

### Set a fact (key-value, visible to all peers)
```bash
python tools/holographic_memory.py fact set <key> "<value>"
```

Example: record that CT=F was promoted to PROBATION:
```bash
python tools/holographic_memory.py fact set ct_f_rehab_stage "PROBATION since 2026-05-16, review 2026-06-06"
```

### Write a decision
```bash
python tools/holographic_memory.py write-decision <decision-id> "<decision text>"
```

Decision IDs use kebab-case with date suffix, e.g. `equity-conf-inversion-20260516`.

### Write a learning
```bash
python tools/holographic_memory.py write-learning "<text>" --tag <tag>
```

Tags: `asset_edge`, `crypto`, `equity`, `forex`, `commodity`, `rehab`, `swarm`, `pipeline`, `protocol`

---

## Step 4 — After writing, verify and git-push

The file is git-tracked. After any write:
```bash
git add agent_shared_memory.json
git commit -m "chore(holo-mem): <description> [skip ci]"
git push origin main
```

This ensures Hermes/Grok on other PCs see the update on their next `git pull`.

---

## Common workflows

### "What does Hermes remember about the current swarm plan?"
```bash
python tools/holographic_memory.py dump
```
Look at `swarm.plan`, `swarm.phase`, recent decisions.

### "Record that we fixed the asset_class casing bug"
```bash
python tools/holographic_memory.py write-learning "asset_class casing: universal_pick_resolver was storing lowercase 'crypto'. Fixed with .upper() at write time 2026-05-16. 3376/5000 picks affected. Backfilled." --tag asset_edge
git add agent_shared_memory.json && git commit -m "chore(holo-mem): asset_class casing fix learning [skip ci]" && git push origin main
```

### "Check what decisions are pending before I make a blocking change"
```bash
python tools/holographic_memory.py decisions --active
```
If a peer has already documented a decision on the same topic, defer to it or update it via `write-decision`.

### "Set the current swarm phase"
```bash
python tools/holographic_memory.py fact set swarm_phase "post-asset-edge-fixes"
```

---

## Key facts about the holographic memory

- **Separate from personal memory:** Your `memory/` MEMORY.md files are Claude Code's personal recall. The holographic memory is the swarm-shared blackboard.
- **Git-tracked:** Changes persist across sessions only if committed and pushed.
- **Hermes reads it via:** `hermes chat -q` — it loads this file on startup for continuity.
- **Do NOT edit JSON directly** — the tool manages schema versioning and timestamps.
- **Size limit:** Keep under ~50KB. Prune old facts/decisions with `python tools/holographic_memory.py fact delete <key>` if it grows large.

---

## Reference

- File: `agent_shared_memory.json` (repo root)
- Tool: `tools/holographic_memory.py`
- Memory note: `~/.claude/projects/c--findtorontoevents-antigravity-ca/memory/reference_holographic_memory.md`
