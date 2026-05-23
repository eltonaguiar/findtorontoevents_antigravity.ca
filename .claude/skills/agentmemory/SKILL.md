---
name: agentmemory
description: Semantic memory layer for long-term knowledge storage and retrieval across sessions. Use for /agentmemory remember, search, context, forget, status commands. Distinct from holographic memory (live cross-agent state) — agentmemory is a searchable knowledge base backed by BM25+vector hybrid search at localhost:3111.
---

# /agentmemory — Semantic Long-Term Memory

Manages the agentmemory REST server at `http://localhost:3111` — a persistent, semantically searchable knowledge base separate from holographic memory.

**When to use agentmemory vs holographic memory:**
- **holographic memory** (`agent_shared_memory.json`) = live cross-agent state handoff; structured JSON; git-tracked; read by Hermes/Grok on startup; best for "what is the swarm doing right now / what decisions were made"
- **agentmemory** (port 3111) = long-term semantic knowledge base; BM25+vector hybrid search; survives across all sessions; best for "what did we learn about CRYPTO edge / how do UTChour filters work / what was the outcome of X experiment"

---

## Prerequisites: Starting the Server

The server must be running before any subcommand. Start it once per machine boot:

```bash
export PATH="$HOME/.local/bin:$PATH"   # needed for iii-engine
CI=true agentmemory &
sleep 8
agentmemory status
```

**Windows note:** The `iii-engine` binary (`iii.exe`) is installed at `%USERPROFILE%\.local\bin\iii.exe`. If the server fails to start, verify it is on PATH:
```bash
export PATH="$HOME/.local/bin:$PATH"
iii --version   # should print 0.11.2
```

If `iii.exe` is missing, reinstall: download `iii-x86_64-pc-windows-msvc.zip` from https://github.com/iii-hq/iii/releases/tag/iii%2Fv0.11.2, extract `iii.exe` to `%USERPROFILE%\.local\bin\`.

---

## Subcommands

### `/agentmemory status`

Check if the server is running and show memory counts.

```bash
agentmemory status
```

Or via REST:
```bash
curl -s http://localhost:3111/agentmemory/health | python -m json.tool 2>&1 | grep -E "status|memories|observations|uptime"
```

---

### `/agentmemory remember <text>`

Store a memory with optional metadata tags.

```bash
# Via CLI tool
curl -s -X POST http://localhost:3111/agentmemory/remember \
  -H "Content-Type: application/json" \
  -d '{
    "content": "<text>",
    "metadata": {
      "project": "findtorontoevents",
      "tag": "<tag>"
    }
  }'
```

**Examples:**

Store an asset edge finding:
```bash
curl -s -X POST http://localhost:3111/agentmemory/remember \
  -H "Content-Type: application/json" \
  -d '{
    "content": "EQUITY edge: UTChour 14-16 + conf>=0.7 + source=hyrotrader gives PF 2.1 over 421 trades (2026-05-16). Promotable to Tier 2.",
    "metadata": {"tag": "equity_edge", "date": "2026-05-16"}
  }'
```

Store a bug/fix:
```bash
curl -s -X POST http://localhost:3111/agentmemory/remember \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Bug fixed 2026-05-16: asset_class casing — universal_pick_resolver was storing lowercase crypto. Fixed with .upper() at write time. 3376/5000 picks backfilled.",
    "metadata": {"tag": "bug_fix"}
  }'
```

The response includes a memory `id` (e.g. `mem_mp882du4_744f8062ace7`) — save it if you may want to delete this memory later.

---

### `/agentmemory search <query>`

Semantic search across stored memories using BM25+vector hybrid search.

```bash
curl -s -X POST http://localhost:3111/agentmemory/search \
  -H "Content-Type: application/json" \
  -d '{"query": "<query>", "limit": 5}'
```

**Examples:**

Find CRYPTO edge knowledge:
```bash
curl -s -X POST http://localhost:3111/agentmemory/search \
  -H "Content-Type: application/json" \
  -d '{"query": "CRYPTO UTChour filter edge PF", "limit": 5}' | python -m json.tool
```

Find FOREX investigation history:
```bash
curl -s -X POST http://localhost:3111/agentmemory/search \
  -H "Content-Type: application/json" \
  -d '{"query": "FOREX rescue plan mutation protocol", "limit": 3}' | python -m json.tool
```

The response includes `results[].score` (relevance) and `results[].observation.narrative` (the stored text).

---

### `/agentmemory context`

Get current agent context — recent memories injected by the server for the current session.

