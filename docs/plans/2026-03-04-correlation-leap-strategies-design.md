# Correlation & Leap Contest Strategies — Design Document

**Date:** 2026-03-04
**Status:** Implemented

## Overview

16 new paper trading strategies + 3 baby bundles + 12 DNA seeds, built from two sources:
1. **Correlation analysis** of BNBUSDT 30m data (614 candles) identifying 6 metrics that track price
2. **TradingView "The Leap" crypto contest** (Feb 2026) — extracting patterns from top performers

## Correlation Metrics Used

| Metric | Correlation | Role |
|--------|------------|------|
| HMA Entry | +0.978 | Primary trend direction |
| KAMA Fast | +0.973 | Adaptive trend confirmation |
| VWAP | +0.913 | Institutional fair value anchor |
| Elton Net | +0.581 | 7-strategy consensus score |
| Z-Score | +0.534 | Mean-reversion extremes |
| RSI | +0.519 | Momentum oscillator |

## The Leap Contest Research

**Top performers (Feb 2026, 48,500 traders):**
- stevemao: +90.54% (no scripts — pure execution)
- Magicfingers0T0: +88.39% (harmonic patterns, weekly TF)
- jazzioman: +88.32% (private — Discord/StockTwits)
- FundedRelay: +77.70% (published Asset Liquidity Meter script)

**Key winning patterns extracted:**
- Swing low trailing stop (Fractalyst — top 3%)
- Elliott Wave entries (Melissa2018 — 1st place, $25K)
- Harmonic pattern confluence (Magicfingers0T0 — #2)
- HTF top-down bias (multiple winners)
- <10 high-R:R trades (Hakukuro — 2nd place)
- Fee awareness / sniper entries (Blasik — 4th place)

## Strategy Set (16 total)

### Tier 1: Correlation Strategies (10)

| # | File | Name | Logic | TP/SL |
|---|------|------|-------|-------|
| 1 | `corr_hma_trend` | HMA Trend | Close > HMA(16) | +8%/-4% |
| 2 | `corr_kama_adaptive` | KAMA Adaptive | Close > KAMA | +8%/-4% |
| 3 | `corr_vwap_reversion` | VWAP Reversion | Price < VWAP-1σ | +5%/-3% |
| 4 | `corr_elton_net_consensus` | Elton Net | Net > +50 | +10%/-5% |
| 5 | `corr_zscore_extreme` | Z-Score Extreme | Z < -2.0 | +6%/-3% |
| 6 | `corr_rsi_momentum` | RSI Momentum | RSI < 30 | +8%/-4% |
| 7 | `corr_hma_elton_confluence` | HMA x Elton | HMA + Net > +35 | +12%/-5% |
| 8 | `corr_vwap_zscore_reversion` | VWAP x Z-Score | VWAP + Z < -1.5 | +6%/-3% |
| 9 | `corr_kama_rsi_trend` | KAMA x RSI | KAMA + RSI < 40 | +10%/-5% |
| 10 | `corr_triple_crown` | Triple Crown | HMA+KAMA+Elton | +15%/-6% |

### Tier 2: Leap Contest Strategies (6)

| # | File | Name | Inspired By | TP/SL |
|---|------|------|-------------|-------|
| 11 | `leap_swing_trail` | Swing Trail | Fractalyst (top 3%) | Trail/-3% |
| 12 | `leap_htf_momentum` | HTF Momentum | Multiple winners | +15%/-6% |
| 13 | `leap_concentrated_rr` | Concentrated R:R | Hakukuro (2nd) | +20%/-6% |
| 14 | `leap_harmonic_confluence` | Harmonic | Magicfingers0T0 (#2) | +12%/-5% |
| 15 | `leap_elliott_impulse` | Elliott Impulse | Melissa2018 (1st) | +15%/-6% |
| 16 | `leap_fee_aware_sniper` | Fee Aware Sniper | Blasik (4th) | +18%/-5% |

## Baby Bundles (3)

| Bundle | Components | Target Return | Max DD |
|--------|-----------|---------------|--------|
| Aggressive | Triple Crown (40%), HMA x Elton (35%), Concentrated R:R (25%) | 25-40% | <35% |
| Balanced | KAMA x RSI (30%), Swing Trail (30%), HTF Momentum (25%), RSI (15%) | 15-25% | <25% |
| Conservative | VWAP Reversion (35%), Z-Score (30%), Fee Sniper (20%), VWAP x Z (15%) | 8-15% | <15% |

## DNA Engine Integration

12 new seeds added (3 per island):
- **Bear:** corr_vwap_reversion, corr_zscore_extreme, leap_swing_trail
- **Bull:** corr_hma_trend, corr_triple_crown, leap_htf_momentum
- **Range:** corr_kama_adaptive, corr_vwap_zscore_reversion, leap_fee_aware_sniper
- **Recent:** corr_hma_elton_confluence, leap_concentrated_rr, leap_elliott_impulse

## Infrastructure

- **Paper Trading:** 2 new portfolios (`correlation`, `leap`) in db.py, $1,000 starting capital each
- **Audit Trail:** All picks recorded with `source_system = "correlation_strategies"` or `"leap_strategies"`
- **Discord:** Posts to `DISCORD_WEBHOOK_PAPER_TRADE` (#paper-trading channel)
- **Workflow:** Existing `paper-trading.yml` (every 4 hours) picks up all 16 strategies automatically
- **Promotion:** INCUBATOR → SANDBOX → FRESH_PICKS → DNA_MASTER pipeline

## File Inventory

### Baby Strategies (baby_strategies/)
- `corr_hma_trend.py`, `corr_kama_adaptive.py`, `corr_vwap_reversion.py`
- `corr_elton_net_consensus.py`, `corr_zscore_extreme.py`, `corr_rsi_momentum.py`
- `corr_hma_elton_confluence.py`, `corr_vwap_zscore_reversion.py`
- `corr_kama_rsi_trend.py`, `corr_triple_crown.py`
- `leap_swing_trail.py`, `leap_htf_momentum.py`, `leap_concentrated_rr.py`
- `leap_harmonic_confluence.py`, `leap_elliott_impulse.py`, `leap_fee_aware_sniper.py`

### Baby Bundles (baby_strategies/bundle_optimized/)
- `bundle_correlation_aggressive.py`
- `bundle_correlation_balanced.py`
- `bundle_correlation_conservative.py`

### Paper Trading Wrappers (paper_trading/strategies/)
- `corr_trend_strategies.py` (HMA, KAMA, Triple Crown)
- `corr_reversion_strategies.py` (VWAP, Z-Score, Elton Net, RSI, combos)
- `leap_strategies.py` (all 6 Leap strategies)

### Modified Files
- `paper_trading/strategies/__init__.py` — added 16 strategies
- `paper_trading/db.py` — added `correlation` and `leap` portfolios
- `genome/seed_strategies.py` — added 12 DNA seeds (3 per island)

## Sources
- TradingView The Leap Feb 2026: https://www.tradingview.com/the-leap/february-2026/
- Fractalyst top 3% approach: https://www.tradingview.com/chart/ETHUSD/LPYpTj5Q-Leap-Competition-Top-3-in-5-Days-Here-s-How/
- FundedRelay Asset Liquidity Meter: https://www.tradingview.com/script/ZrwfYxGW/
- Leap winners blog: https://www.tradingview.com/blog/en/the-leap-2-paper-trading-competition-results-44828/
