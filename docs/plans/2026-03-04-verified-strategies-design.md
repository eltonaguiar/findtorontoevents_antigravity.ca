# Verified Strategies — Design Document

**Date:** 2026-03-04
**Status:** Implemented

## Overview

22 new paper trading strategies + 20 baby strategies + 18 DNA seeds, built from four research sources:
1. **FundedRelay** (TradingView The Leap Feb 2026, +77.7%) — 8 variations of EMA/RSI/ATR reversal system
2. **Verified Research** — 8 strategies from backtested TradingView scripts and quantitative research
3. **Kimi Claw** — 4 strategies from G-Research competition winners and academic research
4. **Academic/Perplexity** — 2 strategies from peer-reviewed crypto momentum papers

## Research Sources

### FundedRelay (The Leap #7, +77.7%)
- **Base:** Advanced Trend Reversal Emoji Indicator + Asset Liquidity Meter
- **Core:** EMA21/55 crossover + EMA200 alignment + RSI(14) + ATR expansion
- **Documented WR:** 40-55% base, improved to 57-65% with filters
- Scripts: Published open-source on TradingView Feb 2026

### Verified Research Strategies
| Strategy | Source | WR | PF | Trades |
|---|---|---|---|---|
| SuperTrend AI | TradeSearcher | 46% | 1.94 | 154 (10yr) |
| WaveTrend Oscillator | PickMyTrade | 58% | 1.9 | 1000+ |
| EMA Stack 9/21/50 | PickMyTrade | 59% | 1.7 | N/A |
| Stochastic RSI | QuantifiedStrategies | 78% | N/A | 228 |
| Keltner Breakout | QuantifiedStrategies | 77% | 2.0 | 288 |
| Donchian Turtle | Gate Research | N/A | N/A | N/A (62.71% ann.) |
| Williams %R | QuantifiedStrategies | 78-81% | 2.2-3.2 | 598 |
| BTC 50MA Momentum | Grayscale Research | N/A | N/A | Sharpe 1.9 |

### Kimi Claw Strategies
| Strategy | Source | Key Metric |
|---|---|---|
| VPIN Reversion | Easley/O'Hara 2012 | Renaissance-style stat arb |
| EMA 600-40 | Jaaskellainen 2022 | Beat BTC B&H 2016-2021 |
| LGBM Feature Proxy | G-Research winners | $85K prize pool |
| Vol-Momentum Blend | Briplotnik research | Sharpe 1.71 |

### Academic Strategies
| Strategy | Source | Key Metric |
|---|---|---|
| TSMOM 28/5 | AUT NZ 2024-2025 paper | Sharpe 1.51, 28d lookback |
| Risk-Managed Momentum | Barroso & Santa-Clara 2015 (crypto) | Sharpe 1.42, vol-scaled |

## Strategy Set (22 paper trading strategies)

### Tier 1: FundedRelay Variations (8)

| # | Name | Logic | TP/SL |
|---|------|-------|-------|
| 1 | FR Base Reversal | EMA21/55 + EMA200 + RSI + ATR | +12%/-5% |
| 2 | FR MTF Aligned | Base + daily trend + higher lows | +15%/-6% |
| 3 | FR Liquidity Filtered | Base + liquidity meter rising | +12%/-5% |
| 4 | FR RSI Divergence | Base + bullish/bearish RSI div | +15%/-6% |
| 5 | FR ADX Regime | Base + ADX>25 + ATR>P50 | +12%/-5% |
| 6 | FR Pullback Entry | EMA cross → pullback → engulfing | +15%/-5% |
| 7 | FR Volume Spike | Base + vol>1.5x avg | +12%/-5% |
| 8 | FR Full Confluence | ALL filters combined | +20%/-6% |

### Tier 2: Verified Research (8)

| # | Name | Logic | TP/SL |
|---|------|-------|-------|
| 9 | SuperTrend AI | SuperTrend flip + ADX + vol | +15%/-6% |
| 10 | WaveTrend | WT1/WT2 cross at oversold/overbought | +10%/-5% |
| 11 | EMA Stack | EMA 9>21>50 alignment | +12%/-5% |
| 12 | Stoch RSI | StochRSI K/D cross at extremes | +8%/-4% |
| 13 | Keltner Breakout | Price > EMA20+2*ATR10 | +10%/-5% |
| 14 | Donchian Turtle | 20-bar high/low breakout | +15%/-6% |
| 15 | Williams %R | %R(2) < -90 oversold | +6%/-3% |
| 16 | BTC 50MA Momentum | BTC above 50d MA proxy | +20%/-8% |

