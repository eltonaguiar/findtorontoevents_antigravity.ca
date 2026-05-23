# Simpleton Trend Reversal Strategy — Design Document

**Date:** 2026-03-04
**Source:** Pine Script v6 "Advanced Trend Reversal Emoji Indicator" by FundedRelay
**Status:** Approved

## Overview

Convert the Pine Script EMA crossover indicator into a fully tracked strategy across 4 systems:
baby strategy, baby bundle, paper trading portfolio, and DNA genome.

## Signal Logic

```
LONG entry:
  EMA(21) crosses above EMA(55)         # crossover detection
  AND close > EMA(200)                   # trend filter
  AND RSI(14) > 55                       # momentum confirmation
  AND true_range > ATR(14) * 1.0         # volatility gate

SHORT entry:
  EMA(21) crosses below EMA(55)          # crossunder detection
  AND close < EMA(200)                   # trend filter
  AND RSI(14) < 45                       # momentum confirmation
  AND true_range > ATR(14) * 1.0         # volatility gate

TP = entry ± 2.5 × ATR(14)
SL = entry ∓ 1.5 × ATR(14)
```

## Deliverables

### 1. Baby Strategy — `baby_strategies/simpleton_trend_reversal.py`
- Class: `SimpletonTrendReversalStrategy`
- 3 tunable params: `tp_atr_mult` (2.5), `sl_atr_mult` (1.5), `rsi_offset` (5)
- Assets: crypto + equity + forex (multi-asset validation)
- Standard signal format: list of dicts with symbol/side/entry/tp/sl/strength/reason/strategy

### 2. Baby Bundle — `baby_strategies/bundle_optimized/bundle_simpleton_reversal.py`
- Standalone bundle wrapping the strategy
- 5-regime detection via ADX + Bollinger Band width
- Half-Kelly position sizing with regime multipliers
- Max 25% allocation cap

### 3. Paper Trading Strategy — `paper_trading/strategies/simpleton_trend_reversal.py`
- Extends BaseStrategy (fetch_data + generate_picks)
- Fetches 1h klines from Binance for crypto symbols
- Returns NormalizedPick objects
- Portfolio type: "technical"
- Registered in paper_trading/strategies/__init__.py

### 4. DNA Registration — genome/seed_strategies.py
- create_strategy_dna() with EMA crossover genes
- Island: "bull" (trend-following)
- Genes: ema_fast=21, ema_slow=55, entry_logic=golden_cross, rsi_period=14

## Pine Script Parameters Mapped

| Pine Input | Python Param | Default |
|---|---|---|
| fastLength (21) | ema_fast / fast_length | 21 |
| slowLength (55) | ema_slow / slow_length | 55 |
| trendLength (200) | trend_length | 200 |
| rsiLength (14) | rsi_period | 14 |
| rsiBullLevel (55) | rsi_bull_level | 55 |
| rsiBearLevel (45) | rsi_bear_level | 45 |
| atrLength (14) | atr_period | 14 |
| atrMultiplier (1.0) | atr_multiplier | 1.0 |

## Academic Source

FundedRelay (2024) — EMA crossover with triple confluence filter (trend + momentum + volatility).
Based on established EMA crossover methodology with RSI momentum filter and ATR volatility gate.
