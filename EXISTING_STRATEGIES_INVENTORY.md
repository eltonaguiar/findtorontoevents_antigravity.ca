# Existing Strategies Inventory
## What Has Already Been Built - Reference for AI Agents

**Last Updated:** February 26, 2026  
**Purpose:** Prevent duplicate strategy creation  
**Rule:** Check this file before creating any new strategy

---

## 🎯 QUICK REFERENCE - Strategy Categories

| Category | Count | Status | File Location |
|----------|-------|--------|---------------|
| **Tier 1 Validated** | 5 | Production | `KIMI_CLAW_RESEARCH_FEB162026/strategies_tier1.py` |
| **ML Battleground** | 5 systems | Active | `ml_battleground/system_*/` |
| **Alpha Engine** | 114 strategies | Mixed | `alpha_engine/` |
| **Crypto Specific** | 14 strategies | Active | `alpha_engine/crypto_strategies.py` |
| **Forex Specific** | 6 strategies | Active | `alpha_engine/forex_strategies.py` |
| **Mercury 2** | 1 system (XGBoost) | Best Performer | `crypto_signal_engine/` |
| **Documented (100 Alg)** | 100 cataloged | Partial | `100_ALGORITHMS_MASTER_CATALOG.md` |
| **Stock Competition** | 11 algorithms | Backtested | `alpha_engine/algorithm_competition/` |
| **Web AI Baby Strats** | 112 strategies | Sandbox | `incubator/agents/web_ai/` |
| **Web AI SOC Batches** | 100 strategies (10 families × 10) | Sandbox | `incubator/agents/web_ai/crypto_soc_*` |

**GRAND TOTAL: ~367 strategy implementations**

---

## ✅ TIER 1 VALIDATED STRATEGIES (Do NOT Duplicate)

These 5 strategies survived forward-testing. They are the gold standard.

### 1. Funding Rate Arbitrage
- **Type:** Crypto arbitrage
- **Logic:** Long spot, short perp when funding rate extremely negative
- **Win Rate:** 88% viability score
- **Status:** PRODUCTION
- **Where:** `KIMI_CLAW_RESEARCH_FEB162026/strategies_tier1.py`
- **Duplicate Risk:** HIGH - don't create another funding rate strategy

### 2. Pairs Trading (Cointegration)
- **Type:** Statistical arbitrage
- **Logic:** Find cointegrated pairs, trade mean reversion of spread
- **Win Rate:** 79% viability
- **Status:** PRODUCTION
- **Where:** `KIMI_CLAW_RESEARCH_FEB162026/strategies_tier1.py`
- **Duplicate Risk:** HIGH

### 3. Betting Against Beta (BAB)
- **Type:** Equity factor
- **Logic:** Long low-beta stocks, short high-beta stocks
- **Win Rate:** 77% viability
- **Status:** PRODUCTION
- **Where:** `KIMI_CLAW_RESEARCH_FEB162026/strategies_tier1.py`
- **Duplicate Risk:** MEDIUM (equity only)

### 4. Flash Crash Reversal
- **Type:** Event-driven
- **Logic:** Buy after extreme downside moves with volume spike
- **Win Rate:** 71% viability
- **Status:** PRODUCTION
- **Where:** `KIMI_CLAW_RESEARCH_FEB162026/strategies_tier1.py`
- **Duplicate Risk:** HIGH - many similar strategies exist

### 5. Quality Minus Junk (QMJ)
- **Type:** Equity factor
- **Logic:** Long high-quality stocks, short low-quality
- **Win Rate:** 75% viability
- **Status:** PRODUCTION
- **Where:** `KIMI_CLAW_RESEARCH_FEB162026/strategies_tier1.py`
- **Duplicate Risk:** MEDIUM

---

## 🔬 ML BATTLEGROUND SYSTEMS (Do NOT Duplicate Core Logic)

These 5 coordinated systems work together. Don't recreate them.

### System A: "The Filter" (ML-Filtered Strategy Signals)
- **Logic:** ML filters traditional strategy signals (MACD, RSI, etc.)
- **Assets:** Crypto
- **Where:** `ml_battleground/system_a_filter/`
- **Status:** Active
- **Duplicate Risk:** HIGH