```bash
curl -s http://localhost:3111/agentmemory/context | python -m json.tool
```

This endpoint returns what the memory server would inject into the current coding session. Useful to see what the server "thinks" is most relevant right now.

---

### `/agentmemory forget <id>`

Delete a specific memory by ID.

```bash
# Get the memory ID from a search result, then:
curl -s -X DELETE "http://localhost:3111/agentmemory/memories/<memory_id>"
```

Or use the forget endpoint:
```bash
curl -s -X POST http://localhost:3111/agentmemory/forget \
  -H "Content-Type: application/json" \
  -d '{"id": "<memory_id>"}'
```

---

## Common Workflows

### "Store what we learned about EQUITY edge after an audit run"
```bash
curl -s -X POST http://localhost:3111/agentmemory/remember \
  -H "Content-Type: application/json" \
  -d '{
    "content": "EQUITY T2 candidate 2026-05-16: PF 1.41 / WR 52.7% / n=421. Top filters: UTChour 14-16 + conf>=0.65 + source in [hyrotrader, ejaguiar1_stocks]. Next: push n to 500 for T2 promotion.",
    "metadata": {"tag": "asset_edge", "class": "EQUITY"}
  }'
```

### "Search for everything we know about FOREX before taking action"
```bash
curl -s -X POST http://localhost:3111/agentmemory/search \
  -H "Content-Type: application/json" \
  -d '{"query": "FOREX performance filter investigation mutation", "limit": 10}' \
  | python -m json.tool | grep -A3 "narrative"
```

### "Import recent Claude Code session transcripts into memory"
```bash
agentmemory import-jsonl --max-files 50
```
This ingests JSONL transcripts from `~/.claude/projects/` into the semantic index automatically.

### "Check if server is up before starting a long audit run"
```bash
export PATH="$HOME/.local/bin:$PATH"
curl -s http://localhost:3111/agentmemory/health | python -c "import sys,json; d=json.load(sys.stdin); print('UP' if d.get('status')=='healthy' else 'DOWN')"
```

---

## Server Configuration

Config file: `~/.agentmemory/.env`
Preferences: `~/.agentmemory/preferences.json`

**Key flags to consider enabling (edit `~/.agentmemory/.env`):**

```bash
# Enable semantic consolidation (deduplicate + synthesize memories over time)
# CONSOLIDATION_ENABLED=true

# Enable knowledge graph extraction (improves search quality)
# GRAPH_EXTRACTION_ENABLED=true

# Enable LLM-backed compression (requires ANTHROPIC_API_KEY or OPENAI_API_KEY)
# AGENTMEMORY_AUTO_COMPRESS=true
# ANTHROPIC_API_KEY=sk-ant-...

# Enable context injection into agent prompts
# AGENTMEMORY_INJECT_CONTEXT=true
```

Without an LLM key the server runs in **noop mode**: observations are indexed via BM25+local-embedding hybrid search (Xenova/all-MiniLM-L6-v2, 384-dim). This is sufficient for semantic recall without LLM cost.

---

## REST API Quick Reference

All endpoints are at `http://localhost:3111/agentmemory/`:

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/agentmemory/health` | Health + stats |
| POST | `/agentmemory/remember` | Store a memory |
| POST | `/agentmemory/search` | Semantic search |
| GET | `/agentmemory/context` | Current session context |
| POST | `/agentmemory/forget` | Delete by ID |
| GET | `/agentmemory/observations` | List all observations |

---

## Relation to Other Memory Systems

| System | File/Port | Format | Scope | Best For |
|--------|-----------|--------|-------|----------|
| MEMORY.md | `~/.claude/projects/.../memory/` | Markdown | Per-Claude-instance | Personal session notes, user preferences |
| Holographic Memory | `agent_shared_memory.json` | Structured JSON | Swarm-wide, git-tracked | Live cross-agent state, decisions, swarm phase |
| agentmemory | `:3111` REST API | Semantic index | Long-term, all sessions | Searchable knowledge base, experiment results, learned patterns |

---

## Reference

- Install: `npm install -g @agentmemory/agentmemory` + `pip install iii-sdk`
- iii-engine: `%USERPROFILE%\.local\bin\iii.exe` (v0.11.2)
- Config: `~/.agentmemory/.env`
- Preferences: `~/.agentmemory/preferences.json`
- Memory note: `~/.claude/projects/c--findtorontoevents-antigravity-ca/memory/reference_agentmemory.md`
- GitHub: https://github.com/rohitg00/agentmemory
