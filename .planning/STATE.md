# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-23)

**Core value:** Generate crypto trading picks that consistently beat the market (Sharpe > 2) through rigorous, research-driven ML — not more strategies, but better ones proven by research
**Current focus:** Phase 5 - Remaining items (Dashboard + GitHub Actions automation)

## Current Position

Phase: 5 of 5 (most core code complete)
Plan: 05-01 complete; 05-02 (Dashboard + Actions) and 03-02 (SHAP selection + first model validation) pending
Status: Core system built and tested — first model trained, DSR gate tested
Last activity: 2026-02-24 — Plan 03-02 complete (first model training run)

Progress: [█████████░] 90%

## Completed Work

### Phase 1: Audit and Data Foundation ✅
- **Plan 01-01** (Audit): All existing crypto ML models audited and discarded — no OOS edge. Connors RSI-2 only proven signal.
- **Plan 01-02** (Data Foundation): `config.py`, `data_fetcher.py`, `data_quality.py`, `stationarity.py` — all tested.

### Phase 2: ML Core (Labels, Features, Validation) ✅
- **Plan 02-01** (Labeler): Triple-barrier labeling with embargo, zero-lookahead verified.
- **Plan 02-02** (Feature Engine): 13 stationary features, single shared `features/engine.py`, causal guarantees.
- **Plan 02-03** (Validation): Walk-forward splits, DSR gate, cost-adjusted Sharpe, regime coverage.

### Phase 3: Model Training and Risk ✅
- **Plan 03-01** (Trainer + Risk): `EdgeTrainer` with Optuna/fallback, SHAP importance, model registry. `risk.py` with Kelly sizing and TP/SL.
- **Plan 03-02** (First model validation): ✅ DONE — BTC gross Sharpe 3.29 (real signal). All 3 models correctly rejected by DSR gate (net Sharpe negative after costs). SHAP pruned 16→12 features. Bugs fixed: SHAP 0.50.0 compat, entry threshold, trade counting.

### Phase 4: Gainer Detector ✅
- **Plan 04-01**: `GainerCollector`, `PrePumpModel`, `BreakoutDetector` — all built and tested (55 test items).

### Phase 5: Autonomous Pipeline and Dashboard (partial)
- **Plan 05-01** (Scanner): `scanner.py`, `quick_scanner.py`, `discord_notify.py` — inference pipeline complete.
- **Plan 05-02** (Dashboard + GitHub Actions): NOT YET DONE — need dashboard HTML and automated workflow.

## Test Summary

**215 tests passing** across all modules:
- `test_data.py`: Data foundation
- `test_labeler.py` (51 items): Triple-barrier labeling
- `test_features.py` (43 items): Feature engine
- `test_validation.py` (73 items): Walk-forward validation + DSR
- `test_trainer.py` (53 items): Training + risk
- `test_gainer.py` (55 items): Gainer detector

## Performance Metrics

**Velocity:**
- Total plans completed: 9 of 10
- Phases fully complete: 4 of 5 (Phases 1, 2, 3, 4)
- Phases partially complete: 1 of 5 (Phase 5)

## Remaining Work

### Plan 05-02: Dashboard + GitHub Actions (Phase 5 completion)
- [ ] Build GitHub Pages dashboard (active picks, P&L history, model health)
- [ ] Wire GitHub Actions workflow for automated scan cycles (4h default)
- [ ] Separate Edge Engine from Gainer Detector picks in UI
- [ ] Auto-deploy on picks change

### Iteration: Model v2 (improve edge to pass DSR)
- [ ] Try 4h timeframe (fewer trades, lower cost drag)
- [ ] Try ENTRY_THRESHOLD = 0.65-0.70 (higher conviction only)
- [ ] Consider binary classification (trade/no-trade) instead of 3-class
- [ ] Add volatility regime features (expanded from SHAP insights)

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: New system vs. improve existing — clean slate chosen; existing systems have too much accumulated complexity
- [Roadmap]: Research-first approach — current systems built feature-first which led to overfitting
- [Roadmap]: Phase 4 (Gainer Detector) depends on Phase 2 not Phase 3 — shares the validation framework but not model training
- [01-01]: All existing crypto ML models discarded — no OOS edge confirmed
- [01-01]: Root cause of v1.2 failure: validation-production gap (validation existed but never gated picks)
- [01-01]: Label construction broken: adaptive positive rate → 45-50% positive labels → coin flip targets
- [01-01]: Reuse: advanced_validation.py, feature_engine.py helpers, realistic_backtester.py, slippage map
- [01-01]: Rebuild: label construction (fixed threshold), pick gate (DSR+CPCV required), timeframes (1h/4h only, drop 15m)
- [01-01]: Only proven signal in codebase: Connors RSI-2 on SPY/QQQ (equity); BTC borderline (p=0.009)

### Pending Todos

- [ ] Plan 05-02: Build dashboard and wire GitHub Actions
- [ ] Model v2 iteration: improve edge to pass DSR gate (see 03-02-SUMMARY.md for strategy)

### Blockers/Concerns

- [Phase 3]: GitHub Actions 6h training limit — benchmark on 5 pairs before expanding to 10
- [Phase 3]: Need LightGBM + Optuna + SHAP installed for actual model training
- [Phase 5]: Dashboard design TBD — need to decide static HTML vs. framework

## Session Continuity

Last session: 2026-02-24
Stopped at: Plan 03-02 complete. First model training run executed: BTC shows gross Sharpe 3.29 (real signal found), but net Sharpe negative after costs — DSR gate correctly rejects. SHAP feature selection working (16→12 features for BTC). Bugs fixed: SHAP 0.50.0 API, entry threshold, trade counting, return scaling.
Resume file: None
