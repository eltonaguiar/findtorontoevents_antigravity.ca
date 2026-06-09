---
tags: [incident]
created: 2026-06-06
severity: P1
status: open
---

# Incident: AI Tournament WR Artifact

## Summary

The `/audit` tournament shows 73-91% WR across models — this is a **single-snapshot resolver artifact**, not real edge.

## Root Cause

Resolver uses `NOW()` for `closed_at` backfill. All picks resolved in a single batch snapshot from a single price point → artificially high WR because TP conditions are evaluated at a single favorable timestamp, not at actual execution time.

## Impact

- 15 affected portfolios
- Live `/audit/ai-tournament.html` shows inflated WR figures
- Users/agents may size up based on false numbers

## Fix Applied (partial)

- PR #500: added banner + drill-down links flagging the artifact
- Full fix: intrabar OHLC replay (same blocker as [[incidents/resolver-intrabar-blocker]])

## Status

Open — banner deployed, root cause not fixed until intrabar resolver ships.

## Related

- [[incidents/resolver-intrabar-blocker]]
- [[reference/performance-tiers]]
