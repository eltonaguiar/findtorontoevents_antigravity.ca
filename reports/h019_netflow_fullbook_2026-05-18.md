# H-019 / C-2 FULL-BOOK — Exchange Net-Flow Cross-Sectional FULL-BOOK — Research Backtest

**Date:** 2026-05-18  
**Hypothesis:** H-019 (`c2_fullbook` in `reports/hypothesis_registry.json`)  
**Module:** `tools/h019_netflow_fullbook.py` (OPT-IN RESEARCH SIDECAR — no production caller)  
**Data source:** free Dune Analytics `cex.flows` Spellbook table — RE-USES the cached H-018 raw result (`tools/cache/h018_dune_netflow_cache.json`, 8550 rows, 0 extra Dune credits).  
**Harness:** `tools/edge_stability_harness.py` imported UNMODIFIED (EFF_MIN=0.3, MIN_WINDOW_N=80, MIN_STABLE_WINDOWS=3).

## VERDICT: REJECTED

REJECTED — strong in 12 windows but signs split (11+/1-); needs 3 same-sign

## Why H-019 (vs H-018)

H-018's registered LONG-2/SHORT-2 daily-rebalanced spec emits exactly 4 leg-coin records per traded day; its densest 14-day window held only 56 records — below the harness 80-record floor — so 0 windows scored and H-018 came back UNTESTED. H-019 keeps the SAME economic prior (exchange-netflow cross-sectional signal) but uses the legitimate continuous-position FULL-BOOK resolution already proven on H-008 (BOND, 57k records) and H-014 (onchain): EVERY EVM coin on EVERY day is one resolved record, position-weighted by its cross-sectional netflow_z rank. This does NOT lower any harness threshold — it uses the FULL signal instead of only the 4 extreme legs. Registered explicitly as a new hypothesis per M-107.

## Construction

Per coin, `netflow_z` = strictly-past 30-day z-score of daily (exchange inflow - outflow) from Dune `cex.flows`. On each signal day D, ALL coins with a `netflow_z` are ranked cross-sectionally; each gets a linear rank weight in [-1, +1] (top outflow = +1 LONG, top inflow = -1 SHORT, linear between), demeaned so the book is market-neutral. Entry D+1 close, exit D+2 close, 1-day hold, continuous daily rebalance. Beta removed: each coin's contribution = its return minus the equal-weight mean of the booked coins. `signed_ret = weight * beta_neutral_return`. ONE resolved record per coin per day. Harness score field = `|weight|` (conviction magnitude). `netflow_z` for day D uses only flow strictly before D; entry is D+1 — strictly look-ahead-free.

## Data coverage

- Dune query (cached): `query_id=7528980`, `execution_id=01KRXC9G124M9HQGZHQRJSDTZ0`, from_cache=True, raw rows=8550.
- Coins with usable netflow_z signal: AAVE, ARB, AVAX, BNB, CRV, ETH, LDO, LINK, MATIC, MKR, OP, UNI (12 coins).
- **Coverage caveat:** Dune `cex.flows` is EVM-only — the universe is 12 EVM majors. H-018 spec majors MISSING clean coverage: ADA, BTC, DOGE, LTC, SOL, XRP (notably BTC/SOL/XRP are absent — BTC/SOL need `cex.addresses` native-chain joins; XRP is non-EVM). The cross-sectional universe is necessarily the EVM-traded subset.
- Dune cex.flows history span: 2024-12-18 .. 2026-05-15 (~18 months — free-tier label depth).
- Signal days: 517; traded days: 514.
- Resolved records (coin x day, FULL BOOK): 5409.
- **Price-coverage note:** of the 12 coins with a netflow_z signal, MATIC contributes 0 records — its Binance price series ends 2024-09-09 (MATIC->POL migration / pair delist), so it never has a D+1 entry inside the cex.flows window. MKR is partial (Binance MKRUSDT history shorter). A coin with no price on day D is dropped from that day's book (not a whole-day abort) — the book is whatever coins resolved cleanly, still cross-sectionally demeaned to market-neutral. Effective tradeable universe is ~11 EVM coins.
- Per-14d-window record counts (densest first): [154, 154, 154, 154, 154, 154, 154, 154, 154, 154, 154, 154, 154, 154, 154, 154, 154, 154, 147, 140, 140, 140, 140, 140, 140, 140, 140, 140, 140, 140, 140, 140, 140, 140, 140, 140, 110].
- Windows at the harness floor (>= 80 records): 37 — harness floor is 80 records WITH >=15 winners AND >=15 losers; need 3 scored windows minimum.
- Per-symbol record share: AAVE=514, ARB=514, AVAX=514, BNB=514, CRV=514, ETH=514, LDO=514, LINK=514, MKR=269, OP=514, UNI=514.

