# M-053: 4-AI Statistical Validation of Dashboard Performance Numbers

## Task

Read the performance data below (extracted from `audit_dashboard/data/dashboard_data.json` at 2026-05-17T06:19Z) and independently verify / challenge each asset class number.

## Raw Numbers to Validate

| Asset Class | n | WR% | PF |
|-------------|---|-----|----|
| COMMODITY | 228 | 85.5% | 7.71 |
| ETF | 75 | 66.7% | 2.25 |
| EQUITY | 393 | 53.2% | 1.65 |
| BOND | 11 | 54.5% | 0.66 |
| CRYPTO | 7748 | 47.2% | 1.33 |
| FOREX | 251 | 57.8% | 0.85 |
| FUTURES | 2 | 100.0% | N/A |

## Context

- COMMODITY recently had matrix gates applied: cta_replicator NG=F (0% WR, n=24) and CL=F (19% WR, n=47) were blocked. This explains some improvement, but **WR=85.5% and PF=7.71 is suspicious for 228 picks** — either the gate changes dramatically cleaned up the cohort, or there is a data artifact.
- FOREX had 9 JPY-crosses and metals blocked from multi_asset_copytrader. WR improved from ~46% to 57.8%, but PF=0.85 is still below T2 floor.
- CRYPTO: PF=1.33 is sub-T2. The matrix gates for quan_engine (LTCUSDT 23.6% WR, RENDERUSDT 30.8% WR) were added but not yet reflected in resolved picks.
- EQUITY: PF=1.65 / WR=53.2% is near T2 (need PF≥1.5 + WR≥50%).
- BOND: n=11, PF=0.66 — insufficient n and below-floor PF. Not tradeable.

## Performance Charter Tiers (docs/PERFORMANCE_CHARTER.md)

- **T1 (Renaissance target)**: PF>2.0, WR>55%, MDD<10%
- **T2 (Institutional floor)**: PF>1.5, WR>50%, MDD<20%
- **T3 (Watchlist)**: PF>1.2, WR>45%, MDD<30%
- **Below T3**: investigate or kill

## Validation Questions

For each asset class:
1. Does the WR/PF make sense given the strategy profile and recent gate changes?
2. Is there a plausible explanation for outlier numbers (COMMODITY WR=85.5%)?
3. What tier does each class currently occupy?
4. What is the single highest-value next action per class?

## Specific Anomalies to Investigate

1. **COMMODITY WR=85.5% / PF=7.71**: Is this real or a data artifact? What would explain 85.5% WR on 228 resolved picks? Could this be post-gate cleanup showing only the "winners" because the "losers" were blocked before resolving? Or is this the real cleaned-up performance?

2. **FOREX WR=57.8% but PF=0.85**: How can WR be 57.8% (above floor) but PF be below 1? This implies wins are smaller than losses on average — a sizing/TP:SL imbalance. Is this from a few large losers pulling down the PF?

3. **CRYPTO PF=1.33 / WR=47.2%**: Below T2 on both metrics. The quan_engine drag (LTCUSDT 23.6%, RENDERUSDT 30.8%) was blocked but not yet in resolved data. What's the expected trajectory?

## Format

Respond in JSON:
```json
{
  "commodity_verdict": "PLAUSIBLE | SUSPICIOUS | DATA_ARTIFACT",
  "commodity_explanation": "one sentence",
  "forex_wr_pf_paradox": "one sentence explaining WR>50% but PF<1",
  "crypto_trajectory": "IMPROVING | STABLE | DECLINING",
  "class_tiers": {
    "COMMODITY": "T1 | T2 | T3 | BELOW_T3",
    "ETF": "T1 | T2 | T3 | BELOW_T3",
    "EQUITY": "T1 | T2 | T3 | BELOW_T3",
    "BOND": "T1 | T2 | T3 | BELOW_T3",
    "CRYPTO": "T1 | T2 | T3 | BELOW_T3",
    "FOREX": "T1 | T2 | T3 | BELOW_T3"
  },
  "top_priority_per_class": {
    "COMMODITY": "next action",
    "EQUITY": "next action",
    "CRYPTO": "next action",
    "FOREX": "next action"
  },
  "stat_divergence_flags": ["any number that looks wrong"],
  "summary": "one paragraph"
}
```
