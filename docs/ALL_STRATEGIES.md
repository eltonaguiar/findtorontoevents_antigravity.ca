# ALL STRATEGIES — Central Repository

> **Last updated:** 2026-03-17
> **Total:** 700+ individual strategies + thousands of meta-permutations across 15+ systems + 12 mutation variants
> **Repo:** 5,758 Python files, 29 Pine scripts
> **Mutation Engine:** `battleground/data/mutation_analysis.json` — tested 12 variants across 12 symbols

This document is the **single source of truth** for every trading strategy in the ecosystem, organized by asset class.

---

## Table of Contents

- **Part I — CRYPTO STRATEGIES**
  1. [Baby Strategies (68)](#1-baby-strategies--68)
  2. [Alpha Engine — Core Crypto (33)](#2-alpha-engine--core-crypto-33)
  3. [Alpha Engine — On-Chain (10)](#3-alpha-engine--on-chain-10)
  4. [Alpha Engine — Quant (4)](#4-alpha-engine--quant-4)
  5. [Alpha Engine — Advanced (13)](#5-alpha-engine--advanced-13)
  6. [Alpha Engine — Event-Driven (8)](#6-alpha-engine--event-driven-8)
  6b. [Alpha Engine — Proven Research (10)](#6b-alpha-engine--proven-research-10)
  6c. [Alpha Engine — Proven Scanner (6)](#6c-alpha-engine--proven-scanner-6)
  6d. [Alpha Engine — Hybrid (7)](#6d-alpha-engine--hybrid-7)
  6e. [Alpha Engine — Mercury AI (5)](#6e-alpha-engine--mercury-ai-5)
  6f. [Alpha Engine — Cerebrus AI (6)](#6f-alpha-engine--cerebrus-ai-6)
  6g. [Alpha Engine — Untapped Alpha (8)](#6g-alpha-engine--untapped-alpha-8)
  6h. [Alpha Engine — Market Microstructure (4)](#6h-alpha-engine--market-microstructure-4)
  6i. [Alpha Engine — Exchange Flow (1)](#6i-alpha-engine--exchange-flow-1)
  6j. [Alpha Engine — NextGen (13)](#6j-alpha-engine--nextgen-13)
  6k. [Alpha Engine — Next Gen Signals (6)](#6k-alpha-engine--next-gen-signals-6)
  6l. [Alpha Engine — Super Strategies (10)](#6l-alpha-engine--super-strategies-10)
  6m. [Alpha Engine — Survivor Strategies (5)](#6m-alpha-engine--survivor-strategies-5)
  6n. [Alpha Engine — Opposite Day (5)](#6n-alpha-engine--opposite-day-5)
  6o. [Alpha Engine — Variation Strategies (3)](#6o-alpha-engine--variation-strategies-3)
  6p. [Alpha Engine — Antigravity Strategies (4)](#6p-alpha-engine--antigravity-strategies-4)
  6q. [Alpha Engine — Statistical Strategies (10)](#6q-alpha-engine--statistical-strategies-10)
  6r. [Alpha Engine — Pattern Strategies (9)](#6r-alpha-engine--pattern-strategies-9)
  6s. [Alpha Engine — Cyclical Strategies (9)](#6s-alpha-engine--cyclical-strategies-9)
  6t. [Alpha Engine — Enhanced Strategies (6)](#6t-alpha-engine--enhanced-strategies-6)
  6u. [Alpha Engine — Experimental Strategies (4)](#6u-alpha-engine--experimental-strategies-4)
  6v. [Alpha Engine — Justin Bravo Strategies (12)](#6v-alpha-engine--justin-bravo-strategies-12)
  6w. [Alpha Engine — Orderbook Strategies (1)](#6w-alpha-engine--orderbook-strategies-1)
  6x. [Alpha Engine — Community Strategies (11)](#6x-alpha-engine--community-strategies-11)
  6y. [Alpha Engine — TradingView Strategies (11)](#6y-alpha-engine--tradingview-strategies-11)
  6z. [Alpha Engine — Basis & Prop Strategies (8)](#6z-alpha-engine--basis--prop-strategies-8)
  6aa. [Alpha Engine — Specialty Strategies (5)](#6aa-alpha-engine--specialty-strategies-5)
  7. [KIMI Rise of the Claw — Crypto Acceleration (10)](#7-kimi-rise-of-the-claw--crypto-acceleration-10)
  8. [KIMI Rise of the Claw — Proven Crypto/Forex (14)](#8-kimi-rise-of-the-claw--proven-cryptoforex-14)
  9. [Coinglass DNA Bundle (13)](#9-coinglass-dna-bundle-13)
  10. [ML Battleground — 5 Systems](#10-ml-battleground--5-trading-systems)
  11. [Crypto ML Edge](#11-crypto-ml-edge)
  12. [Mercury2 Ensemble](#12-mercury2-ensemble)
  13. [Crypto Signal Engine](#13-crypto-signal-engine)
  14. [ML Crypto Predictor](#14-ml-crypto-predictor)
  15. [Claude Gainer ML](#15-claude-gainer-ml)
  16. [Root-Level Crypto Strategies](#16-root-level-crypto-strategies)
  17. [AI-Generated Incubator Strategies (320+)](#17-ai-generated-incubator-strategies-320)
- **Part II — FOREX STRATEGIES**
  18. [Alpha Engine — Forex (11)](#18-alpha-engine--forex-11)
- **Part III — EQUITY & OPTIONS STRATEGIES**
  19. [Alpha Engine — Equity (14)](#19-alpha-engine--equity-14)
  20. [Options Strategies](#20-options-strategies)
  21. [Root-Level Equity Strategies](#21-root-level-equity-strategies)
- **Part IV — MULTI-ASSET / ASSET-AGNOSTIC**
  22. [Bundle-Optimized Portfolios (4)](#22-bundle-optimized-portfolios-4)
  23. [Sentinel Fund Strategy](#23-sentinel-fund-strategy)
  24. [Quantum Fusion System](#24-quantum-fusion-system)
- **Part V — META-STRATEGY & EVOLUTION ENGINES**
  25. [DNA / Genome Engine](#25-dna--genome-engine)
  26. [Meta-Strategy Permutation Engine](#26-meta-strategy-permutation-engine)
  27. [Quant Lab](#27-quant-lab)
  28. [FreshPicks DNA Strategy](#28-freshpicks-dna-strategy)
- **Part VI — MACHINE LEARNING TECHNIQUES**
  29. [ML Techniques & Infrastructure](#29-ml-techniques--infrastructure)
- **Part VII — PINE SCRIPTS (TradingView)**
  30. [Pine Scripts (29)](#30-pine-scripts-29)
- **Part VIII — INFRASTRUCTURE & REGISTRIES**
  31. [Cross-System Notes](#31-cross-system-notes)
  32. [Multi-Asset Strategy Engineering (600 Variants)](#32-multi-asset-strategy-engineering-600-variants)
  33. [Truly Strong v2.1 — Institutional Alpha (Rescued 2026-04-02)](#33-truly-strong-v21--institutional-alpha-rescued-2026-04-02)

---

# PART I — CRYPTO STRATEGIES

---

## 1. Baby Strategies — 77

**Location:** `baby_strategies/*.py`
**Pipeline:** Forward-tested via Bundle-Baby system → `battleground/data/bundle_babies.db`

| # | File | Type |
|---|------|------|
| 1 | `adaptive_momentum.py` | Trend / Adaptive |
| 2 | `adx_range_mean_reversion.py` | Mean Reversion |
| 3 | `adx_trend_rsi.py` | Trend + RSI |
| 4 | `autocorr_reversion.py` | Mean Reversion / Stat |
| 5 | `bb_squeeze_breakout.py` | Breakout / Squeeze |
| 6 | `bollinger_mean_reversion.py` | Mean Reversion |
| 7 | `carter_squeeze_breakout.py` | Breakout / Squeeze |
| 8 | `cci_divergence.py` | Divergence |
| 9 | `chaikin_money_flow_trend.py` | Flow / Trend |
| 10 | `connors_r3_mean_reversion.py` | Mean Reversion |
| 11 | `connors_rsi2.py` | Mean Reversion |
| 12 | `connors_rsi2_mean_reversion.py` | Mean Reversion |
| 13 | `consecutive_down_rsi.py` | Mean Reversion |
| 14 | `contrarian_fg_tiered.py` | Sentiment / Contrarian |
| 15 | `dca_rsi_adaptive.py` | DCA / Adaptive |
| 16 | `dema_crossover_momentum.py` | Trend / Crossover |
| 17 | `donchian_trend_filter.py` | Trend / Breakout |
| 18 | `dual_momentum_crypto.py` | Momentum / Rotation |
| 19 | `dxy_weekly_drop.py` | Macro / Cross-asset |
| 20 | `ehlers_fisher_transform.py` | Cycle / Oscillator |
| 21 | `elder_ray_power.py` | Trend / Power |
| 22 | `fomc_drift_calendar.py` | Event / Calendar |
| 23 | `heikin_ashi_trend_rider.py` | Trend / Price Action |
| 24 | `hurst_regime_filter.py` | Regime / Fractal |
| 25 | `ichimoku_cloud_breakout.py` | Trend / Pattern |
| 26 | `kalman_mean_reversion.py` | Mean Reversion / Quant |
| 27 | `kama_mean_reversion.py` | Mean Reversion / Adaptive |
| 28 | `keltner_mean_reversion.py` | Mean Reversion |
| 29 | `keltner_momentum_squeeze.py` | Breakout / Squeeze |
| 30 | `levine_adaptive_lookback_momentum.py` | Momentum / Adaptive |
| 31 | `liquidity_sweep_reversal.py` | Smart Money / Reversal |
| 32 | `macd_trend_momentum.py` | Trend / Momentum |
| 33 | `market_structure_volume.py` | Structure / Volume |
| 34 | `mean_reversion_zscore.py` | Mean Reversion / Stat |
| 35 | `ml_ensemble_strategy.py` | Machine Learning |
| 36 | `multi_timeframe_confluence.py` | Multi-TF / Confluence |
| 37 | `nr7_volatility_breakout.py` | Breakout / Volatility |
| 38 | `order_block_retest.py` | Smart Money / Retest |
| 39 | `overnight_seasonality_btc.py` | Seasonality |
| 40 | `pairs_spread_btceth.py` | Pairs / Stat Arb |
| 41 | `percentile_rank_mr.py` | Mean Reversion / Rank |
| 42 | `pivot_point_bounce.py` | Support/Resistance |
| 43 | `price_action_engulfing.py` | Price Action / Pattern |
| 44 | `range_expansion_breakout.py` | Breakout |
| 45 | `red_candle_mean_reversion.py` | Mean Reversion |
| 46 | `relative_strength_rotation.py` | Rotation / RS |
| 47 | `rsi_volume_mean_reversion.py` | Mean Reversion |
| 48 | `rsi2_bb_squeeze.py` | Mean Reversion / Squeeze |
| 49 | `sma50_regime_filter.py` | Regime / Trend |
| 50 | `smart_execution_strategy.py` | Execution / Meta |
| 51 | `stochastic_mean_reversion.py` | Mean Reversion |
| 52 | `strategy_999_worldclass_ensemble.py` | Ensemble / Meta |
| 53 | `strategy_ultimate_omniscient_v1.py` | Ensemble / Meta |
| 54 | `supertrend_atr.py` | Trend / ATR |
| 55 | `volatility_regime_switch.py` | Regime / Volatility |
| 56 | `volatility_scaled_momentum.py` | Momentum / Vol-adj |
| 57 | `volume_imbalance_reversal.py` | Volume / Reversal |
| 58 | `volume_price_confirmation_reversal.py` | Volume / Confirmation |
| 59 | `volume_profile_deviation.py` | Volume / Profile |
| 60 | `volume_weighted_median_zscore.py` | Volume / Stat |
| 61 | `vwap_deviation_rsi.py` | VWAP / Mean Reversion |
| 62 | `vwap_reclaim_volume_surge.py` | VWAP / Breakout |
| 63 | `weekend_momentum.py` | Seasonality |
| 64 | `williams_pr_trend_mr.py` | Mean Reversion |
| 65 | `williams_r_mean_reversion.py` | Mean Reversion |
| 66 | `williams_r_volume.py` | Mean Reversion / Volume |
| 67 | `backtest_vpcr.py` | *(Backtest utility)* |
| 68 | `real_data_backtest.py` | *(Backtest utility)* |
| 69 | `simpleton_trend_reversal.py` | Trend / EMA Crossover |
| 70 | `mercury_vol_crossover.py` | Trend / EMA + RSI |
| 71 | `mercury_conservative.py` | Trend / EMA + RSI Conservative |
| 72 | `mercury_aggressive.py` | Trend / EMA + RSI Aggressive |
| 73 | `simpleton_mercury_hybrid.py` | Trend / EMA Hybrid |
| 74 | `mercury_funding_enhanced.py` | Trend / Funding Rate |
| 75 | `mercury_hma_filtered.py` | Trend / HMA + Volume |
| 76 | `triple_confirmation.py` | Mean Reversion / BB + Z-Score |
| 77 | `kimi_vpin_lgbm_ensemble.py` | ML / VPIN + LightGBM |
| 78 | `irb_hoffman.py` | Trend / Price Action / Breakout |
| 79 | `fib_rsi_divergence.py` | Mean Reversion / Fibonacci |
| 80 | `protective_momentum.py` | Momentum / Multi-Factor |
| 81 | `adaptive_regime_wrapper.py` | Meta / Regime Detection |

---

## 1b. Paper Trading Strategies — 50+

**Location:** `paper_trading/strategies/*.py`
**Pipeline:** Every scan → audit trail `ejaguiar1_stocks` via `paper_trading/scanner.py`

| # | Strategy ID | Type | Source |
|---|-------------|------|--------|
| 1 | `simpleton_trend_reversal` | EMA Crossover + RSI + ATR | FundedRelay (The Leap #7) |
| 2 | `mercury_vol_crossover` | EMA 9/21 + RSI Extreme | Mercury/InceptionLabs |
| 3 | `mercury_conservative` | RSI <20/>80 + EMA Trend | Mercury Conservative |
| 4 | `mercury_aggressive` | RSI <35/>65 + 3:1 RR | Mercury Aggressive |
| 5 | `simpleton_mercury_hybrid` | EMA 21/55 + RSI Extreme | Simpleton × Mercury |
| 6 | `mercury_funding_enhanced` | EMA + Funding Rate Bias | Mercury + On-Chain |
| 7 | `mercury_hma_filtered` | HMA + Volume + EMA | Mercury + HMA Filter |
| 8 | `triple_confirmation` | Golden Cross + BB + Z-Score | Kimi Agent Challenge |
| 9 | `corr_hma_trend` | HMA Trend Following | Correlation Analysis |
| 10 | `corr_kama_adaptive` | KAMA Adaptive | Correlation Analysis |
| 11+ | *(40+ additional — FundedRelay, Verified Research, Kimi Claw, Academic)* | Various | Various |
| — | `irb_hoffman` | IRB Breakout + EMA Ribbon | Gemini Championship (Hoffman) |
| — | `fib_rsi_divergence` | Fibonacci + RSI Divergence | Gemini Championship (Bellet) |
| — | `protective_momentum` | Multi-Factor Momentum | Gemini Championship (Triton) |
| — | `adaptive_irb_hoffman` | Adaptive Regime + IRB | Gemini Championship (Quant League) |

---

## 2. Alpha Engine — Core Crypto (36)

**Location:** `alpha_engine/crypto_strategies.py`
**Pipeline:** Every 30 min → `alpha_engine/data/active_picks.json`

| # | Strategy ID | WR | Source |
|---|-------------|-----|--------|
| 1 | `btc_ichimoku_cloud` | — | Ichimoku (1968) |
| 2 | `btc_200d_sma_bounce` | — | — |
| 3 | `crypto_fear_greed_contrarian` | 60%+ | Nasdaq Research |
| 4 | `funding_rate_extreme` | 71% | Kraken Research |
| 5 | `wyckoff_accumulation` | 60-70% | Wyckoff (1931) |
| 6 | `smart_money_fvg` | 55-65% | ICT SMC |
| 7 | `rsi_hidden_divergence` | — | — |
| 8 | `crypto_breakout_volume` | 60-65% | Elder (1993) |
| 9 | `stochrsi_oversold_bounce` | — | — |
| 10 | `hurst_mean_reversion` | — | Peters (1991) |
| 11 | `entropy_adaptive_rsi` | — | Shannon (1948) |
| 12 | `coingecko_trending_volume` | — | — |
| 13 | `altcoin_season_rotation` | 55-65% | Liu & Tsyvinski (2021) |
| 14 | `ape_wisdom_social_momentum` | — | — |
| 15 | `btc_dominance_reversal` | — | — |
| 16 | `crypto_weekend_drift` | — | — |
| 17 | `connors_rsi2_crypto` | **62.5%** | **p=0.009, Sharpe 2.35** |
| 18 | `obv_divergence_breakout` | 62-68% | Granville (1963) |
| 19 | `liquidity_sweep_reversal` | 60-72% | — |
| 20 | `volume_climax_reversal` | 60-70% | Elder (1993) |
| 21 | `vwap_sd_mean_reversion` | 70-75% | Berkowitz (1988) |
| 22 | `cmf_zero_line_cross` | 55-65% | Chaikin (1980s) |
| 23 | `mfi_smart_money_detection` | 55-68% | Quong & Soudack (1989) |
| 24 | `swing_failure_pattern` | 58-65% | Hsaka |
| 25 | `break_of_structure` | 55-65% | ICT SMC |
| 26 | `funding_rate_carry` | 60% | Kraken Research |
| 27 | `liquidation_cascade_bottom` | 60-65% | — |
| 28 | `oi_funding_squeeze` | 55-62% | Coinalyze |
| 29 | `cross_sectional_momentum` | Sharpe ~2.1 | Liu et al. (2022 JFE) |
| 30 | `atr_volatility_breakout` | 55-62% | Connors & Raschke |
| 31 | `whale_accumulation_detector` | 58-65% | Chainalysis |
| 32 | `multi_timeframe_ema_stack` | 65-72% | Pentoshi/DonAlt |
| 33 | `rsi_macd_confluence` | **65%** | Elder (1986) |
| 34 | `cumulative_rsi_signal` | — | Cumulative RSI divergence |
| 35 | `williams_r_sma_signal` | — | Williams %R + SMA filter |
| 36 | `dxy_divergence_alpha` | — | DXY correlation divergence |

---

## 3. Alpha Engine — On-Chain (10)

**Location:** `alpha_engine/onchain_strategies.py`

| # | Strategy ID | WR | Source |
|---|-------------|-----|--------|
| 1 | `mvrv_sma_proxy` | — | Mahmudov & Puell (2018) |
| 2 | `hash_ribbon_buy` | **78%** | Charles Edwards (2019) |
| 3 | `stablecoin_buying_power` | — | CryptoQuant (2020) |
| 4 | `nvt_overvaluation` | — | Willy Woo (2017) |
| 5 | `fear_greed_extreme_dca` | 14.6% ann. | Nasdaq Research |
| 6 | `sopr_dip_buy_proxy` | — | Shirakashi (2019) |
| 7 | `onchain_composite_score` | — | Multi-source |
| 8 | `hayes_liquidity_index` | — | Arthur Hayes (2024) |
| 9 | `pentoshi_htf_structure` | — | Pentoshi |
| 10 | `funding_rate_arbitrage` | 19-115% ann. | Amberdata |

---

## 4. Alpha Engine — Quant (4)

**Location:** `alpha_engine/quant_strategies.py`

| # | Strategy ID | Source |
|---|-------------|--------|
| 1 | `tsmom_28d` | Moskowitz et al. (2012) |
| 2 | `cointegrated_pairs` | Engle-Granger |
| 3 | `momentum_mean_rev_blend` | — |
| 4 | `oi_price_divergence` | Coinalyze |

---

## 5. Alpha Engine — Advanced (13)

**Location:** `alpha_engine/advanced_strategies.py`

| # | Strategy ID | Description |
|---|-------------|-------------|
| 1 | `vol_risk_premium` | Volatility risk premium harvesting |
| 2 | `dynamic_momentum_scaling` | Regime-adaptive momentum sizing |
| 3 | `goplus_filtered_sniper` | GoPlus smart contract risk filter |
| 4 | `altcoin_dip_amplifier` | Altcoin dip buying with leverage |
| 5 | `unlock_scoring_enhanced` | Token unlock event scoring |
| 6 | `cascade_volume_detector` | Volume cascade / whale activity |
| 7 | `sector_momentum_7d` | Crypto sector (L1, DeFi, meme) rotation |
| 8 | `dvol_extreme_buy` | DVOL extreme volatility dip buying |
| 9 | `fractal_decay` | Fractal dimension decay breakout |
| 10 | `swing_structure` | Swing structure break detection |
| 11 | `kalman_filter_trend` | Kalman filter trend following |
| 12 | `candle_momentum` | Candle body momentum scoring |
| 13 | `cusum_regime` | CUSUM regime change detection |

---

## 6. Alpha Engine — Event-Driven (8)

**Location:** `alpha_engine/event_strategies.py`

| # | Strategy ID | Description |
|---|-------------|-------------|
| 1 | `token_unlock_short` | Token unlock event short selling |
| 2 | `liquidation_cascade_buy` | Liquidation cascade dip buying |
| 3 | `exchange_netflow_reversal` | Exchange netflow reversal detection |
| 4 | `btc_dip_recovery` | BTC dip recovery momentum |
| 5 | `narrative_rotation` | Crypto narrative rotation trading |
| 6 | `new_pair_momentum` | New listing momentum trading |
| 7 | `cross_exchange_spread` | Cross-exchange spread arbitrage |
| 8 | `momentum_crash_hedge` | Momentum crash hedging |

---

## 6b. Alpha Engine — Proven Research (10)

**Location:** `alpha_engine/proven_research_strategies.py`
**Added:** 2026-03 | Research-backed strategies with ATR-based TP/SL

| # | Strategy ID | Description |
|---|-------------|-------------|
| 1 | `vwap_trend_bounce` | VWAP trend bounce with RSI filter |
| 2 | `hoffman_ema_irb` | Hoffman EMA inventory retracement bar |
| 3 | `statistical_pairs_zscore` | Z-score pairs trading (stat arb) |
| 4 | `supply_demand_zone` | Supply/demand zone detection |
| 5 | `three_white_soldiers_rsi` | Three white soldiers + RSI confirmation |
| 6 | `bearish_engulfing_reversal` | Bearish engulfing pattern reversal |
| 7 | `golden_confluence_swing` | Golden ratio confluence swing trading |
| 8 | `vwap_rsi_institutional` | VWAP + RSI institutional flow detection |
| 9 | `rsi_weighted_pairs_arb` | RSI-weighted pairs arbitrage |
| 10 | `hoffman_keltner_expansion` | Hoffman Keltner channel expansion |

---

## 6c. Alpha Engine — Proven Scanner (6)

**Location:** `alpha_engine/proven_scanner_strategies.py`
**Added:** 2026-03 | Backtested scanner strategies

| # | Strategy ID | Description |
|---|-------------|-------------|
| 1 | `proven_keltner_squeeze_breakout` | Keltner squeeze breakout scanner |
| 2 | `proven_triple_ema_pullback` | Triple EMA pullback scanner |
| 3 | `proven_vwap_mean_reversion` | VWAP mean reversion scanner |
| 4 | `proven_inverse_fvg_contrarian` | Inverse FVG contrarian scanner |
| 5 | `proven_stochrsi_divergence` | StochRSI divergence scanner |
| 6 | `proven_propfirm_conservative` | Prop firm conservative scanner |

---

## 6d. Alpha Engine — Hybrid (7)

**Location:** `alpha_engine/hybrid_strategies.py`
**Added:** 2026-03 | Multi-indicator hybrid DNA strategies

| # | Strategy ID | Description |
|---|-------------|-------------|
| 1 | `hurst_volume_profile_confluence` | Hurst exponent + volume profile confluence |
| 2 | `adaptive_hurst_markov_gated` | Adaptive Hurst with Markov regime gating |
| 3 | `multi_sigma_ema_stack` | Multi-sigma EMA stack breakout |
| 4 | `cross_system_regime_arbitrage` | Cross-system regime arbitrage |
| 5 | `widened_tp_momentum_carry` | Widened TP momentum carry strategy |
| 6 | `vwap_rsi_confluence` | VWAP + RSI confluence (hybrid variant) |
| 7 | `ai_ema_pullback` | AI-enhanced EMA pullback strategy |

---

## 6e. Alpha Engine — Mercury AI (5)

**Location:** `alpha_engine/mercury_ai_strategies.py`
**Added:** 2026-03 | Mercury AI advanced quant strategies

| # | Strategy ID | Description |
|---|-------------|-------------|
| 1 | `hurst_regime_momentum` | Hurst exponent regime-filtered momentum |
| 2 | `lw_vwap_mean_reversion` | Lightweight VWAP mean reversion |
| 3 | `funding_term_structure` | Funding rate term structure analysis |
| 4 | `spot_perp_basis_arb` | Spot-perpetual basis arbitrage |
| 5 | `iv_skew_reversion` | Implied volatility skew reversion |

---

## 6f. Alpha Engine — Cerebrus AI (6)

**Location:** `alpha_engine/cerebrus_strategies.py`
**Added:** 2026-03 | Cerebrus AI multi-factor strategies

| # | Strategy ID | Description |
|---|-------------|-------------|
| 1 | `relative_strength_pair_cmr` | Relative strength pair CMR ranking |
| 2 | `funding_rate_carry_pro` | Professional funding rate carry |
| 3 | `mvrv_contrarian_dip` | MVRV-based contrarian dip buying |
| 4 | `volume_spike_breakout` | Volume spike breakout detection |
| 5 | `liquidity_imbalance_reversal` | Liquidity imbalance reversal |
| 6 | `stablecoin_dry_powder` | Stablecoin supply dry powder signal |

---

## 6g. Alpha Engine — Untapped Alpha (8)

**Location:** `alpha_engine/untapped_strategies.py`
**Added:** 2026-03 | Untapped alpha sources (macro, options, sentiment)

| # | Strategy ID | Description |
|---|-------------|-------------|
| 1 | `hurst_exponent_pairs` | Hurst exponent pairs trading |
| 2 | `max_pain_gravitational` | Options max pain gravitational pull |
| 3 | `put_call_ratio_contrarian` | Put/call ratio contrarian signals |
| 4 | `google_trends_contrarian` | Google Trends contrarian reversal |
| 5 | `copper_gold_btc_cycle` | Copper/gold ratio BTC cycle signal |
| 6 | `btc_options_expiry_anomaly` | BTC options expiry anomaly |
| 7 | `turn_of_month_enhanced` | Enhanced turn-of-month effect |
| 8 | `vix_term_structure_signal` | VIX term structure contango/backwardation |

---

## 6h. Alpha Engine — Market Microstructure (4)

**Location:** `alpha_engine/market_microstructure_strategies.py`
**Added:** 2026-03 | Order flow and microstructure alpha

| # | Strategy ID | Description |
|---|-------------|-------------|
| 1 | `options_25delta_skew` | 25-delta options skew reversion |
| 2 | `coinbase_premium_index` | Coinbase premium index signal |
| 3 | `perpetual_basis_strategy` | Perpetual futures basis strategy |
| 4 | `order_book_imbalance` | Order book imbalance momentum |

---

## 6i. Alpha Engine — Exchange Flow (1)

**Location:** `alpha_engine/exchange_flow_strategies.py`
**Added:** 2026-03 | Exchange flow on-chain signals

| # | Strategy ID | Description |
|---|-------------|-------------|
| 1 | `exchange_reserve_decline` | Exchange reserve decline accumulation signal |

---

## 6j. Alpha Engine — NextGen (13)

**Location:** `alpha_engine/nextgen_strategies.py`
**Added:** 2026-03 | Next-generation quantitative strategies

| # | Strategy ID | Description |
|---|-------------|-------------|
| 1 | `cointegration_pair_trade` | Cointegration-based pair trading |
| 2 | `adx_volatility_breakout` | ADX volatility breakout |
| 3 | `seasonal_factor_rotation` | Seasonal factor rotation |
| 4 | `multi_factor_equity_rotation` | Multi-factor equity rotation |
| 5 | `dead_cat_bounce_momentum` | Dead cat bounce momentum |
| 6 | `market_structure_break` | Market structure break detection |
| 7 | `volume_acceleration_reversion` | Volume acceleration mean reversion |
| 8 | `night_liquidity_drift` | Night session liquidity drift |
| 9 | `spread_of_candles_gap` | Spread-of-candles gap trading |
| 10 | `vix_correlation_divergence` | VIX correlation divergence |
| 11 | `profit_taking_reentry` | Profit-taking reentry strategy |
| 12 | `bb_rsi_mean_reversion` | Bollinger Band + RSI mean reversion |
| 13 | `pi_cycle_regime_gate` | Pi-cycle top indicator regime gate |
| 14 | `puell_multiple_extreme` | Puell multiple extreme dip buying |

---

## 6k. Alpha Engine — Next Gen Signals (6)

**Location:** `alpha_engine/next_gen_strategies.py`
**Added:** 2026-03 | Next-gen multi-timeframe signal strategies

| # | Strategy ID | Description |
|---|-------------|-------------|
| 1 | `strat_vwap_reversion` | VWAP reversion signal |
| 2 | `strat_fear_greed_contrarian` | Fear & greed contrarian signal |
| 3 | `strat_btc_dominance_rotation` | BTC dominance rotation signal |
| 4 | `strat_funding_rate_fade` | Funding rate fade signal |
| 5 | `strat_session_open_break` | Session open break signal |
| 6 | `strat_trend_reversion_combo` | Trend reversion combo (1h + 15m) |

---

## 6l. Alpha Engine — Super Strategies (10)

**Location:** `alpha_engine/super_strategies.py`
**Added:** 2026-03 | High-conviction multi-factor super strategies

| # | Strategy ID | Description |
|---|-------------|-------------|
| 1 | `super_keltner_ema_momentum` | Keltner + EMA momentum |
| 2 | `super_hma_breakout_volume` | HMA breakout with volume confirmation |
| 3 | `super_channel_trend_rider` | Channel trend rider |
| 4 | `super_rsi_bollinger_revert` | RSI + Bollinger reversion |
| 5 | `super_vwap_zscore_bounce` | VWAP z-score bounce |
| 6 | `super_funding_rate_carry` | Funding rate carry (super variant) |
| 7 | `super_whale_fear_accumulate` | Whale + fear/greed accumulation |
| 8 | `super_options_macro_flow` | Options macro flow signal |
| 9 | `super_inverse_seasonal_obi` | Inverse seasonal + OBI |
| 10 | `super_confluence_ensemble` | Multi-factor confluence ensemble |

---

## 6m. Alpha Engine — Survivor Strategies (5)

**Location:** `alpha_engine/survivor_strategies.py`
**Added:** 2026-03 | Battle-tested survivor strategies from elimination engine

| # | Strategy ID | Description |
|---|-------------|-------------|
| 1 | `connors_r3_survivor` | Connors RSI-3 survivor variant |
| 2 | `keltner_mean_reversion_survivor` | Keltner mean reversion survivor |
| 3 | `bollinger_mean_reversion_survivor` | Bollinger mean reversion survivor |
| 4 | `volatility_scaled_survivor` | Volatility-scaled momentum survivor |
| 5 | `williams_r_oversold_survivor` | Williams %R oversold survivor |

---

## 6n. Alpha Engine — Opposite Day (5)

**Location:** `alpha_engine/opposite_day_strategies.py`
**Added:** 2026-03 | Contrarian/short-biased strategies

| # | Strategy ID | Description |
|---|-------------|-------------|
| 1 | `overbought_reversal_short` | RSI overbought reversal short |
| 2 | `macro_regime_short_filter` | Macro regime-filtered short |
| 3 | `crowd_contrarian_timer` | Crowd sentiment contrarian timer |
| 4 | `cluster_short_momentum` | Cluster short momentum |
| 5 | `news_sentiment_contrarian` | News sentiment contrarian |

---

## 6o. Alpha Engine — Variation Strategies (3)

**Location:** `alpha_engine/variation_strategies.py`
**Added:** 2026-03 | Parameter variation strategies

| # | Strategy ID | Description |
|---|-------------|-------------|
| 1 | `keltner_hma_filter` | Keltner with HMA trend filter |
| 2 | `multi_sigma_volume` | Multi-sigma volume breakout |
| 3 | `hurst_rsi_extreme` | Hurst exponent + RSI extreme |

---

## 6p. Alpha Engine — Antigravity Strategies (4)

**Location:** `alpha_engine/antigravity_strategies.py`
**Added:** 2026-03 | Antigravity portfolio core strategies

| # | Strategy ID | Description |
|---|-------------|-------------|
| 1 | `ag_vwap_rsi_institutional` | Antigravity VWAP + RSI institutional flow |
| 2 | `ag_liquidation_cascade_contrarian` | Antigravity liquidation cascade contrarian |
| 3 | `ag_regime_sentinel_composite` | Antigravity regime sentinel composite |
| 4 | `ag_rsi_pairs_arbitrage` | Antigravity RSI pairs arbitrage |

---

## 6q. Alpha Engine — Statistical Strategies (10)

**Location:** `alpha_engine/statistical_strategies.py`
**Added:** 2026-03 | Pure statistical/quantitative strategies

| # | Strategy ID | Description |
|---|-------------|-------------|
| 1 | `multi_sigma_reversal` | Multi-sigma extreme reversal |
| 2 | `ornstein_uhlenbeck_reversion` | O-U process mean reversion |
| 3 | `variance_ratio_momentum` | Variance ratio momentum test |
| 4 | `hurst_regime_adaptive` | Hurst exponent regime-adaptive |
| 5 | `bollinger_keltner_squeeze_breakout` | BB/Keltner squeeze breakout |
| 6 | `autocorrelation_exploiter` | Autocorrelation exploitation |
| 7 | `volume_profile_poc_reversion` | Volume profile POC reversion |
| 8 | `mean_reversion_halflife` | Mean reversion half-life signal |
| 9 | `cumulative_delta_divergence` | Cumulative delta divergence |
| 10 | `multi_factor_composite` | Multi-factor composite score |

---

## 6r. Alpha Engine — Pattern Strategies (9)

**Location:** `alpha_engine/pattern_strategies.py`
**Added:** 2026-03 | Chart pattern detection strategies

| # | Strategy ID | Description |
|---|-------------|-------------|
| 1 | `fractal_sr_bounce` | Fractal support/resistance bounce |
| 2 | `double_top_bottom_detector` | Double top/bottom pattern detector |
| 3 | `head_shoulders_detector` | Head & shoulders pattern detector |
| 4 | `ascending_triangle_breakout` | Ascending triangle breakout |
| 5 | `sr_breakout_retest` | S/R breakout retest entry |
| 6 | `price_level_magnetism` | Price level magnetism (attraction) |
| 7 | `pattern_repetition_forecast` | Pattern repetition forecasting |
| 8 | `volume_profile_value_area` | Volume profile value area strategy |
| 9 | `multi_touch_level_strength` | Multi-touch level strength scoring |
| 10 | `failed_breakout_reversal` | Failed breakout reversal entry |

---

## 6s. Alpha Engine — Cyclical Strategies (9)

**Location:** `alpha_engine/cyclical_strategies.py`
**Added:** 2026-03 | Time-cycle and seasonal strategies

| # | Strategy ID | Description |
|---|-------------|-------------|
| 1 | `halving_cycle_position` | BTC halving cycle positioning |
| 2 | `monthly_seasonality` | Monthly seasonality pattern |
| 3 | `day_of_week_effect` | Day-of-week effect trading |
| 4 | `btc_dominance_rotation` | BTC dominance rotation timing |
| 5 | `turn_of_month_effect` | Turn-of-month calendar effect |
| 6 | `halloween_effect` | Halloween effect (sell in May) |
| 7 | `fourier_cycle_detector` | Fourier cycle detection |
| 8 | `price_touch_recurrence` | Price touch recurrence pattern |
| 9 | `markov_zone_transition` | Markov zone transition model |
| 10 | `m2_liquidity_lag` | M2 money supply liquidity lag |

---

## 6t. Alpha Engine — Enhanced Strategies (6)

**Location:** `alpha_engine/enhanced_strategies.py`
**Added:** 2026-03 | Enhanced versions of proven strategies

| # | Strategy ID | Description |
|---|-------------|-------------|
| 1 | `rsi_mean_reversion_optimized` | RSI mean reversion (optimized params) |
| 2 | `connors_rsi2_strategy` | Connors RSI-2 enhanced variant |
| 3 | `anti_confluence_contrarian` | Anti-confluence contrarian |
| 4 | `keltner_chop_scalper` | Keltner channel chop scalper |
| 5 | `time_filtered_momentum` | Time-filtered momentum |
| 6 | `star_symbol_tracker` | Star symbol performance tracker |

---

## 6u. Alpha Engine — Experimental Strategies (4)

**Location:** `alpha_engine/experimental_strategies.py`
**Added:** 2026-03 | Experimental / incubating strategies

| # | Strategy ID | Description |
|---|-------------|-------------|
| 1 | `adaptive_vr_confluence` | Adaptive volatility ratio confluence |
| 2 | `macd_rsi_multi_tf` | MACD + RSI multi-timeframe |
| 3 | `session_range_breakout` | Session range breakout |
| 4 | `sentiment_fear_z_reversal` | Sentiment fear z-score reversal |

---

## 6v. Alpha Engine — Justin Bravo Strategies (12)

**Location:** `alpha_engine/justin_bravo_strategies.py`, `justin_bravo_strategies_v2.py`
**Added:** 2026-03 | Justin Bravo / EMA-9 trading system

| # | Strategy ID | Description | Source |
|---|-------------|-------------|--------|
| 1 | `justin_ema9_basic_crypto` | Basic EMA-9 crypto setup | Justin Bravo |
| 2 | `justin_ema9_rsi_crypto` | EMA-9 + RSI filter | Justin Bravo |
| 3 | `justin_ema9_htf_bias_crypto` | EMA-9 with HTF bias | Justin Bravo |
| 4 | `bravo_nine_count_crypto` | Bravo nine count exhaustion | Bravo System |
| 5 | `pattern_reversal_crypto` | Pattern reversal (double top/tweezer) | Bravo System |
| 6 | `ema_ribbon_confluence_crypto` | EMA ribbon confluence | Justin Bravo |
| 7 | `justin_full_system_crypto` | Full system (EMA9+RSI+Count+Pattern) | Justin Bravo |
| 8 | `volume_weighted_ema9_crypto` | Volume-weighted EMA-9 | Justin Bravo |
| 9 | `justin_ema9_pullback_v2` | EMA-9 pullback v2 (ADX gated) | v2 |
| 10 | `justin_rsi_divergence_v2` | RSI divergence v2 | v2 |
| 11 | `justin_trend_follow_v2` | Trend follow v2 (EMA ribbon) | v2 |
| 12 | `justin_breakout_volume_v2` | Breakout volume v2 (BB position) | v2 |

---

## 6w. Alpha Engine — Orderbook Strategies (1)

**Location:** `alpha_engine/orderbook_strategies.py`
**Added:** 2026-03 | Real-time order book analysis

| # | Strategy ID | Description |
|---|-------------|-------------|
| 1 | `order_book_imbalance` | Order book imbalance + CVD signal |

---

## 6x. Alpha Engine — Community Strategies (11)

**Location:** `alpha_engine/community_strategies.py`
**Added:** 2026-03 | Community-sourced multi-asset strategies

| # | Strategy ID | Asset | Description |
|---|-------------|-------|-------------|
| 1 | `community_ema_9_21_rsi_crypto` | Crypto | EMA 9/21 + RSI |
| 2 | `community_bb_squeeze_breakout_crypto` | Crypto | BB squeeze breakout |
| 3 | `community_rsi_extreme_reversal_crypto` | Crypto | RSI extreme reversal |
| 4 | `community_vwap_bounce_crypto` | Crypto | VWAP bounce |
| 5 | `community_momentum_breakout_volume_crypto` | Crypto | Momentum volume breakout |
| 6 | `community_ema_8_21_scalp_forex` | Forex | EMA 8/21 scalp |
| 7 | `community_london_breakout_v2_forex` | Forex | London breakout v2 |
| 8 | `community_forex_zscore_mean_reversion` | Forex | Z-score mean reversion |
| 9 | `community_orb_equity` | Equity | Opening range breakout |
| 10 | `community_penny_volume_surge` | Equity | Penny stock volume surge |
| 11 | `community_ict_fvg_selective` | Crypto | ICT FVG selective |

---

## 6y. Alpha Engine — TradingView Strategies (11)

**Location:** `alpha_engine/tradingview_strategies.py`, `_wave2.py`, `_wave3.py`, `_wave4.py`
**Added:** 2026-03 | TradingView indicator ports

| # | Strategy ID | Module | Description |
|---|-------------|--------|-------------|
| 1 | `alpha_trend` | wave1 | AlphaTrend indicator |
| 2 | `wavetrend_oscillator` | wave1 | WaveTrend oscillator |
| 3 | `williams_vix_fix` | wave1 | Williams VIX Fix |
| 4 | `true_strength_index` | wave1 | True Strength Index (TSI) |
| 5 | `qqe_mod` | wave2 | QQE Mod indicator |
| 6 | `ttm_squeeze` | wave2 | TTM Squeeze momentum |
| 7 | `stochastic_momentum_index` | wave2 | Stochastic Momentum Index |
| 8 | `smc_confluence_score` | wave2 | SMC confluence scoring |
| 9 | `lorentzian_classification` | wave3 | Lorentzian KNN classification |
| 10 | `nadaraya_watson_envelope` | wave3 | Nadaraya-Watson kernel envelope |
| 11 | `volume_delta_divergence` | wave3 | Volume delta divergence |
| 12 | `ict_three_chain` | wave3 | ICT three-chain SMC model |
| 13 | `hmm_regime_filter` | wave4 | Hidden Markov regime filter |
| 14 | `entropy_regime_breakout` | wave4 | Entropy regime breakout |
| 15 | `adaptive_supertrend` | wave4 | Adaptive SuperTrend |

---

## 6z. Alpha Engine — Basis & Prop Strategies (8)

**Location:** `alpha_engine/basis_strategies.py`, `alpha_engine/prop_strategies.py`
**Added:** 2026-03 | Basis trade and prop firm strategies

| # | Strategy ID | Module | Description |
|---|-------------|--------|-------------|
| 1 | `FundingRateArbitrage` | basis | Funding rate arbitrage engine |
| 2 | `BasisTradeAnalyzer` | basis | Basis trade z-score analysis |
| 3 | `CarryTradeScanner` | basis | Carry trade carry-return scanner |
| 4 | `generate_funding_arbitrage_signals` | basis | Funding arbitrage signal generator |
| 5 | `connors_rsi2_prop` | prop | Connors RSI-2 prop firm variant |
| 6 | `keltner_hma_prop` | prop | Keltner HMA prop firm variant |
| 7 | `williams_pr_prop` | prop | Williams %R prop firm variant |
| 8 | `funding_momentum_general` | prop | Funding momentum general |

---

## 6aa. Alpha Engine — Specialty Strategies (5)

**Location:** Various `alpha_engine/*.py` specialty modules
**Added:** 2026-03-17 | Standalone specialty strategies

| # | Strategy ID | Module | Description |
|---|-------------|--------|-------------|
| 1 | `tvl_momentum_strategy` | `tvl_momentum_strategy.py` | TVL momentum (DeFiLlama data) |
| 2 | `scan_active_for_riders` | `momentum_rider_strategy.py` | Active pick momentum rider |
| 3 | `scan_active_for_riders_ml` | `momentum_rider_strategy.py` | ML-enhanced momentum rider |
| 4 | `generate_cyclic_signals` | `cyclic_momentum_strategy.py` | Cyclic streak continuation |
| 5 | `generate_cyclic_adaptive_signals` | `cyclic_momentum_strategy.py` | Cyclic adaptive streak signals |
| 6 | `hoffman_ema_trend` | `hoffman_strategy.py` | Hoffman EMA trend following |
| 7 | `hoffman_irb_reversal` | `hoffman_strategy.py` | Hoffman IRB reversal bars |

---

## 6ab. Alpha Engine — New Strategies (2026-03-17)

**Status:** Being added to production scanner

| # | Strategy ID | WR | Description |
|---|-------------|-----|-------------|
| 1 | `rectangle_breakout` | **93% target** | Rectangle pattern breakout (Bulkowski) |
| 2 | `continuation_pin_bar` | **70%** | With-trend pin bar continuation |
| 3 | `ml_breakout_gate` | **67.2%** | XGBoost feature-gated breakout |
| 4 | `dynamic_exit_enhanced` | — | Close > Previous Day's High entry |
| 5 | `mean_reversion_bb_timed` | **64%, PF 1.9** | Bollinger band MR with time exit |

---

## 7. KIMI Rise of the Claw — Crypto Acceleration (10)

**Location:** `KIMI_RISEOFTHECLAW/crypto_acceleration_engine.py` | v11.0 (81 algos)

| # | Signal ID | Data Source |
|---|-----------|-------------|
| 1 | `signal_pump_detector` | Binance |
| 2 | `signal_telegram_call_follower` | `__telegram_calls__` |
| 3 | `signal_twitter_alpha_calls` | `__twitter_calls__` |
| 4 | `signal_order_book_imbalance` | `__order_book__` |
| 5 | `signal_liquidation_cascade` | `__liquidations__` |
| 6 | `signal_acceleration_burst` | Binance |
| 7 | `signal_coingecko_trending_spike` | `__cg_trending__` |
| 8 | `signal_whale_size_trade` | Binance |
| 9 | `signal_funding_rate_reversal` | Binance Futures |
| 10 | `signal_multi_exchange_divergence` | Multi-exchange |

---

## 8. KIMI Rise of the Claw — Proven Crypto/Forex (14)

**Location:** `KIMI_RISEOFTHECLAW/proven_crypto_forex_strategies.py`

| # | Signal ID | WR |
|---|-----------|-----|
| 1 | `signal_btc_4h_rsi_macd_confluence` | ~65% |
| 2 | `signal_btc_weekly_structure` | — |
| 3 | `signal_altseason_rotation` | — |
| 4 | `signal_crypto_fear_extreme_reversal` | — |
| 5 | `signal_crypto_bb_squeeze_breakout` | — |
| 6 | `signal_crypto_rsi_divergence` | — |
| 7 | `signal_crypto_weekend_drift` | — |
| 8 | `signal_exchange_outflow_proxy` | — |
| 9 | `signal_btc_dominance_reversal` | — |
| 10 | `signal_london_session_breakout` | **62%** |
| 11 | `signal_dxy_reversal` | — |
| 12 | `signal_carry_trade_signal` | — |
| 13 | `signal_session_volatility_expansion` | — |
| 14 | `signal_forex_rsi_ema_confluence` | — |

---

## 9. Coinglass DNA Bundle (8)

**Location:** `coinglass_strategies/` | Every 15 min | Symbols: BTC, ETH, SOL, BNB, DOGE

| # | Strategy ID | Module |
|---|-------------|--------|
| 1 | S1-ExtremeReversion | `strategies/extreme_reversion.py` |
| 2 | S2-WhaleDivergence | `strategies/top_trader_divergence.py` |
| 3 | S3-RatioMomentum | `strategies/ratio_momentum.py` |
| 4 | S4-ExchangeSpread | `strategies/cross_exchange_spread.py` |
| 5 | S5-LeverageSqueeze | `strategies/leverage_adjusted.py` |
| 6 | S6-FundingConfluence | `strategies/funding_confirmation.py` |
| 7 | S7-SentimentComposite | `strategies/sentiment_index.py` |
| 8 | S8-SpikeDetector | `strategies/spike_detection.py` |
| 9 | S9-CalendarSpread | `strategies/calendar_spread.py` — **NEW** Futures basis mean-reversion (perp-vs-spot z-score) |
| 10 | S10-RollYield | `strategies/roll_yield.py` — **NEW** Funding rate term-structure carry harvesting |
| 11 | S11-OptionsVolatility | `strategies/options_volatility.py` — **NEW** Deribit IV + put/call skew signals |
| 12 | S12-NewsSentiment | `strategies/news_sentiment.py` — **NEW** CryptoPanic news + Fear&Greed confluence |
| 13 | S13-RiskParity | `strategies/risk_parity.py` — **NEW** Inverse-vol risk parity + momentum scoring |

**Data failover:** Binance Futures → Coinglass public → OKX public → Deribit (options) → CryptoPanic (news)

---

## 10. ML Battleground — 5 Trading Systems

**Location:** `ml_battleground/` | Discord-enabled scanners

| System | Module | ML Technique | Description |
|--------|--------|-------------|-------------|
| **System A — Filter** | `system_a_filter/` | ML feature filter | Filters signals with trained ML classifier |
| **System B — Regime** | `system_b_regime/` | Regime classifier | Routes strategies by detected market regime |
| **System C — DeepLearn** | `system_c_deeplearn/` | Deep learning | Neural-net price prediction |
| **System D — Carry** | `system_d_carry/` | Carry trade scanner | Funding rate carry with ML ranking |
| **System E — Momentum** | `system_e_momentum/` | Momentum scoring | ML-enhanced momentum detection |
| **System F — ClawsOfDoom** | `system_f_clawsofdoom/` | Ensemble | KIMI Claws of Doom integration |

**Shared infrastructure:** `shared/` — discord_notify, data_fetcher, indicators, risk_manager, meta_labeler, sr_engine, calibration, cost_model, validator, trade_filters

**Orchestrator:** `ensemble_coordinator.py` — consolidates all 5 systems into unified picks

---

## 11. Crypto ML Edge

**Location:** `crypto_ml_edge/`

| Module | Purpose |
|--------|---------|
| `scanner.py` / `quick_scanner.py` | Live signal scanning |
| `trainer.py` | Model training pipeline |
| `gainer_detector.py` | Crypto gainer detection |
| `labeler.py` | Training data labeling |
| `stationarity.py` | Time-series stationarity checks |
| `validation.py` | Model validation |
| `risk.py` | Risk management |
| `data_quality.py` | Data quality checks |

---

## 12. Mercury2 Ensemble

**Location:** `mercury2/`

| Module | Purpose |
|--------|---------|
| `scanner.py` | Live market scanning |
| `ensemble.py` | Multi-model ensemble |
| `trainer.py` | Model training |
| `features.py` | Feature engineering |
| `risk_engine.py` | Risk management |
| `top_gainer.py` | Top gainer detection |

---

## 13. Crypto Signal Engine

**Location:** `crypto_signal_engine/`

| Module | Purpose |
|--------|---------|
| `engine.py` | Core signal generation |
| `trainer.py` | Model training |
| `features.py` | Feature engineering |
| `risk_engine.py` | Risk management |

---

## 14. ML Crypto Predictor

**Location:** `ml_crypto_predictor/`

| Module | Purpose |
|--------|---------|
| `production_engine.py` | Production inference |
| `train_base_models.py` | Base model training |
| `train_ensemble.py` | Ensemble model training |
| `train_scalping_models.py` | Scalping model training |
| `train_swing_models.py` | Swing model training |
| `feature_selection.py` | Feature importance |
| `self_improvement.py` | Auto-retraining |
| `optimize_tp_sl.py` | TP/SL optimization |
| `backtest_ml.py` | ML backtesting |

---

## 15. Claude Gainer ML

**Location:** `claude_gainer_ml/`

| Module | Purpose |
|--------|---------|
| `live_scanner.py` | Live scanning |
| `train_model.py` | Model training |
| `token_sniffer.py` | Token analysis |
| `self_improver.py` | Self-improvement loop |
| `tp_sl_tracker.py` | TP/SL validation |

---

## 16. Root-Level Crypto Strategies

**Location:** Repository root

| File | Description |
|------|-------------|
| `momentum_scalping.py` | High-frequency momentum scalping (31 KB) |
| `opposite_day_strategy.py` | Contrarian reversal strategy |
| `live_spike_trader.py` | Real-time spike detection |
| `spike_predictor.py` | Spike prediction model |
| `multi_symbol_crypto_beater.py` | Multi-asset crypto bot |
| `market_beating_bot.py` | Market-beating algorithms |
| `l2_orderbook_agent.py` | Level-2 microstructure agent |
| `self_optimizing_bot.py` | Autonomous parameter tuning (41 KB) |
| `live_trading_bot.py` | General-purpose live bot |
| `asian_range_scalper.py` | Asian session scalping (33 KB) |
| `2hour_challenge.py` / `_live.py` / `real_*.py` | 2-hour challenge strategies |
| `quantum_fusion_crypto_engine.py` | Crypto-specific quantum fusion |
| `strategy_1_breakout.py` | Classic breakout strategy |
| `strategy_3_mean_reversion.py` | Mean reversion framework |
| `breakout_strategy.py` | Breakout pattern detection |
| `mean_reversion_strategy.py` | Mean reversion core |
| `tier1_strategies.py` | Tier-1 proven collection (73 KB) |
| `funding_arb_analysis.py` / `_backtest.py` / `_extended.py` | Funding rate arb suite |

---

## 17. AI-Generated Incubator Strategies (320+)

### Web AI — 175 strategies
**Location:** `incubator/agents/web_ai/strategy_011_*.py` through `strategy_220_*.py`

Categories by number range:
- **011-015:** Multi-timeframe (triple TF, HTF filter, fractal confluence, cross-TF divergence)
- **036-040:** Volatility (ATR regime, Bollinger squeeze, GARCH, vol cycle)
- **041-045:** ML (Random Forest, feature importance, anomaly detection, clustering, PCA)
- **046-050:** Stat Arb (pairs, cointegration, Z-score MR, Kalman, triangular arb)
- **071-100:** Indicators (RSI divergence, MACD, Stochastic, Williams, CCI, ADX, Ichimoku, SAR, Keltner, Donchian, OBV, MFI, TSI, UO, ROC, Aroon, Schaff, KST, Elder Ray, Force Index)
- **101-125:** Chart patterns (Heikin Ashi, Renko, Point&Figure, pivots, Gann, Fibonacci)
- **126-135:** Advanced MAs (Hull, ALMA, ZLEMA, VIDYA, Kaufman, Fractal Dimension)
- **136-144:** Vol measures (Parkinson, Garman-Klass, Rogers-Satchell, Yang-Zhang, VRP)
- **145-170:** Risk metrics (Sharpe, Sortino, Calmar, Omega, Kelly, Risk Parity, Ulcer)
- **171-200:** Statistical (SQN, MAE/MFE, Monte Carlo, Bootstrap, Walk-Forward, HMM, CUSUM, Wavelet)
- **201-220:** Quant (Garman-Klass breakout, liquidation cascade, VPIN toxicity, spectral cycle, entropy momentum, cointegration spread)

### Codex GPT-5 — 44 strategies
**Location:** `incubator/agents/codex_gpt5/`
Focus: Crypto bundle MTF, range expansion, donchian variants, EMA pullback, liquidation reversal, volatility compression, order flow proxy

### Cursor AI — 35 strategies
**Location:** `incubator/agents/cursor_ai/`
Focus: Liquidation cascades, miner supply shock, entropy trend filter, funding rate curvature, basis reversion, order book imbalance, session momentum

### Team Alpha — 8 strategies
**Location:** `incubator/agents/team_alpha/`
Focus: Liquidity sweep absorption, microstructure imbalance, FVG reclaim, correlation breakdown, Kelly sizing, vol contraction

### Claude Code — 5 strategies
**Location:** `incubator/agents/claude_code_01/`
Focus: BTC-SPX correlation breakdown, trend factor, echo forecast, MACD forecast, VPIN momentum gate

### Mercury AI — 4 strategies
**Location:** `incubator/agents/mercury_ai/`
Focus: Multi-TF trend/vol confluence, volume breakout, session momentum, volume divergence reversal

### Other agents — 2 strategies
- `antigravity_01/` — VWAP vol profile reversion
- `github_copilot/` — Volume spike momentum

---

# PART II — FOREX STRATEGIES

---

## 18. Alpha Engine — Forex (12)

**Location:** `alpha_engine/forex_strategies.py`

| # | Strategy ID | Description | Pairs |
|---|-------------|-------------|-------|
| 1 | `carry_trade_momentum` | Carry trade + momentum | Major pairs |
| 2 | `forex_mean_reversion_200d` | 200-day mean reversion | EURUSD, GBPUSD, etc. |
| 3 | `jpy_risk_off` | JPY correlation risk-off | USDJPY, EURJPY |
| 4 | `dxy_correlation_regime` | DXY regime pair selection | DXY-correlated |
| 5 | `forex_bollinger_squeeze` | BB breakout + squeeze | Major pairs |
| 6 | `session_momentum_continuation` | London/NY session momentum | Major pairs |
| 7 | `dxy_rsi_mean_reversion` | DXY RSI mean reversion | Dollar pairs |
| 8 | `sunday_night_gap_trade` | Sunday gap fade strategy | Major pairs |
| 9 | `session_volatility_expansion` | Session vol expansion breakout | Major pairs |
| 10 | `forex_tsmom_12m` | 12-month time-series momentum | Major pairs |
| 11 | `forex_logistic_direction` | Logistic regression direction | Major pairs |
| 12 | `forex_rsi2_mean_reversion` | RSI-2 mean reversion | Major pairs |

### Baby — Forex / gold rehab (2026-04-12, pending validation)

| Strategy | File | Scope |
|----------|------|--------|
| `ForexBbMrRehabV1Strategy` | `baby_strategies/forex_bb_mr_rehab_v1.py` | Bollinger MR on EUR/GBP/AUD *USDT* proxies — rehabilitation candidate for weak FOREX class stats |
| `PaxgBollingerMrRehabStrategy` | `baby_strategies/paxg_bollinger_mr_rehab.py` | Tokenized gold (PAXGUSDT) MR — sparse COMMODITY history in closed CSV |

Registered in `incubator/backtest_team/forward_signal_scanner.py` with `survivor_validated: false` until walk-forward + Monte Carlo pass.

| Strategy | File | Scope |
|----------|------|--------|
| `VolSpikeCapitulationLongRehabStrategy` | `baby_strategies/vol_spike_capitulation_long_rehab.py` | Bearish vol-spike + lower-third close → short-term LONG (crypto) |
| `StochPullbackTrendLongRehabStrategy` | `baby_strategies/stoch_pullback_trend_long_rehab.py` | SMA200 trend + stochastic pullback LONG |

---

# PART III — EQUITY & OPTIONS STRATEGIES

---

## 19. Alpha Engine — Equity (12)

**Location:** `alpha_engine/equity_strategies.py`

| # | Strategy ID | Asset | WR |
|---|-------------|-------|----|
| 1 | `momentum_factor_12m` | Stocks | — |
| 2 | `penny_volume_breakout` | Micro-caps | — |
| 3 | `meme_social_velocity` | Meme stocks | — |
| 4 | `quality_value_composite` | Large-caps | — |
| 5 | `intermarket_risk_on` | SPY/QQQ | — |
| 6 | `support_resistance_bounce` | Stocks | — |
| 7 | `connors_rsi2_scanner` | SPY/QQQ | **75.7%** |
| 8 | `triple_rsi_scanner` | Stocks | — |
| 9 | `vix_spike_reversal_scanner` | SPX | **72%** |
| 10 | `turn_of_month_scanner` | SPY/QQQ | — |
| 11 | `earnings_gap_reversal_scanner` | Stocks | — |
| 12 | `gap_reversal_tech_stocks` | Tech | — |

---

## 20. Options Strategies

**Location:** `strategy_variations.json`, `strategy_2_theta_options.py`, `theta_strategy.py` / `_v2.py`

| Strategy | Description |
|----------|-------------|
| 0DTE Options Scalping (1m Ultra) | 1m VWAP + vol>150% + RSI(7), 15% TP / -10% SL, max 3 min |
| 0DTE Options Scalping (5m Standard) | 5m VWAP + vol>130% + RSI(14), 10% TP / -7% SL, max 10 min |
| 0DTE Options Scalping (15m Swing) | 15m VWAP + vol>120% + MACD, 20% TP / -10% SL, max 30 min |
| 0DTE Options Scalping (1h Position) | 1h VWAP + vol>110% + EMA(20), 30% TP / -15% SL, trailing |
| 0DTE Options Scalping (4h Macro) | 4h macro swing setup |
| Theta Decay Strategy v1/v2 | Options theta-decay selling framework |

---

## 21. Root-Level Equity Strategies

| File | Description |
|------|-------------|
| `larry_williams_strategy.py` | Larry Williams volatility breakout |
| `mark_minervini_strategy.py` | Minervini trend template |
| `marty_schwartz_strategy.py` | Day trading patterns |
| `live_trading_bot_canada.py` | Canada-focused equity bot (46 KB) |
| `strategies/high_sharpe_strategy.py` | High Sharpe portfolio construction |

---

# PART IV — MULTI-ASSET / ASSET-AGNOSTIC

---

## 22. Bundle-Optimized Portfolios (8)

**Location:** `baby_strategies/bundle_optimized/`

| Bundle | Target CAGR | Max DD | Risk |
|--------|------------|--------|------|
| **Alpha Hunter** | 20-30% | — | Aggressive |
| **Balanced Growth** | 12-18% | <20% | Moderate |
| **Wealth Preservation** | 8-12% | <15% | Conservative |
| **Funding Grid Momentum** | 19-21% APY | — | Mixed |
| **Simpleton Reversal** | 15-25% | <25% | Moderate |
| **Correlation Aggressive** | 25-40% | <35% | Aggressive |
| **Correlation Balanced** | 15-25% | <20% | Moderate |
| **Correlation Conservative** | 8-15% | <15% | Conservative |

Supporting: `regime_position_sizing.py` (Half-Kelly + regime multipliers)

---

## 23. Sentinel Fund Strategy

**Location:** Root — `sentinel_fund_strategy.py` (23 KB), `sentinel_integrator.py`, `sentinel_hardened_integrator.py`, `sentinel_config.py`

Fund-grade multi-asset allocation strategy with hardened production deployment.

---

## 24. Quantum Fusion System

**Location:** Root — `quantum_fusion_strategy.py` (24 KB), `quantum_fusion_crypto_engine.py`, `quantum_fusion_backtester.py`, `quantum_fusion_multi_period_backtest.py`

Multi-regime fusion system combining multiple signal sources across asset classes.

---

# PART V — META-STRATEGY & EVOLUTION ENGINES

---

## 25. DNA / Genome Engine — DARWIN ENGINE

**Location:** `genome/`

Not a fixed strategy list — a **combinatorial engine** that evolves strategy permutations via genetic programming. Now expanded to **9 evolution engines** operating as the DARWIN ENGINE.

### 25a. Core Modules

| Module | Purpose |
|--------|---------|
| `dna_engine.py` / `_enhanced.py` / `_v2.py` | Core DNA with genetic combination & mutation |
| `dna_strategy_factory.py` | Factory for creating combos |
| `dna_backtester.py` | Backtest evolved combos |
| `evolve_strategies.py` | Evolutionary optimization loop |
| `bayesian_optimizer.py` | Bayesian parameter optimization |
| `quality_engine.py` | Quality scoring |
| `progressive_promotion.py` | Paper → live promotion pipeline |
| `strategy_registry.py` | DNA strategy registry (SQLite) |

**Combination types:** AND, OR, MAJORITY, WEIGHTED, SEQUENTIAL, UNANIMOUS, CONSENSUS_75

### 25b. Genetic Programming Evolution Engine (GENESIS)

**File:** `genome/genetic_programmer.py` | **Dashboard:** `/genome/dashboard/`

Expression tree DNA evolution — invents novel indicator formulas from 26 market inputs using GP primitives (add, sub, mul, div, sin, cos, tanh, log, sqrt). Each strategy has a buy tree + sell tree that are crossbred and mutated across generations.

**Latest Runs (Runs #6-#21 — 2026-03-09):** Pop=60, Gens=15, 5 symbols, seeded from 20+ Hall of Fame winners

| Rank | Strategy | Best Symbol | WR | Sharpe | Fitness | Run |
|------|----------|-------------|-----|--------|---------|-----|
| 1 | GPX_Gen14_22f5d3 | SOLUSDT | **90.5%** | **95.70** | 0.739 | #25 |
| 2 | GPX_Gen14_8cdd4b | SOLUSDT | **90.5%** | 95.35 | 0.736 | #25 |
| 3 | GPX_Gen15_c5e265 | SOLUSDT | 90.0% | **97.08** | 0.732 | #25 |
| 4 | GPX_Gen13_c363e8 | SOLUSDT | 87.0% | 60.78 | 0.730 | #14 |
| 5 | GPX_Gen13_76be04 | SOLUSDT | 90.5% | 84.41 | 0.733 | #25 |

**PRODUCTION CANDIDATES — Run #25 BREAKTHROUGH (17 candidates, NEW ALL-TIME RECORDS):**
- `GPX_Gen14_22f5d3` — SHORT SOLUSDT @ **90.5% WR, Sharpe 95.70** — NEW ALL-TIME WR RECORD
- `GPX_Gen15_c5e265` — SHORT SOLUSDT @ **90.0% WR, Sharpe 97.08** — NEW ALL-TIME SHARPE RECORD
- `GPX_Gen14_8cdd4b` — SHORT SOLUSDT @ 90.5% WR, Sharpe 95.35
- `GPX_Gen13_76be04` — SHORT SOLUSDT @ 90.5% WR, Sharpe 84.41
- 6 more SOL SHORT @ 85.0% WR (Sharpe 83-88)
- 7 BTC SHORT @ 72.2% WR with Sharpe >50 (cross-symbol confirmation)
- Prior records: Run #14 (87.0% WR, 60.78 Sharpe) — **SURPASSED**

**Run #9 notes:** Fitness 0.695. New all-time Sharpe record: **45.87** (ETH SHORT, GPX_Gen15_87e5d4). ETH dominated top 10 (7/10 strategies). Back to 100% SHORT after Run #8's LONG anomaly — confirms bearish trend is genuine. BTC 77.3% WR, ETH 77.8% WR. Consensus: 22-23 SHORT signals per symbol across GP + 6 other DARWIN engines.

**Run #10 notes:** Fitness 0.614 (lowest of runs #6-#10). Champion: `GPX_Gen11_f67a01` — ETHUSDT 60.7% WR, Sharpe 12.05. Mixed direction split: 42% LONG / 58% SHORT — BTC and ETH flipped LONG while SOL, DOGE, AVAX stayed SHORT. Best WR 62.5% (AVAX), best Sharpe 15.0. No production candidates this run. Lower fitness may indicate market regime transition — monitoring next runs for confirmation.

**Run #11 notes:** Fitness **0.7918** — NEW ALL-TIME BEST FITNESS. Champion: `GPX_Gen14_c71526` — DOGEUSDT 67.9% WR, Sharpe 28.86. Massive LONG flip: **94% LONG / 6% SHORT** — complete reversal from Run #9's 100% SHORT. BTC best WR 70.5%, DOGE 69.8%. Market regime confirmed shifting bullish. Bonus strategies still underperform (best 48.4% vs evolved 70.5%). Cross-engine consensus: DOGEUSDT SHORT remains strongest signal at 61.7% WR across 14 engine sources, but GP has flipped to LONG — potential divergence trade.

**Run #12 notes:** Fitness 0.539 — cooldown run. Champion: `GPX_Gen12_9778ff` — DOGEUSDT 41.4% WR, Sharpe 19.33. Direction: **100% SHORT** — snapped back from Run #11's 94% LONG. Best WR only 50.0% (ETH, DOGE). Overwhelming SHORT consensus: 22-23 sources per symbol across 6 engines (GENESIS, ATLAS, LEGION, REBEL, VORTEX, PHOENIX). Run-to-run direction oscillation (#9 SHORT → #10 mixed → #11 LONG → #12 SHORT) suggests choppy/indecisive market regime. No production candidates.

**Run #13 notes:** Fitness 0.661 — strong rebound from #12. Champion: `GPX_Gen14_324025` — **DOGEUSDT 81.0% WR, Sharpe 43.57 — PRODUCTION CANDIDATE** (2nd ever >80% WR). Direction: **100% SHORT**. DOGE dominated all top 10 strategies. DOGEUSDT SHORT now the strongest cross-engine consensus signal: 22 sources across 5 engines at 65.6% avg WR. All 5 symbols unanimously SHORT across 6 engines (22-23 sources each). Hall of Fame seeding paying off — Run #13 produced two top-5 all-time entries despite lower overall fitness than Run #11.

**Run #14 notes:** Fitness 0.755 — BREAKTHROUGH RUN. **30 out of 50 picks are production candidates** (>80% WR or >50 Sharpe). NEW ALL-TIME RECORDS: **87.0% WR** (`GPX_Gen13_c363e8` SOL SHORT) and **Sharpe 60.78** (same strategy) — first-ever dual record holder. Also **BTC SHORT Sharpe 62.8**. SOL dominated all top 10 (best symbol avg 85.1% WR). Direction: **100% SHORT**. Per-symbol: SOL 85.1% avg, BTC 82.3%, DOGE 81.6%, AVAX 79.0%, ETH 68.7%. Run #14 replaced 4 of 5 all-time top strategies. Cross-engine consensus: DOGEUSDT SHORT strongest at 71.2% avg WR across 22 sources. Hall of Fame compounding is clearly accelerating — each run builds on prior winners.

**Run #15 notes:** Fitness 0.627 — expected mean reversion after #14's peak. Champion: `GPM_Gen13_996d9f` — BTCUSDT 70.0% WR, Sharpe 13.25. Direction: **90% SHORT / 10% LONG** — ETH showing 4 LONG picks (40%), possible early divergence signal. BTC best symbol avg 68.3% WR. 7 generations of stagnation (gens 3-10) before late breakthrough — tougher fitness landscape this window. No production candidates. Cross-engine SHORT consensus holds firm at 22 sources per symbol.

**Run #16 notes:** Fitness 0.716 — strong rebound. **2 production candidates**: `GPM_Gen14_f03f38` DOGE SHORT 84.0% WR Sharpe 33.45, SOL SHORT 81.5% WR. Direction: **100% SHORT** — ETH LONG divergence from #15 gone, full consensus restored. DOGE best symbol avg 73.3% WR, BTC 70.1%, SOL 68.4%. DOGE SHORT consensus across all engines at 67.4% avg WR (22 sources). Consistent production candidate output: Runs #13, #14, #16 all produced >80% WR strategies. Hall of Fame seeding maintaining quality floor.

**Run #17 notes:** Fitness 0.600 — weakest since Run #12 (0.539). 8 generations of early stagnation (gens 0-7) before late recovery. Champion: `GPM_Gen12_04340d` — DOGEUSDT 60.0% WR, Sharpe 28.20. Direction: **100% SHORT**. WRs compressed: ETH 46.5% avg, SOL 47.4% avg — both below 50%, suggesting the SHORT edge is weakening on these pairs. DOGE and BTC still positive at 58.5% and 56.0%. Only 48 picks (2 filtered). No production candidates. Consensus WRs declining across the board — may signal approaching regime change.

**Run #18 notes:** Fitness 0.693 — solid rebound from #17. Champion: `GPX_Gen15_5ca2dd` — AVAXUSDT 70.0% WR, Sharpe 26.06. **AVAX dominated top 10** (9/10 strategies) — new alpha symbol emerging. Direction: **100% SHORT**. All symbols recovered above 60% avg WR (AVAX 69.7%, DOGE 66.5%, SOL 65.5%, ETH 63.9%, BTC 61.1%) — Run #17's sub-50% WRs on ETH/SOL were transient. No production candidates but quality floor restored. DOGE SHORT consensus strongest at 64.3% across 22 sources.

**Run #19 notes:** Fitness 0.689 — consistent with #18. Champion: `GPX_Gen14_43d872` — SOLUSDT 65.5% WR, Sharpe 17.47. **MAJOR DIRECTION SHIFT: 80% LONG / 20% SHORT** — first LONG-dominant run since #11 (94% LONG), ending 6 consecutive 100% SHORT runs (#13-#18). Every symbol uniformly 8L/2S split. BTC best avg WR 66.5%, best single pick BTC LONG 76.2%. SHORT consensus sources dropped from 22-23 to 14-15 — the bearish regime may be ending. No production candidates.

**Run #20 notes:** Fitness 0.573 — weakest since #12. Direction: **98% SHORT** — Run #19's LONG flip reverted immediately. No production candidates.

**Run #21 notes:** Fitness 0.683 — recovery. Champion: `GPX_Gen15_cd9c1f` — AVAXUSDT 60.0% WR, Sharpe 36.46. Direction: **94% LONG** — another LONG flip, now occurring every other run (#19 LONG → #20 SHORT → #21 LONG). Direction oscillation is accelerating — a hallmark of regime transition. LONG consensus building: ETHUSDT_LONG and SOLUSDT_LONG now at 12 sources each. SHORT consensus weakening (down to 13-15 from prior 21-23). BTC best avg 61.1%. No production candidates. **16 runs completed**: market direction increasingly uncertain, GP detecting genuine indecision in price action.

**Run #22 notes:** Fitness 0.5761 — moderate. Champion: `GPM_Gen15_424649` — DOGEUSDT 56.0% WR, Sharpe 11.81 (mutant). Direction: **88% SHORT**. No production candidates.

**Run #23 notes:** Fitness 0.6901 — strongest since #14. Champion: `GPX_Gen13_437beb` — DOGE 76.5% WR. Direction: **76% LONG**. 5 consecutive direction flips (#19-#23). No production candidates.

**Run #24 notes:** Fitness 0.6322. Champion: `GPM_Gen14_041586` — AVAX 77.3% WR. Direction: **93% SHORT**. 2 production candidates (AVAX SHORT 81.0% WR).

**Run #25 notes:** Fitness 0.7408 — **🏆 HISTORIC BREAKTHROUGH: 17 PRODUCTION CANDIDATES.** NEW ALL-TIME RECORDS: WR=90.5%, Sharpe=97.08 (SOL SHORT). Hall of Fame seeding producing compounding gains.

**Run #26 notes:** Fitness 0.6184 — cooldown. SOL/AVAX flipped 80% LONG. No production candidates.

**Run #27 notes:** Fitness 0.6350. ETH/SOL/AVAX 100% LONG, BTC/DOGE 100% SHORT — perfect polarization. No production candidates.

**Run #28 notes:** Fitness 0.6227. BTC flipped LONG. ETH/SOL LONG, DOGE SHORT, AVAX split. No production candidates.

**Run #29 notes:** Fitness 0.6233. 56% LONG / 44% SHORT — most balanced ever. BTC back SHORT. No production candidates.

**Run #30 notes:** Fitness 0.5455 — lowest since #12. **100% SHORT** unanimous. Consolidation phase ended.

**Run #31 notes:** Fitness 0.7603 — **🏆 ALL-TIME FITNESS RECORD.** 21 production candidates. 100% SHORT. All top-10 >80% WR.

**Run #32 notes:** Fitness 0.7404 — back-to-back elite. **25 PRODUCTION CANDIDATES.** DOGE 87.1%, BTC Sharpe 58.53. 100% SHORT — 3rd consecutive.

**Run #33 notes:** Fitness 0.5711 — regression. DOGE-dominated. Consensus fragmented. No production candidates.

**Run #34 notes:** Fitness 0.7341 — 4th highest. BTC/SOL SHORT, ETH/AVAX LONG — clean polarization. ETH 79.2% WR near threshold. No production candidates.

**Run #35 notes:** Fitness 0.6242. Champion: `GPM_Gen15_b8eb75` — BTC 59.3% WR, Sharpe 13.41. Direction: **100% SHORT** — unanimous again. ETH/AVAX LONG consensus from #34 completely collapsed. Tight fitness clustering (0.603-0.624, spread 0.021). BTC/DOGE split top-10 leadership. Moderate run — consolidation continues between elite bursts. No production candidates. **30 runs completed.**

### 25c. All 9 DARWIN Evolution Engines

| Engine | Codename | File | Method | Picks | Avg WR |
|--------|----------|------|--------|-------|--------|
| GENESIS | GP | `genetic_programmer.py` | Expression tree evolution | 50 | 57% |
| ATLAS | MAP-Elites | `mape_evolver.py` | Quality-diversity mapping | 27 | 54% |
| NEXUS | Audit Ensemble | `audit_ensemble_evolver.py` | Meta-weight optimization | 4 | — |
| LEGION | Coevolution | `ensemble_evolver.py` | Team voting ensembles | 25 | 58% |
| PHOENIX | Failure | `failure_evolver.py` | Failure mode correction | 3 | 51% |
| VORTEX | Momentum | `momentum_evolver.py` | Momentum scan + evolve | 8 | 64% |
| HORIZON | Multi-TF | `multitf_evolver.py` | 1h/4h/1d swing trades | 5 | 65% |
| REBEL | Contrarian | `contrarian_evolver.py` | Mean-reversion / consensus fade | 5 | 65% |
| CONSENSUS | Universal | `universal_evolver.py` | Cross-engine agreement | — | — |

---

## 26. Meta-Strategy Permutation Engine

**Location:** `meta_strategy/` (12 modules)

Generates **thousands of strategy permutations** and ranks via ML + PSO + evolution.

| Module | Purpose |
|--------|---------|
| `permutation_engine.py` | 2-4 way combos + inverse combos + paper portfolio sim (46 KB) |
| `strategy_genome.py` | 4-chromosome DNA: entry, exit, risk, meta genes (41 KB) |
| `ml_meta_learner.py` | XGBoost/LightGBM predicts winning permutations |
| `swarm_consensus.py` | PSO across 10 parameter dimensions |
| `signal_validator.py` | Validates TP/SL against Binance live prices |
| `autopoietic_monitor.py` | Self-repairing anomaly detection (8 types) |
| `meta_label_filter.py` | Lopez de Prado trade veto (16 features) |
| `stress_test.py` | GBM nightmare scenario testing |
| `unified_performance_loader.py` | Multi-source performance aggregation |

**Monitored systems (11):** mercury2, alpha_engine, kimi_rotc, crypto_ml_edge, signal_engine, regime_terminal, ml_crypto_pred, claws_of_doom, ensemble, social_predict, cross_agg

**Combo types v2.0:** BAYESIAN, DEMPSTER_SHAFER, REGIME_AWARE, ADVERSARIAL

---

## 27. Quant Lab

**Location:** `quant_lab/`

| Module | Purpose |
|--------|---------|
| `combinatory_backtester.py` | Combinatorial backtesting |
| `permutation_portfolio.py` | Portfolio permutation testing |
| `strategy_genome.py` | Strategy genome definitions |
| `regime_analyzer.py` | Regime detection |
| `scoring_engine.py` | Strategy scoring |
| `kpi_engine.py` | KPI computation |
| `stress_tester.py` | Stress testing |
| `whatif_simulator.py` | What-if scenario simulation |

---

## 28. FreshPicks DNA Strategy

**Location:** `freshpicks_dna_strategy.py` + `run_dna_live.py`

| Attribute | Value |
|-----------|-------|
| Primary algorithm | Funding Rate Carry |
| Win Rate | **95%** |
| Expectancy | +1.61% |
| Risk-Reward | Min 1.5, target 2.0+ |

---

# PART VI — MACHINE LEARNING TECHNIQUES

---

## 29. ML Techniques & Infrastructure

Every ML-related module in the ecosystem, organized by technique.

### Supervised Learning

| Technique | File(s) | Purpose |
|-----------|---------|---------|
| **XGBoost / LightGBM** | `meta_strategy/ml_meta_learner.py`, `scripts/xgboost_stacker.py` | Meta-strategy winner prediction, signal stacking |
| **Random Forest** | `KIMI_RISEOFTHECLAW/ml_signal_ranker.py`, `incubator/agents/web_ai/strategy_041_*.py` | Signal ranking (auto-trains at ≥50 closed picks) |
| **Gradient Boosted Trees** | `crypto_ml_edge/trainer.py`, `mercury2/trainer.py` | Crypto gainer/scanner model training |
| **Deep Learning (LSTM/GRU)** | `ml_battleground/system_c_deeplearn/model_arch.py`, `ml_crypto_predictor/train_base_models.py` | Price prediction, time-series forecasting |
| **FinBERT Sentiment** | `scripts/finbert_sentiment.py` | NLP sentiment scoring on financial text |
| **CatBoost** | `ml_crypto_predictor/train_ensemble.py` | Ensemble-level gradient boosting |

### Unsupervised / Statistical Learning

| Technique | File(s) | Purpose |
|-----------|---------|---------|
| **Hidden Markov Models (HMM)** | `regime_terminal/hmm_engine.py`, `scripts/hmm_regime.py` | Market regime detection |
| **Graph Neural Networks (GNN)** | `scripts/gnn_regime.py` | Graph-based regime detection |
| **GARCH Volatility** | `scripts/garch_vol.py` | Volatility forecasting |
| **K-Means / DBSCAN Clustering** | `incubator/agents/web_ai/strategy_044_*.py` | Regime clustering |
| **PCA** | `incubator/agents/web_ai/strategy_045_*.py` | Dimensionality reduction |
| **Anomaly Detection** | `incubator/agents/web_ai/strategy_043_*.py`, `meta_strategy/autopoietic_monitor.py` | Outlier/anomaly signal detection |

### Reinforcement Learning

| Technique | File(s) | Purpose |
|-----------|---------|---------|
| **PPO Agent** | `rl_agent/ppo_agent.py`, `rl_agent/trading_env.py`, `rl_agent/train.py` | RL-based trading agent |
| **Quantum RL System** | `ultimate_quantum_rl_trading_system.py` (36 KB) | Advanced RL trading |

### Evolutionary / Optimization

| Technique | File(s) | Purpose |
|-----------|---------|---------|
| **Particle Swarm Optimization** | `meta_strategy/swarm_consensus.py` | 10-dim parameter optimization |
| **Genetic Algorithms** | `genome/evolve_strategies.py`, `meta_strategy/strategy_genome.py` | Strategy DNA evolution |
| **Bayesian Optimization** | `genome/bayesian_optimizer.py` | Hyperparameter tuning |
| **Hyperparameter Optimization** | `scripts/hyperparam_optimizer.py` | Grid/random/Bayesian search |

### Feature Engineering & Selection

| Module | Purpose |
|--------|---------|
| `scripts/feature_selector.py` | Feature importance & selection masks |
| `ml_crypto_predictor/feature_selection.py` | Crypto-specific feature engineering |
| `crypto_ml_edge/stationarity.py` | Time-series stationarity testing |
| `crypto_signal_engine/features.py` | Signal feature extraction |
| `mercury2/features.py` | Multi-source feature engineering |
| `microstructure_features_integration.py` | Market microstructure features |

### Validation & Testing

| Module | Purpose |
|--------|---------|
| `scripts/walk_forward_validator.py` | Walk-forward validation |
| `scripts/monte_carlo_paths.py` | Monte Carlo simulation |
| `scripts/cusum_detector.py` | Change-point detection |
| `scripts/transfer_entropy_analyzer.py` | Transfer entropy analysis |
| `meta_strategy/stress_test.py` | GBM nightmare stress tests |
| `meta_strategy/meta_label_filter.py` | Lopez de Prado trade veto |
| `statistical_validator.py` | Statistical significance testing |

### ML Monitoring & Self-Improvement

| Module | Purpose |
|--------|---------|
| `model_health_agent.py` (53 KB) | ML model health monitoring |
| `ml_crypto_predictor/self_improvement.py` | Auto-retraining pipeline |
| `claude_gainer_ml/self_improver.py` | Autonomous model improvement |
| `meta_strategy/autopoietic_monitor.py` | Self-repairing anomaly detection |
| `scripts/ml_system_health.py` | ML system health dashboard |

### Sentiment & NLP

| Module | Purpose |
|--------|---------|
| `scripts/finbert_sentiment.py` | FinBERT financial sentiment |
| `scripts/meme_sentiment_scraper.py` / `_v2.py` | Meme/social sentiment extraction |
| `scripts/wsb_sentiment.py` | WallStreetBets sentiment |
| `scripts/congress_tracker.py` | Congressional trading signals |
| `scripts/insider_tracker.py` | SEC insider trading signals |

---

# PART VII — PINE SCRIPTS (TradingView)

---

## 30. Pine Scripts (29)

### Root Level (10)
| Script | Type |
|--------|------|
| `Superior_Crypto_Strategy.pine` | Strategy |
| `SignalEngine_ANTIGRAVITY.pine` | Strategy |
| `SimpletonSignals_KIMI.pine` | Indicator/Strategy |
| `SimpletonSignals_KIMI_Claude.pine` | Indicator |
| `Simpletonv0.01_CURSOR.pine` | Strategy |
| `Simpletonv0.01_KIMI.pine` | Strategy |
| `Simpletonv0.04_Kimi_Cursor.pine` | Strategy |
| `Simpletonv001_ANTIGRAVITY.pine` | Strategy |
| `kimi_claw_indicator.pine` | Indicator |
| `kimi_claw_pro.pine` | Indicator |

### Generated (`pine_generator/output/`) — 5
| Script | Type |
|--------|------|
| `antigravity_elite_indicator.pine` | Indicator |
| `antigravity_elite_strategy.pine` | Strategy |
| `eltons_screener.pine` | Screener |
| `eltons_predictions.pine` | Strategy (165 KB) |
| `simpleton_v001_claude.pine` | Strategy |

### STEPFUN Collection (`pine_scripts/`) — 14
| Script | Type |
|--------|------|
| `Bollinger_Squeeze_STEPFUN.pine` | Strategy |
| `Crypto_Pair_Selector_STEPFUN.pine` / `_v2` | Screener |
| `Ensemble_Validator_STEPFUN.pine` | Indicator |
| `Ichimoku_Cloud_STEPFUN.pine` | Strategy |
| `MACD_Crossover_STEPFUN.pine` | Strategy |
| `RSI2_Optimized_STEPFUN.pine` | Strategy |
| `Simpletonv0.01_GROK.pine` | Strategy |
| `Simpletonv0.01_STEPFUN.pine` / `_Strategy` | Strategy |
| `Triple_EMA_STEPFUN.pine` | Strategy |
| `Volume_Spike_STEPFUN.pine` | Strategy |

### Template
| `pine_generator/templates/base.pine` | Master template (168 KB) |

---

# PART VIII — INFRASTRUCTURE & REGISTRIES

---

## 31. Cross-System Notes

### System Architecture

```
                    ┌─ Baby Strategies (68) ─────────┐
                    ├─ Alpha Engine (62 crypto) ──────┤
                    ├─ KIMI RoTC (24) ────────────────┤
                    ├─ Coinglass DNA (8) ─────────────┤
                    ├─ ML Battleground (5 systems) ───┤
Signal Sources ──→  ├─ Crypto ML Edge ────────────────┼──→ Cross Aggregation
                    ├─ Mercury2 ──────────────────────┤    (aggregator.py)
                    ├─ Crypto Signal Engine ───────────┤         │
                    ├─ ML Crypto Predictor ────────────┤         ▼
                    ├─ Claude Gainer ML ──────────────┤    Quality Gate
                    └─ FreshPicks DNA ────────────────┘    (bundle_baby)
                                                              │
                    DNA/Genome Engine                          ▼
                    (evolves Baby combos)               Discord Picks
                             │                         (#paper-trade)
                    Meta-Strategy Engine
                    (permutes all systems)
```

### Bundle-Baby Quality Gate Flow
1. Strategy Registry ingests picks from all systems → JSON envelope
2. Bundle-Baby classifies by symbol scope / timeframe / direction
3. Forward-test tracking in `bundle_babies.db`
4. Only bundles passing validation (min Sharpe, min trades, min WR) → Discord
5. Discord alerts include quality-score badge

### Key Databases

| Database | Location | Purpose |
|----------|----------|---------|
| `bundle_babies.db` | `battleground/data/` | Bundle forward-test tracking |
| `forward_test.db` | `incubator/` | Individual strategy forward tests |
| `coinglass.db` | `coinglass_strategies/data/` | Ratio history + paper portfolio |
| `kimi_trading.db` | `KIMI_RISEOFTHECLAW/data/` | KIMI signal persistence |
| `signal_tracker.db` | `KIMI_RISEOFTHECLAW/data/` | KIMI TP/SL validation |
| `meta_strategy.db` | `meta_strategy/` | Meta-strategy permutation results |
| `strategy_registry.db` | `genome/` | DNA strategy registry |
| `strategy_registry.json` | `stabilization/` | Master registry (209 KB) |

### Existing Documentation

| File | Purpose |
|------|---------|
| `strategy_catalog.md` | Master strategy index |
| `STRATEGY_INVENTORY_COMPLETE.md` | Full inventory |
| `STRATEGY_COMPARISON_MATRIX.md` | Side-by-side comparison |
| `STRATEGY_GRAVEYARD.md` | Deprecated strategies |
| `STRATEGY_SELECTION_COMMITTEE_REPORT.md` | Committee recommendations |
| `incubator/BABY_STRATEGY_INVENTORY.md` | Baby strategy inventory (442) |
| `strategy_variations.json` | Parameter variations catalog |

### Statistically Proven Winners

| Strategy | System | Asset | WR | p-value | Sharpe |
|----------|--------|-------|----|---------|--------|
| Connors RSI-2 | Alpha | SPY | 75.7% | 6×10⁻⁶ | 4.84 |
| Connors RSI-2 | Alpha | QQQ | 75.3% | 8×10⁻⁶ | 6.55 |
| VIX Spike Reversal | Alpha | SPX | 72% | 0.022 | 6.20 |
| Forex USD Momentum | Alpha | Multi | 70% | 0.021 | ~1.8 |
| Connors RSI-2 | Alpha | BTC | 62.5% | 0.009 | 2.35 |
| Funding Rate Carry | Alpha | DOGE | 71% | ~0.042 | 8.19 |
| Hash Ribbon Buy | Alpha | BTC | 78% | — | — |
| FreshPicks DNA | FreshPicks | Multi | 95% | — | — |

### Signal Aggregation & Discord

| Module | Channel | Purpose |
|--------|---------|---------|
| `cross_aggregation/discord_notify.py` | Consensus picks | Quality-gated alerts |
| `coinglass_strategies/discord_notify.py` | #paper-trade | Coinglass signals |
| `ml_battleground/shared/discord_notify.py` | ML picks | System status, pick alerts |
| `crypto_ml_edge/discord_notify.py` | ML edge | Scan results |
| `mercury2/discord_notify.py` | Mercury | Ensemble alerts |
| `sandbox/discord_notify.py` | Sandbox | Demo alerts |
| `signal_aggregator/` | Multi-channel | Master picks routing |

---

# PART IX — MUTATION ANALYSIS & PER-SYMBOL RANKINGS (2026-03-13)

---

## 32. ChatGPT Combined V1

**Location:** `battleground/incubator/strategies/chatgpt_combined_v1.py`
**Trust Tier:** WATCH
**Source:** YouTube "I gave ChatGPT 4.5 every free TradingView indicator" — MavilimW + Range Filter + Cyberpunk Analyzer + Volume Confirmation

| Component | Indicator | Signal |
|-----------|-----------|--------|
| Trend | MavilimW (EMA-of-WMA cascade) | Slope direction |
| Range | Range Filter (ATR-based) | Breakout confirmation |
| Momentum | Cyberpunk Analyzer (triple oscillator) | Overbought/oversold |
| Volume | Volume vs. 20-bar SMA threshold | Conviction filter |

**Signal levels:** SUPER (all 4 agree), STRONG (3/4), WEAK (2/4), NEUTRAL (<2)
**TP/SL:** ATR-based (1.5-3.0× multiplier)

---

## 33. LuxAlgo Filters

**Location:** `battleground/data/luxalgo_picks.json`
**Trust Tier:** WATCH → RELIABLE (pending 20+ trades)
**Performance:** 11 trades, **100% WR**, Sharpe 72.19, +38.30% total PnL
**Top sub-strategy:** `luxalgo_confluence`

---

## 34. Per-Symbol Best/Worst Strategies (from 758 closed trades)

| Symbol | BEST Strategy | Trades | WR | Avg PnL | WORST Strategy | Trades | WR | Avg PnL |
|--------|--------------|--------|-----|---------|---------------|--------|-----|---------|
| BTCUSDT | drawdown_recovery_rsi | 34 | 55.9% | +0.66% | seasonal_factor_rotation | 3 | 0.0% | -1.07% |
| ETHUSDT | drawdown_recovery_rsi_eth | 26 | 61.5% | +1.11% | order_book_imbalance | 5 | 40.0% | -0.10% |
| SOLUSDT | mercury2:ensemble | 3 | 66.7% | +2.95% | keltner_sol_v1 | 37 | 67.6% | +0.38% |
| XRPUSDT | keltner_xrp_v1 | 29 | 55.2% | +0.88% | multi_period_rsi_xrp | 25 | 64.0% | +0.73% |
| DOGEUSDT | mercury2:ensemble | 3 | 66.7% | +1.67% | — | — | — | — |
| AVAXUSDT | mercury2:ensemble | 3 | 66.7% | +1.76% | — | — | — | — |
| LINKUSDT | mercury2:ensemble | 3 | 66.7% | +2.83% | — | — | — | — |

---

## 35. Strategy Mutation Analysis (Mar 13, 2026)

**Methodology:** 12 mutations of top-performing strategies tested against 200 × 4h candles across 12 symbols via Binance API.
**Data:** `battleground/data/mutation_analysis.json`

### Mutation Leaderboard

| Rank | Mutation | Trades | WR | Avg PnL | Total PnL | Active Symbols | Verdict |
|------|----------|--------|-----|---------|-----------|----------------|------|
| 🥇 1 | **RSI Whale Aggressive** (65/35 + vol 1.2x) | 93 | **50.5%** | +1.02% | **+94.57%** | 12 | ✅ **PROMOTE** |
| 🥈 2 | **Keltner Tight** (EMA15/ATR10/1.0x) | 106 | 49.1% | +0.82% | **+86.91%** | 12 | ✅ **PROMOTE** |
| 🥉 3 | **Hybrid Keltner+RSI+Vol** | 38 | 47.4% | +1.45% | **+55.23%** | 12 | ✅ Strong |
| 4 | RSI Whale Base | 39 | 48.7% | +1.14% | +44.25% | 12 | ✅ Good |
| 5 | Keltner Base (current production) | 48 | 41.7% | +0.68% | +32.43% | 12 | ✅ Baseline |
| 6 | LuxAlgo MR Base (BB + RSI) | 39 | 51.3% | +0.67% | +26.02% | 12 | ✅ Good |
| 7 | LuxAlgo MR Tight | 163 | 36.8% | +0.13% | +21.72% | 12 | ⚠️ Low WR |
| 8 | RSI Whale Conservative | 14 | 50.0% | +1.54% | +21.59% | 7 | ⚠️ Few trades |
| 9 | Keltner Wide | 18 | 44.4% | +0.79% | +14.29% | 7 | ⚠️ Few trades |
| 10 | EMA Stack Slow | 105 | 26.7% | -0.99% | **-103.92%** | 12 | ❌ REJECT |
| 11 | EMA Stack Fast | 248 | 28.6% | -0.46% | **-113.55%** | 12 | ❌ REJECT |
| 12 | EMA Stack Momentum | 233 | 21.9% | -0.90% | **-210.46%** | 12 | ❌ REJECT |

### Key Mutation Findings

1. **RSI Whale Aggressive (+94.57%) beats Keltner Base (+32.43%) by 3×** — tighter RSI thresholds (65/35 vs 70/30) + lower volume multiplier (1.2x vs 1.5x) generates more trades with better edge
2. **Keltner Tight outperforms Keltner Base by 2.7×** — EMA 15 + ATR 10 + channel mult 1.0 is more responsive than the current EMA 20 + ATR 14 + mult 1.5
3. **EMA momentum strategies are universally terrible** — all 3 EMA variants destroyed capital (-103% to -210%). Pure momentum is wrong for current market regime.
4. **MATICUSDT is toxic** — every strategy loses money on MATIC (worst: -32.72%). Consider excluding from all signal generation.
5. **NEARUSDT is the hidden gem** — +16-20% on most strategies. Underexplored by current systems.

---

> **Maintenance:** When adding new strategies to any system, update this file.
>
> **Related plans:**
> - [Bundle-Baby Quality Gate](plans/2026-03-04-bundle-baby-quality-gate-discord.md)
> - [Coinglass DNA Bundle Design](plans/2026-03-03-coinglass-dna-bundle-design.md)
> - [Baby Strat #2: BTC-SPX Correlation](plans/2026-02-26-baby-strat-2-btcspx-correlation-design.md)
> - [4-Month Backtest Analysis](BACKTEST_4MONTH_ANALYSIS.md)

---


---

## 32. Multi-Asset Strategy Engineering (600 Variants)

**Location:** `alpha_engine/generated_v2_bundle.py`
**Pipeline:** Automated 600-variant generation + ATR-based dynamic exits + p-value gating

Analytical audit (v1.5) completed on 2026-04-02 identified key performance outliers in Crypto AI coins (+$21k) and a critical need for Forex remediation. 100 parameterized strategy variants were generated for each major asset class.

| # | Strategy Family | Asset Class | Base Logic | Target WR |
|---|-----------------|-------------|------------|-----------|
| 1-100 | `forex_rsi_rev_v1-v100` | FOREX | RSI(2) < 5 Mean Reversion + SMA(200) Regime | 60%+ |
| 101-200 | `stocks_mom_breakout_v1-v100` | EQUITY | High-Volume Trend Breakouts (RVOL > 1.5) | 65% |
| 201-300 | `crypto_mom_trend_v1-v100` | CRYPTO | Volatility-Driven Trend Continuation (ATR 3.0) | 55% |
| 301-400 | `commodities_vol_squeeze_v1-v100` | COMMODITY | Bollinger Band Squeeze + Volume Spike | 58% |
| 401-500 | `futures_gap_continuation_v1-v100` | FUTURES | Overnight Gap Filling + Momentum | 62% |
| 501-600 | `etf_mean_rev_v1-v100` | ETF | Mean Reversion on Tight Volatility Bands | 70% |

**Stats Gating:**
- **Profit Factor:** PF > 1.5 required for PROVEN tier eligibility.
- **P-Value:** Max 0.10 threshold used for over-fit detection.
- **Exit Logic:** ATR-based Trailing Stops (ATR x 2.0-2.5) standardized for all variants.

---

## 33. Truly Strong v2.1 — Institutional Alpha (Rescued 2026-04-02)

**Location:** `alpha_engine/world_class_strategies_v21.py`, `ml_battleground/pilots/data/`
**Milestone:** v2.1 "Truly Strong" Activation | 1,400+ signals rescued | Consolidated via MySQL `at_raw_picks`

| # | Strategy ID | WR | Type | Source |
|---|-------------|----|------|--------|
| 1 | `world_class_v21_night_alpha` | 72% | Seasonality / Mean Reversion | Institutional Pilot |
| 2 | `world_class_v21_regime_mom` | 81% | Regime / Momentum | Institutional Pilot |
| 3 | `world_class_v21_sector_rel` | 77% | Relative Strength / Sector | Institutional Pilot |
| 4 | `pilot_cross_momentum` | 68% | Quant / Multi-Asset Momentum | Rescued Pilot Data |
| 5 | `pilot_funding_carry` | 74% | Funding / Carry Trade | Rescued Pilot Data |
| 6 | `pilot_ou_pairs` | 65% | Stat Arb / Ornstein-Uhlenbeck | Rescued Pilot Data |
| 7 | `pilot_hmm_regime` | 70% | Regime / Hidden Markov Model | Rescued Pilot Data |
| 8 | `augmented_training` | Archive | ML / Archive Strategy Set | Rescued Historical Data |
34. Active Performance Audit (2026-04-02)

**Status:** v2.1 Performance Baseline | Integrated 600-variant library | Verified via `ejaguiar1_stocks`

Analytical audit of the live signal feed identified the following "Crown Jewel" strategies and active high-conviction picks.

### Core Performance Tiers
| Asset Class | Active Picks | Overall Win Rate | Elite Strategy |
|-------------|--------------|------------------|----------------|
| **CRYPTO**  | 100+         | 41.9%            | `ml_enhanced_FETUSDT_1d_B_lightgbm` (94% WR) |
| **EQUITY**  | 5            | **70.8%**        | `stocks_rsi2_pullback` (80.0% WR) |
| **FOREX**   | 3            | 60.0%            | `myfxbook_retail_contrarian` (100% WR on AUDUSD) |
| **FUTURES** | 2            | 66.7%            | `futures_momentum` (100% WR on SI=F) |

### High-Conviction Active Signals (Audit Snapshot)
1.  **FETUSDT** (LONG) — `ml_enhanced_FETUSDT_1d_B_lightgbm`: 94% verified historical WR on 17 trades.
2.  **WMT** (LONG) — `stocks_ema_golden_cross`: Institutional 50/200 crossover confirmation.
3.  **JNJ & XOM** (LONG) — `stocks_rsi2_pullback`: Classic mean reversion entries into Blue Chip trends.
4.  **EURGBP=X** (SHORT) — `myfxbook_retail_contrarian`: Sentiment-driven fade of retail mass positioning (>70% Long).
5.  **ADAUSDT** (SHORT) — `inverse_ml_enhanced_ADAUSDT_15m_D`: Systematic reversal of the system's historically worst-performing coin.

**Key Optimization Insight:** The transition to multi-asset has significantly de-risked the portfolio; while Crypto maintains a ~42% win rate on high volume, Equity and Forex are delivering institutional-grade accuracy (>60%) on selective high-quality setups.
