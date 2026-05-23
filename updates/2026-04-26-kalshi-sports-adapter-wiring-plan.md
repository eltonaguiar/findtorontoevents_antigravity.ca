# Kalshi sports-markets adapter — wiring plan

**Branch:** `feat/kalshi-sports-adapter`
**Date:** 2026-04-26
**Status:** opt-in sidecar (Phase 1). Phase 2 wires into production.

## Why this exists

The sports-betting pipeline (`live-monitor/api/sports_*.php`) already
plumbs in Polymarket prediction-market signals via
`tools/polymarket_edge_scan.py` and the manual-picks verifier. The
verifier's first-run report flagged most curated UFC / Tennis / Golf picks
as `no_polymarket_match` — Polymarket simply does not list per-event h2h
contracts for these sports at the cadence we need.

Kalshi (CFTC-regulated) does. UFC / NBA / Tennis / Golf all have
per-event series tickers (`KXUFC`, `KXNBA`, `KXATPMATCH`, `KXPGA`, etc.)
with continuously priced YES/NO contracts. Pulling those gives our
verifier real crowd-priced reference points for the picks Polymarket
can't see.

## What's in this PR (Phase 1, opt-in sidecar)

1. `tools/kalshi_sports_fetch.py` — stdlib-only adapter for the public
   Kalshi API.
   * Snapshots open markets per sport to `data/kalshi_snapshots/<UTC>.json`.
   * `--sport ufc|nba|tennis|golf|nfl|nhl|mlb|soccer|all`
   * `--list-series` discovers the live sports catalog.
2. `tools/verify_kalshi_picks.py` — mirror of the Polymarket verifier.
   * Reads picks from `data/goldmine/sports_picks.json` (or HTML
     `ufcPicksData/tennisPicksData/golfPicksData` arrays if present).
   * Cross-checks each curated UFC / Tennis / Golf / NBA pick against
     the closest matching Kalshi market.
   * Writes
     `reports/MANUAL_SPORTS_PICKS_VERIFICATION_KALSHI_<UTC>.md` (+ `.json`).
3. First-run report committed alongside the code.

**Production behavior is unchanged.** No `sports_*.php` file is
modified. No data-flow into `lm_sports_value_bets`,
`lm_sports_daily_picks`, `calculate_smart_score`, `passes_active_gate`,
or any scorer / pick-generator is added.

## API surface — measured 2026-04-26

| Host | Auth required? | Verdict |
|---|---|---|
| `https://trading-api.kalshi.com/trade-api/v2/...`   | YES (every endpoint returns 401) | unusable for sidecar |
| `https://api.elections.kalshi.com/trade-api/v2/...` | NO for `/markets` and `/series?category=Sports` | ✅ used |

The elections host is the unified exchange feed Kalshi exposes for
unauthenticated discovery. It returns the full market object (`yes_bid`,
`yes_ask`, `no_bid`, `no_ask`, `volume`, `close_time`, etc.) for any
series.

If Kalshi later locks down the elections host as well, the operator
must capture an API key (`KALSHI_API_KEY_ID` + `KALSHI_API_PRIVATE_KEY_PEM`)
and the adapter will need RSA-PSS request signing added. Until then,
**no auth required**.

### Series catalog gaps

The `KXUFC` series returned **zero open markets** at probe time —
no upcoming UFC card had open contracts at 2026-04-26 02:50 UTC.
This is expected (UFC cards are weekly; Kalshi posts contracts a few
days out). The endpoint shape is correct; markets will appear ahead
of the next card. The verifier handles empty snapshots gracefully.

`KXATPMATCH` (tennis) and `KXNBA` returned live markets.

## Phase 2 — production wiring (NOT in this PR)

Target caller: `live-monitor/api/sports_picks.php`, alongside the existing
`sports_pm_load_signals()` / `sports_pm_best_match()` Polymarket helpers.

Plan:
1. Add `sports_kalshi_load_signals()` reading the most recent
   `data/kalshi_snapshots/*.json` (mirror of `sports_pm_load_signals`).
2. Add `sports_kalshi_best_match($signals, $home, $away, $market)` that
   returns the matched ticker + mid-price.
3. Augment `sports_pm_matched_count` summary with a parallel
   `sports_kalshi_matched_count` so the dashboard exposes coverage.
4. Wire into the value-bet ranker only after we measure that the
   Kalshi mid materially de-biases the ranker on the picks Polymarket
   can't see (the verifier reports in this branch are the
   measurement).

**Self-deletion target:** if Phase 2 is not landed by **2026-06-15**, this
sidecar is removed in the same PR that deletes `tools/kalshi_sports_fetch.py`,
`tools/verify_kalshi_picks.py`, and `data/kalshi_snapshots/`. The wiring
plan is the contract; no orphan modules.

## CLAUDE.md Wire-Up Rule compliance

Per `CLAUDE.md` § "Wire-Up Rule":

> Opt-in sidecar: PR title/body explicitly says "opt-in" or "sidecar",
> the module does not change production behavior, AND the PR body
> contains a `## Wiring Plan` section naming the target caller file +
> function + expected PR/date for the wire-up.

PR title says "opt-in sidecar". This document names the target caller
(`live-monitor/api/sports_picks.php`), the new functions
(`sports_kalshi_load_signals`, `sports_kalshi_best_match`), and the
deadline (2026-06-15).
