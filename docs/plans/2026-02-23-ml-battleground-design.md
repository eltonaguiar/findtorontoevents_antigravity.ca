# ML Battleground — Design Document

**Date:** 2026-02-23
**Status:** Approved
**Goal:** Build 3 independent ML trading systems as a head-to-head competition to find which approach delivers consistent, safe crypto trading signals fastest.

---

## Problem Statement

Current ML systems (claude_gainer_ml, ml_crypto_predictor) take too long to accumulate trustworthy forward results. They try to predict price direction — a notoriously hard problem requiring hundreds of trades for statistical proof. Meanwhile, rule-based strategies (Connors RSI-2 at 75.7% WR, Supertrend at Sharpe 2.57) already have academic backing.

**Solution:** Build 3 competing approaches, each with its own scanner and "Superpowers" dashboard, running in parallel. Let real paper-trading data determine the winner.

---

## Constraints (All 3 Systems)

- **Assets:** Crypto-only, 20 Binance USDT pairs (3 tiers by liquidity)
- **Timeframes:** 15m scalp + 1h swing (both run in parallel)
- **Risk:** 2% per trade, 10% max portfolio drawdown, max 5 concurrent positions
- **Sizing:** Fractional Kelly (0.25×)
- **Costs:** 0.1% maker + 0.1% taker + pair-specific slippage (0.05%-0.2%)
- **Validation:** Paper trade first → "proven" badge at 50+ trades, WR>55%, Sharpe>1.0, DD<15%, MC p<0.05
- **Branding:** All dashboards titled "Superpowers"

### Pair Universe (20 pairs)

| Tier | Pairs |
|------|-------|
| Tier 1 (liquid) | BTCUSDT, ETHUSDT, BNBUSDT, SOLUSDT, XRPUSDT |
| Tier 2 (alt L1) | ADAUSDT, DOTUSDT, AVAXUSDT, LINKUSDT, NEARUSDT, SUIUSDT, APTUSDT |
| Tier 3 (mid-cap) | DOGEUSDT, ARBUSDT, OPUSDT, INJUSDT, FETUSDT, TIAUSDT, SEIUSDT, FILUSDT |

---

## Directory Structure

```
ml_battleground/
├── system_a_filter/          # Approach A: ML Filter + S/R TP/SL
│   ├── scanner.py
│   ├── sr_engine.py
│   ├── ml_filter.py
│   ├── train_filter.py
│   ├── strategies.py
│   ├── models/
│   ├── data/
│   │   ├── active_picks.json
│   │   ├── closed_picks.json
│   │   └── sr_levels.json
│   └── index.html            # Superpowers Dashboard A: "The Filter"
│
├── system_b_regime/          # Approach B: Regime Classifier
│   ├── scanner.py
│   ├── regime_classifier.py
│   ├── train_regime.py
│   ├── strategy_router.py
│   ├── models/
│   ├── data/
│   │   ├── active_picks.json
│   │   ├── closed_picks.json
│   │   └── regime_history.json
│   └── index.html            # Superpowers Dashboard B: "The Regime"
│
├── system_c_deeplearn/       # Approach C: End-to-End Deep Learning
│   ├── scanner.py
│   ├── model_arch.py
│   ├── train_model.py
│   ├── models/
│   ├── data/
│   │   ├── active_picks.json
│   │   ├── closed_picks.json
│   │   └── predictions.json
│   └── index.html            # Superpowers Dashboard C: "The Neural Net"
│
├── shared/
│   ├── data_fetcher.py
│   ├── indicators.py
│   ├── validator.py
│   ├── cost_model.py
│   ├── risk_manager.py
│   └── performance.py
│
├── arena.html                # Superpowers Arena: head-to-head comparison
└── requirements.txt
```

---

## System A: "The Filter" — ML Filter + S/R TP/SL

### Philosophy
Keep proven strategies for *what* to trade. Use ML for *when* to take the trade. Use S/R levels for *where* to exit.

### Signal Generation (8 strategies)

