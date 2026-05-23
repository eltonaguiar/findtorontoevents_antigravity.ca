# memory_archive/

Censored, git-versioned snapshots of the two agent memory stores. API keys,
tokens, passwords, and other secret-shaped strings are `[REDACTED]`.

| File | Source | Live location |
|---|---|---|
| `agentmemory_snapshot_2026-05-17.json` | agentmemory semantic store | REST server `localhost:3111` (not git-tracked — ephemeral per machine) |
| `holographic_memory_snapshot_2026-05-17.json` | holographic memory | `agent_shared_memory.json` at repo root (already git-tracked) |

## Why archive

- **agentmemory** runs as a local REST server; its index is per-machine and
  not in git. A snapshot here makes the long-term knowledge recoverable.
- **holographic memory** is already versioned, but a censored point-in-time
  snapshot is kept alongside agentmemory for a single recovery point.

## Censoring

Snapshots are passed through a regex redactor for `sk-…`, `ghp_…`, `xai-…`,
`AKIA…`, `gsk_…`, and `api_key/token/password/secret = …` literals before
being written. The live `agent_shared_memory.json` was scanned 2026-05-17 and
contained **0** secret-pattern hits.

## Refresh

Re-export with the censor pass, then commit. Never commit a raw (uncensored)
dump.