### System B: "The Regime" (PRIMARY - 56.6% WR, Sharpe 9.91)
- **Logic:** HMM regime detection + strategy routing
- **Assets:** Crypto
- **Where:** `ml_battleground/system_b_regime/`
- **Status:** PRIMARY SYSTEM
- **Duplicate Risk:** HIGH - this is the best performer

### System C: "The Neural Net" (Deep Learning)
- **Logic:** GRU-Attention neural network
- **Assets:** Crypto
- **Where:** `ml_battleground/system_c_deeplearn/`
- **Status:** Active
- **Duplicate Risk:** HIGH

### System D: "The Carry Trade" (Independent)
- **Logic:** Funding rate contrarian carry
- **Assets:** Crypto
- **Where:** `ml_battleground/system_d_carry/`
- **Status:** Active
- **Duplicate Risk:** HIGH

### System E: "The Momentum" (Independent)
- **Logic:** Cross-sectional momentum
- **Assets:** Crypto
- **Where:** `ml_battleground/system_e_momentum/`
- **Status:** Active
- **Duplicate Risk:** HIGH

---

## 📊 MERCURY 2 (Best Performer - Do NOT Duplicate)

**Status:** BEATING MARKET | 94% Win Rate | +44.32% avg

### Architecture
- **Models:** XGBoost Ensemble (3 classifiers: Conservative/Aggressive/Balanced)
- **Features:** 12 features (returns, RSI, MACD, ATR, volume, trend, sentiment)
- **Assets:** 20 crypto pairs (BTC, ETH, SOL, etc.)
- **Logic:** 
  - LONG: Contrarian dip-buy (default)
  - SHORT: RSI > 70 + below 200SMA
  - TP: 2× ATR
  - SL: 1.5× ATR
  - Max hold: 24 hours
- **Where:** `crypto_signal_engine/`
- **Duplicate Risk:** VERY HIGH - this is the current best system

---

## 🚀 CRYPTO STRATEGIES (14 in alpha_engine - Check Before Creating)

Located in: `alpha_engine/crypto_strategies.py`

| # | Strategy | Type | Logic | Duplicate Risk |
|---|----------|------|-------|----------------|
| 1 | BTC Ichimoku Cloud | Trend | Weekly-equivalent Ichimoku on daily | MEDIUM |
| 2 | BTC 200-Day SMA Bounce | Mean Reversion | Buy bounces near 200d SMA | HIGH |
| 3 | Fear & Greed Contrarian | Sentiment | Buy extreme fear (<25) | HIGH |
| 4 | Funding Rate Extreme Reversal | Mean Reversion | Buy when funding <-0.01% | VERY HIGH |
| 5 | Wyckoff Accumulation Spring | Technical | Detect accumulation pattern | MEDIUM |
| 6 | Smart Money FVG | Technical | Buy at unfilled fair value gaps | MEDIUM |
| 7 | RSI Hidden Divergence | Momentum | Hidden bullish divergence | HIGH |
| 8 | Crypto Breakout + Volume | Momentum | 30-day breakout with 3× volume | HIGH |
| 9 | StochRSI Oversold Bounce | Mean Reversion | StochRSI crossover | HIGH |
| 10 | Hurst Mean Reversion | Statistical | Hurst <0.4 + lower BB | MEDIUM |
| 11 | Entropy-Adaptive RSI | Adaptive | Shannon entropy thresholds | MEDIUM |
| 12 | CoinGecko Trending + Volume | Momentum | Trending coins + volume | MEDIUM |
| 13 | **ATRRegimeRSI** | Vol-Regime + Mean Rev | ATR regime gatekeeper + RSI <35 in low-vol only | MEDIUM |
| 14 | **FearGreed_Reversion** | Sentiment + Mean Rev | Fear<25 / Greed>75 with SMA(20)+volume confirmation and 5% risk cap | HIGH |

---

## 💱 FOREX STRATEGIES (6 Total)

Located in: `alpha_engine/forex_strategies.py`

