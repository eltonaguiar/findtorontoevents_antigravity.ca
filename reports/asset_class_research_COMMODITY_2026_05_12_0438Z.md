# Asset-Class Research Swarm - COMMODITY

**Generated:** 2026-05-12 04:38 UTC
**Live state:** n=412, WR=66.7%, PF=3.77, status=stable

## grok-4  (elapsed 33.2s)
- **Diagnosis:** The commodity trading system is stable with strong win rate and profit factor but risks maximum drawdown exceeding 20% during volatile market regimes.
- **Tier-2 attainability:** 90%
  - candidate: **Seasonal Ag Cycle Trader** (Crop planting and harvest cycles) - expected PF 2.2, data USDA, ~12h
  - candidate: **Energy Supply Shock Model** (OPEC production changes) - expected PF 1.8, data FRED, ~15h
  - candidate: **Metals Demand Momentum** (Industrial output indicators) - expected PF 2.5, data Quandl, ~10h
  - candidate: **Weather Volatility Hedge** (Climate impact on soft commodities) - expected PF 1.9, data CME, ~18h
  - external: USDA crop yield reports
  - external: FRED commodity price indices
  - external: Quandl global trade data
  - priority: Run CPCV anti-overfit validation on new candidates
  - priority: Incorporate per-source volume caps for risk management
  - priority: Enhance COT signals with USDA data integration
  - kill/rehab: Rehab underperforming livestock strategies with weather factors
  - kill/rehab: Kill obsolete precious metals mean-reversion models

## cerebras-qwen-3-235b  (elapsed ?s)
- ERROR: HTTP Error 403: Forbidden

## cerebras-gpt-oss-120b  (elapsed ?s)
- ERROR: HTTP Error 403: Forbidden

## Consensus
- avg Tier-2 attainability: **90.0%** across 1 models