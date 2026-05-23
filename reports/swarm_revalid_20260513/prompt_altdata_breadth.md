# Alt-data edge harvest — rank 14 candidate threads by tractability

## Context

Trading repo seeks hedge-fund-level edge across asset classes. Existing per-class baselines: CRYPTO PF 1.25, FOREX PF 0.27, EQUITY PF 1.58, BOND PF 0.66, FUTURES sub-floor, ETF PF 1.34. Standard signal sources (yfinance, COT, FRED) exhausted. Need NON-OBVIOUS alt-data threads.

## 14 user-proposed alt-data threads

**A. Top criteria per asset class (P/E, EV/EBITDA, on-chain, etc.)** — 20-round deep research
**B. Penny stocks bucketing** — <$6/$3/$2/$1 universe segmentation
**C. Mutual funds (no-load, no-redemption-fee)** — long-horizon buy-and-hold
**D. Options data + put/call ratios + UOA** — flow-leads-price hypothesis
**E. "Secret patterns" — SEC 8-K/13D/G + EDGAR + USPTO + SAM.gov contract awards** — corporate-relationship arbitrage (Samsung-vendor example)
**F. Chinese/Hong Kong markets** — KWEB / HSI / ADR premium-discount stat-arb
**G. Gas-price correlation** — NG/RB → consumer discretionary, refiners
**H. Polymarket prediction data** — election odds → small-cap risk-on; geopolitical events → oil/gold
**I. Weather → farming softs** — NOAA forecasts → ZC/ZW/ZS=F
**J. Mining capex vs minerals** — CAT/Komatsu guidance → copper/iron leading indicator
**K. Weddings vs diamonds** — US marriage rate → SIG; India festival cycle → gold
**L. Other (TSA, container rates, box office, sports betting handle, MTA turnstile, Reddit WSB, Arkham whale labels)** — laundry list

## Question to engines

You are a quant researcher evaluating ALT-DATA edge candidates. Rank threads A-L by **expected risk-adjusted edge per dev-hour** considering:
- Free-tier data accessibility (no Bloomberg/Refinitiv)
- Backtestable horizon ≥10 years
- Economic logic strength (causal, not just correlation)
- Likely Sharpe lift on a TIER-2 candidate strategy

Return strict JSON ONLY:

```json
{
  "ranking": [
    {
      "thread_id": "<A-L>",
      "rank": <1-14>,
      "tractability_score": <0-100>,
      "expected_sharpe_lift": <number>,
      "free_tier_data_path": "<concrete API/feed>",
      "minimum_viable_backtest_spec": "<universe + signal + horizon>",
      "killer_caveat": "<single biggest reason this might fail>",
      "dev_hours_estimate": <integer>
    }
  ],
  "top_3_picks_with_reasoning": [
    {"thread_id": "<X>", "why": "<1-2 sentences>"}
  ],
  "bottom_3_dismissals_with_reasoning": [
    {"thread_id": "<X>", "why": "<1-2 sentences>"}
  ],
  "single_most_surprising_correlation_worth_testing": "<one specific (signal, asset, horizon) tuple, e.g., 'India Diwali calendar vs GLD 60-day return'>"
}
```

## Constraints

- Score on real free-tier data access, NOT theoretical Bloomberg fields
- Reject threads requiring paid market-microstructure feeds
- Reject threads with <5-year usable history
- Must consider survivorship/look-ahead bias risk
