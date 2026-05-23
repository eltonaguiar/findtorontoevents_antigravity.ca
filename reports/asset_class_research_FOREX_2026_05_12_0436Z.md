# Asset-Class Research Swarm - FOREX

**Generated:** 2026-05-12 04:36 UTC
**Live state:** n=1343, WR=45.6%, PF=0.29, status=stressed

## grok-4  (elapsed 22.1s)
- **Diagnosis:** The FOREX trading system is stressed with a critically low profit factor of 0.29 and sub-50% win rate, indicating ineffective signal generation and high risk of capital drawdown.
- **Tier-2 attainability:** 65%
  - candidate: **Interest Rate Differential Carry** (Exploit yield spreads between currencies) - expected PF 1.8, data FRED interest rates, ~12h
  - candidate: **COT Sentiment Reversal** (Adapt CFTC COT data for forex pairs using commercial positioning) - expected PF 1.6, data CME COT reports, ~18h
  - candidate: **Volatility Breakout with ATR** (Enter trades on volatility expansions filtered by economic calendars) - expected PF 1.7, data OANDA economic data, ~10h
  - candidate: **Cross-Asset Correlation Hedge** (Pair forex with correlated commodities via USDA data) - expected PF 1.9, data USDA commodity reports, ~15h
  - external: FRED
  - external: OANDA
  - external: CME
  - external: USDA
  - priority: Validate new strategies with anti_overfit_validator using CPCV and PBO metrics
  - priority: Incorporate per_source_volume_cap to limit exposure on high-volume pairs
  - priority: Run stress tests on historical drawdowns to ensure MDD under 20%
  - kill/rehab: Rehab underperforming momentum strategies by adding COT filters
  - kill/rehab: Kill high-frequency scalping pairs listed in BLACKLISTED_STRATEGIES

## cerebras-qwen-3-235b  (elapsed ?s)
- ERROR: HTTP Error 403: Forbidden

## cerebras-gpt-oss-120b  (elapsed ?s)
- ERROR: HTTP Error 403: Forbidden

## Consensus
- avg Tier-2 attainability: **65.0%** across 1 models