### Tier 3: Kimi Claw + Academic (6)

| # | Name | Logic | TP/SL |
|---|------|-------|-------|
| 17 | VPIN Reversion | Z-score + VPIN clean flow | +6%/-3% |
| 18 | EMA 600-40 | Fast/slow EMA crossover | +15%/-6% |
| 19 | LGBM Feature Proxy | 5-feature composite score | +12%/-5% |
| 20 | Vol-Momentum Blend | Momentum Z + vol filter | +12%/-5% |
| 21 | TSMOM 28/5 | 28d return percentile ranking | ATR-based |
| 22 | Risk-Managed Momentum | Vol-scaled 14d momentum | +12%/-5% |

## Infrastructure

### New Portfolio
- **"verified"** portfolio in db.py, $1,000 starting capital
- All 22 strategies tagged with `portfolio_type = "verified"`

### Audit Trail Integration
- Scanner v2.0 records all picks to `audit_trail.db` (SQLite)
- Source systems: `paper_correlation`, `paper_leap`, `paper_verified`, `paper_trading`
- Raw picks → `at_raw_picks`, entries → `at_consensus_picks`, exits → `at_audit_events`
- Strategy stats auto-refreshed after each scan run

### DNA Engine Integration
18 new seeds across 4 islands:
- **Bear:** verified_stoch_rsi, verified_williams_r, kimi_vpin_reversion
- **Bull:** fr_mtf_aligned, verified_supertrend_ai, verified_ema_stack, academic_tsmom_28_5, kimi_ema600_40
- **Range:** verified_keltner_breakout, verified_wavetrend, fr_liquidity_filtered
- **Recent:** fr_full_confluence, verified_donchian_turtle, risk_managed_momentum, kimi_lgbm_features, kimi_vol_momentum_blend

## File Inventory

### Baby Strategies (baby_strategies/)
**FundedRelay (8):**
- `fr_base_reversal.py`, `fr_mtf_aligned.py`, `fr_liquidity_filtered.py`
- `fr_rsi_divergence.py`, `fr_adx_regime.py`, `fr_pullback_entry.py`
- `fr_volume_spike.py`, `fr_full_confluence.py`

**Verified Research (8):**
- `verified_supertrend_ai.py`, `verified_wavetrend.py`, `verified_ema_stack.py`
- `verified_stoch_rsi.py`, `verified_keltner_breakout.py`, `verified_donchian_turtle.py`
- `verified_williams_r.py`, `verified_btc_50ma_momentum.py`

**Kimi Claw (4):**
- `kimi_vpin_reversion.py`, `kimi_ema600_40_momentum.py`
- `kimi_lgbm_features.py`, `kimi_volatility_momentum_blend.py`

### Paper Trading Wrappers (paper_trading/strategies/)
- `fr_strategies.py` (8 classes)
- `verified_strategies.py` (8 classes)
- `kimi_strategies.py` (6 classes including TSMOM + Risk-Managed)

### Modified Files
- `paper_trading/strategies/__init__.py` — added 22 strategies
- `paper_trading/db.py` — added "verified" portfolio
- `paper_trading/scanner.py` — v2.0 with audit trail integration
- `genome/seed_strategies.py` — added 18 DNA seeds
- `.github/workflows/paper-trading.yml` — updated version, audit commit

## Academic References
- Easley, D. & O'Hara, M. (2012). VPIN and informed trading
- Jaaskellainen (2022). EMA trading strategies for Bitcoin. Lappeenranta University thesis
- AUT NZ (2024-2025). Time-Series and Cross-Sectional Momentum in Crypto
- Barroso, P. & Santa-Clara, P. (2015). Risk-managed momentum
- Briplotnik. Systematic Crypto Trading Strategies (Medium)
- G-Research Crypto Forecasting Competition (Kaggle, 1,946 teams)
- Grayscale Research. The Trend is Your Friend (Bitcoin 50-day MA)
- QuantifiedStrategies.com — Stoch RSI, Keltner, Williams %R backtests
- Gate Research — Improved Turtle Trading Rules (62.71% annual)
