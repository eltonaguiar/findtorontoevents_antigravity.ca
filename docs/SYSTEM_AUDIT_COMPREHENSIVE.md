# Comprehensive System Audit — Institutional Grade
**Date:** 2026-03-24 | **Version:** Alpha Engine v2.0 | **Total Strategies:** 130+

---

## 1. System Overview

### Prediction Models & Strategies
| Asset Class | Count | Key Strategies | File |
|-------------|-------|----------------|------|
| Crypto | 44 | Keltner squeeze, autocorrelation, MVRV, funding carry | crypto_strategies.py |
| Forex | 12 | Carry trade, Connors RSI2, Asian range, London breakout | forex_strategies.py |
| Equity | 12 | Momentum factor, quality value, gap reversal | equity_strategies.py |
| Commodities | 8-10 | Seasonal momentum, gold safe haven, oil inventory | commodities_strategies.py |
| On-chain | 10 | MVRV, SOPR, whale flow, exchange netflow | onchain_strategies.py |
| Advanced/Quant | 30+ | HMM regime, cross-sectional momentum, Hurst adaptive | advanced_strategies.py |

### Active Technical Indicators
- RSI (14, 2-period Connors), MACD, Stochastic K/D, CCI, Williams %R
- Bollinger Bands, Keltner Channels, ATR (14)
- EMA (9/21/50/200), SMA (20/50/200)
- Volume ratio, OBI (orderbook imbalance), VPIN toxicity
- Funding rate, futures premium, open interest

### Data Sources & Failover Chain
| Source | Purpose | Failover Position |
|--------|---------|-------------------|
| Binance (api, api1, api2, api3) | OHLCV, funding, OI | Primary (4 mirrors) |
| CoinGecko | Prices, market cap, trends | Secondary |
| KuCoin | Alternative futures pricing | Tertiary |
| CryptoCompare | Multi-exchange consensus | Quaternary |
| Yahoo Finance | VIX, DXY, SPY, forex pairs | Macro data |
| Glassnode/Kaiko | On-chain metrics | Supplementary |

### Deployment & Execution
- **Scan frequency:** Every 30 min (GitHub Actions cron)
- **Latency:** ~5 min scan-to-signal
- **Environment:** GitHub Actions runner (Python 3.12)
- **Output:** active_picks.json, premium_signals.json

---

## 2. Performance Metrics

### System-Wide Performance (1,705 closed trades)

| Metric | Value | Institutional Threshold | Status |
|--------|-------|------------------------|--------|
| Win Rate | 41.9% overall / 64% Smart Picks | >55-60% | Below (overall) / Above (filtered) |
| Profit Factor | 1.19 overall / 1.26 crypto | >1.5 | Below threshold |
| Expectancy | +0.26% per trade | >0 | Positive but thin |
| Sharpe Ratio | 2.95 (no fees) | >1.0 | Inflated — needs fee adjustment |
| Sortino Ratio | -0.0111 (now being recomputed) | >1.5 | **Critical gap — new module deployed** |
| Max Drawdown | -302.62% (leveraged) | <20% | **Unacceptable — new tracker deployed** |
| Calmar Ratio | -0.0127 | >0.5 | **Negative — needs improvement** |
| Max Win Streak | 7 | — | Moderate |
| Max Loss Streak | 18 | <10 | **Too long** |
| Score-PnL Correlation | r=0.043 | >0.15 | **Near-random — scoring needs overhaul** |

### Performance by Asset Class

| Category | Trades | WR | PF | P&L | Status |
|----------|--------|-----|-----|------|--------|
| Crypto | ~1,200 | 42.8% | 1.26 | +3,818% | **PROVEN EDGE** |
| Forex | ~120 | 33.9% | 0.53 | -18.17% | PROBATION (gates fixed 2026-03-24) |
| Equity | ~150 | 31.8% | 0.63 | -617% | PROBATION (macro gate active) |
| claude_gainer_ml | ~30 | 11.1% | — | -27.10% | HARD KILLED |

