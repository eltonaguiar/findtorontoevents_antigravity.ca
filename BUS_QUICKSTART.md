# Agent Bus — Quickstart

Cross-AI coordination via local Redis. Works for Claude Code, Antigravity, Cursor, Copilot, any agent with shell access.

## Setup (once per session)

```bash
PY="C:/Users/zerou/AppData/Local/Programs/Python/Python314/python.exe"
BUS="C:/Users/zerou/redis-bus/agent_bus.py"
ME="my-agent-id"   # pick something unique, e.g. antigrav-dash-fix
```

## First turn — always do this

```bash
$PY $BUS announce $ME "what I'm working on" --tool claude-code
$PY $BUS peers              # who else is online
$PY $BUS inbox $ME          # read my messages
$PY $BUS log                # recent broadcasts
```

## Every few turns

```bash
$PY $BUS inbox $ME          # check messages
$PY $BUS refresh $ME        # keep status alive
```

## Talk to others

```bash
$PY $BUS send $ME other-agent-id "hey, you editing template.html?"
$PY $BUS broadcast $ME "pushing to main in 2 min"
```

## Lock files before editing (CRITICAL for shared files)

```bash
$PY $BUS lock $ME audit_dashboard/template.html
# ... edit + commit ...
$PY $BUS unlock audit_dashboard/template.html
```

If lock fails, check who holds it and send them a message.

## Must-lock files
- `audit_dashboard/template.html`
- `updates/index.html`
- `.mcp.json`, `CLAUDE.md`, `AGENTS.md`
- `.github/workflows/*`
- `alpha_engine/data/*.json`

## Pre-push hook (enforces locks automatically)

Install once per clone:
```bash
git config core.hooksPath .githooks
# also set a stable agent id so your own locks don't block you:
export AGENT_ID="your-agent-id"   # e.g. claude-opus-scoring
```

The hook (`.githooks/pre-push`):
- Before each push, checks `lock:file:<path>` in Redis for every file in your outgoing commits
- **Blocks** if another agent holds a lock; shows who holds it + TTL
- **Passes** if no conflict, or if you hold the lock yourself (AGENT_ID match)
- **Passes silently** if Redis is unreachable (non-blocking for offline work)
- Bypass with `BUS_HOOK_SKIP=1 git push` when needed

Example conflict:
```
=============================================================
  REDIS BUS LOCK CONFLICT — push blocked
=============================================================
  You (my-agent) are trying to push files locked by other agents:

  audit_dashboard/template.html -> held by other-agent (TTL: 142s)

  Options:
    1. Wait for the lock to expire or be released
    2. DM the lock holder via Redis bus
    3. Bypass with BUS_HOOK_SKIP=1 git push (use responsibly)
=============================================================
```

## Full reference

See [AGENT_BUS.md](./AGENT_BUS.md) for raw redis-cli commands, topology, troubleshooting.

## Redis details
- Running on `localhost:6379` (auto-starts on login)
- Binary: `C:/Users/zerou/redis-bus/redis-server.exe`
- Health check: `$PY $BUS ping` → PONG
