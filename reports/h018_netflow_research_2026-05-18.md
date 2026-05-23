# H-018 / C-2 — Exchange Net-Flow Cross-Sectional Spread — Research Backtest

**Date:** 2026-05-18  
**Hypothesis:** H-018 (`c2_exchange_flow_spread` in `reports/hypothesis_registry.json`)  
**Module:** `tools/h018_netflow_research.py` (OPT-IN RESEARCH SIDECAR — no production caller)  
**Data source:** free Dune Analytics `cex.flows` Spellbook table (2,500 credits/mo free tier).  
**Harness:** `tools/edge_stability_harness.py` imported UNMODIFIED (EFF_MIN=0.3, MIN_WINDOW_N=80, MIN_STABLE_WINDOWS=3).

## VERDICT: UNTESTED-data-gap

only 0 window(s) reached the harness's >= 80-record / >=15-winner / >=15-loser floor (need >= 3). The H-018 daily-rebalanced LONG-2/SHORT-2 spread emits exactly 4 leg-coin records per traded day; across 293 traded days the densest 14-day window holds only 56 records (0 windows >= 80). This is a structural density gap, not a signal verdict.

## Construction

Per coin, `netflow_z` = strictly-past 30-day z-score of daily (exchange inflow - outflow) from Dune `cex.flows`. Each day the majors are ranked by `netflow_z`; LONG the 2 lowest (largest OUTFLOW = accumulation), SHORT the 2 highest (largest INFLOW = distribution). Beta removed: each leg-coin's contribution = its return minus the equal-weight mean of the 4 legged coins. Entry D+1, 1-day hold, daily rebalance. One resolved record per leg-coin per day; the harness score field is `|netflow_z|` (conviction magnitude). netflow_z for day D uses only flow strictly before entry — entry is D+1.

## Data coverage

- Dune query: `query_id=7528980`, `execution_id=01KRXC9G124M9HQGZHQRJSDTZ0`, from_cache=True, raw rows=8550.
- Coins with usable netflow_z signal: AAVE, ARB, AVAX, BNB, CRV, ETH, LDO, LINK, MATIC, MKR, OP, UNI (12 coins).
- Coins from the H-018 universe MISSING clean coverage: ADA, BTC, DOGE, LTC, SOL, XRP.
- Dune cex.flows history span: 2024-12-18 .. 2026-05-15 (~18 months — free-tier label depth).
- Signal days: 517; traded days: 293.
- Resolved records (leg-coin x day): 1172.
- Per-14d-window record counts (densest first): [56, 48, 44, 40, 40, 40, 40, 40, 40, 36, 36, 36, 36, 36, 36, 36, 32, 32, 32, 32, 32, 32, 28, 28, 28, 28, 28, 24, 24, 24, 24, 24, 24, 20, 16, 12, 8].
- Windows at the harness floor (>= 80 records): 0 — **harness floor is 80 records WITH >=15 winners AND >=15 losers; need 3 scored windows minimum**.
- Per-symbol record share: AAVE=112, ARB=128, AVAX=122, BNB=67, CRV=122, ETH=143, LDO=117, LINK=105, MKR=62, OP=93, UNI=101.
- Max single-symbol share: 12.2% (cap 25%) — OK.

## Harness verdict (UNMODIFIED edge_stability_harness)

- Windows scored: 0  
- Windows strong (|eff| >= 0.3): 0 (0+ / 0-)  
- Per-window eff (new->old): []  
- Same-sign check: sign=`mixed`  
- **is_admissible(): False** — REJECTED — only 0/0 windows reach eff>=0.3

## Performance (informational — see caveat)

- Pooled spread WR (leg-coin records): 53.33%  
- Gross edge: 14.639 bps/leg-trade  
- Net edge after 30.0bps round-trip: -15.361 bps  
- Cost-survival: -104.93% of gross (floor 60%) — FAIL  
- Purged/embargoed walk-forward embargo: 5 days (AFML Ch.7).

> **Caveat:** when the verdict is UNTESTED (data-gap) these pooled numbers are NOT verdict-grade — the harness scored zero windows, so in-sample WR / gross-vs-net edge carry no statistical weight. They are reported only to document what the thin sample looked like; they are explicitly NOT an edge or no-edge claim.

## Honest next step

