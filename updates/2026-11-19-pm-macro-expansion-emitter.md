# PM Macro Expansion Emitter — Kalshi + Polymarket binary contracts

**Date:** 2026-11-19
**Status:** shipped (shadow / forward-test only)

## What was broken / missing

`prediction_market_agents/pm_macro_overlay.py` converts prediction-market
probabilities into *spot-derived* FOREX/ETF trades (EURUSD, TLT, …). It also
emits **0 picks** whenever Kalshi and Polymarket disagree on the Fed decision
(today: Kalshi `hike` vs Polymarket `hold`), so macro prediction markets
contributed essentially nothing to `/audit`.

There was no emitter that treats macro PM markets as what they are: **binary
contracts** that settle at 1.0 / 0.0 on the actual outcome.

## What was added

`tools/pm_macro_expansion.py` — stdlib-only emitter that fetches:

- Kalshi series: `KXFEDDECISION`, `KXGDP`, `KXCPI`, `KXDJIA`, `KXNASDAQ100`
- Polymarket `/public-search`: Fed cut/hike, unemployment, GDP, S&P 500,
  Treasury yields

For each source it picks the nearest future-resolving event and emits the
single highest-probability leg (≥65%) as an **outcome-resolvable contract pick**:

- `asset_class = "PREDICTION_MARKET"`, `platform`, `market_id`,
  `contract_side = "YES"`, `market_title`
- `entry_price` = implied probability (contract cost), `resolution_date`
- `signal_time_utc` / `ingest_time_utc`
- `verification_state = "forward_test_only"`, `bias_controls =
  ["resolve_by_market_outcome", "no_spot_tp_sl"]`, `sizing_allowed = false`,
  `shadow = true`
- **no** take-profit / stop-loss (contracts have none)

Outputs:
- `prediction_market_agents/data/pm_macro_expansion_signals.json` (envelope)
- `alpha_engine/data/pm_macro_expansion_picks.json` (flat mirror)

Live run 2026-11-19 produced 5 picks (e.g. Kalshi GDP 94%, CPI 94%, Fed-hike
92%; Polymarket China GDP 97.2%, 30y Treasury 66%).

## Wiring

- `audit_trail/pm_contract_resolver.py` — added `pm_macro_expansion` to
  `PM_SYSTEMS`.
- `audit_trail/universal_pick_resolver.py` — added source to `SYSTEM_SOURCES`
  and `_PREDICTION_MARKET_SYSTEMS`; picks route through the contract path
  (`is_contract_pick` → True) and settle on outcome, never price TP/SL.
- `audit_trail/dashboard_generator.py` — added to `JSON_PICK_SOURCES` so cards
  render on `/audit`.
- `.github/workflows/prediction-market-agents.yml` — runs the emitter after the
  orchestrator (non-blocking) and commits the mirror file.

## Verification

- `py_compile` OK for all touched files.
- All 5 emitted picks: `is_contract_pick=True`, `contract_side=YES`.
- Settlement test: outcome YES → WON (+8.70% on a 0.92 entry), NO → LOST
  (−100%), no outcome → OPEN with `pnl_pct=None` (no fabricated 0).
- Both output files parse as strict JSON (no NaN/Infinity).

## Notes / next steps

- Macro contracts are **not** wired into the crypto cross-market consensus:
  that engine only aggregates `*USDT` spot symbols; contract picks belong on
  the resolver/dashboard path instead.
- Outcome feeds (`pm_market_outcomes.json`, `data/kalshi_snapshots/`) are still
  thin, so picks will sit OPEN until settlements land. That is correct
  behaviour — no invented PnL.
- Acceptance (future): require PF≥1.25 and WR≥50% on ≥30 resolved macro
  contracts before any promotion beyond shadow.