| # | Strategy | Type | Logic | Duplicate Risk |
|---|----------|------|-------|----------------|
| 1 | Carry Trade with Momentum | Carry | Long high-yield + momentum | HIGH |
| 2 | 200-Day SMA Mean Reversion | Mean Reversion | Fade extreme deviations | HIGH |
| 3 | JPY Risk-Off Regime | Macro | Short JPY during risk-off | MEDIUM |
| 4 | DXY Correlation Regime | Macro | Trade EUR/USD based on DXY | MEDIUM |
| 5 | London Breakout Session | Session | London session volatility | MEDIUM |
| 6 | Bollinger Squeeze Momentum | Volatility | BB squeeze breakouts | HIGH |

---

## 📈 STOCK STRATEGIES (From Competition)

Located in: `alpha_engine/algorithm_competition/`

| Algorithm | Type | Description | Duplicate Risk |
|-----------|------|-------------|----------------|
| Meta Learner (God-Mode) | Ensemble | Regime-aware aggregator | VERY HIGH |
| Classic Momentum | Momentum | 6-month momentum, skip month | HIGH |
| Trend Following | Trend | Above 50/200 MA | HIGH |
| Breakout Momentum | Momentum | 52-week highs + volume | HIGH |
| Bollinger Mean Reversion | Mean Reversion | BB oversold/overbought | HIGH |
| Short-Term Reversal | Mean Reversion | 5-day losers | HIGH |
| Quality Compounders | Quality | High ROE/ROIC | MEDIUM |
| Value + Quality | Value | Undervalued + quality | MEDIUM |
| Dividend Aristocrats | Dividend | 25+ years dividend growth | LOW |
| Earnings Drift (PEAD) | Event | Post-earnings drift | MEDIUM |
| Consecutive Beats | Momentum | 3+ positive periods | MEDIUM |
| ML Ranker (LightGBM) | ML | Composite ranking | HIGH |

---

## 🐣 WEB AI BABY STRATEGIES (112 Non-SOC — `incubator/agents/web_ai/`)

### Category A: Pre-existing Advanced Strategies (12 files)

These were created by earlier agents with full v1 naming convention.

| # | File | Type | Core Logic | Duplicate Risk |
|---|------|------|------------|----------------|
| 1 | `atr_regime_rsi.py` | Vol-Regime Gate | ATR regime RSI <35 in low-vol | HIGH |
| 2 | `fear_greed_reversion.py` | Sentiment | Fear<25/Greed>75 + SMA/vol confirm | VERY HIGH |
| 3 | `crypto_adx_pullback_sortino_guard_v1.py` | Trend + Risk | ADX pullback + Sortino gate | MEDIUM |
| 4 | `crypto_beta_neutral_sector_rotation_v1.py` | Cross-Sect | Beta-neutral sector rotation | LOW |
| 5 | `crypto_corrshock_dispersion_reversion_v1.py` | Stat-Arb | Correlation shock dispersion | LOW |
| 6 | `crypto_donchian_retest_voltarget_kellycap_v1.py` | Breakout | Donchian retest + Kelly sizing | MEDIUM |
| 7 | `crypto_entropy_hurst_dual_engine_v1.py` | Regime | Entropy + Hurst dual engine | MEDIUM |
| 8 | `crypto_fng_funding_regime_router_v1.py` | Sentiment | FNG + funding regime router | VERY HIGH |
| 9 | `crypto_funding_curvature_wick_absorption_v1.py` | Micro | Funding curvature + wicks | MEDIUM |
| 10 | `crypto_mark_spot_premium_meanrevert_v1.py` | Arb | Mark/spot premium mean revert | LOW |
| 11 | `crypto_mtf_trend_resume_funding_flush_v1.py` | Multi-TF | MTF trend + funding flush | MEDIUM |
| 12 | `crossasset_btcspx_vix_residual_router_v1.py` | Cross-Asset | BTC/SPX/VIX residual router | LOW |
| 13 | `crossasset_spxbtc_zscore_divergence_v1.py` | Cross-Asset | SPX/BTC z-score divergence | LOW |
| 14 | `dxy_divergence_alpha.py` | Macro | DXY divergence | LOW |
| 15 | `mean_reversion_momentum.py` | Hybrid | Mean-reversion + momentum | HIGH |
| 16 | `volume_breakout_regime_switch.py` | Regime | Volume breakout regime switch | MEDIUM |
| 17 | `whale_vwap_breakout.py` | Microstructure | Whale VWAP breakout | LOW |

### Category B: 100 Baby Strategies (Created Feb 26, 2026)

