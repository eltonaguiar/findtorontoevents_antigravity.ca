# Requirements: Crypto ML Edge Engine

**Defined:** 2026-02-23
**Core Value:** Generate crypto trading picks that consistently beat the market (Sharpe > 2) through rigorous, research-driven ML

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Data Foundation

- [ ] **DATA-01**: System fetches OHLCV data from Binance for top-10 liquid pairs by 24h volume
- [ ] **DATA-02**: System fetches funding rate data from Binance perpetual futures API
- [ ] **DATA-03**: All features enforce stationarity (fractional differentiation d≈0.4 or percentage returns — no raw prices as model input)
- [ ] **DATA-04**: Liquidity filter excludes pairs where position size would exceed 0.5% of daily volume
- [ ] **DATA-05**: Data pipeline caches historical data locally in Parquet format to avoid redundant API calls

### Existing System Audit

- [ ] **AUDT-01**: Audit existing ML Predictor, KIMI, and Alpha Engine forward test results for any patterns with genuine out-of-sample edge
- [ ] **AUDT-02**: Extract any working signal patterns (strategies, features, pair/TF combos) from existing backtests that survive DSR correction
- [ ] **AUDT-03**: Document which existing components can be reused vs must be rebuilt

### Label Construction

- [ ] **LABL-01**: Labels use forward returns only (close[t+N]) with zero lookahead bias — verified by code audit
- [ ] **LABL-02**: Triple-barrier labeling: +1 when TP hit, -1 when SL hit, 0 on timeout
- [ ] **LABL-03**: Label threshold set by minimum profitable trade after fees (not tuned for class balance)
- [ ] **LABL-04**: Embargo period between training and test labels to prevent leakage

### Feature Engineering

- [ ] **FEAT-01**: Momentum features: lagged returns at 1h, 4h, 24h, 7d intervals
- [ ] **FEAT-02**: Funding rate features: current rate, rate z-score, rate momentum
- [ ] **FEAT-03**: Volume features: relative volume vs 20-period average, volume momentum
- [ ] **FEAT-04**: Volatility features: ATR, realized vol percentile (90-day rolling)
- [ ] **FEAT-05**: Support/resistance features: distance to key levels (recent swing highs/lows, round numbers, high-volume nodes)
- [ ] **FEAT-06**: Total feature count stays between 10-20 per model (no feature bloat)
- [ ] **FEAT-07**: Single feature engine module used identically by training and inference (no training-serving skew)

### Validation Framework

- [ ] **VALD-01**: Walk-forward validation with expanding or rolling window spanning 2020-2025
- [ ] **VALD-02**: Validation must include 2022 bear market data (regime coverage)
- [ ] **VALD-03**: Purged cross-validation with embargo gap (no random k-fold on time series)
- [ ] **VALD-04**: Deflated Sharpe Rate gate: only models with DSR probability > 0.95 are promoted to live
- [ ] **VALD-05**: Maximum 10 model variants per training run (prevent multiple testing inflation)
- [ ] **VALD-06**: Transaction cost model applied to all backtest results (Binance fees + estimated slippage)

### Model Training

- [ ] **MODL-01**: Primary model: LightGBM with Optuna hyperparameter tuning inside training folds only
- [ ] **MODL-02**: All preprocessing (scaling, any resampling) inside sklearn Pipeline — never applied before split
- [ ] **MODL-03**: SHAP-based feature importance: drop features below importance threshold
- [ ] **MODL-04**: Model training runs on GitHub Actions CPU runners within time limits

### Risk & Position Sizing

- [ ] **RISK-01**: ATR-based volatility-adjusted position sizing (fractional Kelly 10-25%)
- [ ] **RISK-02**: Maximum position size cap per pick
- [ ] **RISK-03**: TP/SL levels set per pick based on ATR multiple

### Gainer Detector

- [ ] **GAIN-01**: System collects daily top gainers (>20% 24h move) from Binance/CoinGecko and stores historical gainer data
- [ ] **GAIN-02**: Pre-pump model: analyzes common patterns in hours before historical 20%+ moves (volume acceleration, funding rate shifts, price compression)
- [ ] **GAIN-03**: Breakout detector: identifies pairs already showing early-stage explosive moves for timely entry
- [ ] **GAIN-04**: Gainer signals are separate from Edge Engine signals (clearly labeled on dashboard)
- [ ] **GAIN-05**: Gainer model backtested with same rigorous validation as Edge Engine (walk-forward, DSR gate)

### Autonomous Pipeline

- [ ] **PIPE-01**: GitHub Actions workflow runs end-to-end: data fetch → feature compute → predict → output picks
- [ ] **PIPE-02**: Active picks written to JSON file (entry price, TP, SL, confidence, timestamp)
- [ ] **PIPE-03**: Pipeline runs on configurable schedule (default: every 4 hours)
- [ ] **PIPE-04**: Automated TP/SL tracking validates picks against real Binance prices
- [ ] **PIPE-05**: Discord notification on each pipeline run with GSD branding, honest performance assessment (training status, forward win rate, whether system is a "winner" yet)