### Top 5 Strategies (Forward-Tested)

| Strategy | WR | Sharpe | P&L | Trades | p-value |
|----------|-----|--------|------|--------|---------|
| autocorrelation_exploiter | 83.3% | 28.74 | +$1,459 | 6 | — |
| volume_profile_value_area | 80.0% | 26.17 | +$887 | 5 | — |
| hurst_regime_adaptive | 71.4% | 12.07 | +$854 | 7 | — |
| keltner_compression_eth | 58.5% | 4.18 | +$2,635 | 41 | 0.001 |
| keltner_compression_btc | 70.9% | 2.88 | +$1,932 | 55 | 0.001 |

### Sample Trades (Recent)
```
2026-03-23 14:30 | BTCUSDT LONG | Entry: $70,507 | TP: $72,115 | SL: $69,380
  Strategy: keltner_compression | Conf: 0.68 | R:R: 1.42 | Elite: 82
  Result: PENDING (active)

2026-03-22 09:15 | ETHUSDT SHORT | Entry: $2,134 | TP: $2,070 | SL: $2,170
  Strategy: funding_rate_carry | Conf: 0.71 | R:R: 1.78 | Elite: 76
  Result: WON (+3.0%)
```

---

## 3. Signal Generation & Validation

### Algorithmic Pipeline
```
Data Fetch (Binance+fallbacks)
  → Regime Detection (BTC price, F&G, funding, volume)
  → Strategy Execution (130+ strategies across 6 modules)
  → Quality Gates (5 hard filters)
  → ML Ranking (XGBoost/LightGBM/RandomForest)
  → Elite Scoring (23 components, 0-100 scale)
  → Smart Pick Selection (top N by composite score)
  → Position Sizing (half-Kelly + vol scaling)
  → Output (active_picks.json, premium_signals.json)
```

### Signal Validation Criteria
1. **Regime alignment:** LONG in bull, SHORT in bear (40pt weight)
2. **R:R >= 1.0** hard floor, sweet spot 2.0-2.5 (73.7% WR)
3. **Confidence 0.50-0.80** band (0.60-0.70 = best at 61% WR)
4. **Strategy track record:** Min 10 trades at 45%+ WR for core
5. **Stop distance:** Optimal 1.5-3% crypto, 0.5-1.5% forex

### ML Components
| Component | Model | Features | Status |
|-----------|-------|----------|--------|
| Primary ranker | XGBoost (warm-start) | 39 engineered → 15-20 via Boruta | Active |
| Secondary | LightGBM | Same feature set | Fallback |
| Cold-start | RandomForest | Heuristic | When < 50 trades |
| Feature selection | Boruta (Kursa & Rudnicki 2010) | 7-day cache TTL | Active |
| Cross-validation | Purged time-series CV | 2% embargo (Lopez de Prado) | Active |
| Drift detection | Accuracy < 45% on 50-pick window | Triggers full retrain | Active |
| Labeling | Triple-barrier (+1 TP, 0 expire, -1 SL) | Asymmetric weights | Active |

### Statistical Tests
- Binomial test vs 50% baseline for strategy WR significance
- P-value tracking per strategy (keltner_compression: p=0.001)
- ML model AUC tracking (was 1.0 due to leaky features — fixed, now realistic)

---

## 4. Operational & Data Integrity

### Signal Consistency
- **Scan frequency:** Every 30 min via GitHub Actions
- **Active picks:** ~283 open positions tracked
- **Signal stability:** Strategy tiers reviewed weekly
- **Lifecycle:** Incubator → Core → Kill (with mutation before kill)

### Look-Ahead Bias Prevention
- Purged time-series CV with 2% embargo gap
- Leaky features identified and excluded (entry_vs_optimal, hold_duration, MFE, MAE)
- Triple-barrier labeling uses only post-entry price data
- Walk-forward validation module deployed (threshold_overfit_validator.py)

