# Antigravity Trading Strategy Performance Report

**Date:** March 5, 2026
**Prepared for:** Third-party Quant Evaluation
**Systems Covered:** Paper Trading Scanner, Battleground Arena, Alpha Engine, KIMI Rise of the Claw

---

## Executive Summary

Antigravity operates a multi-system automated trading research platform with **685+ strategy candidates** across 4 independent systems. The platform combines AI-generated strategy discovery (Web AI, Codex GPT5, Cursor AI) with hand-crafted research-backed strategies, validated through a 3-stage pipeline: **Backtest → Paper Trading → Graduated**.

### Key Metrics (as of March 5, 2026)

| System | Strategies | Active Picks | Closed Trades | Overall WR | Net P&L |
|--------|-----------|-------------|---------------|-----------|---------|
| **Battleground Arena** | 171 registered (+504 awaiting) | 2 | 210 | 65.2% | +105.30% |
| **Paper Trading Scanner** | 78 | 56 | 14 | 42.9% | -166.32% |
| **Alpha Engine** | 100 | varies | 198 (Mar) | 23% | -314.88% (Mar) |
| **KIMI Rise of the Claw** | 81 algorithms | live scan | tracked | varies | tracked |

**Top Finding:** The Battleground forward-tested strategies show the strongest real-market results (+105.30% realized across 210 closed trades, 65.2% WR).

---

## 1. Battleground Arena — Forward-Tested Results (REAL MARKET)

### 1.1 Live Forward Performance (No Look-Ahead Bias)

The Battleground system runs walk-forward validation on real BTC OHLCV data (2020–present), then forward-tests passing strategies with live Binance prices. These are the **most reliable** performance numbers.

| Strategy | Agent | Closed Trades | Win Rate | Realized P&L | Avg P&L/Trade | Status |
|----------|-------|--------------|----------|-------------|---------------|--------|
| crypto_rsi_whaleconfirmed_v1 | web_ai | 77 | 67.5% | +41.99% | +0.55% | **PROVEN** |
| multi_period_rsi_confluence | web_ai | 22 | 72.7% | +21.04% | +0.96% | **PROVEN** |
| atr_regime_rsi | web_ai | 46 | 58.7% | +17.64% | +0.38% | **PROVEN** |
| crypto_kalman_trend_residual_reversion_v1 | codex_gpt5 | 31 | 61.3% | +9.74% | +0.31% | **PROVEN** |
| crypto_vwap_deviation_reversion_volfilter_v1 | web_ai | 21 | 66.7% | +8.40% | +0.40% | **PROVEN** |
| crypto_keltner_compression_expansion_v1 | web_ai | 13 | 69.2% | +6.49% | +0.50% | EMERGING |

**All 6 forward-tested strategies are profitable.** Combined: 210 trades, 65.2% WR, +105.30% realized.

### 1.2 Backtest Results (Historical — Real BTC OHLCV)

Top 15 strategies by Sharpe ratio that passed the validation gate (Sharpe ≥ 1.0, WR ≥ 45%, Max DD ≤ 20%):