### Dashboard

- [ ] **DASH-01**: HTML dashboard shows active picks with entry price, TP/SL, confidence
- [ ] **DASH-02**: Dashboard shows historical P&L: total return, win rate, Sharpe ratio
- [ ] **DASH-03**: Dashboard shows model health: last training date, validation Sharpe, feature importance
- [ ] **DASH-04**: Dashboard deployed via GitHub Pages (guaranteed uptime)
- [ ] **DASH-05**: Edge Engine picks and Gainer Detector picks displayed in separate sections

## v2 Requirements

Deferred to future release. Add after v1 forward results prove edge exists.

### Regime Enhancement
- **REGM-01**: Regime-conditional model switching (separate LightGBM per bull/bear/sideways)
- **REGM-02**: Fear/Greed Index as trade suspension gate (pause during extreme fear)

### Meta-Labeling
- **META-01**: M2 precision filter activated after 200+ closed picks
- **META-02**: M2 model trained on closed pick outcomes to filter false positives

### Cross-Sectional
- **XSEC-01**: Cross-sectional momentum ranking across universe
- **XSEC-02**: Relative strength features (pair vs BTC, pair vs sector)

### On-Chain
- **ONCN-01**: Real MVRV ratio (not proxy) via paid API
- **ONCN-02**: Exchange netflow data for whale detection

## Out of Scope

| Feature | Reason |
|---------|--------|
| Deep learning (LSTM, Transformer) | Research shows equal/worse out-of-sample vs tree models on CPU; requires GPU |
| Trade execution / brokerage integration | Signal generation only — v1 is manual execution |
| 36-pair uniform coverage | Research says alpha concentrates in fewer pairs; focus on 5-10 with proven edge |
| High-frequency retraining (daily) | Without DSR gates, frequent retraining overfits to noise |
| Twitter/Telegram scraping | High maintenance, inconsistent quality; Fear/Greed Index suffices |
| Strategy zoo (100+ strategies) | Multiple testing inflation; proven failure mode in existing systems |
| Mobile app | Web dashboard only |
| Forex/equity in v1 | Crypto-only to prove approach |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DATA-01 | Phase 1 | Pending |
| DATA-02 | Phase 1 | Pending |
| DATA-03 | Phase 1 | Pending |
| DATA-04 | Phase 1 | Pending |
| DATA-05 | Phase 1 | Pending |
| AUDT-01 | Phase 1 | Pending |
| AUDT-02 | Phase 1 | Pending |
| AUDT-03 | Phase 1 | Pending |
| LABL-01 | Phase 2 | Pending |
| LABL-02 | Phase 2 | Pending |
| LABL-03 | Phase 2 | Pending |
| LABL-04 | Phase 2 | Pending |
| FEAT-01 | Phase 2 | Pending |
| FEAT-02 | Phase 2 | Pending |
| FEAT-03 | Phase 2 | Pending |
| FEAT-04 | Phase 2 | Pending |
| FEAT-05 | Phase 2 | Pending |
| FEAT-06 | Phase 2 | Pending |
| FEAT-07 | Phase 2 | Pending |
| VALD-01 | Phase 2 | Pending |
| VALD-02 | Phase 2 | Pending |
| VALD-03 | Phase 2 | Pending |
| VALD-04 | Phase 2 | Pending |
| VALD-05 | Phase 2 | Pending |
| VALD-06 | Phase 2 | Pending |
| MODL-01 | Phase 3 | Pending |
| MODL-02 | Phase 3 | Pending |
| MODL-03 | Phase 3 | Pending |
| MODL-04 | Phase 3 | Pending |
| RISK-01 | Phase 3 | Pending |
| RISK-02 | Phase 3 | Pending |
| RISK-03 | Phase 3 | Pending |
| GAIN-01 | Phase 4 | Pending |
| GAIN-02 | Phase 4 | Pending |
| GAIN-03 | Phase 4 | Pending |
| GAIN-04 | Phase 4 | Pending |
| GAIN-05 | Phase 4 | Pending |
| PIPE-01 | Phase 5 | Pending |
| PIPE-02 | Phase 5 | Pending |
| PIPE-03 | Phase 5 | Pending |
| PIPE-04 | Phase 5 | Pending |
| DASH-01 | Phase 5 | Pending |
| DASH-02 | Phase 5 | Pending |
| DASH-03 | Phase 5 | Pending |
| DASH-04 | Phase 5 | Pending |
| DASH-05 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 45 total
- Mapped to phases: 45
- Unmapped: 0 ✓

---
*Requirements defined: 2026-02-23*
*Last updated: 2026-02-23 — traceability complete after roadmap creation*
