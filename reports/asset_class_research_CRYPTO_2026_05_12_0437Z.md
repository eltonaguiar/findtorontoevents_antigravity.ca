# Asset-Class Research Swarm - CRYPTO

**Generated:** 2026-05-12 04:37 UTC
**Live state:** n=7860, WR=47.1%, PF=1.36, status=stable

## grok-4  (elapsed 85.1s)
- **Diagnosis:** The crypto trading system suffers from suboptimal win rate and profit factor due to inadequate incorporation of on-chain metrics and macro correlations in a highly volatile market.
- **Tier-2 attainability:** 75%
  - candidate: **On-Chain Momentum** (MVRV Z-Score for entry signals) - expected PF 1.65, data Glassnode, ~12h
  - candidate: **Funding Rate Arbitrage** (Perpetual futures funding rates) - expected PF 1.55, data Binance, ~8h
  - candidate: **Macro-Crypto Correlation** (USD index correlation with BTC) - expected PF 1.6, data FRED, ~10h
  - candidate: **Volume Breakout** (Abnormal volume spikes with price momentum) - expected PF 1.52, data CoinGecko, ~6h
  - external: Glassnode
  - external: FRED
  - external: Quandl
  - priority: Validate On-Chain Momentum with anti_overfit_validator
  - priority: Optimize position sizing using per_source_volume_cap
  - priority: Run CPCV tests on macro correlations
  - kill/rehab: Kill low-WR altcoin mean-reversion strategies
  - kill/rehab: Rehab BTC trend-following by adding funding rate filters

## cerebras-qwen-3-235b  (elapsed ?s)
- ERROR: HTTP Error 403: Forbidden

## cerebras-gpt-oss-120b  (elapsed ?s)
- ERROR: HTTP Error 403: Forbidden

## Consensus
- avg Tier-2 attainability: **75.0%** across 1 models