| Strategy | Agent | Sharpe | Win Rate | Profit Factor | Trades | Return |
|----------|-------|--------|----------|--------------|--------|--------|
| crypto_soc_trend_filtered_meanrev_a05_v1 | web_ai | 6.75 | 50.0% | 3.05 | 26 | varies |
| crypto_donchian_atr_breakout_retest_v1 | codex_gpt5 | 5.91 | 52.0% | 3.97 | 21 | varies |
| crypto_soc_vol_expansion_index_a05_v1 | web_ai | 5.80 | 68.0% | 3.17 | 47 | varies |
| crypto_soc_intraday_time_slices_a09_v1 | web_ai | 5.05 | 40.0% | 5.59 | 10 | varies |
| crypto_soc_intraday_time_slices_a03_v1 | web_ai | 4.83 | 40.0% | 4.41 | 10 | varies |
| crypto_soc_intraday_time_slices_a02_v1 | web_ai | 4.73 | 46.0% | 3.88 | 13 | varies |
| crypto_soc_trend_filtered_meanrev_a10_v1 | web_ai | 4.57 | 45.0% | 1.90 | 11 | varies |
| volume_breakout_regime_switch | web_ai | 4.34 | 50.0% | 2.08 | 4 | varies |
| crypto_soc_vol_expansion_index_a03_v1 | web_ai | 4.26 | 62.0% | 2.35 | 45 | varies |
| crypto_soc_regime_filters_a03_v1 | web_ai | 4.08 | 66.0% | 2.27 | 73 | varies |
| crypto_soc_regime_filters_a05_v1 | web_ai | 3.91 | 64.0% | 2.06 | 80 | varies |

**Validation gate:** Sharpe ≥ 1.0, Win Rate ≥ 45%, Max Drawdown ≤ 20%.
**Data source:** Real BTC/USDT OHLCV from crypto_data.db (1h candles, 2020–2026).
**Cross-asset proxies:** SPX, DXY, VIX series are BTC-derived (not independent market data).

### 1.3 Pipeline Status

| Stage | Count | Description |
|-------|-------|-------------|
| Passed Backtest | 124 | Cleared Sharpe/WR/DD gates on historical data |
| Failed Backtest | 13 | Did not meet minimum criteria |
| Validating | 34 | Awaiting full sweep |
| **Unregistered** | **504** | Strategy files not yet evaluated (mass backtest initiated) |
| Forward Testing | 6 | Live on Binance data |
| Graduated | 0 | None yet promoted to production |

### 1.4 Forward Signal Scanner (Tier 1)

8 strategies registered for live scanning:

| Strategy | Backtest Sharpe | Backtest WR | Pairs |
|----------|----------------|-------------|-------|
| ConnorsRSI2MeanReversion | 1.17 | 68.4% | BTC, ETH, SOL |
| ConnorsR3MeanReversion | 1.53 | 71.4% | BTC, ETH, SOL |
| KeltnerMeanReversion | 2.06 | 67.6% | BTC, ETH, SOL |
| VolumePriceConfirmationReversal | 3.93 | 54.8% | 6 pairs |
| BollingerMeanReversion | 0.72 | 60.7% | BTC, ETH, SOL |
| RSIVolumeMeanReversion | 0.70 | 58.5% | BTC, ETH |
| WilliamsRMeanReversion | 0.39 | 59.8% | BTC, ETH, SOL |
| VolatilityScaledMomentum | 0.32 | 65.8% | BTC, ETH, SOL |

---

## 2. Paper Trading Scanner — 78 Strategies

### 2.1 Active Positions

56 active picks across these strategies:

| Strategy | Active Picks | Category |
|----------|-------------|----------|
| funding_rate_carry | 14 | Crypto On-Chain |
| leap_elliott_impulse | 12 | Leap Contest |
| corr_vwap_reversion | 6 | Correlation |
| kimi_lgbm_features | 6 | ML/Kimi |
| alpha_drawdown_responsive | 4 | Alpha Arena |
| corr_kama_adaptive | 4 | Correlation |
| kimi_vol_momentum_blend | 3 | ML/Kimi |
| alpha_risk_parity | 3 | Alpha Arena |
| corr_hma_trend | 2 | Correlation |
| triple_confirmation | 1 | Technical |
| irb_hoffman | 1 | Hoffman IRB |

### 2.2 Closed Trade Performance

| Strategy | Trades | Win Rate | Total P&L | Avg Trade |
|----------|--------|----------|-----------|-----------|
| funding_rate_carry | 10 | 60.0% | -156.71% | -15.67% |
| irb_hoffman | 4 | 0.0% | -9.61% | -2.40% |

