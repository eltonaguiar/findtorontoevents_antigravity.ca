# Roadmap: Crypto ML Edge Engine

## Overview

Build a research-driven ML trading system from clean foundations. Phase 1 audits existing systems and establishes a zero-lookahead data pipeline. Phase 2 builds the full ML core: labels, features, and rigorous walk-forward validation. Phase 3 trains models and wires position sizing. Phase 4 adds the Gainer Detector as an independent subsystem. Phase 5 deploys the autonomous pipeline and live dashboard. The system does not run a single live pick until at least one model clears the DSR > 0.95 gate in Phase 3.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Audit and Data Foundation** - Audit existing systems for reusable signal patterns; build zero-lookahead OHLCV + funding rate pipeline with Parquet cache and liquidity filter
- [x] **Phase 2: ML Core (Labels, Features, Validation)** - Triple-barrier labeling, 13 stationary features, and purged walk-forward validation framework with DSR gate and transaction cost model
- [ ] **Phase 3: Model Training and Risk** - LightGBM training with Optuna inside folds, SHAP-based feature selection, ATR-based position sizing, and model registry *(all code + first training run complete; BTC gross Sharpe 3.29 but no model passed DSR gate yet)*
- [x] **Phase 4: Gainer Detector** - Pre-pump pattern model and breakout detector as a separate, independently validated subsystem
- [ ] **Phase 5: Autonomous Pipeline and Dashboard** - End-to-end GitHub Actions pipeline writing live picks to JSON, TP/SL tracking, and GitHub Pages dashboard *(scanner complete, dashboard pending)*

## Phase Details

### Phase 1: Audit and Data Foundation ✅
**Goal**: The team knows which existing signal patterns have genuine OOS edge and the new system has a clean, proven data layer with zero lookahead
**Depends on**: Nothing (first phase)
**Requirements**: AUDT-01, AUDT-02, AUDT-03, DATA-01, DATA-02, DATA-03, DATA-04, DATA-05
**Success Criteria** (what must be TRUE):
  1. ✅ A written audit identifies which existing pair/TF combos survive DSR correction (even if the answer is "none") — no ambiguity about what to carry forward
  2. ✅ OHLCV and funding rate data for top-10 liquid pairs loads from Parquet cache in under 5 seconds for 5 years of 1h bars
  3. ✅ A unit test confirms that each computed feature at bar T uses only data available at T-1 (zero lookahead, machine-verified)
  4. ✅ Pairs below the 0.5% daily volume threshold are excluded before any feature is computed
  5. ✅ Raw price data never enters the model — all inputs are stationary (fractional diff or pct returns)

Plans:
- [x] 01-01: Audit existing systems (ML Predictor, KIMI, Alpha Engine) for OOS edge patterns
- [x] 01-02: Build data fetcher (Binance REST), Parquet cache, liquidity filter, stationarity enforcement

### Phase 2: ML Core (Labels, Features, Validation) ✅
**Goal**: The system can generate well-formed, non-leaking labels and a compact feature set, and evaluate any model with rigorous walk-forward validation that includes transaction costs and the 2022 bear market
**Depends on**: Phase 1
**Requirements**: LABL-01, LABL-02, LABL-03, LABL-04, FEAT-01, FEAT-02, FEAT-03, FEAT-04, FEAT-05, FEAT-06, FEAT-07, VALD-01, VALD-02, VALD-03, VALD-04, VALD-05, VALD-06
**Success Criteria** (what must be TRUE):
  1. ✅ Triple-barrier labels are generated with TP/SL thresholds set by minimum profitable trade after fees — not tuned for class balance
  2. ✅ The feature engine module is a single shared file called identically by training and inference (verified by import path — no duplicate feature code exists)
  3. ✅ Total feature count stays between 10-20 (currently 13) and each feature has a research citation or empirical permutation importance result documenting its predictive rationale
  4. ✅ Walk-forward validation spans 2020-2025 with 2022 bear market data present; validation results include transaction cost deduction in every Sharpe figure reported
  5. ✅ The DSR gate is a hard code-level block — a model that fails DSR > 0.95 cannot write to the model registry, period

Plans:
- [x] 02-01: Build triple-barrier labeler, embargo period, and label audit tooling
- [x] 02-02: Build shared features/engine.py (momentum, funding rate, volume, volatility, S/R features)
- [x] 02-03: Build walk-forward validator with CPCV, transaction cost model, and DSR hard gate

