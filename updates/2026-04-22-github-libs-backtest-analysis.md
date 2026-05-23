# GitHub Libraries Integration & Performance Enhancement Analysis

**Date**: 2026-04-22
**Source**: Codebase exploration for findtorontoevents.ca/audit

---

## Libraries Integrated

### Alpha Engine Requirements (`alpha_engine/requirements.txt`)

| Library | Version | Purpose |
|---------|---------|---------|
| vectorbt | >=0.28.0 | High-performance backtesting (OSS) |
| bayesian-optimization | >=1.2.0 | Parameter optimization |
| yfinance | >=0.2.30 | Market data |
| lightgbm | >=4.0.0 | ML boosting |
| xgboost | >=2.0.0 | ML boosting |
| shap | >=0.42.0 | SHAP explainability |
| scikit-learn | >=1.3.0 | ML |
| hurst | >=0.0.5 | Hurst exponent |

---

## GitHub Actions Failures (Recent)

### 4 Failing Tests (CI Run 24788523202)

1. **test_sanity_gate_off_allows_extreme_risk_reward** - Expects extreme R:R when gate=OFF
2. **test_sanity_gate_on_skips_prediction_market** - Expects PM picks allowed when gate=ON  
3. **test_pre_score_active_candidate_keeps_valid_zero_score_pick_alive** - Zero score blocked
4. **test_smart_gate_uses_concentration_adjusted_score_floor** - Smart gate failing

All failures relate to `passes_active_gate` in `audit_trail/quality_gates.py`.

### Root Cause

Environment variable `AUDIT_PICK_SANITY_GATE` handling may not be applying correctly to the test monkeypatch.

---

## Backtesting Capabilities

### Already Implemented

1. **vectorbt_explorer.py** - Parameter sweeps with vectorbt OSS:
   - `ma_crossover_entries_exits()` - MA crossover signals
   - `explore_ma_crossover()` - Full grid search
   - Uses `Portfolio.from_signals` (non-PRO alternative)

2. **walk_forward_backtester.py** - Walk-forward validation:
   - `backtest_single_strategy()` - Single strategy across symbols
   - `generate_backtest_report()` - Full report generation
   - Fetches from Binance with failover

3. **hyrotrader_enhanced_scoring.py** - Short-term entry backtesting

---

## Enhancement Opportunities

### 1. Fix QA Test Failures
- The tests are checking proper gate behavior but failing
- Fix env var handling in tests or quality_gates.py logic

### 2. Expand VectorBT Usage (Already Integrated)
- The vectorbt library is already installed
- Could add more strategy explorers beyond MA crossover
- Current: `explore_ma_crossover()` only

### 3. Bayesian Optimization (Already Integrated)
- bayesian-optimization is in requirements
- Could integrate with vectorbt for automated parameter tuning

---

## Recommendations

1. **Fix failing tests first** - Core quality gates are critical for pick filtering
2. **Leverage existing vectorbt** - More strategy explorers could be added
3. **The system already has solid backtesting** - Just needs the tests fixed

---

## Files to Review

- `audit_trail/quality_gates.py` - Quality gate logic (line 1560+: AUDIT_PICK_SANITY_GATE)
- `tests/test_audit_pick_sanity_gate.py` - Failing tests
- `tests/test_quality_gates.py` - Additional failing test
- `tests/test_dashboard_generator.py` - Failing test
- `alpha_engine/vectorbt_explorer.py` - Backtesting explorer
- `alpha_engine/walk_forward_backtester.py` - Walk-forward backtester