All located in `incubator/agents/web_ai/`. Each is a self-contained class with `generate_signals()`.

#### B1. Volatility & ATR-Based (15 strategies)

| # | File | Logic | Unique Value | Dup Risk |
|---|------|-------|-------------|---------|
| 1 | `vol_contraction_breakout.py` | ATR ratio <0.75 + 20-bar high break | VCP-style contraction | HIGH |
| 2 | `atr_percentile_gate.py` | ATR pct <0.25 + EMA(20) trend | Percentile gating | MEDIUM |
| 3 | `keltner_squeeze_breakout.py` | Keltner width pct <10% + upper break | Channel squeeze | HIGH |
| 4 | `range_contraction_revert.py` | Range pct <15% + RSI <35 | Contraction + oversold | MEDIUM |
| 5 | `dual_atr_regime.py` | ATR(7)/ATR(21) <0.7 + VWAP proxy | Dual timeframe vol | MEDIUM |
| 6 | `volatility_mean_reversion.py` | RVol drops 50%+ from peak | Vol compression from peak | MEDIUM |
| 7 | `volatility_breakout_ratio.py` | Close > prev high by 1+ ATR | ATR-momentum breakout | HIGH |
| 8 | `atr_expansion_momentum.py` | ATR expands 1.5x + bullish | Vol expansion + direction | MEDIUM |
| 9 | `true_range_percentile.py` | TR at 10th percentile + bullish bar | Extreme quiet breakout | MEDIUM |
| 10 | `price_channel_squeeze.py` | Donchian width at 10th pct + break | Channel squeeze variant | HIGH |
| 11 | `acceleration_bands_squeeze.py` | Accel band width at 15th pct | Band squeeze variant | MEDIUM |
| 12 | `range_expansion_alert.py` | Range expands 2x from avg after contraction | Expansion signal | MEDIUM |
| 13 | `narrow_range_nr7.py` | NR7 (narrowest range 7 bars) + upside break | Classic NR7 pattern | MEDIUM |
| 14 | `bollinger_width_percentile.py` | BB width at 10th pct + near lower band | BB squeeze variant | HIGH |
| 15 | `supertrend_proxy.py` | Simplified supertrend flip detection | Trend flip | MEDIUM |

#### B2. RSI & Momentum-Based (14 strategies)

| # | File | Logic | Unique Value | Dup Risk |
|---|------|-------|-------------|---------|
| 16 | `drawdown_recovery_rsi.py` | Drawdown >6% + RSI <35 | Drawdown-gated RSI | MEDIUM |
| 17 | `multi_period_rsi_confluence.py` | RSI14 <35 AND RSI50 <40 | Dual-period RSI | MEDIUM |
| 18 | `rsi_velocity_cross.py` | RSI ROC flips positive below 40 | RSI acceleration | MEDIUM |
| 19 | `rsi_mean_cross.py` | RSI crosses above its own 10-SMA below 40 | RSI vs own MA | MEDIUM |
| 20 | `connors_rsi.py` | Composite RSI (3-period + streak + rank) <15 | ConnorsRSI | MEDIUM |
| 21 | `roc_acceleration_trend.py` | ROC accel (ROC of ROC) positive + EMA confirm | 2nd derivative | LOW |
| 22 | `momentum_percentile_rank.py` | Momentum pct rank <15th + RSI <40 | Rank-based | MEDIUM |
| 23 | `momentum_stall_reversal.py` | Down ROC stalls near zero | Momentum exhaustion | LOW |
| 24 | `dual_timeframe_momentum.py` | ROC5 >0 AND ROC20 >0 AND fast>slow | Dual TF alignment | MEDIUM |
| 25 | `smoothed_momentum_crossover.py` | Smoothed momentum crosses zero | EMA-smoothed mom | MEDIUM |
| 26 | `price_acceleration_gate.py` | 2nd derivative of price flips positive | Price acceleration | LOW |
| 27 | `momentum_divergence_rsi.py` | Price lower low + ROC higher low + RSI <45 | Momentum div | MEDIUM |
| 28 | `stochastic_divergence.py` | Price lower low + Stoch %K higher low <30 | Stoch divergence | MEDIUM |
| 29 | `williams_r_extreme.py` | Williams %R <-90 + ATR contraction | Extreme oversold | MEDIUM |