## Harness verdict (UNMODIFIED edge_stability_harness)

- Windows scored: 37  
- Windows strong (|eff| >= 0.3): 12 (11+ / 1-)  
- Per-window eff (new->old): [0.0, -0.02, -0.0, 0.162, 0.346, 0.04, 0.111, -0.203, -0.21, -0.222, -0.02, 0.041, 0.23, 0.162, -0.385, -0.061, 0.184, 0.297, 0.21, 0.227, 0.466, 0.272, 0.451, 0.246, 0.373, 0.489, 0.377, 0.345, 0.358, 0.218, 0.49, 0.422, 0.218, 0.402, 0.21, 0.262, -0.027]  
- Same-sign check: sign=`mixed`  
- **is_admissible(): False** — REJECTED — strong in 12 windows but signs split (11+/1-); needs 3 same-sign

## Performance

- Pooled book WR (coin-day records): 48.51%  
- Gross edge: 3.385 bps/coin-trade  
- Net edge after 30.0bps round-trip: -26.615 bps  
- Cost-survival: -786.25% of gross (floor 60%) — FAIL  
- Purged/embargoed walk-forward embargo: 5 days (AFML Ch.7).

> **Caveat:** when the verdict is UNTESTED (data-gap) the pooled numbers are NOT verdict-grade — the harness scored fewer than 3 windows, so in-sample WR / gross-vs-net edge carry no statistical weight. They document what the sample looked like; they are explicitly NOT an edge or no-edge claim.

## Honest next step

Clean harness KILL (#10) — the FULL-BOOK construction scored 37 windows but the eff sign SPLITS across them (no stable same-sign separation). Exchange netflow rank weight does not predict cross-sectional crypto returns stably on this 12-EVM-coin / 18-month sample. Do NOT re-test this construction on this data. A future retry needs a materially different signal (e.g. the registered H-018 SOPR/realized-profit construction via paid Glassnode, an operator paid-data decision).

## JSON summary

```json
{
  "hypothesis": "H-019",
  "strategy": "C-2 exchange net-flow cross-sectional FULL-BOOK",
  "data_source": "Dune Analytics cex.flows (free tier, cached H-018 raw)",
  "verdict": "REJECTED",
  "verdict_reason": "REJECTED \u2014 strong in 12 windows but signs split (11+/1-); needs 3 same-sign",
  "n": 5409,
  "coins_tested": [
    "AAVE",
    "ARB",
    "AVAX",
    "BNB",
    "CRV",
    "ETH",
    "LDO",
    "LINK",
    "MATIC",
    "MKR",
    "OP",
    "UNI"
  ],
  "coins_missing_from_spec": [
    "ADA",
    "BTC",
    "DOGE",
    "LTC",
    "SOL",
    "XRP"
  ],
  "coverage_caveat": "Dune cex.flows is EVM-only; BTC/SOL/XRP absent; universe is 12 EVM majors",
  "windows_scored": 37,
  "windows_strong": 12,
  "per_window_eff": [
    0.0,
    -0.02,
    -0.0,
    0.162,
    0.346,
    0.04,
    0.111,
    -0.203,
    -0.21,
    -0.222,
    -0.02,
    0.041,
    0.23,
    0.162,
    -0.385,
    -0.061,
    0.184,
    0.297,
    0.21,
    0.227,
    0.466,
    0.272,
    0.451,
    0.246,
    0.373,
    0.489,
    0.377,
    0.345,
    0.358,
    0.218,
    0.49,
    0.422,
    0.218,
    0.402,
    0.21,
    0.262,
    -0.027
  ],
  "same_sign": "mixed",
  "is_admissible": false,
  "harness_reason": "REJECTED \u2014 strong in 12 windows but signs split (11+/1-); needs 3 same-sign",
  "pooled_wr": 48.51,
  "gross_edge_bps": 3.385,
  "net_edge_bps": -26.615,
  "cost_survival_pct": -786.25,
  "cost_gate_passes": false,
  "next_step": "Clean harness KILL (#10) \u2014 the FULL-BOOK construction scored 37 windows but the eff sign SPLITS across them (no stable same-sign separation). Exchange netflow rank weight does not predict cross-sectional crypto returns stably on this 12-EVM-coin / 18-month sample. Do NOT re-test this construction on this data. A future retry needs a materially different signal (e.g. the registered H-018 SOPR/realized-profit construction via paid Glassnode, an operator paid-data decision)."
}
```

---
*Research sidecar. No production wiring. Pre-registered per M-107 before backtest logic was written. Harness imported unmodified; EFF_MIN / MIN_WINDOW_N / MIN_STABLE_WINDOWS untouched. FULL-BOOK construction is legitimate density (H-008/H-014 precedent), not p-hacking.*