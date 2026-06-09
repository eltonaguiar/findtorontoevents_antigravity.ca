---
tags: [reference]
created: 2026-06-06
---

# Banned Sources

The `BANNED_SOURCES` set in `alpha_engine/` is the only active gate for blocking losers.
`negative_knowledge_registry.py` is dead code — do not reference it.

## Currently Banned (as of 2026-06-05)

4 sources added in session 4 (2026-06-05) after PF<1 verified. Exact names in `alpha_engine/` config.

## How to Ban a Source

1. Verify PF<1 with n≥20 clean trades (post-dedup, post-resolver-fix)
2. Follow `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` + `docs/MUTATION_THREE_AXIS_PROTOCOL.md`
3. Export closed CSV → `python tools/mutation_analysis.py`
4. Add to `BANNED_SOURCES`
5. Document in an `incidents/` note

## How NOT to Ban

- Never ban based on fabricated DB stats from subagents — cross-verify with live DB query
- Never ban on n<20 (insufficient sample)
- Never ban a strategy based on asset-class aggregate WR — measure at strategy level

## Related

- [[reference/performance-tiers]]
- [[incidents/resolver-intrabar-blocker]]
