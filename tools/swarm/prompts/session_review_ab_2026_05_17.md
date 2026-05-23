# Session AB Review — 2026-05-17

## Context
Continuation of autonomous trading-edge improvement session on findtorontoevents.ca/audit.
This session follows Session AA (M-073 btc_hour_filter wiring + banner corrections).

## Deliverables This Session

### 1. new-strategies-scanner GitHub Actions workflow
Created `.github/workflows/new-strategies-scanner.yml`:
- Runs `tools/new_strategies_emitter.py` daily at 10:45 AM ET (14:45 UTC) Mon-Fri
- Uses same rebase-retry commit pattern as etf-bond-scanner.yml
- Generates `alpha_engine/data/scanner_output/new_strategies_picks.json`
- workflow_dispatch with dry_run=true option for testing
- Shadow-mode validation: 14-day observation period before gate promotion (2026-05-31)

The emitter: `tools/new_strategies_emitter.py`
- Fetches OHLCV for 37 symbols (27 equity/ETF + 10 commodity)
- Runs 20 strategies from `alpha_engine/new_equity_commodity_strategies_20.py`
- Applies `passes_active_gate()` — 6 raw -> 4 gated picks (2 rejected)
- JSON pick source already registered in dashboard_generator.py:JSON_PICK_SOURCES

**Review questions:**
- Is 14:45 UTC (10:45 AM ET) the right time? Should it run at a different time for OHLCV data freshness?
- Is the shadow-mode gate (no sizing until 2026-05-31) documented sufficiently in the workflow?
- The emitter runs tools/new_strategies_emitter.py (not as a module) — any import path issues on Ubuntu runners?

### 2. Initial picks file generated
`alpha_engine/data/scanner_output/new_strategies_picks.json` — 4 gated picks:
- low_volatility_factor (EQUITY) — 2 picks
- sector_rotation_etf (ETF) — 1 pick
- 1 commodity pick
Committed to main to bootstrap the JSON pick source.

### 3. Bond scanner ran (background task)
`alpha_engine/data/scanner_output/active_picks_bond.json` — 8 picks:
- bond_yield_momentum: TLT, IEF, TLH (conf~0.58)
- bond_mean_reversion: TLT, IEF (conf~0.68-0.70)
BOND class currently: WR=45%, n=11, NOT_READY (needs n>=100 for T2 cert).
These 8 picks will start the accumulation process.

## Current Actionable Item Status
- Wire btc_hour_filter: DONE (M-073)
- COMMODITY banner: DONE (NOT_READY)
- CRYPTO banner: DONE (MONEY_READY)
- MONEY READY tooltip: DONE
- Wire 20 new equity/commodity strategies: DONE (workflow + initial picks)
- bond_scanner first picks: DONE (8 picks generated)
- FOOLPROOF_ACTION_PLAN remaining open items: mostly blocked on PA console or time-gated

## Still Blocked (PA console / time-gated)
- MySQL ghost-row purge (655k stale rows, target 2026-05-24)
- UEPS_ENABLE_PEAD=1 (PA console)
- COT commercial z-score gate (needs backtest data from DB)
- FRED API key (PA console)
- connors_rsi2_scanner shadow: accumulating (review 2026-06-17)
- Meta-labeler enforcement: accumulating (review 2026-06-16)
- OVERCONFIDENCE_DECAY A/B: 30d of tagged picks needed

## Output Format Required
Provide a JSON assessment:
- verdict: APPROVE, REQUEST_CHANGES, or NEEDS_DISCUSSION
- concerns: list of {severity, area, issue, recommendation}
- action_items: list of {priority, description, file, rationale}
- summary: one paragraph overall assessment
