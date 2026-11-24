# 2026-11-16 — Prediction markets: no synthetic stats, contracts settle on outcome

**Scope.** Two related fixes for Kalshi/Polymarket handling on /audit.

## 1. `stamp_pick_quality.py` no longer fabricates PM forward stats

**Broken.** When a prediction-market source had no closed picks, the stamper
substituted `n >= 5` and `wr >= 50%` (`consensus_trades` / `consensus_wr`,
defaults 10 / 0.55) so the pick could clear Gate 4. Those numbers were never
measured, yet they fed `trust_tier`, `hf_quality_score` and Smart Picks.

**Changed.** The override is deleted. An empty ledger stays `n=0`, which yields
`trust_tier=UNKNOWN`, and the pick is tagged `pm_stats_source=insufficient_ledger`
/ `pm_stats_fabricated=false` so the coverage gap is visible in the payload.

**Verified.** Running the real stamper on a synthetic `polymarket_signals` pick:

```
strat_fwd_trades: 0   trust_tier: UNKNOWN
pm_stats_source: insufficient_ledger   pm_stats_fabricated: False
```

## 2. Binary contracts resolve on outcome, not on price geometry

**Broken.** The resolver treated every pick as a spot trade: it fetched a
"current price", synthesized a 2.5%/1.5% TP/SL pair for PM picks with no entry,
and closed them on price movement. A contract settles at 1.0 (side wins) or 0.0
— price-based P&L on one cannot exist.

**Changed.**
* New `audit_trail/pm_contract_resolver.py`:
  * `is_contract_pick()` = market id **and** a side, or
    `asset_class=PREDICTION_MARKET`. PM-sourced **spot** trades are classified
    `spot_derived` and stay on the price path.
  * `resolve_contract_pick()` settles from the market outcome with
    `pnl_pct = (payout - entry) / entry * 100` (`+233.33%` for 0.30 → YES win,
    `-100%` for a loss), leaves live markets OPEN, and expires a market that
    passed its deadline without an outcome as `EXPIRED` with `pnl_pct=None` —
    never a fabricated zero.
  * `load_market_outcomes()` indexes settled records from local feeds
    (`data/pm_market_outcomes.json`, the RE'd signal files, and globbed
    `*polymarket*` / `*kalshi*` / `pm_market*` feeds).
* `audit_trail/universal_pick_resolver.py`:
  * contract picks branch off **before** the no-live-price/TIME_EXIT path, so
    they are never price-resolved;
  * `pm_pick_kind` tags PM-sourced spot trades;
  * `TP/SL synthesis` skips contract picks;
  * `market_id` / `contract_side` / `resolution_date` / `pm_resolution_status`
    are preserved through resolution (`_SCORING_FIELDS`).

**Verified.** `py_compile` on all three modules; 25 tests pass, including 12 new
ones (winning/losing payout math, unresolved-expiry with `pnl_pct=None`,
live-market OPEN, side mapping, outcome normalisation, loader indexing);
`audit_trail.universal_pick_resolver` imports with the contract flag on.

## 3. Outcome producer (added in the same change)

Without a producer the resolver's contract branch would only ever expire picks.
`audit_trail/pm_outcome_ingest.py` now builds the feed:

* Polymarket Gamma `GET /markets?closed=true` — winner from `outcomes` +
  `outcomePrices` (settled prices are 1.0 / 0.0).
* Kalshi Trade API `GET /markets?status=settled` — winner from `result`.
* Merges with the existing `data/pm_market_outcomes.json` (never drops known
  outcomes) and writes atomically via `os.replace`.
* Fail-open per source: a feed error is reported, the dashboard still builds,
  and contract picks stay unresolved instead of being invented.
* CLI: `python -m audit_trail.pm_outcome_ingest [--local-only] [--out PATH]`.

Wired into `.github/workflows/audit-dashboard.yml` immediately **before** the
"Resolve active picks" step, so the resolver sees outcomes from the same run.

**Verified.** 7 offline tests (`tests/test_pm_outcome_ingest.py`) cover settled
price parsing, unsettled rejection, Kalshi `result`, merge-with-existing,
fail-open on a 429, `--local-only` (no fetch), and the full chain:
ingest → `load_market_outcomes` → `resolve_contract_pick` settles a 0.30 YES
contract at `+233.33%`. `--local-only` CLI smoke writes a valid empty feed when
no local outcomes exist.

## Remaining limitation

The producer needs network egress from CI (it is fail-open if absent), and it
only settles markets that are already closed at ingest time — a market that
settles later is picked up on the next run because the file is merged, not
replaced. None of the 27 live PM rows are contracts; all are `spot_derived`,
so live settlement volume will start only when the emitters pass `market_id` +
`contract_side` through to the pick.