| # | Strategy | Source (existing code) | Timeframe | Expected WR |
|---|---|---|---|---|
| 1 | Supertrend Follow | ml_crypto_predictor v4 | 15m, 1h | 60-71% |
| 2 | Connors RSI-2 (crypto) | alpha_engine/connors_rsi2.py | 1h | 62% |
| 3 | Bollinger-Keltner Squeeze | alpha_engine/pattern_strategies.py | 15m, 1h | 55-62% |
| 4 | RSI+MACD Confluence | alpha_engine/crypto_strategies.py | 1h | 65% |
| 5 | EMA Stack (9/21/50/200) | alpha_engine/crypto_strategies.py | 1h | 65-72% |
| 6 | Volume Climax Reversal | alpha_engine/crypto_strategies.py | 15m | 58-65% |
| 7 | Swing Failure Pattern | alpha_engine/crypto_strategies.py | 15m, 1h | 58-65% |
| 8 | Mean Reversion (O-U) | alpha_engine/statistical_strategies.py | 15m | 55-60% |

### S/R Engine (`sr_engine.py`)

Consolidated from existing `pattern_strategies.py` code:

1. **Fractal pivots** — Williams fractals (window=5) for swing highs/lows
2. **Volume Profile** — POC, VAH, VAL from volume-at-price histogram (70% value area)
3. **Multi-touch clustering** — Group pivots within 0.3% tolerance, score by touch_count × recency_weight
4. **Round number magnetism** — Psychological levels ($100, $1000, etc.)
5. **Output:** Ordered list of S/R levels with strength scores, labeled support/resistance relative to current price

### ML Context Filter (`ml_filter.py`)

XGBoost binary classifier: "take this signal" vs "skip"

**~20 features:**
- Distance to nearest support/resistance (% of price)
- S/R level strength score (touch count)
- Volume ratio vs 20-bar MA
- RSI(14)
- ATR percentile (volatility regime)
- Fear & Greed index
- Funding rate
- Hour-of-day (sin/cos encoded)
- BTC correlation (20-bar) + BTC 1h return
- Consecutive green/red candles
- Bollinger %B
- S/R spread (nearest resistance - nearest support, squeeze detection)
- Strategy ID (one-hot — lets ML learn strategy × context interactions)

**Training:** Walk-forward on historical signals labeled by triple-barrier outcome. Retrain weekly.

### Dynamic TP/SL

- **TP** = Next resistance level above entry (if strength ≥ 3 touches), fallback 2.5× ATR
- **SL** = Next support level below entry (if strength ≥ 2 touches), fallback 1.5× ATR
- **Minimum R:R gate** = 1.5:1 (skip if S/R gives worse ratio)
- **Trailing stop** = Ratchet SL to each new support level as price advances

### Dashboard: "Superpowers: The Filter"

- Active picks table with S/R levels visually marked (entry, TP at resistance, SL at support)
- S/R Level Map per active pair
- ML Filter stats (acceptance rate, filter accuracy)
- Strategy breakdown (WR by strategy)
- Equity curve + drawdown chart

---

## System B: "The Regime" — Regime Classifier + Strategy Router

### Philosophy
Markets behave differently in different regimes. Classify first, then deploy the right strategy.

### Regime Classifier (`regime_classifier.py`)

XGBoost multi-class (4 regimes):

| Regime | Detection | Deployed Strategies |
|--------|-----------|-------------------|
| Trending Up | ADX>25, price>EMA50, higher highs | Supertrend, EMA Stack, Momentum Breakout |
| Trending Down | ADX>25, price<EMA50, lower lows | Short SFP, Funding Carry, Momentum Crash Hedge |
| Range-Bound | ADX<20, BB width < 20th pctl | Mean Reversion, Bollinger Bounce, RSI-2, Volume POC |
| High Volatility | ATR > 80th pctl | Reduced sizing, Vol Squeeze Breakout, Liquidation Cascade |

**~15 features:** ADX, DI+/DI-, EMA slope, BB width percentile, ATR percentile, Hurst exponent, volume trend, BTC correlation, Fear & Greed, price vs EMA 50/200, realized volatility percentile.

**Training:** Label historical periods by rule-based regime definitions, train ML to predict 1-bar ahead. Walk-forward.

### Strategy Router

- Each regime activates 3-4 strategies
- Fixed ATR-based TP/SL per regime:
  - Trending: TP 3.5× ATR, SL 1.5× ATR
  - Range: TP 1.5× ATR, SL 1.0× ATR
  - High Vol: TP 2.0× ATR, SL 2.5× ATR (wider stops, smaller size)