### Data Quality Assurance
- API failover chain (3+ endpoints mandatory per CLAUDE.md)
- Duplicate pick detection in forward_validator.py
- Symbol sanity checks and price bounds validation
- Graceful degradation when data sources fail

### Latency & Slippage
- **Scan-to-signal:** ~5 min (acceptable for swing trading)
- **Estimated slippage:** 0.1% per trade (now included in realistic Sharpe via institutional_metrics.py)
- **Execution:** Manual (paper trading phase) — no auto-execution yet

---

## 5. Risk Management

### Position Sizing
| Parameter | Value | Notes |
|-----------|-------|-------|
| Starting capital | $10,000 | Base portfolio |
| Max risk per trade | 2% ($200) | Hard cap |
| Max allocation per pick | 15% ($1,500) | Concentration limit |
| Max total exposure | 80% ($8,000) | Cash reserve |
| Max correlated exposure | 40% ($4,000) | Same asset class |
| Kelly cap | 5% | Half-Kelly conservative |
| Vol target | 15% annualized | Inverse vol scaling |

### Stop Loss / Take Profit by Category
| Category | SL | TP | Max Hold | Trail |
|----------|-----|-----|----------|-------|
| Crypto | -8.0% | +15% | 7 days | 10% after 4% profit |
| Forex | -2.5% | +3.0% | 14 days | 2% after 4% profit |
| Equity | -6.0% | +12% | 10 days | 6% after 4% profit |
| Meme | -15% | +35% | 3 days | 15% |
| Penny | -12% | +25% | 5 days | 10% |

### Dynamic Risk Controls
- **Trailing stops:** Activate after TRAIL_ACTIVATE_PCT (4%) profit
- **Forex macro gate:** Blocks LONGs when DXY trend opposes, vol > 2x baseline
- **Equity macro gate:** Blocks LONGs when SPY < 200d SMA or 5d return < -7%
- **SHORT gate:** Data-driven via short_trade_validator.py (system SHORT WR = 20.5%)
- **Drawdown tracker:** NEW — `drawdown_tracker.py` monitors per-strategy and portfolio DD

---

## 6. Performance Variance & Failure Modes

### Known Failure Scenarios
| Scenario | Impact | Mitigation |
|----------|--------|------------|
| Choppy/ranging regime | WR drops to ~30% | Regime detector reduces position count |
| Flash crash | SL hit on all positions | Max 80% exposure, trailing stops |
| Single-symbol concentration | FETUSDT = 153.6% of total P&L | Max 2 picks per symbol |
| Overconfidence trap | Conf > 0.80 = 49% WR | Confidence band 0.55-0.80 |
| Forex deadlock | Gate blocked all forex | Fixed 2026-03-24 (insufficient data = pass) |
| API geo-block | Primary Binance blocked | 3+ fallback chain mandatory |
| ML leaky features | AUC = 1.0 (overfit) | Purged CV, feature exclusion list |

### Drawdown History
- Max drawdown: -302.62% (leveraged, early system)
- Max loss streak: 18 trades
- Recovery: Ongoing — system profitable since quality gates added
- **NEW:** Per-strategy drawdown tracking deployed via drawdown_tracker.py

### Iteration History (Recent)
| Date | Change | Impact |
|------|--------|--------|
| 2026-03-24 | Forex deadlock gate fixed | Forex picks now flow through |
| 2026-03-24 | 4 institutional modules deployed | Sortino, drawdown, walk-forward, scorecard |
| 2026-03-23 | Indicator correlation tracker | Technical confirmation scoring |
| 2026-03-22 | Non-crypto quality gates | Forex/equity probation system |
| 2026-03-16 | Strategy audit (574 trades) | 41 strategies ranked |
| 2026-03-03 | Core whitelist + kill list | Data-driven strategy lifecycle |

---

## 7. Institutional Modules (Deployed 2026-03-24)

### New Modules Summary