#### B3. EMA & Moving Average-Based (8 strategies)

| # | File | Logic | Unique Value | Dup Risk |
|---|------|-------|-------------|---------|
| 30 | `ema_slope_divergence.py` | EMA slope flips from negative to positive | Slope detection | MEDIUM |
| 31 | `ema_ribbon_compression.py` | 8/13/21 EMAs within 0.5% + break above | Ribbon squeeze | MEDIUM |
| 32 | `triple_ema_alignment.py` | 5/13/34 EMAs align bullish + pullback to 13 | Triple alignment | MEDIUM |
| 33 | `ema_crossover_pullback.py` | 10/30 EMA golden cross + pullback to 10 | Cross + pullback | HIGH |
| 34 | `quad_ema_cross.py` | 5/10/20/50 EMAs all align bullish | Quad alignment | MEDIUM |
| 35 | `weighted_close_trend.py` | Weighted close (H+L+2C)/4 crosses above SMA | Weighted close | LOW |
| 36 | `relative_strength_ma.py` | Price/50-SMA ratio at 15th pct then recovers | RS percentile | MEDIUM |
| 37 | `high_low_midpoint_reversion.py` | Price reclaims rolling midpoint | Midpoint reclaim | LOW |

#### B4. Statistical & Regime-Based (12 strategies)

| # | File | Logic | Unique Value | Dup Risk |
|---|------|-------|-------------|---------|
| 38 | `zscore_mean_reversion.py` | Z-score <-2.0 | Statistical revert | HIGH |
| 39 | `variance_ratio_reversion.py` | VR(short/long) <0.5 + RSI <40 | Regime detection | LOW |
| 40 | `hurst_exponent_gate.py` | Hurst <0.4 (mean-reverting) + RSI <35 | Regime gate | MEDIUM |
| 41 | `skewness_gate.py` | Return skewness flips neg→pos | Sentiment shift | LOW |
| 42 | `kurtosis_regime.py` | Kurtosis >5 + positive momentum | Fat-tail regime | LOW |
| 43 | `return_autocorrelation.py` | AC <-0.2 (mean-reverting) + RSI <40 | AC regime | LOW |
| 44 | `negative_correlation_reversal.py` | Lagged corr flips from <-0.5 to >0 | Corr regime flip | LOW |
| 45 | `entropy_low_entry.py` | Shannon entropy <1.5 + above EMA | Low entropy regime | LOW |
| 46 | `choppiness_filter_entry.py` | Choppiness index <38 + RSI pullback | Trend filter | MEDIUM |
| 47 | `calmar_recovery_signal.py` | Calmar ratio crosses above 0.5 | Recovery signal | LOW |
| 48 | `sortino_gate_momentum.py` | Sortino >1.0 + EMA pullback | Quality gate | LOW |
| 49 | `rolling_sharpe_gate.py` | Rolling Sharpe >0.5 + EMA pullback | Quality gate | LOW |

#### B5. Volume-Based (7 strategies)

| # | File | Logic | Unique Value | Dup Risk |
|---|------|-------|-------------|---------|
| 50 | `volume_spike_reversal.py` | Volume 3x avg + close in upper 60% of range | Capitulation | HIGH |
| 51 | `volume_dry_up_breakout.py` | Volume at 20th pct then price break | Dry-up breakout | MEDIUM |
| 52 | `relative_volume_breakout.py` | RVOL >2.5 + break above prior high | Relative volume | MEDIUM |
| 53 | `up_volume_ratio.py` | Up-vol/total-vol >70% over 10 bars | Volume sentiment | MEDIUM |
| 54 | `volume_weighted_rsi.py` | Volume-weighted RSI <30 | VWRSI oversold | MEDIUM |
| 55 | `volume_profile_poc.py` | Price returns to POC (histogram peak) bounce | Volume profile | LOW |
| 56 | `obv_divergence.py` | Price lower low + OBV higher low | OBV divergence | MEDIUM |

#### B6. Candlestick & Price Action (10 strategies)

