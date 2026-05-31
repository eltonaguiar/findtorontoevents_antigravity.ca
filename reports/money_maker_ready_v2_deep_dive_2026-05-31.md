# Money-Maker-Ready v2 — Per-Asset-Class Deep Dive
>
>**Generated:** 2026-05-31  
>**Method:** 10,000-sample Monte Carlo bootstrap on `ejaguiar1_stocks.trading_picks`  
>**Thresholds:** Industry-standard: PF ≥ 1.0, n ≥ 30, WR ≥ 45%, PF 95% CI lower bound ≥ 1.0  
>
>---
>
>## Executive Summary
>
>**0 of 8 asset classes pass at the class level.** However, **5 TIER-1 sub-strategies** exist within CRYPTO and **2 EDGE-tier** in FOREX/COMMODITY. The problem is not the absence of edge — it's that winning strategies are diluted by catastrophic losers sharing the same asset class.
>
>### Key Finding
>
>The per-class aggregates look terrible because **every asset class contains destroyer strategies** that burn capital at 5-20x the rate winners earn it. The fix is **per-strategy allowlisting**, not per-class blanket decisions.
>
>---
>
>## Per-Asset-Class Forward Performance
>
>| Class | n | WR | PF | PF CI Low | Total PnL | Verdict |
>|-------|---|------|------|-----------|-----------|---------|
>| CRYPTO | 3,626 | 48.3% | 0.92 | 0.81 | -942% | DESTROYER |
>| EQUITY | 843 | 29.4% | 0.31 | 0.23 | -809% | DESTROYER |
>| ETF | 488 | 33.6% | 0.39 | 0.31 | -439% | DESTROYER |
>| COMMODITY | 183 | 24.6% | 0.17 | 0.11 | -681% | DESTROYER |
>| FOREX | 2,754 | 46.1% | 0.29 | 0.22 | -1,026% | DESTROYER |
>| FUTURES | 138 | 25.4% | 0.18 | 0.11 | -438% | DESTROYER |
>| MEMECOIN | 374 | 41.4% | 0.55 | 0.39 | -593% | DESTROYER |
>| STOCKS | 103 | 19.4% | 0.11 | 0.06 | -271% | DESTROYER |
>
>---
>
>## Winners Per Asset Class (Monte Carlo Bootstrap)
>
>### CRYPTO — 5 TIER-1 Winners
>
>| Strategy | Dir | n | WR | PF | PF CI Low | Verdict |
>|----------|-----|---|------|------|-----------|---------|
>| mega_mutation | — | 283 | 65.4% | 3.33 | **2.59** | TIER-1 |
>| prediction_market_consensus | SHORT | 44 | 95.5% | 36.81 | **10.40** | TIER-1 |
>| prediction_market_consensus | LONG | 45 | 84.4% | 19.34 | **4.43** | TIER-1 |
>| ml_enhanced_DYDXUSDT | LONG | 34 | 94.1% | 10.36 | **3.16** | TIER-1 |
>| ml_enhanced_RENDERUSDT | LONG | 30 | 83.3% | 6.83 | **2.30** | TIER-1 |
>
>**Note:** `prediction_market_consensus` SHORT (n=44) is BTC/ETH-dominated with small absolute PnLs. `mega_mutation` (n=283) is the broadest and most robust.
>
>### FOREX — 1 EDGE-tier Winner (+ 1 Probation)
>
>| Strategy | Dir | n | WR | PF | PF CI Low | Notes |
>|----------|-----|---|------|------|-----------|-------|
>| ig_contrarian_sentiment | SHORT | 241 | 49.4% | 2.71 | **1.78** | ⚠️ 86.7% from top 3 trades — winsorized |
>| dxy_trend_filter | — | 0 | — | — | — | **Probation** (backtest: 995 trades, PF 1.63) |
>
>**Note:** `cta_cross_asset_tsmom` SHORT is 51% USDJPY (only working pair) — PF 0.44 overall. Non-USDJPY pairs are catastrophic (WR ~20%).
>
>### COMMODITY — All Destroyers
>
>All 4 strategies with n≥20 are DESTROYERS (PF 0.17–0.37). No winners.
>
>### EQUITY — All Destroyers
>
>All 7 strategies with n≥20 are DESTROYERS. Best: `earnings_momentum` LONG (n=35, PF 0.87, CI low 0.42).
>
>### ETF — All Destroyers
>
>All 2 strategies are DESTROYERS. Best: `etf_sector_rotation` (n=112, PF 0.68, CI low 0.43).
>
>### FUTURES — All Destroyers
>
>All 3 strategies are DESTROYERS. Best: `futures_momentum` SHORT (n=32, PF 0.71, CI low 0.18).
>
>---
>
>## Top Destroyers (Capital Burns)
>
>| Strategy | Class | n | WR | PF | Total PnL |
>|----------|-------|---|------|------|-----------|
>| forex_rsi2_mean_reversion | FOREX | 401+345 | 19.7% | 0.24 | -1,200%+ |
>| ensemble | CRYPTO | 73 | 34.2% | 0.32 | -623% |
>| cot_positioning | COMMODITY | 140 | 25.7% | 0.17 | -592% |
>| cta_commodity_momentum_term | COMMODITY | 80 | 31.3% | 0.37 | -315% |
>| cta_cross_asset_tsmom (non-USDJPY) | FOREX | 102 | ~20% | ~0.11 | -104% |
>
>---
>
>## Changes Applied (2026-05-31)
>
>### 1. `dxy_trend_filter` Added to Policy → `alpha_engine/non_crypto_policy.py`
>
>- **Policy entry:** probationary (`allow_without_forward=True`)
>- **Backtest:** 995 trades, 49.25% WR, PF 1.63, Sharpe 6.75, MaxDD -15.13%
>- **Diversification:** 7 pairs (USDCHF, EURUSD, AUDUSD, USDJPY, GBPUSD, NZDUSD, USDCAD)
>- **Forward:** ZERO trades — needs to build record
>- **Thresholds:** min_confidence=0.55, min_rr=1.20, min_elite_score=50, min_forward_wr=0.40
>
>### 2. Monte Carlo Edge Audit Tool → `tools/monte_carlo_edge_audit.py`
>
>- Queries all closed trades from `trading_picks`
>- Groups by (category, strategy, direction) with n ≥ min_n
>- Runs 10,000 bootstrap resamples per group
>- Reports PF 95% CI lower bound and tier classification
>
>---
>
>## Priority Actions (P0 → P3)
>
>### P0 — Immediate
>
>1. **Blacklist `forex_rsi2_mean_reversion` BOTH directions** — single largest capital destroyer (746 trades, PF 0.24/0.66, -1,200%+)
>2. **Hard-disable COMMODITY at emission gate** — all 4 strategies are destroyers, class PF 0.17
>3. **Wire `mega_mutation` as named strategy** — currently NULL-strategy in DB (283 trades, PF 3.33, TIER-1)
>
>### P1 — This Week
>
>4. **Cap `cta_cross_asset_tsmom` FOREX to USDJPY-only SHORT** — non-USDJPY are catastrophic
>5. **Audit `prediction_market_consensus`** — n=44/45 is small, verify Kalshi/Polymarket signal freshness
>6. **Blacklist `cot_positioning` COMMODITY** — PF 0.17 on 140 trades
>
>### P2 — Next Sprint
>
>7. **Let `dxy_trend_filter` accumulate 20+ forward trades** before evaluating gate enforcement
>8. **Investigate EQUITY class from scratch** — all 7 strategies are destroyers, need new edge hypothesis
>
>### P3 — Backlog
>
>9. **ML ensemble single-symbol strats (DYDX, RENDER)** — high PF but single-symbol concentration risk
>10. **ETF class reboot** — etf_sector_rotation is closest to break-even (PF 0.68), needs regime overlay
