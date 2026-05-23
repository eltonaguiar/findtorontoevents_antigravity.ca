### Redis bus — instructions for agents

**What it is:** Local Redis at `localhost:6379` used so multiple AIs/agents coordinate (presence, DMs, broadcasts, file locks). It is **not** a substitute for git; use it for visibility and conflict avoidance.

**Prerequisites:** Redis must be running (`redis-cli -p 6379 ping` → `PONG`). This repo’s docs assume Windows paths like `C:/Users/zerou/redis-bus/` for `redis-server.exe`, `redis-cli.exe`, and `agent_bus.py` — **replace with the human’s actual paths** if different.

**Easiest interface (recommended):** Python helper `agent_bus.py` (no extra Python deps; shells out to `redis-cli`):

```bash
PY="<path-to-python.exe>"
BUS="<path-to-redis-bus>/agent_bus.py"
ME="<unique-agent-id>"   # e.g. cursor-audit-foo, claude-scoring-1 — must not collide

$PY $BUS ping
$PY $BUS announce $ME "one-line: what I'm doing" --tool <tool-name>
$PY $BUS peers
$PY $BUS inbox $ME
$PY $BUS log
```

**Every few turns:** `$PY $BUS inbox $ME` and optionally `$PY $BUS refresh $ME`.

**Talk to others:**
`$PY $BUS send $ME <other-id> "message"`
`$PY $BUS broadcast $ME "short announcement"`

**File locks (required before editing hot shared files):**
`$PY $BUS lock $ME <repo-relative-path>` → edit → commit → `$PY $BUS unlock <path>`
Must‑lock examples in‑repo: `audit_dashboard/template.html`, `updates/index.html`, `.github/workflows/*`, `alpha_engine/data/*.json`, plus `AGENTS.md` / `CLAUDE.md` / `.mcp.json` per `BUS_QUICKSTART.md`.

**Structured fleet messages:** For JSON envelopes (topic, summary, doc paths), follow `docs/REDIS_BUS_SCHEMA.md` and use the repo’s `tools/bus_post_*.py` or `tools/redis_bus_tick.py` patterns. After publishing audit‑style updates, append **`docs/REDIS_BUS_CHANGELOG.md`** when that’s the team convention.

**Agent ID etiquette:** Pick a stable, unique id; see prefix hints in `docs/AGENT_BUS_AGENTS.md`. Don’t reuse another agent’s id.

**Deep references in this repo:** `BUS_QUICKSTART.md`, `AGENT_BUS.md`, `REDIS_BUS_QUICKREF.md`, `REDIS_BUS_MESSAGES.md`, `docs/REDIS_BUS_SCHEMA.md`, `docs/REDIS_BUS_CHANGELOG.md`.

**One sentence version:** *“Use `agent_bus.py` to announce, poll `inbox`, lock shared paths before editing, broadcast coordination notes; structured posts follow `docs/REDIS_BUS_SCHEMA.md` and the changelog when applicable.”*