| # | File | Logic | Unique Value | Dup Risk |
|---|------|-------|-------------|---------|
| 57 | `inside_bar_breakout.py` | Inside bar + upside breakout | Classic pattern | HIGH |
| 58 | `body_ratio_reversal.py` | Body <25% of range + in bottom 30% + downtrend | Doji-like reversal | MEDIUM |
| 59 | `gap_fill_reversion.py` | Gap down >1.5% + partial fill (>30% of gap) | Gap fill | MEDIUM |
| 60 | `consecutive_down_reversal.py` | 4+ down closes + first up close | Streak reversal | MEDIUM |
| 61 | `exhaustion_candle.py` | 3+ down bars with decreasing range + reversal | Exhaustion | LOW |
| 62 | `engulfing_pattern_filter.py` | Bullish engulfing in low-vol ATR regime | Filtered engulfing | MEDIUM |
| 63 | `hammer_candle_filter.py` | Hammer (lower wick >2x body) in downtrend | Filtered hammer | MEDIUM |
| 64 | `lower_wick_absorption.py` | Close in bottom 25% + ATR lowest 30th pct | Wick absorption | LOW |
| 65 | `false_low_break_reversal.py` | Low breaks 25-bar low (sweep) + close recovers | SFP variant | MEDIUM |
| 66 | `swing_failure_pattern.py` | Wick below swing low + close above it | SFP | MEDIUM |

#### B7. Support/Resistance & Channel (6 strategies)

| # | File | Logic | Unique Value | Dup Risk |
|---|------|-------|-------------|---------|
| 67 | `donchian_midline_bounce.py` | Pullback to Donchian midline in uptrend | Midline bounce | MEDIUM |
| 68 | `pivot_point_bounce.py` | Classic pivot S1 touch + bounce | Pivot levels | MEDIUM |
| 69 | `retest_support_level.py` | Prior resistance becomes support (retest) | S/R flip | MEDIUM |
| 70 | `double_bottom_detector.py` | Two lows within 1 ATR + higher close (W-bottom) | Double bottom | MEDIUM |
| 71 | `chandelier_exit_reversal.py` | Chandelier exit reclaim (was below, now above) | Trailing stop flip | LOW |
| 72 | `opening_range_breakout.py` | Price breaks above first 3-bar high | ORB | MEDIUM |

#### B8. Trend-Following (5 strategies)

| # | File | Logic | Unique Value | Dup Risk |
|---|------|-------|-------------|---------|
| 73 | `hh_hl_trend_follow.py` | Higher highs + higher lows confirmed | HH/HL structure | MEDIUM |
| 74 | `trend_intensity_index.py` | TII (up/down close ratio) crosses above 60 | TII crossover | LOW |
| 75 | `adx_rising_gate.py` | ADX rises from <20 to >25 with +DI dominant | ADX ignition | MEDIUM |
| 76 | `avg_directional_movement.py` | +DI crosses above -DI with ADX >20 | DI crossover | MEDIUM |
| 77 | `aroon_crossover.py` | Aroon Up crosses above Aroon Down | Aroon cross | MEDIUM |

#### B9. VWAP & Price Level (3 strategies)

| # | File | Logic | Unique Value | Dup Risk |
|---|------|-------|-------------|---------|
| 78 | `vwap_deviation_snap.py` | Price >2 ATR below VWAP then snaps back | VWAP reversion | MEDIUM |
| 79 | `mean_distance_reversion.py` | Price deviation from 50-EMA exceeds -2x ATR | Rubber-band | HIGH |
| 80 | `median_price_reversion.py` | Close >2% below rolling median | Median reversion | MEDIUM |

#### B10. Classic Oscillators & Indicators (12 strategies)

| # | File | Logic | Unique Value | Dup Risk |
|---|------|-------|-------------|---------|
| 81 | `close_location_value.py` | CLV flips from negative to positive | CLV accumulation | LOW |
| 82 | `cumulative_delta_proxy.py` | Cumulative (close-open) flips positive | Delta proxy | LOW |
| 83 | `tick_imbalance.py` | Up-tick/down-tick ratio >2:1 | Tick ratio | LOW |
| 84 | `detrended_price_oscillator.py` | DPO drops <-2% then recovers above 0 | DPO flip | LOW |
| 85 | `trix_zero_cross.py` | TRIX (triple EMA ROC) crosses above zero | TRIX cross | LOW |
| 86 | `vortex_indicator_cross.py` | VI+ crosses above VI- | Vortex cross | LOW |
| 87 | `coppock_curve_signal.py` | Coppock curve (weighted ROC) crosses above 0 | Coppock signal | LOW |
| 88 | `ultimate_oscillator_reversal.py` | UO (7/14/28 weighted) <30 then rises | UO oversold | LOW |
| 89 | `intraday_momentum_index.py` | IMI <30 + rising | Intraday momentum | LOW |
| 90 | `price_rate_disparity.py` | Disparity index (close/EMA -1) <-3% | Price displacement | MEDIUM |
| 91 | `elder_ray_bull_power.py` | Bull power (high-13EMA) flips positive | Elder Ray | LOW |
| 92 | `mass_index_reversal.py` | Mass index >27 then drops <26.5 (reversal bulge) | Mass index | LOW |

