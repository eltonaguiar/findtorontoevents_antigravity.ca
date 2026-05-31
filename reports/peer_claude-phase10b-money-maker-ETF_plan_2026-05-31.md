# Phase 10b — /money-maker-readyv2 plan: ETF class

**Author:** peer_claude (subagent, Opus 4.7)
**Date:** 2026-05-31
**Class:** ETF (categories union: 'etf')

## Plan of attack

1. Pull live ETF cohort from `ejaguiar1_stocks.trading_picks` filtered by `LOWER(category)='etf'`. Aggregate n, WR, PF, avg_pnl, status mix, NULL pnl rate.
2. Per-strategy breakdown (source_system × strategy) sorted by closures.
3. Cross-check vs `audit_dashboard/data/pf_registry.json` (`by_asset_class_policy_clean_net.ETF`) and verify which strategies the registry sees.
4. Cross-check vs MC watchlist from Phase 3 — ETF has NO candidate in Phase 3 MC list (stocks_rsi2_pullback is EQUITY-tagged not ETF; fx_smart_carry_trade_momentum is FOREX). ETF is currently an MC orphan.
5. Audit emission cadence (last 30d) and closure cadence (last 30d).
6. Identify resolver / mis-tagging blockers (Phase 4 finding) specific to ETF.
7. Produce ranked action items naming files + line ranges + configs.

## Data sources used

- DB: `mysql.50webs.com / ejaguiar1_stocks.trading_picks` (live)
- `audit_dashboard/data/pf_registry.json` (committed 2026-05-25)
- `audit_dashboard/data/money_ready_verdict.json` (referenced via incidents feed)
- Phase 3 MC watchlist (PR #179 — no ETF candidate)
- ETF code paths: `alpha_engine/etf_scanner.py`, `alpha_engine/etf_strategies.py`, `alpha_engine/strategies/etf_decay_shorts.py`, `tools/etf_emitter_spike.py`, `tools/etf_sector_emitter.py`, `alpha_engine/config.py:894 (ETF_SYMBOLS)`, `alpha_engine/outcome_resolver.py:2489 (ETF_LEVERAGED_DECAY_FILE)`