| Module | Purpose | Output |
|--------|---------|--------|
| `institutional_metrics.py` | Sortino, Calmar, realistic Sharpe (with 0.1% fees), IC | data/institutional_metrics.json |
| `drawdown_tracker.py` | Max DD per strategy + portfolio, recovery time, streak tracking | data/drawdown_report.json |
| `threshold_overfit_validator.py` | Walk-forward validation, overfit risk score (0-100) | data/walk_forward_report.json |
| `institutional_scorecard.py` | 250-point hedge fund signal scorecard | data/institutional_scorecard.json |

### Scorecard Sections (250 points total)
| Section | Max Points | What It Measures |
|---------|-----------|------------------|
| Data Quality | 25 | Field completeness, no look-ahead bias, scan recency |
| Statistical Power | 75 | WR, PF, expectancy, IC, p-value |
| Operational | 30 | Stability, volume, latency |
| Risk Management | 45 | Drawdown, streaks, R:R, stress resilience |
| Market Resilience | 30 | Regime robustness, crash correlation, liquidity |
| Validation | 45 | Walk-forward, Monte Carlo, decay, forward test depth |

### Grading Scale
| Grade | Score | Meaning |
|-------|-------|---------|
| A | 200-250 | Top-tier, suitable for professional deployment |
| B | 150-199 | Promising, needs refinement |
| C | 100-149 | Significant gaps remain |
| D | 50-99 | Major overhaul needed |
| F | <50 | Not viable |

**Estimated current score: ~110-130 (Grade C)** — strong forward testing and multi-factor filtering, but gaps in statistical validation, drawdown control, and slippage modeling.

---

## 8. Recommendations & Roadmap

### Phase 1: Quick Wins (This Week)
- [x] Deploy Sortino/Calmar/realistic Sharpe computation
- [x] Deploy per-strategy drawdown tracker
- [x] Deploy walk-forward overfitting validator
- [x] Deploy 250-point institutional scorecard
- [ ] R:R >= 1.5 hard gate in production_scanner.py
- [ ] Fix confidence scoring (0.60-0.70 = best zone)
- [ ] Wire drawdown_tracker into strategy gating

### Phase 2: Scoring Overhaul (Next Week)
- [ ] Regime match weight 0.40 → 0.50
- [ ] Strategy track record weight doubled to 20 pts
- [ ] Implement half-Kelly with vol scaling in production
- [ ] Fix Score-PnL correlation (r=0.043 → target r>0.15)

### Phase 3: Advanced (Month 1)
- [ ] HMM/Bayesian regime detection
- [ ] Portfolio correlation monitoring
- [ ] Stress testing framework (flash crash, gap scenarios)
- [ ] Monte Carlo simulation integration
- [ ] Slippage modeling per asset class
- [ ] Formal audit trail logging

### Phase 4: Institutional Readiness (Month 2-3)
- [ ] Multi-manager pod structure (trend, mean-reversion, on-chain, copy, event)
- [ ] Quarterly strategy rebalancing automation
- [ ] Regulatory compliance documentation
- [ ] Investor-grade reporting dashboard
- [ ] Fee structure modeling (2/20 with clawback)

---

## 9. Academic References

| Strategy/Method | Reference | Application |
|----------------|-----------|-------------|
| Cross-sectional momentum | Jegadeesh & Titman (1993) | Equity momentum factor |
| Carry trade | Lustig & Verdelhan (2007) | Forex carry premium |
| Connors RSI2 | Connors & Alvarez | Mean reversion (68% WR) |
| Time-series momentum | Moskowitz et al. (2012, JFE) | Trend following |
| Feature selection | Kursa & Rudnicki (2010) | Boruta algorithm |
| ML validation | Lopez de Prado (AFML) | Purged time-series CV |
| Cross-sectional crypto | Liu et al. (2022, JFE) | Crypto factor model |
| Position sizing | Kelly (1956) | Optimal fraction |

---

*This audit is a living document. Regenerate institutional_scorecard.py on each alpha engine cycle for current grading.*