#### B11. Pattern & Structure (6 strategies)

| # | File | Logic | Unique Value | Dup Risk |
|---|------|-------|-------------|---------|
| 93 | `fractal_breakout.py` | Price breaks above Williams fractal high | Fractal break | MEDIUM |
| 94 | `ulcer_index_recovery.py` | Ulcer index drops 50% from peak | Pain recovery | LOW |
| 95 | `parabolic_stop_reversal.py` | SAR proxy flips from below to above | Parabolic flip | MEDIUM |

---

## 🧪 WEB AI SOC BATCH STRATEGIES (100 strategies, 10 families × 10 variants)

Located in: `incubator/agents/web_ai/crypto_soc_*_a01_v1.py` through `a10_v1.py`

| Family | Prefix | Core Logic | Variants | Dup Risk |
|--------|--------|-----------|----------|---------|
| Delta Divergence | `crypto_soc_delta_divergence` | Order flow delta divergence from price | 10 | MEDIUM |
| Dynamic Risk Heat | `crypto_soc_dynamic_risk_heat` | Dynamic risk/heat-based position sizing | 10 | LOW |
| Intraday Time Slices | `crypto_soc_intraday_time_slices` | Time-of-day seasonality patterns | 10 | LOW |
| Micro Noise Filter | `crypto_soc_micro_noise_filter` | Microstructure noise filtering | 10 | LOW |
| MTF ORB Pivots | `crypto_soc_mtf_orb_pivots` | Multi-timeframe ORB + pivot levels | 10 | MEDIUM |
| Orderflow Absorption | `crypto_soc_orderflow_absorption` | Order flow absorption detection | 10 | LOW |
| Proxy Decoupling | `crypto_soc_proxy_decoupling` | Proxy asset decoupling detection | 10 | LOW |
| Regime Filters | `crypto_soc_regime_filters` | Regime-based trade filtering | 10 | MEDIUM |
| Trend-Filtered MeanRev | `crypto_soc_trend_filtered_meanrev` | Trend-aware mean reversion | 10 | HIGH |
| Vol Expansion Index | `crypto_soc_vol_expansion_index` | Volatility expansion detection | 10 | MEDIUM |

---

## ⚠️ STRATEGIES WITH HIGH DUPLICATE RISK — SATURATION WARNING

**DO NOT create strategies similar to these — we have 5+ implementations each:**

1. **RSI-based mean reversion** — 10+ implementations (multi_period_rsi, drawdown_recovery_rsi, rsi_velocity, rsi_mean_cross, connors_rsi, williams_r, volume_weighted_rsi, momentum_divergence_rsi, etc.)
2. **EMA/SMA crossovers** — 8+ implementations (ema_slope, ema_ribbon, triple_ema, ema_crossover, quad_ema, weighted_close, etc.)
3. **Bollinger/Keltner Bands** — 5+ implementations (bollinger_width, keltner_squeeze, acceleration_bands, price_channel, etc.)
4. **ATR-based volatility** — 8+ implementations (vol_contraction, atr_percentile, dual_atr, atr_expansion, true_range, range_contraction, etc.)
5. **Volume breakout** — 5+ implementations (volume_spike, volume_dry_up, relative_volume, up_volume_ratio, volume_breakout_regime, etc.)
6. **Candlestick patterns** — 6+ implementations (inside_bar, engulfing, hammer, body_ratio, exhaustion, lower_wick, etc.)
7. **Momentum/ROC** — 6+ implementations (roc_acceleration, momentum_percentile, dual_timeframe, momentum_stall, smoothed_momentum, price_acceleration)
8. **Mean reversion z-score/deviation** — 5+ implementations (zscore, mean_distance, median_price, vwap_deviation, price_rate_disparity)
9. **Support/resistance** — 5+ implementations (donchian_midline, pivot_point, retest_support, double_bottom, swing_failure, false_low_break)
10. **Funding rate** — 3+ implementations (Tier 1 + fear_greed_reversion + crypto_fng_funding + crypto_funding_curvature)