- Regime transition → close existing positions from prior regime's strategies

### Dashboard: "Superpowers: The Regime"

- Current regime classification with confidence bar
- Regime timeline (color-coded 7-day history)
- Active strategies table with picks
- Win rate + Sharpe by regime type
- Equity curve + drawdown chart

---

## System C: "The Neural Net" — End-to-End Deep Learning

### Philosophy
Let the model learn everything from raw data. Most ambitious, longest to validate.

### Architecture (`model_arch.py`)

```
Input: 200 bars × [OHLCV + 10 features] × 2 timeframes (15m + 1h)
  ↓
GRU(128 units, 2 layers, dropout=0.3) per timeframe
  ↓
Concatenate
  ↓
Multi-Head Self-Attention(4 heads)
  ↓
Dense(64) → Dropout(0.3)
  ↓
3 output heads:
  - Entry probability (sigmoid)
  - TP distance in ATR units (linear)
  - SL distance in ATR units (linear)
```

**Input features per bar (~16):** OHLCV (normalized), RSI(14), MACD histogram, Bollinger %B, volume ratio, ATR normalized, hour sin/cos, BTC return, Fear & Greed, funding rate, price vs EMA200.

### Training

- **Data:** 6 months rolling window, 15m + 1h Binance OHLCV per pair
- **Labels:** Triple-barrier (TP hit = 1, SL hit or expiry = 0)
- **Loss:** Multi-task: BCE(entry) + MSE(TP distance) + MSE(SL distance)
- **Validation:** Purged walk-forward (5 folds, 50-bar gap)
- **Regularization:** Dropout 0.3, early stopping, L2 weight decay
- **Framework:** PyTorch (CPU inference in GitHub Actions)
- **Retrain:** Weekly

### Inference

- Every 15 min: feed 200 bars → entry probability + TP/SL
- Entry threshold: probability > 0.65
- TP/SL in ATR units → convert to price

### Dashboard: "Superpowers: The Neural Net"

- Confidence heatmap (pairs × timeframes, colored by entry probability)
- Active picks with predicted TP/SL
- Model diagnostics (loss curves, calibration plot)
- Attention visualization (which bars/features matter)
- Equity curve + drawdown chart

---

## Arena Dashboard: "Superpowers Arena"

The meta-dashboard comparing all 3 systems:

- Head-to-head table: WR, Sharpe, total return, max DD, trades closed
- Overlaid equity curves (3 lines on one chart)
- Current picks comparison (do systems agree on the same pairs?)
- "Winner" badge: auto-awarded to system with best risk-adjusted return after 50+ trades each
- Consensus signals: pairs where 2+ systems agree (highest conviction)

---

## GitHub Actions Deployment

3 workflows:
- `ml-battleground-a.yml` — System A every 15 min
- `ml-battleground-b.yml` — System B every 30 min (regime changes slowly)
- `ml-battleground-c.yml` — System C every 15 min

Dashboard deployment via existing GitHub Pages workflow pattern.

---

## Shared Modules

| Module | Purpose |
|--------|---------|
| `data_fetcher.py` | Binance OHLCV (primary), OKX/Bybit failover, CoinGecko market data |
| `indicators.py` | RSI, MACD, Bollinger, ATR, EMA, ADX, Supertrend, Hurst, etc. |
| `validator.py` | Forward validation: check TP/SL/trailing/expiry vs live prices |
| `cost_model.py` | 0.1% maker + 0.1% taker + slippage (0.05%-0.2% per pair) |
| `risk_manager.py` | 2% risk, Kelly(0.25×), 10% DD breaker, 5 concurrent max |
| `performance.py` | Sharpe, Sortino, Calmar, DSR, Monte Carlo, equity curve |

---

## Success Criteria

1. All 3 systems running autonomously on GitHub Actions within 2 weeks
2. Each system accumulating paper trades at ≥10 trades/week
3. At least 1 system achieves "proven" status (50+ trades, WR>55%, Sharpe>1.0) within 4 weeks
4. Arena dashboard shows real-time comparison
5. Zero manual intervention required after initial deployment
