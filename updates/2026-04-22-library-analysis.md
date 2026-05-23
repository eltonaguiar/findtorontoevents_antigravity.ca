# Library Analysis - Prediction System Enhancement
Date: 2026-04-22

## UPDATE: Integrated Libraries

### ✅ vectorbt - Integrated
- **Status:** Installed and module created: `alpha_engine/vectorbt_explorer.py`
- **Usage:**
  ```python
  from alpha_engine.vectorbt_explorer import explore_ma_crossover
  results = explore_ma_crossover('BTC-USD', fast_windows=[5,10,15], slow_windows=[20,50,100])
  ```

### ✅ bayesian-optimization - Integrated
- **Status:** Installed and module created: `alpha_engine/bayes_optimizer.py`
- **Usage:**
  ```python
  from alpha_engine.bayes_optimizer import optimize_tp_sl
  best = optimize_tp_sl("ema_crossover", "BTCUSDT", n_iterations=30)
  ```

---

## Current Stack (alpha_engine/requirements.txt)

**Data:** yfinance, pandas-datareader, requests, beautifulsoup4, feedparser
**ML:** scikit-learn, lightgbm, xgboost, shap, hmmlearn
**Stats:** numpy, pandas, scipy, hurst
**Viz:** matplotlib, seaborn, jinja2, plotly
**Misc:** tqdm, joblib, pyyaml, rich, tabulate, textblob, vaderSentiment

---

## High-Value Missing Libraries

### Tier 1: Critical for Edge Detection

| Library | Purpose | Value | Status |
|---------|---------|-------|--------|
| **vectorbt** | Ultra-fast vectorized backtesting (millions of sims/sec) | Massive parameter exploration speed | Integrated (`alpha_engine/vectorbt_explorer.py`) |
| **mlfinlab** | Lopez de Prado methods (triple barrier, CPCV) | Better ML labeling, proper cross-validation | Not integrated |
| **bayesian-optimization** | Bayesian hyperparameter tuning | Smarter param search vs grid | Integrated (`alpha_engine/bayes_optimizer.py`) |

### Tier 2: Validation Enhancement

| Library | Purpose | Value | Status |
|---------|---------|-------|--------|
| **quant-backtest-framework** | Walk-forward, Monte Carlo, CPCV | Rigorous OOS validation | Not integrated |
| **PyBroker** | Walkforward + ML + bootstrap metrics | End-to-end ML workflow | Not integrated |
| **Backtesting.py** | Simple backtest + SAMBO optimizer | Quick strategy testing | Not integrated |

### Tier 3: Nice to Have

| Library | Purpose | Value |
|---------|---------|-------|
| **qf-lib** | Event-driven backtester, Bloomberg support | Enterprise features |
| **walk-forward-backtester** | WFO implementation | Simpler than custom |
| **triple-barrier** | Trade labeling utility | Standalone labeling |

---

## Recommendations

### Priority 1: vectorbt
**Why:** Your backtest_*.py files do grid search. VectorBT runs 10,000-1,000,000x faster with Numba acceleration. Critical for exploring strategy parameter space.

**Use case:** Replace/replace slow grid searches in battle_test.py, backtest_new_strategies.py with vectorbt for exploration phase.

### Priority 2: mlfinlab / quantreo
**Why:** Your ML models use simple returns as labels. Triple barrier labeling = realistic trade outcomes. CPCV = leak-free cross-validation.

**Use case:** Improve ML feature engineering in backfill_ml_features.py with proper labels.

### Priority 3: bayesian-optimization
**Why:** Your auto_tuner.py likely uses grid/random search. Bayesian finds better params in fewer iterations.

**Use case:** Enhance adaptive_tp_sl.py parameter search.

### Priority 4: quant-backtest-framework (Advanced)
**Why:** Walk-forward validation + Monte Carlo + GO/NO-GO criteria. Solves "backtest looks great, live loses" problem.

**Use case:** Add rigorous OOS layer to battle_test.py before deploying picks.

---

## Integration Candidates

### Can Integrate: vectorbt

**Feasibility:** HIGH
- Pure Python/NumPy/Pandas + Numba (already have numpy, pandas)
- pip install vectorbt
- No database/API dependencies
- Works offline with OHLCV data (your existing backtest infrastructure)

**Effort:** 2-4 hours to create a vectorbt wrapper that converts your existing picks/strategies to vectorbt format for exploration phase.

### Can Integrate: bayesian-optimization

**Feasibility:** HIGH
- pip install bayesian-optimization
- Simple API: define objective function, pass bounds
- Works with any backtester

**Effort:** 1-2 hours to add to adaptive_tp_sl.py or create new optimizer module.

### Can Integrate: mlfinlab

**Feasibility:** MEDIUM
- pip install mlfinlab (requires paid license for some features) OR quantreo (open source)
- Need OHLCV with high/low timestamps for triple barrier
- More involved integration

**Effort:** 4-8 hours for full integration, modifies labeling in backfill_ml_features.py.

### Can Integrate: Backtesting.py

**Feasibility:** MEDIUM  
- pip install backtesting
- Built-in optimizer, interactive plots
- Simpler than vectorbt, slower but more features

**Effort:** 2-3 hours for basic integration.

---

## Integration Plan

### Phase 1: vectorbt (Quick Win)
1. Install: `pip install vectorbt`
2. Create wrapper: convert existing strategy signals to vbt format
3. Run parameter sweeps on top strategies
4. Feed best params back to existing pipeline

### Phase 2: bayesian-optimization (Quick Win)
1. Install: `pip install bayesian-optimization`
2. Add to auto_tuner.py for TP/SL parameter optimization
3. Use in adaptive_tp_sl.py

### Phase 3: mlfinlab (Medium Effort)
1. Evaluate: mlfinlab (paid) vs quantreo (open source)
2. Implement triple barrier labeling
3. Add CPCV to battle_test.py

### Phase 4: quant-backtest-framework (Advanced)
1. Clone/install quant-backtest-framework
2. Add rigorous walk-forward layer
3. Gate picks with GO/NO-GO criteria

---

## Notes

- **vectorbt** is the highest ROI: 10,000x speedup for parameter exploration = more strategies tested = higher edge discovery probability
- **bayesian-optimization** pairs well: smart parameter search instead of exhaustive grid
- **mlfinlab** / **quantreo** fixes the backtest-to-live gap: proper labeling and cross-validation
- **quant-backtest-framework** adds Monte Carlo simulation: robustness testing beyond single historical run

All integrate with existing data sources (yfinance, your existing MySQL data).