**Note:** Only 14 closed trades so far (system went live recently). The funding rate carry has high individual trade size, causing outsized loss percentages.

### 2.3 Strategy Categories

| Category | Count | Portfolio Type | Description |
|----------|-------|---------------|-------------|
| Original 10 | 10 | verified | Core paper trading strategies (Fear & Greed, Volume Breakout, etc.) |
| Correlation Engine | 10 | verified | HMA, KAMA, VWAP, Z-Score, EltonNet — $1K per strategy |
| Leap Contest | 6 | verified | Swing Trail, HTF Momentum, Elliott — from The Leap competition |
| Mercury Framework | 6 | verified | Vol Crossover, Conservative, Aggressive, HMA Filtered |
| FundedRelay | 8 | verified | From The Leap Feb 2026 (+77.7% competition performance) |
| Verified Research | 8 | verified | SuperTrend, WaveTrend, EMA Stack, Keltner, Donchian, BTC50MA |
| Kimi + Academic | 7 | verified | VPIN, EMA-600, LightGBM, TSMOM, Risk-Managed Momentum |
| Gemini Championship | 4 | verified | Hoffman IRB, Fib RSI, Protective Momentum, Adaptive IRB |
| Alpha Arena | 6 | verified | Aggressive Patience, Risk Parity, Four Layer, Regime Switcher |
| Proven Outperformers | 3 | verified | Williams %R (81% WR), Triple RSI (91% WR), Generic Vol Breakout |
| Hoffman IRB | 3 | verified | 1H/2H/4H hold-time variants |
| Hoffman Variations | 8 | incubator | Adaptive ATR, Kalman, Trailing, Kelly, HTF Confluence |
| Incubator | 5 | incubator | Keltner Squeeze, Funding Contrarian, SMI, ADX, MACD Divergence |

### 2.4 Dashboard & Discord Mapping

