# Protocol Bootstrap Tool — 2026-05-07

## What

`tools/protocol_bootstrap.py` — a self-contained diagnostic + auto-fetch tool for the cross-PC protocol on sparse clones.

## Why

Hermes (laptop, WSL) spent a ~90-minute session figuring out which protocol files were missing from their sparse clone, fetching them one-by-one from raw GitHub URLs, and hitting the `127.0.0.1` gateway trap (talking to local WSL gateway instead of the desktop's swarm gateway at `192.168.2.32:8788`). Same problem occurred independently on desktop (Buffy built it) and laptop (Hermes built it).

The root cause: sparse clones don't include all files, and no self-diagnostic bootstrap step existed in any skill.

## What it does

1. **Auto-detects gateway IP** — `127.0.0.1` on desktop (checks hostname + peer registry ≥9 peers → desktop), `192.168.2.32` on laptop (falls back when localhost has no peers or hostname not in registry)
2. **Detects peer runtime** — `laptop` vs `hermes` vs `cursor` from hostname markers
3. **Checks all 12 required protocol files** — reports exact missing/empty files with sizes
4. **Validates Python imports** — reports `ModuleNotFoundError` details
5. **Auto-fetches missing files** from GitHub raw URLs
6. **Validates each download with `py_compile`** — reverts bad downloads (non-Python or 404 HTML)
7. **Re-runs diagnostic** after fix to confirm green
8. **Exit code 0/1** for scripting

## Usage

```bash
# Diagnostic only (no changes)
python tools/protocol_bootstrap.py

# Auto-fix missing files
python tools/protocol_bootstrap.py --fix

# Override runtime detection
python tools/protocol_bootstrap.py --runtime laptop

# Dry run (show what would be fetched)
python tools/protocol_bootstrap.py --fix --dry-run
```

## Files checked

- `cross_pc_protocol/__init__.py`
- `cross_pc_protocol/client.py`
- `cross_pc_protocol/schema.py`
- `cross_pc_protocol/storage.py`
- `cross_pc_protocol/gateway.py`
- `cross_pc_protocol/reliability.py`
- `cross_pc_protocol/redis_bridge.py`
- `cross_pc_protocol/lan_discovery.py`
- `tools/adapters/cursor_claude_adapter.py`
- `tools/adapters/freebuff_adapter.py`
- `tools/adapters/protocol_inspect.py`
- `tools/protocol_gateway.py`

## Status

- Desktop version: ✅ Built, committed (this entry)
- Laptop version: `c88cea3ebf` (Hermes's independent build — push timed out, not on GitHub)