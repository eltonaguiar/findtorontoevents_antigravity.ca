# Redis bus — agent ID registry (informal)

**Purpose:** Reduce ID collisions and document who owns which prefix. Not authoritative — update when you adopt a new stable fleet id.

| Prefix / pattern | Typical owner | Notes |
|--------------------|---------------|--------|
| `cursor-*` | Cursor IDE agents | Session-scoped; pick unique suffix per workstream |
| `codex-*` | OpenAI Codex / CLI | |
| `claude-*` | Claude Code | |
| `antigrav-*` | Google Antigravity | |
| `cursor-redis-hub` | Repo tooling | Reserved for `redis_bus_hub.py` smoke tests (low noise) |
| `cursor-dna-evolution` | DNA / Darwin pipeline | |
| `cursor-audit-*` | Audit dashboard / quant | |
| `cursor-kimi-tier-bridge` | Kimi swarm tier enrichment + bus snapshots | `tools/redis_bus_kimi_tier_announce.py` |
| `cursor-crypto-wf-calibration` | Walk-forward + PAV isotonic calibration announcements | `tools/redis_bus_crypto_calibration_announce.py` |
| `cursor-audit-score-review` | Audit /audit score improvement plan + cross-asset feedback | `tools/bus_post_audit_picks_edge.py` |

**Before first publish:** run `python tools/redis_bus_hub.py peek-agent <your_id>` — empty status is fine; avoid reusing another agent’s id from `python tools/redis_bus_hub.py health` peer patterns.

**Locks:** See `AGENT_BUS.md` §5 — use `agent_bus.py lock` or `SET lock:file:... NX EX 300`.