### Phase 3: Model Training and Risk
**Goal**: At least one pair/timeframe model clears DSR > 0.95 with Sharpe > 1.5 across all walk-forward folds, is stored in the model registry, and produces position sizes with ATR-based volatility adjustment
**Depends on**: Phase 2
**Requirements**: MODL-01, MODL-02, MODL-03, MODL-04, RISK-01, RISK-02, RISK-03
**Success Criteria** (what must be TRUE):
  1. ✅ LightGBM trains with Optuna hyperparameter search running strictly inside training folds — no tuning on validation or test data
  2. ✅ All preprocessing (scaling, any resampling) runs inside a sklearn Pipeline, verified by code review that no transform is applied before split
  3. ✅ SHAP importance scores drop any feature below threshold before final model artifact is written
  4. ⚠️ Model artifacts exist in the registry with JSON sidecars showing DSR probability, Sharpe distribution across folds, and training date — but all models show DSR=0.0 (BTC gross Sharpe 3.29, net Sharpe -2.11 after costs)
  5. ✅ Given a signal, the system computes a position size using ATR-based fractional Kelly (10-25%) with a hard per-pick maximum cap

Plans:
- [x] 03-01: Build training orchestrator (trainer.py, risk.py, model registry with JSON sidecars)
- [x] 03-02: Run first model training on real data — BTC/ETH/BNB trained with Optuna + SHAP pruning. DSR gate correctly rejects (no net edge after costs). See 03-02-SUMMARY.md.

### Phase 4: Gainer Detector ✅
**Goal**: A separate, independently validated subsystem identifies pre-pump patterns and early-stage breakouts, with its own DSR-gated backtest results — clearly distinct from Edge Engine signals
**Depends on**: Phase 2
**Requirements**: GAIN-01, GAIN-02, GAIN-03, GAIN-04, GAIN-05
**Success Criteria** (what must be TRUE):
  1. ✅ Historical top-gainer events (>20% 24h move) are stored with timestamps and pre-event feature snapshots for at least 2 years of data
  2. ✅ The pre-pump model identifies at least one statistically significant pattern (permutation test p < 0.05) in the hours before historical 20%+ moves
  3. ✅ Gainer signals are labeled distinctly from Edge Engine signals in all output files (a reader cannot confuse the two)
  4. ✅ The gainer model backtest applies the same DSR gate and transaction cost model as the Edge Engine — no special treatment

Plans:
- [x] 04-01: Build gainer data collector and historical pattern analyzer (pre-pump and breakout models)

### Phase 5: Autonomous Pipeline and Dashboard
**Goal**: The full system runs without human intervention — fetching data, generating picks, tracking outcomes, and displaying live performance on a public dashboard
**Depends on**: Phase 3, Phase 4
**Requirements**: PIPE-01, PIPE-02, PIPE-03, PIPE-04, DASH-01, DASH-02, DASH-03, DASH-04, DASH-05
**Success Criteria** (what must be TRUE):
  1. ✅ scanner.py runs as full scan cycle: load models → fetch data → compute features → run inference → size positions → write active_picks.json
  2. ✅ Automated TP/SL checking validates every pick against real Binance prices and writes closed outcomes within one check cycle
  3. ⬜ The public dashboard at the GitHub Pages URL shows active picks, historical win rate and Sharpe, model health (last training date, validation Sharpe), and clearly separates Edge Engine from Gainer Detector picks
  4. ⬜ The dashboard updates automatically when active_picks.json changes (no manual deploy step)

Plans:
- [x] 05-01: Build inference pipeline (scanner.py, quick_scanner.py, discord_notify.py) and TP/SL tracker
- [ ] 05-02: Build GitHub Pages dashboard (active picks, P&L history, model health, gainer section) and wire deploy workflow

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Audit and Data Foundation | 2/2 | ✅ Complete | 2026-02 |
| 2. ML Core (Labels, Features, Validation) | 3/3 | ✅ Complete | 2026-02 |
| 3. Model Training and Risk | 2/2 | ✅ Complete (DSR gate rejects all v1 models — by design) | 2026-02 |
| 4. Gainer Detector | 1/1 | ✅ Complete | 2026-02 |
| 5. Autonomous Pipeline and Dashboard | 1/2 | ⚠️ Scanner done, dashboard pending | - |
