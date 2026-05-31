# Plan — Wire pf_registry to live trading_picks DB (2026-05-31)

## Task
Phase 4 Layer 2 finding: `tools/build_pf_registry.py` reads JSON-mirror
closed-pick ledgers (`*/data/closed_picks.json`). `n` drifts 20-80% vs the
live `ejaguiar1_stocks.trading_picks` table.

## Steps
1. Locate generator + source-list config.
2. Pull JSON-mirror `n` vs live DB `n` for 5 strategies.
3. Design diff (file:line), risk + downstream impact.
4. Ship docs-only PR. **No code change.**
