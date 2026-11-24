# 2026-11-19 — Remove `redis-bus` MCP server (fixes "waiting for redis-bus" hang)

## What was broken

Every MCP-aware client (VS Code Copilot Chat, Cursor, Claude Code) that discovered
this repo's workspace MCP configs sat at **"waiting for redis-bus"** on startup.

Root cause: both `.mcp.json` and `.cursor/mcp.json` declared a `redis-bus` MCP
server that launches `npx -y @modelcontextprotocol/server-redis redis://localhost:6379`.
On machines with no Redis listening on `localhost:6379` (confirmed: connection
refused on this box), the server process starts but never becomes ready, so the
MCP client hangs in the "waiting" state indefinitely.

The `.githooks/pre-push` redis-bus lock check was investigated and ruled out:
it silently exits 0 when Redis is unreachable, and `core.hooksPath` isn't even
pointed at `.githooks/` locally — it was never the blocker.

## What changed

- Removed the `redis-bus` entry from `.mcp.json`
- Removed the `redis-bus` entry from `.cursor/mcp.json`
- `tradingview-desktop` entry left untouched in both files

Machines that actually run the Redis fleet bus can re-add the server in a
**user-level** MCP config (e.g. `~/.cursor/mcp.json` or `~/.copilot/mcp-config.json`)
instead of the shared workspace config, so Redis-less machines don't hang.

## Verification

- `python3 -c "import json; json.load(open('.mcp.json')); json.load(open('.cursor/mcp.json'))"` — both parse clean
- Repo-wide grep confirms no other MCP config declares `redis-bus`
  (remaining hits are `tools/bus_post_*.py` publisher scripts and docs, which
  are optional and connect only when explicitly run)