UNTESTED — data-gap, explicitly NOT a pass. TWO compounding free-tier gaps:
  (1) COIN COVERAGE — Dune `cex.flows` is EVM-only, so 6 of the 10 H-018 spec majors are absent: ADA, BTC, DOGE, LTC, SOL, XRP. BTC/SOL would need `cex.addresses` joins against native-chain transfer tables; XRP/ADA/DOGE/LTC labels are thin. The 12 EVM coins that DID resolve (AAVE/ARB/AVAX/BNB/CRV/ETH/LDO/LINK/MATIC/MKR/OP/UNI) clear the >= 6-coin floor, so coverage alone is not the blocker.
  (2) WINDOW DENSITY (the binding constraint) — `cex.flows` history begins 2024-11-18 (~18 months), and the H-018 daily-rebalanced LONG-2/SHORT-2 construction emits only 4 leg-coin records per traded day. Across 293 traded days the densest 14-day harness window holds just 56 records — every window is below the harness's >= 80-record / >=15-winner / >=15-loser floor, so ZERO windows score and the harness cannot render an eff-stability verdict.
To make H-018 testable WITHOUT lowering any harness threshold: (a) extend history — `cex.flows` only goes back ~18 months on the free tier, so even a wider universe will not 4x the window density without older labels; (b) the registered H-018 entry actually specifies a SOPR / realized-profit construction via Glassnode realized_profit/realized_loss (Standard tier ~$29/mo, 8-asset coverage) — that is the operator-decision path the registry names; (c) a cross-sectional FULL-BOOK resolution (one record per coin-day, not just the 4 legs) would 3x density but would change the registered LONG-2/SHORT-2 spec and must be re-registered as a new hypothesis. NOT an edge claim either way.

## JSON summary

```json
{
  "hypothesis": "H-018",
  "strategy": "C-2 exchange net-flow cross-sectional spread",
  "data_source": "Dune Analytics cex.flows (free tier)",
  "verdict": "UNTESTED-data-gap",
  "verdict_reason": "only 0 window(s) reached the harness's >= 80-record / >=15-winner / >=15-loser floor (need >= 3). The H-018 daily-rebalanced LONG-2/SHORT-2 spread emits exactly 4 leg-coin records per traded day; across 293 traded days the densest 14-day window holds only 56 records (0 windows >= 80). This is a structural density gap, not a signal verdict.",
  "n": 1172,
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
  "coins_missing_from_universe": [
    "ADA",
    "BTC",
    "DOGE",
    "LTC",
    "SOL",
    "XRP"
  ],
  "windows_scored": 0,
  "windows_strong": 0,
  "per_window_eff": [],
  "same_sign": "mixed",
  "is_admissible": false,
  "harness_reason": "REJECTED \u2014 only 0/0 windows reach eff>=0.3",
  "pooled_wr": 53.33,
  "gross_edge_bps": 14.639,
  "net_edge_bps": -15.361,
  "cost_survival_pct": -104.93,
  "cost_gate_passes": false,
  "max_symbol_share_pct": 12.2,
  "next_step": "UNTESTED \u2014 data-gap, explicitly NOT a pass. TWO compounding free-tier gaps:\n  (1) COIN COVERAGE \u2014 Dune `cex.flows` is EVM-only, so 6 of the 10 H-018 spec majors are absent: ADA, BTC, DOGE, LTC, SOL, XRP. BTC/SOL would need `cex.addresses` joins against native-chain transfer tables; XRP/ADA/DOGE/LTC labels are thin. The 12 EVM coins that DID resolve (AAVE/ARB/AVAX/BNB/CRV/ETH/LDO/LINK/MATIC/MKR/OP/UNI) clear the >= 6-coin floor, so coverage alone is not the blocker.\n  (2) WINDOW DENSITY (the binding constraint) \u2014 `cex.flows` history begins 2024-11-18 (~18 months), and the H-018 daily-rebalanced LONG-2/SHORT-2 construction emits only 4 leg-coin records per traded day. Across 293 traded days the densest 14-day harness window holds just 56 records \u2014 every window is below the harness's >= 80-record / >=15-winner / >=15-loser floor, so ZERO windows score and the harness cannot render an eff-stability verdict.\nTo make H-018 testable WITHOUT lowering any harness threshold: (a) extend history \u2014 `cex.flows` only goes back ~18 months on the free tier, so even a wider universe will not 4x the window density without older labels; (b) the registered H-018 entry actually specifies a SOPR / realized-profit construction via Glassnode realized_profit/realized_loss (Standard tier ~$29/mo, 8-asset coverage) \u2014 that is the operator-decision path the registry names; (c) a cross-sectional FULL-BOOK resolution (one record per coin-day, not just the 4 legs) would 3x density but would change the registered LONG-2/SHORT-2 spec and must be re-registered as a new hypothesis. NOT an edge claim either way."
}
```

---
*Research sidecar. No production wiring. Pre-registered per M-107 before backtest logic was written. Harness imported unmodified; EFF_MIN / MIN_WINDOW_N / MIN_STABLE_WINDOWS untouched.*