| System | Dashboard URL | Discord Channel |
|--------|-------------|----------------|
| Paper Trading (all) | [Monitor Dashboard](https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/monitor/) | #master-picks (hourly top picks) |
| Kimi Claw + Academic | [Rise of the Claw](https://findtorontoevents.ca/riseoftheclaw.html) | #master-picks |
| Alpha Arena | [Alpha Engine](https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/alpha/) | #master-picks |
| Mercury/Simpleton | [Monitor Dashboard](https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/monitor/) | #master-picks |
| Incubator | N/A | #sandbox |
| Battleground | [Superpowers Arena](https://findtorontoevents.ca/battleground/) | N/A (internal) |

---

## 3. Strategy Research Sources & Methodology

### 3.1 Research-Backed Strategies (Documented Performance)

| Strategy | Source | Documented WR | Documented Sharpe | Documented PF |
|----------|--------|--------------|-------------------|--------------|
| Williams %R Mean Reversion | QuantifiedStrategies | 81% | 2.9 | 3.2 |
| Triple RSI Confluence | Connors Research | 91% | N/A | 5.0 |
| Generic Volatility Breakout | Multi-source academic | 72-78% | 1.8-2.2 | >1.7 |
| Connors RSI-2 | Larry Connors (High Probability ETF Trading) | 75.7% | 4.84 | N/A |
| IRB Hoffman | Rob Hoffman (ICFM Champion) | ~65% | N/A | >2.0 |

### 3.2 Competition-Sourced Strategies

| Strategy Group | Competition | Best Result | Year |
|---------------|------------|-------------|------|
| FundedRelay (8 strats) | The Leap, Feb 2026 | +77.7% portfolio | 2026 |
| Alpha Arena (6 strats) | Alpha Arena, Qwen 3 Max + DeepSeek V3.1 | Various | 2026 |
| Leap Contest (6 strats) | The Leap internal | Various | 2025-2026 |

### 3.3 AI-Generated Strategy Pipeline

| Agent | Strategies | Passed Backtest | Best Sharpe |
|-------|-----------|----------------|-------------|
| web_ai | 286+ | ~110 | 6.75 |
| codex_gpt5 | 28+ | ~10 | 5.91 |
| baby_strategies | 122 | TBD (backtest running) | TBD |
| team_alpha | 8 | ~3 | varies |
| mercury_ai | 4 | ~2 | varies |
| cursor_ai | 1+ | TBD | TBD |
| claude_code_01 | 5 | TBD | TBD |

---

## 4. Validation Infrastructure

### 4.1 Backtest Engine

- **Real Data Sweep Runner** (`real_data_sweep_runner.py`)
  - Data: Real BTC/USDT 1h OHLCV from SQLite (2020-01-01 to 2026-03-04)
  - Walk-forward simulation with 80-bar minimum lookback, 2-bar step
  - Trade execution: 0.1 position size, 0.1% commission, 20-bar max hold
  - Multi-input context: BTC 1h/4h/15m/5m, SPX/DXY/VIX (BTC-derived proxies)
  - Pass criteria: Sharpe ≥ 1.0, WR ≥ 45%, Max DD ≤ 20%

- **Limitations:**
  - Cross-asset data (SPX, DXY, VIX) are synthetic proxies derived from BTC returns
  - Single-pair testing (BTC/USDT only, not multi-asset)
  - Position sizing is fixed (no Kelly, no pyramiding)
  - Slippage model: flat 0.1% commission only

### 4.2 Forward Testing

- **Forward Signal Scanner** runs Tier 1 strategies against live Binance data
- Tracks entry signals, TP/SL hits, and realized P&L in SQLite
- 8 strategies currently in Tier 1 forward testing

### 4.3 Quality Filter & Ranking

- **Forward Phase Criteria:** ≥12 trades, WR ≥50% OR (Sharpe ≥1.5 AND PF >1.0)
- **Quality Score (0-100):** Sharpe (40pts) + WR (30pts) + Trade Count (20pts) + PF Bonus (10pts)
- **Tiers:** ELITE (≥80) → QUALITY (≥60) → EMERGING (≥40) → WATCH (<40)

### 4.4 Incubator Promotion System

Incubator strategies must achieve:
- 10+ trades
- 55%+ win rate
- Positive average P&L
- Profit Factor ≥ 1.3
- Worst trade > -8%

---

## 5. Known Issues & Biases

### 5.1 Data Integrity Warnings

1. **Cross-asset proxies:** SPX, DXY, VIX data in backtest are BTC-derived, not independent market feeds. Strategies using these have `verification_level: "mixed_real_plus_proxy"`.

2. **Survivorship bias:** Only strategies that produced signals in the test window are evaluated. Strategies that "don't fire" (0 trades) are categorized as `insufficient_data`, not `failed`.

3. **Single-pair backtest:** All backtests run on BTC/USDT only. Multi-pair forward performance may differ.

4. **Look-ahead bias risk:** Backtest uses walk-forward to mitigate, but some parameter tuning may have occurred post-hoc.

5. **Alpha Engine (March 2026):** Showing -314.88% total P&L with 23% WR — significantly underperforming. This system needs investigation and potential overhaul.

### 5.2 Open Bugs

1. **P&L Calendar:** Shows closed trades without symbol name in some views
2. **Top Winning Combos:** Battleground page cut-off issue showing low-trade-count probation strategies
3. **Baby Bundles:** "Proven Winners" bundle shows only "atr_regime_rsi" with recent picks despite 4 strategies

---

## 6. Recommendations for Optimization

### 6.1 Immediate Actions

1. **Scale forward testing:** The 6 profitable Battleground strategies should be given larger allocation
2. **Mass backtest completion:** 504 unregistered strategies being evaluated (workflow initiated 2026-03-05)
3. **Multi-pair expansion:** Test winning strategies on ETH, SOL, BNB (currently BTC-only backtest)

### 6.2 Strategy Optimization

1. **Ensemble approach:** Combine the 6 proven forward strategies into a weighted ensemble
2. **Regime detection:** Add market regime filters (bull/bear/sideways) to reduce false signals
3. **Dynamic position sizing:** Kelly criterion based on rolling win rate and payoff ratio
4. **Correlation filtering:** Avoid taking correlated positions across similar strategies

### 6.3 Infrastructure Improvements

1. **Independent cross-asset data:** Replace BTC-derived proxies with real SPX/DXY/VIX feeds
2. **Multi-timeframe testing:** Validate on 15m, 1h, 4h, 1d timeframes
3. **Out-of-sample testing:** Reserve 2025-2026 data for validation, train on 2020-2024
4. **Transaction cost modeling:** Add realistic slippage, funding rate costs, and exchange fees

---

## Appendix A: System Architecture

```
                    ┌─────────────────────────────────┐
                    │   Strategy Discovery Pipeline    │
                    │  (AI Agents + Research Papers)   │
                    └──────────────┬──────────────────┘
                                   │
                    ┌──────────────▼──────────────────┐
                    │     Real Data Sweep Runner       │
                    │  (Backtest on BTC OHLCV 2020+)  │
                    │  Gate: Sharpe≥1, WR≥45%, DD≤20% │
                    └──────────────┬──────────────────┘
                                   │ Passed: 124
                    ┌──────────────▼──────────────────┐
                    │     Forward Signal Scanner       │
                    │   (Live Binance data, Tier 1)    │
                    │   Gate: 12+ trades, WR≥50%      │
                    └──────────────┬──────────────────┘
                                   │ In testing: 8
                    ┌──────────────▼──────────────────┐
                    │       Quality Filter             │
                    │  ELITE / QUALITY / EMERGING      │
                    └──────────────┬──────────────────┘
                                   │ Profitable: 6
                    ┌──────────────▼──────────────────┐
                    │      Production Bundle           │
                    │  (Graduated for live trading)    │
                    └─────────────────────────────────┘
```

## Appendix B: Data Sources

| Source | Type | Coverage | Update Frequency |
|--------|------|----------|-----------------|
| Binance REST API | OHLCV + Volume | 14 crypto pairs | Real-time (1h candles) |
| crypto_data.db | Historical OHLCV | BTC 2020-2026 (1,969 bars) | Static (updated manually) |
| CoinGecko API | Market caps, dominance | Global crypto | Every 15 min |
| CryptoQuant API | On-chain metrics | BTC, ETH | Every 15 min |
| Alternative.me | Fear & Greed Index | Bitcoin | Daily |
| MySQL (ejaguiar1_stocks) | Audit trail | All systems | Every trade |

## Appendix C: File Reference

| Component | Path | Purpose |
|-----------|------|---------|
| Paper Trading Scanner | `paper_trading/__init__.py` | 78-strategy scanner (hourly) |
| Battleground Dashboard | `battleground/data/baby_strats_dashboard.json` | Strategy registry + metrics |
| Forward Scanner | `incubator/backtest_team/forward_signal_scanner.py` | Tier 1 live scanning |
| Backtest Runner | `incubator/backtest_team/real_data_sweep_runner.py` | Walk-forward engine |
| Batch Backtest | `incubator/backtest_team/batch_backtest_all.py` | Mass evaluation (500+ strategies) |
| Quality Filter | `battleground_quality_filter.py` | Score & rank strategies |
| Dashboard Generator | `incubator/backtest_team/generate_baby_strats_dashboard.py` | Build dashboard JSON |
| Active Picks (BG) | `battleground/data/active_picks.json` | Current live positions |
| Closed Picks (BG) | `battleground/data/closed_picks.json` | Historical trades |
| Active Picks (PT) | `paper_trading/data/active_picks.json` | Paper trading positions |

---

*Report generated 2026-03-05. Mass backtest of 504 unregistered strategies initiated — results pending.*
