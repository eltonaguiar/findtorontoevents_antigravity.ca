# P1-F Goldmine Stocks — Full Kill Closure
**Date:** 2026-05-07
**Status:** CLOSED ✅ — No source removal needed

## Investigation Summary

`goldmine_stocks` is a composite equity scanner from the Goldmine data pipeline. It was investigated as P1-F in the 2026-05-06 edge action plan audit.

## Findings

### Source Code Location
`goldmine_stocks` is **not a standalone Python module** — it is a string identifier (source_system label) used across 30+ files in the repo. The actual data comes from:
- `data/goldmine/stock_picks.json` — live active picks
- `data/goldmine/closed_trades.json` — historical closed picks
- `data/goldmine/unified_picks.json` — aggregated picks

These JSON files are generated externally (not in this repo) and committed to the repo.

### Kill Layers (All Active — No Source Removal Needed)

**Layer 1 — Quality Gates (audit_trail/quality_gates.py):**
- `BLOCKED_SOURCE_SYSTEMS` includes `goldmine_stocks` — blocks all equity picks from this source
- `BLOCKED_ASSET_STRATEGY_PAIRS` includes `(goldmine_stocks, EQUITY)` — blocks any goldmine pick on equities
- Comment: `0% WR (0W/5L), -22.3% PnL — zero wins ever`

**Layer 2 — Strategy Blocklist (alpha_engine/strategy_blocklist.py):**
- `RETIRED_COMPOSITE_PAIRS` includes 3 pairs:
  - `(goldmine_stocks, goldmine_5x_consensus)`
  - `(goldmine_stocks, goldmine_6x_consensus)`
  - `(goldmine_stocks, goldmine_7x_consensus)`
- Default: **hot** (kills active). Rollback: set `GOLDMINE_STOCKS_KILL_DISABLED=1`
- `WEAK_SOURCES` in ml_gatekeeper/gatekeeper.py includes `goldmine_stocks` → -2 downweight

**Layer 3 — Scanner Blocklist (alpha_engine/production_scanner.py):**
- Explicit equity goldmine composite kills:
  - `(equity, goldmine_1x_consensus)`
  - `(equity, goldmine_2x_consensus)`
  - `(equity, goldmine_3x_consensus)`
  - `(equity, goldmine_4x_consensus)`

### Current State
- **Active picks from goldmine_stocks:** 0 (confirmed by active_picks.json scan)
- **Closed picks from goldmine_stocks:** present in closed_picks.json (historical)
- **Source JSON files:** `data/goldmine/*.json` exist and are git-tracked — these are data, not code
- **Unit tests:** `tests/test_strategy_blocklist_goldmine_stocks.py` pins the kill logic

## Conclusion

**No source code removal needed.** `goldmine_stocks` is a data source label, not executable code. The three independent kill layers ensure no new picks from this source can enter the pipeline. The existing tests guard against regression.

**Closure:** P1-F is closed. The strategy is comprehensively dead across all asset classes.