---

## ✅ WHITE SPACE - Areas Still Underexplored

**These areas have FEWER existing strategies and are the best targets for new work:**

### Alternative Data (Underexplored)
- On-chain metrics (whale movements, exchange flows)
- ~~Social sentiment (Twitter, Reddit, Discord) with NLP~~ ✅ **FILLED:** `coinglass_strategies/strategies/news_sentiment.py` (S12-NewsSentiment — CryptoPanic + Fear&Greed)
- ~~Options flow data / implied volatility surface~~ ✅ **FILLED:** `coinglass_strategies/strategies/options_volatility.py` (S11-OptionsVolatility — Deribit IV + put/call skew)
- Order book microstructure (real L2/L3 data)
- Cross-exchange arbitrage signals
- Liquidation cascade detection

### Advanced ML (Underexplored)
- Reinforcement Learning for position sizing
- Transformer architectures for time series
- Graph neural networks (market as graph)
- Multi-task learning (predict direction + volatility)
- Uncertainty quantification (predict confidence intervals)
- Online learning (adaptive models)

### Cross-Asset (Partially Explored)
- Crypto-equity correlations ← 2 strategies exist but room for more
- Forex-crypto carry relationships
- Commodity-crypto inflation hedges
- Inter-market spreads
- Crypto sector rotation (DeFi, L1, L2, memes)

### Risk Management (Underexplored)
- Dynamic position sizing based on Kelly criterion
- Portfolio-level heat management
- Drawdown control systems
- Correlation breakdown detection
- ~~Portfolio optimization (Markowitz, risk parity)~~ ✅ **FILLED:** `coinglass_strategies/strategies/risk_parity.py` (S13-RiskParity — inverse-vol weighting + correlation-adjusted sizing)

### Exotic (Underexplored)
- ~~Options strategies for crypto~~ ✅ **FILLED:** S11-OptionsVolatility (see above)
- Volatility surface arbitrage
- ~~Calendar spreads~~ ✅ **FILLED:** `coinglass_strategies/strategies/calendar_spread.py` (S9-CalendarSpread — perp-vs-spot basis z-score)
- Cross-margin optimization
- DEX vs CEX arbitrage

### Carry / Term-Structure (NEW — Previously Absent)
- ~~Funding rate term-structure carry~~ ✅ **FILLED:** `coinglass_strategies/strategies/roll_yield.py` (S10-RollYield — persistent funding regime harvesting)

---

## 🔍 HOW TO CHECK FOR DUPLICATES

Before creating a strategy:

1. **Check this file** - Is the core idea already listed?
2. **Search the tables above** - Is the indicator/technique already used?
3. **Check `100_ALGORITHMS_MASTER_CATALOG.md`** - Theoretical algorithms
4. **Count existing implementations** - If 5+ exist for that category, STOP

**If similarity > 90%:** REJECT and iterate
**If similarity 70-90%:** Must add a genuinely unique twist (new indicator combo, different regime filter, etc.)
**If similarity < 70%:** Likely safe to proceed

---

## 📝 STRATEGY NAMING CONVENTION

To avoid confusion, use this format:

```
{asset_class}_{core_indicator}_{unique_twist}_{version}

Examples:
- crypto_rsi_fundingconfirmed_v1.py
- crossasset_btcspx_correlation_v2.py
- onchain_whale_momentum_v1.py
- defi_sector_relative_v1.py
```

---

## 🚨 REMEMBER

> **"The best strategy is one that complements existing systems, not duplicates them."**

Before creating:
- [ ] Checked this inventory?
- [ ] Checked saturation warnings for that technique?
- [ ] Identified what's different/unique?
- [ ] Can explain why this adds value vs existing 367 strategies?

**When in doubt, ask:** "Does this strategy generate signals that are uncorrelated with existing systems?"
