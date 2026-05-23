# 2026-05-16 — Grok OOM Killer + Broken MCP Config Fix

## What Was Broken

### Primary Cause: OOM Killer (Confirmed via syslog + Hermes agent)
Grok TUI processes were repeatedly terminated by the Linux OOM killer on the 16 GB WSL instance:
- Multiple PIDs (3154, 426, 431, 795, etc.) killed when RSS reached 14.6–14.9 GB.
- Current running instance sits at ~3.7 GB but spikes during "extensive workspace exploration" sessions (large context + repeated `read_file`/`grep`/`list_dir` on the 20k-file crypto trading repo + 18 MB dashboard JSONs + strategy files).
- No swap pressure (swap at 0 B). WSL itself was healthy; Grok simply outgrew the 16 GB limit during deep analysis sessions (e.g. session 019e3318 cloud-agent crypto edge review).

### Secondary Issue: Project `.mcp.json` Path Corruption
The repo root `.mcp.json` (and copies in worktrees + `.cursor/mcp.json`) contained raw Windows drive-letter paths:
- `claude-peers`: `bun C:/Users/zerou/claude-peers-mcp/server.ts` (server source does not exist on disk)
- `tradingview-desktop`: `node E:/findtorontoevents_antigravity.ca/node_modules/...` (old E: drive location of the repo)
- `tradingview-analysis`: `uv run` with `cwd: E:/...`

When Grok (WSL) loaded these while CWD = `/mnt/c/findtorontoevents_antigravity.ca`, child processes received mangled paths such as:
`/mnt/c/findtorontoevents_antigravity.ca/E:/findtorontoevents_antigravity.ca/node_modules/tradingview-mcp/src/server.js`

Result: immediate `MODULE_NOT_FOUND` in `~/.grok/logs/mcp/tradingview-desktop.stderr.log`, plus noisy failures for the other two. This wasted process table entries and contributed to instability during MCP-heavy sessions. Only `redis-bus` was actually starting.

These three MCPs were exactly the ones the system banner listed as "failed to connect" at the start of the session.

## Changes Made

### 1. Optimized `~/.grok/config.toml` (Memory Hardening + Proper MCP Registration)
- `auto_compact_threshold_percent = 65` (was default ~85) — forces earlier context compaction to keep RAM well below the 14+ GB danger zone during long repo explorations.
- `codebase_indexing = false` — disabled global indexing (graphify on this repo size is a known heavy RAM consumer; use `/graphify-map` or the skill on-demand instead).
- `toolset.bash.output_byte_limit = 32768` (was 65536) + added `[toolset.read_file] max_bytes = 524288` — prevents single tool calls from pulling multi-MB outputs (dashboard JSON, logs, scanner results) into memory.
- `permission_mode = "ask"` (was "always-approve") — adds a human gate on heavy tool sequences that were previously running away and ballooning RSS.
- Registered the two working MCPs properly under `[mcp_servers.*]` using **absolute WSL paths** (the canonical location per Grok docs). This is the supported way; project `.mcp.json` is now only a fallback for other tools.
- Added `[memory.*]` sections with safe defaults (enabled + save_on_end + watcher + initial_injection).

### 2. Cleaned Project MCP Config Files
- `/mnt/c/findtorontoevents_antigravity.ca/.mcp.json` — removed the two non-functional servers; kept only `redis-bus` + `tradingview-desktop` with correct absolute WSL path to the vendored package in `node_modules/tradingview-mcp/src/server.js`.
- Same treatment for `.cursor/mcp.json` (for Cursor IDE consistency) and the active worktree copy (`~/.grok/worktrees/.../2026-05-16-ca221d29/.mcp.json`) so the current running session benefits immediately.
- `claude-peers` and `tradingview-analysis` can be re-added later only after the actual server code is restored with a correct WSL path.

## Verification
- `node --check .../tradingview-mcp/src/server.js` → Syntax OK.
- Quick launch test of the MCP server exited cleanly (as expected for a stdio server waiting on parent).
- New `~/.grok/config.toml` parses as valid TOML.
- After restart, `grok mcp list` should show the two registered servers without the previous MODULE_NOT_FOUND spam in `~/.grok/logs/mcp/*.stderr.log`.
- Future sessions in this repo (or its worktrees) will no longer inherit the broken E:/ C:/ paths.

## Follow-up Recommendations (Outside This PR)
- On the Windows host, create/update `%USERPROFILE%\.wslconfig` to raise `memory=24GB` (or higher) if the physical machine has 32 GB+ RAM. This is the long-term fix for 16 GB WSL pressure.
- When doing very heavy sessions (multi-hour swarm + large file audits), manually watch `free -h` or use the `/memory` commands to compact early.
- The `large-repo-read` and `large-repo-git` skills already exist precisely to avoid these OOM patterns — the config changes above make the agent more likely to stay in the safe zone even if it temporarily ignores them.

## Files Changed
- `~/.grok/config.toml` (primary Grok config — memory + MCP)
- `/mnt/c/findtorontoevents_antigravity.ca/.mcp.json`
- `/mnt/c/findtorontoevents_antigravity.ca/.cursor/mcp.json`
- `~/.grok/worktrees/c-findtorontoevents-antigravityca/2026-05-16-ca221d29/.mcp.json` (ephemeral worktree copy)

This change set contains only fixes by the current agent. No other authors' work was included.

References:
- Hermes agent diagnosis (syslog OOM events 6:14 AM, 6:18 AM, 7:35 PM).
- `~/.grok/logs/mcp/tradingview-desktop.stderr.log` (mangled path).
- AGENTS.md / Claude.md Goal #1 (phenomenal /audit performance requires stable long-running Grok sessions on this exact repo).
- Grok user-guide/05-configuration.md and 07-mcp-servers.md (canonical MCP + memory sections).