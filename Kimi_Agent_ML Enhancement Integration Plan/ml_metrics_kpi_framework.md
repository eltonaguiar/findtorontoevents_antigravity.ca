# ML Enhancement Integration Plan - Metrics & KPI Framework
## Crypto Prediction System - Comprehensive Monitoring Specification

---

## 1. EXECUTIVE SUMMARY: CURRENT KPI EVALUATION

### 1.1 Assessment of Existing KPIs

| KPI | Status | Assessment | Recommendation |
|-----|--------|------------|----------------|
| Dead features <=10/39 | ⚠️ Partial | Good baseline but needs % threshold | Add percentage metric |
| Constant features <=20% | ✅ Good | Clear, measurable threshold | Keep as-is |
| Entry quality (adverse entry bps) | ⚠️ Vague | "Reduced vs baseline" not quantified | Define specific bps targets |
| Stop quality (SL-hit rate) | ⚠️ Partial | "Lower without expectancy drop" vague | Define max SL-hit % and min expectancy |
| Regime robustness | ⚠️ Subjective | "No single regime dominates" needs quantification | Define concentration threshold |
| Live safety (max intraday DD) | ⚠️ Partial | "No increase" needs baseline definition | Define max acceptable DD |

### 1.2 Critical Gaps Identified

| Category | Missing Elements |
|----------|------------------|
| **Feature Health** | No feature drift metrics, no correlation monitoring |
| **Model Performance** | No precision/recall, no calibration metrics, no AUC |
| **Trading Performance** | No win rate targets, no profit factor, no R-multiple |
| **Risk Metrics** | No VaR, no tail risk, no correlation breakdown |
| **Operational** | No latency SLAs, no coverage tracking, no availability |
| **SL Calibrator** | No coverage % target, no calibration quality metric |

---

## 2. COMPREHENSIVE METRIC FRAMEWORK

### 2.1 FEATURE HEALTH METRICS

#### 2.1.1 Dead Features Detection

**Metric: DEAD_FEATURE_COUNT**
- **Definition**: Number of features with zero variance or <0.1% unique values in rolling window
- **Formula**: `COUNT(features WHERE std_dev(feature) < ε OR unique_ratio < 0.001)`
- **Data Source**: `ml_features_at_entry` table, 7-day rolling window
- **Calculation Frequency**: Daily (batch)
- **Thresholds**:
  - 🟢 Healthy: <= 5 features (12.8%)
  - 🟡 Warning: 6-10 features (15.4-25.6%)
  - 🔴 Critical: > 10 features (>25.6%)
- **Alert Rule**: Trigger if count increases by 3+ from previous day

**Metric: DEAD_FEATURE_PERCENTAGE**
- **Definition**: Percentage of total features that are dead
- **Formula**: `(DEAD_FEATURE_COUNT / TOTAL_FEATURES) × 100`
- **Total Features**: 39 (as per contract)
- **Thresholds**:
  - 🟢 Healthy: <= 12%
  - 🟡 Warning: 12-25%
  - 🔴 Critical: > 25%

#### 2.1.2 Constant Features Detection

**Metric: CONSTANT_FEATURE_COUNT**
- **Definition**: Features with identical values across all samples in window
- **Formula**: `COUNT(features WHERE max(feature) = min(feature))`
- **Data Source**: `ml_features_at_entry`, 24-hour window
- **Calculation Frequency**: Hourly
- **Thresholds**:
  - 🟢 Healthy: 0 features
  - 🟡 Warning: 1-3 features
  - 🔴 Critical: > 3 features

**Metric: CONSTANT_FEATURE_PERCENTAGE**
- **Formula**: `(CONSTANT_FEATURE_COUNT / TOTAL_FEATURES) × 100`
- **Thresholds**:
  - 🟢 Healthy: 0%
  - 🟡 Warning: 1-10%
  - 🔴 Critical: > 10% (stricter than current 20%)

#### 2.1.3 Feature Drift Metrics

**Metric: FEATURE_DRIFT_PSI (Population Stability Index)**
- **Definition**: Measures distribution shift between reference and current data
- **Formula**: `PSI = Σ((Actual% - Expected%) × ln(Actual% / Expected%))`
- **Binning**: 10 equal-frequency bins per feature
- **Data Source**: Reference = training data, Current = last 7 days
- **Calculation Frequency**: Daily
- **Thresholds**:
  - 🟢 Stable: PSI < 0.1
  - 🟡 Moderate drift: 0.1 <= PSI < 0.25
  - 🔴 Significant drift: PSI >= 0.25

**Metric: FEATURE_DRIFT_KS (Kolmogorov-Smirnov)**
- **Definition**: Maximum difference between reference and current CDFs
- **Formula**: `KS = max|CDF_reference(x) - CDF_current(x)|`
- **Calculation Frequency**: Daily
- **Thresholds**:
  - 🟢 Stable: KS < 0.05
  - 🟡 Moderate: 0.05 <= KS < 0.1
  - 🔴 Significant: KS >= 0.1

**Metric: MEAN_SHIFT_ZSCORE**
- **Definition**: Z-score of feature mean shift
- **Formula**: `(mean_current - mean_reference) / (std_reference / sqrt(n_current))`
- **Thresholds**:
  - 🟢 Stable: |z| < 2
  - 🟡 Moderate: 2 <= |z| < 3
  - 🔴 Significant: |z| >= 3

#### 2.1.4 Feature Correlation Monitoring

**Metric: MAX_FEATURE_CORRELATION**
- **Definition**: Maximum absolute correlation between any two features
- **Formula**: `max(|corr(f_i, f_j)|) for all i ≠ j`
- **Data Source**: `ml_features_at_entry`, 7-day window
- **Calculation Frequency**: Daily
- **Thresholds**:
  - 🟢 Healthy: < 0.8
  - 🟡 Warning: 0.8-0.9
  - 🔴 Critical: > 0.9 (multicollinearity risk)

**Metric: FEATURE_CORRELATION_MATRIX_CHANGE**
- **Definition**: Frobenius norm of correlation matrix change
- **Formula**: `||Corr_current - Corr_reference||_F`
- **Thresholds**:
  - 🟢 Stable: < 2.0
  - 🟡 Moderate: 2.0-4.0
  - 🔴 Significant: > 4.0

#### 2.1.5 Coverage Metrics

**Metric: FEATURE_COVERAGE_PERCENT**
- **Definition**: Percentage of entries with complete feature data
- **Formula**: `(entries_with_all_features / total_entries) × 100`
- **Data Source**: `ml_features_at_entry`
- **Calculation Frequency**: Real-time (per entry) + hourly aggregate
- **Thresholds**:
  - 🟢 Healthy: >= 99%
  - 🟡 Warning: 95-99%
  - 🔴 Critical: < 95%

**Metric: FEATURE_NULL_RATE**
- **Definition**: Percentage of null values per feature
- **Formula**: `(null_count / total_rows) × 100` per feature
- **Thresholds (per feature)**:
  - 🟢 Healthy: < 1%
  - 🟡 Warning: 1-5%
  - 🔴 Critical: > 5%

---

### 2.2 MODEL PERFORMANCE METRICS

#### 2.2.1 Prediction Accuracy Metrics

**Metric: PRECISION_AT_K**
- **Definition**: Precision at top K predictions by confidence
- **Formula**: `TP_topK / (TP_topK + FP_topK)`
- **K Values**: 10%, 20%, 50% of predictions
- **Calculation Frequency**: Per trade outcome + daily aggregate
- **Thresholds (for K=20%)**:
  - 🟢 Good: >= 0.55
  - 🟡 Acceptable: 0.50-0.55
  - 🔴 Poor: < 0.50

**Metric: RECALL_AT_K**
- **Definition**: Recall at top K predictions
- **Formula**: `TP_topK / Total_Positive`
- **Calculation Frequency**: Daily
- **Thresholds**:
  - 🟢 Good: >= 0.60
  - 🟡 Acceptable: 0.50-0.60
  - 🔴 Poor: < 0.50

**Metric: AUC_ROC**
- **Definition**: Area under ROC curve
- **Formula**: Standard AUC calculation
- **Calculation Frequency**: Daily (on last 500 trades)
- **Thresholds**:
  - 🟢 Good: >= 0.58
  - 🟡 Acceptable: 0.53-0.58
  - 🔴 Poor: < 0.53

**Metric: LOG_LOSS**
- **Definition**: Cross-entropy loss
- **Formula**: `-Σ(y_true × log(y_pred) + (1-y_true) × log(1-y_pred)) / n`
- **Calculation Frequency**: Per prediction + hourly aggregate
- **Thresholds**:
  - 🟢 Good: < 0.65
  - 🟡 Acceptable: 0.65-0.69
  - 🔴 Poor: > 0.69

#### 2.2.2 Calibration Metrics

**Metric: EXPECTED_CALIBRATION_ERROR (ECE)**
- **Definition**: Average calibration error across bins
- **Formula**: `Σ(bins) (n_bin/n) × |accuracy_bin - confidence_bin|`
- **Bins**: 10 equal-width confidence bins
- **Calculation Frequency**: Daily
- **Thresholds**:
  - 🟢 Well-calibrated: < 0.05
  - 🟡 Moderate: 0.05-0.10
  - 🔴 Poor: > 0.10

**Metric: MAX_CALIBRATION_ERROR (MCE)**
- **Definition**: Maximum calibration error across bins
- **Formula**: `max(|accuracy_bin - confidence_bin|)`
- **Thresholds**:
  - 🟢 Good: < 0.10
  - 🟡 Acceptable: 0.10-0.15
  - 🔴 Poor: > 0.15

**Metric: BRIER_SCORE**
- **Definition**: Mean squared error of probabilistic predictions
- **Formula**: `Σ(y_pred - y_true)² / n`
- **Thresholds**:
  - 🟢 Good: < 0.20
  - 🟡 Acceptable: 0.20-0.25
  - 🔴 Poor: > 0.25

#### 2.2.3 Regime-Specific Performance

**Metric: REGIME_PRECISION**
- **Definition**: Precision per market regime
- **Formula**: `TP_regime / (TP_regime + FP_regime)` per regime
- **Regimes**: Trending Up, Trending Down, Ranging, High Vol, Low Vol
- **Calculation Frequency**: Daily
- **Thresholds**:
  - 🟢 Good: >= 0.52 in all regimes
  - 🟡 Acceptable: >= 0.50 in all regimes, one regime >= 0.52
  - 🔴 Poor: Any regime < 0.50

**Metric: REGIME_ROBUSTNESS_SCORE**
- **Definition**: Coefficient of variation of regime returns
- **Formula**: `std(returns_by_regime) / mean(returns_by_regime)`
- **Calculation Frequency**: Weekly (need 50+ trades per regime)
- **Thresholds**:
  - 🟢 Robust: CV < 0.5
  - 🟡 Moderate: 0.5-1.0
  - 🔴 Concentrated: > 1.0

**Metric: REGIME_CONCENTRATION_INDEX**
- **Definition**: Herfindahl index of PnL by regime
- **Formula**: `Σ(regime_pnl_share)²`
- **Thresholds**:
  - 🟢 Diversified: < 0.25
  - 🟡 Moderate: 0.25-0.35
  - 🔴 Concentrated: > 0.35 (single regime > 60% of PnL)

---

### 2.3 TRADING PERFORMANCE METRICS

#### 2.3.1 Entry Quality Metrics

**Metric: ADVERSE_ENTRY_BPS**
- **Definition**: Average adverse price movement after entry (in basis points)
- **Formula**: `mean(entry_price - worst_price_in_next_N_seconds) / entry_price × 10,000`
- **N**: 30 seconds (configurable)
- **Calculation Frequency**: Per entry + hourly aggregate
- **Baseline**: Current production average (measure before deployment)
- **Thresholds**:
  - 🟢 Improved: < baseline - 2 bps
  - 🟡 Neutral: baseline ± 2 bps
  - 🔴 Degraded: > baseline + 2 bps

**Metric: ENTRY_SLIPPAGE_BPS**
- **Definition**: Difference between expected and actual entry price
- **Formula**: `mean(actual_entry - expected_entry) / expected_entry × 10,000`
- **Calculation Frequency**: Per entry + hourly aggregate
- **Thresholds**:
  - 🟢 Good: < 5 bps
  - 🟡 Acceptable: 5-10 bps
  - 🔴 Poor: > 10 bps

**Metric: ENTRY_TIMING_SCORE**
- **Definition**: Correlation between entry timing and subsequent move
- **Formula**: `correlation(entry_signal, price_move_next_5min)`
- **Calculation Frequency**: Daily (on 100+ entries)
- **Thresholds**:
  - 🟢 Good: > 0.15
  - 🟡 Acceptable: 0.05-0.15
  - 🔴 Poor: < 0.05

#### 2.3.2 Stop Loss Metrics

**Metric: SL_HIT_RATE**
- **Definition**: Percentage of trades hitting stop loss
- **Formula**: `(trades_hit_sl / total_trades) × 100`
- **Calculation Frequency**: Daily
- **Thresholds**:
  - 🟢 Good: < 35%
  - 🟡 Acceptable: 35-45%
  - 🔴 Poor: > 45%

**Metric: SL_HIT_RATE_CHANGE**
- **Definition**: Change in SL hit rate vs baseline
- **Formula**: `SL_HIT_RATE_current - SL_HIT_RATE_baseline`
- **Thresholds**:
  - 🟢 Improved: < -2%
  - 🟡 Neutral: -2% to +2%
  - 🔴 Degraded: > +2%

**Metric: SL_EFFICIENCY**
- **Definition**: Ratio of SL distance to actual adverse move
- **Formula**: `mean(sl_distance / max_adverse_excursion)`
- **Calculation Frequency**: Daily (on SL-hit trades only)
- **Thresholds**:
  - 🟢 Efficient: 0.8-1.2
  - 🟡 Loose: > 1.2 (SL too far)
  - 🔴 Tight: < 0.8 (SL too tight)

#### 2.3.3 Expectancy Metrics

**Metric: EXPECTANCY_PER_TRADE**
- **Definition**: Average PnL per trade
- **Formula**: `(win_rate × avg_win) - (loss_rate × avg_loss)`
- **Calculation Frequency**: Daily (rolling 100 trades)
- **Thresholds**:
  - 🟢 Good: > 0.3% per trade
  - 🟡 Acceptable: 0.1-0.3%
  - 🔴 Poor: < 0.1%

**Metric: EXPECTANCY_DROP**
- **Definition**: Maximum drawdown in rolling expectancy
- **Formula**: `max(EXPECTANCY_peak - EXPECTANCY_current)` over rolling window
- **Window**: 50 trades
- **Thresholds**:
  - 🟢 Stable: < 0.15%
  - 🟡 Moderate: 0.15-0.30%
  - 🔴 Severe: > 0.30%

**Metric: EXPECTANCY_BY_REGIME**
- **Definition**: Expectancy per market regime
- **Formula**: Same as EXPECTANCY_PER_TRADE, filtered by regime
- **Thresholds**:
  - 🟢 All positive: > 0 in all regimes
  - 🟡 Mostly positive: > 0 in 80%+ of regimes
  - 🔴 Poor: < 0 in > 20% of regimes

#### 2.3.4 Win Rate Metrics

**Metric: OVERALL_WIN_RATE**
- **Definition**: Percentage of winning trades
- **Formula**: `(winning_trades / total_trades) × 100`
- **Calculation Frequency**: Daily (rolling 100 trades)
- **Thresholds**:
  - 🟢 Good: >= 52%
  - 🟡 Acceptable: 48-52%
  - 🔴 Poor: < 48%

**Metric: WIN_RATE_BY_REGIME**
- **Definition**: Win rate per market regime
- **Formula**: Same as OVERALL_WIN_RATE, filtered by regime
- **Thresholds**:
  - 🟢 Good: >= 50% in all regimes
  - 🟡 Acceptable: >= 45% in all regimes
  - 🔴 Poor: < 45% in any regime

**Metric: PROFIT_FACTOR**
- **Definition**: Gross profit / Gross loss
- **Formula**: `sum(winning_trades_pnl) / abs(sum(losing_trades_pnl))`
- **Calculation Frequency**: Daily (rolling 100 trades)
- **Thresholds**:
  - 🟢 Good: >= 1.3
  - 🟡 Acceptable: 1.1-1.3
  - 🔴 Poor: < 1.1

#### 2.3.5 R-Multiple Metrics

**Metric: AVG_R_MULTIPLE**
- **Definition**: Average R-multiple (return per unit risk)
- **Formula**: `mean(trade_pnl / trade_risk)`
- **Calculation Frequency**: Daily
- **Thresholds**:
  - 🟢 Good: >= 1.5R
  - 🟡 Acceptable: 1.0-1.5R
  - 🔴 Poor: < 1.0R

**Metric: R_DISTRIBUTION_SKEW**
- **Definition**: Skewness of R-multiple distribution
- **Formula**: Standard skewness calculation
- **Thresholds**:
  - 🟢 Favorable: > 0 (positive skew)
  - 🟡 Neutral: -0.5 to 0
  - 🔴 Unfavorable: < -0.5

---

### 2.4 RISK METRICS

#### 2.4.1 Drawdown Metrics

**Metric: MAX_INTRADAY_DRAWDOWN**
- **Definition**: Maximum peak-to-trough decline within a trading day
- **Formula**: `max(daily_peak - daily_trough) / daily_peak × 100`
- **Calculation Frequency**: Real-time + EOD
- **Baseline**: Current production max DD
- **Thresholds**:
  - 🟢 Safe: < baseline
  - 🟡 Elevated: baseline to baseline + 1%
  - 🔴 Breach: > baseline + 1%
- **Hard Limit**: 5% intraday (circuit breaker)

**Metric: MAX_DRAWDOWN_7D**
- **Definition**: Maximum drawdown over 7-day window
- **Formula**: `max(peak_7d - trough_7d) / peak_7d × 100`
- **Calculation Frequency**: Daily
- **Thresholds**:
  - 🟢 Safe: < 3%
  - 🟡 Elevated: 3-5%
  - 🔴 Breach: > 5%

**Metric: DRAWDOWN_DURATION**
- **Definition**: Time to recover from max drawdown
- **Formula**: `days_from_trough_to_new_peak`
- **Thresholds**:
  - 🟢 Quick: < 5 days
  - 🟡 Moderate: 5-10 days
  - 🔴 Extended: > 10 days

#### 2.4.2 Value at Risk (VaR) Metrics

**Metric: DAILY_VAR_95**
- **Definition**: 95th percentile daily loss
- **Formula**: `percentile(daily_pnl, 5)`
- **Calculation Frequency**: Daily (rolling 60 days)
- **Thresholds**:
  - 🟢 Safe: > -2% of capital
  - 🟡 Elevated: -2% to -3%
  - 🔴 Breach: < -3%

**Metric: DAILY_VAR_99**
- **Definition**: 99th percentile daily loss
- **Formula**: `percentile(daily_pnl, 1)`
- **Thresholds**:
  - 🟢 Safe: > -3% of capital
  - 🟡 Elevated: -3% to -5%
  - 🔴 Breach: < -5%

**Metric: VAR_BREACH_RATE**
- **Definition**: Frequency of VaR breaches
- **Formula**: `(actual_losses_exceeding_var / total_days) × 100`
- **Expected**: ~5% for 95% VaR
- **Thresholds**:
  - 🟢 Normal: 3-7%
  - 🟡 Elevated: 7-10%
  - 🔴 Model issue: > 10%

#### 2.4.3 Tail Risk Metrics

**Metric: CONDITIONAL_VAR_95 (CVaR)**
- **Definition**: Average loss when VaR is exceeded
- **Formula**: `mean(losses | loss > VaR_95)`
- **Calculation Frequency**: Weekly
- **Thresholds**:
  - 🟢 Safe: > -4%
  - 🟡 Elevated: -4% to -6%
  - 🔴 High: < -6%

**Metric: MAX_CONSECUTIVE_LOSSES**
- **Definition**: Maximum consecutive losing trades
- **Formula**: `max_streak(negative_trades)`
- **Thresholds**:
  - 🟢 Normal: < 8
  - 🟡 Elevated: 8-12
  - 🔴 Concerning: > 12

**Metric: LOSS_TAIL_RATIO**
- **Definition**: Ratio of 95th to 50th percentile loss
- **Formula**: `|percentile(losses, 5)| / |percentile(losses, 50)|`
- **Thresholds**:
  - 🟢 Normal: 2-4
  - 🟡 Elevated: 4-6
  - 🔴 Fat tails: > 6

#### 2.4.4 Correlation Risk Metrics

**Metric: PORTFOLIO_CORRELATION**
- **Definition**: Average correlation between active positions
- **Formula**: `mean(corr(position_i, position_j))` for all pairs
- **Calculation Frequency**: Real-time
- **Thresholds**:
  - 🟢 Diversified: < 0.3
  - 🟡 Moderate: 0.3-0.5
  - 🔴 Concentrated: > 0.5

---

### 2.5 OPERATIONAL METRICS

#### 2.5.1 Latency Metrics

**Metric: FEATURE_CALCULATION_LATENCY_MS**
- **Definition**: Time from signal to feature availability
- **Formula**: `timestamp_features_ready - timestamp_signal`
- **Calculation Frequency**: Per entry
- **Thresholds**:
  - 🟢 Fast: < 50ms
  - 🟡 Acceptable: 50-100ms
  - 🔴 Slow: > 100ms

**Metric: PREDICTION_LATENCY_MS**
- **Definition**: Time from features to prediction
- **Formula**: `timestamp_prediction - timestamp_features_ready`
- **Thresholds**:
  - 🟢 Fast: < 20ms
  - 🟡 Acceptable: 20-50ms
  - 🔴 Slow: > 50ms

**Metric: END_TO_END_LATENCY_MS**
- **Definition**: Total time from signal to trade decision
- **Formula**: `timestamp_decision - timestamp_signal`
- **Thresholds**:
  - 🟢 Fast: < 100ms
  - 🟡 Acceptable: 100-200ms
  - 🔴 Slow: > 200ms

**Metric: LATENCY_P99**
- **Definition**: 99th percentile latency
- **Formula**: `percentile(latency_samples, 99)`
- **Calculation Frequency**: Hourly
- **Thresholds**:
  - 🟢 Good: < 150ms
  - 🟡 Acceptable: 150-300ms
  - 🔴 Poor: > 300ms

#### 2.5.2 Coverage Metrics

**Metric: SL_CALIBRATOR_COVERAGE**
- **Definition**: Percentage of trades using calibrated SL
- **Formula**: `(trades_with_calibrated_sl / total_trades) × 100`
- **Current**: 2/N groups calibrated
- **Target**: >= 80% coverage
- **Thresholds**:
  - 🟢 Good: >= 80%
  - 🟡 Building: 50-80%
  - 🔴 Low: < 50%

**Metric: CALIBRATED_GROUPS_COUNT**
- **Definition**: Number of groups with 10+ winners (calibration threshold)
- **Formula**: `COUNT(groups WHERE winner_count >= 10)`
- **Target**: All major groups (>= 10 groups)
- **Thresholds**:
  - 🟢 Good: >= 10 groups
  - 🟡 Building: 5-9 groups
  - 🔴 Low: < 5 groups

**Metric: HIERARCHICAL_FALLBACK_RATE**
- **Definition**: Rate of fallback to parent/global defaults
- **Formula**: `(fallback_trades / total_trades) × 100`
- **Thresholds**:
  - 🟢 Low: < 10%
  - 🟡 Moderate: 10-20%
  - 🔴 High: > 20%

**Metric: FEATURE_CONTRACT_COVERAGE**
- **Definition**: Percentage of expected features present
- **Formula**: `(features_present / 39) × 100`
- **Thresholds**:
  - 🟢 Complete: 100%
  - 🟡 Partial: 95-99%
  - 🔴 Incomplete: < 95%

#### 2.5.3 Availability Metrics

**Metric: SYSTEM_UPTIME_PERCENT**
- **Definition**: Percentage of time system is operational
- **Formula**: `(uptime_minutes / total_minutes) × 100`
- **Calculation Frequency**: Real-time
- **SLA Target**: 99.9%
- **Thresholds**:
  - 🟢 Excellent: >= 99.9%
  - 🟡 Degraded: 99-99.9%
  - 🔴 Outage: < 99%

**Metric: FEATURE_PIPELINE_ERROR_RATE**
- **Definition**: Rate of feature calculation failures
- **Formula**: `(failed_calculations / total_calculations) × 100`
- **Thresholds**:
  - 🟢 Healthy: < 0.1%
  - 🟡 Elevated: 0.1-1%
  - 🔴 Critical: > 1%

**Metric: PREDICTION_SERVICE_ERROR_RATE**
- **Definition**: Rate of prediction failures
- **Formula**: `(failed_predictions / total_requests) × 100`
- **Thresholds**:
  - 🟢 Healthy: < 0.1%
  - 🟡 Elevated: 0.1-1%
  - 🔴 Critical: > 1%

---

## 3. MEASUREMENT SPECIFICATIONS

### 3.1 Data Sources

| Metric Category | Primary Source | Secondary Source | Retention |
|-----------------|----------------|------------------|-----------|
| Feature Health | `ml_features_at_entry` | Feature store snapshots | 90 days |
| Model Performance | Prediction logs | Model artifact metadata | 180 days |
| Trading Performance | Trade execution DB | Exchange fill data | 2 years |
| Risk Metrics | Portfolio state DB | Market data | 2 years |
| Operational | Application logs | Infrastructure metrics | 30 days |

### 3.2 Calculation Frequencies

| Metric Type | Real-Time | Batch (Hourly) | Batch (Daily) | Batch (Weekly) |
|-------------|-----------|----------------|---------------|----------------|
| Feature Health | Coverage % | Null rates | Drift, Dead features | Correlation |
| Model Performance | Log loss | Precision | AUC, Calibration | Regime perf |
| Trading Performance | Entry slippage | Win rate | Expectancy, PF | R-multiple |
| Risk Metrics | Intraday DD | VaR | Max DD | Tail risk |
| Operational | Latency, Errors | Uptime | Coverage | - |

### 3.3 Alert Threshold Summary

| Metric | P1 (Critical) | P2 (Warning) | P3 (Info) |
|--------|---------------|--------------|-----------|
| Dead Features | > 10 (25%) | 6-10 (15-25%) | 3-5 (8-12%) |
| Feature Drift PSI | > 0.25 | 0.1-0.25 | < 0.1 |
| SL Hit Rate | > 45% | 35-45% | < 35% |
| Expectancy Drop | > 0.30% | 0.15-0.30% | < 0.15% |
| Max Intraday DD | > baseline + 1% | baseline to +1% | < baseline |
| Latency P99 | > 300ms | 150-300ms | < 150ms |
| System Uptime | < 99% | 99-99.9% | >= 99.9% |

---

## 4. MONITORING DASHBOARD SPECIFICATION

### 4.1 Dashboard Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  EXECUTIVE SUMMARY                    [Last Updated: HH:MM:SS]  │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────┐ │
│  │ System      │ │ Feature     │ │ Trading     │ │ Risk      │ │
│  │ Health      │ │ Health      │ │ Performance │ │ Status    │ │
│  │ [Overall]   │ │ [Score]     │ │ [Score]     │ │ [Score]   │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └───────────┘ │
├─────────────────────────────────────────────────────────────────┤
│  FEATURE HEALTH METRICS                                         │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐   │
│  │ Dead Features   │ │ Drift PSI Trend │ │ Coverage %      │   │
│  │ [Gauge Chart]   │ │ [Line Chart]    │ │ [Progress Bar]  │   │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│  MODEL PERFORMANCE                                              │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐   │
│  │ Precision@K     │ │ Calibration     │ │ Regime Perf     │   │
│  │ [Bar Chart]     │ │ [Reliability    │ │ [Heatmap]       │   │
│  │                 │ │  Diagram]       │ │                 │   │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│  TRADING PERFORMANCE                                            │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐   │
│  │ Expectancy      │ │ Win Rate Trend  │ │ SL Hit Rate     │   │
│  │ [Line Chart]    │ │ [Line Chart]    │ │ [Gauge Chart]   │   │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│  RISK METRICS                                                   │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐   │
│  │ Drawdown Curve  │ │ VaR Breaches    │ │ Regime Conc.    │   │
│  │ [Area Chart]    │ │ [Count Chart]   │ │ [Pie Chart]     │   │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│  OPERATIONAL METRICS                                            │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐   │
│  │ Latency P99     │ │ SL Calibrator   │ │ Error Rate      │   │
│  │ [Line Chart]    │ │ [Coverage Bar]  │ │ [Sparkline]     │   │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│  ACTIVE ALERTS                                                  │
│  [Alert Table with Severity, Metric, Value, Time, Action]       │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Chart Specifications

| Chart | Type | Data Source | Refresh Rate |
|-------|------|-------------|--------------|
| System Health Score | Gauge | Aggregated metrics | 5 min |
| Dead Features Count | Gauge + Trend | Feature health DB | 1 hour |
| Feature Drift PSI | Line (7-day) | Drift calculations | Daily |
| Precision@K | Bar (K=10,20,50) | Model predictions | Daily |
| Calibration Diagram | Reliability plot | Prediction outcomes | Daily |
| Regime Performance | Heatmap | Trade outcomes | Weekly |
| Expectancy Trend | Line (rolling 100) | Trade PnL | Daily |
| Drawdown Curve | Area chart | Portfolio value | Real-time |
| SL Calibrator Coverage | Progress bar | Calibration state | Daily |
| Latency Distribution | Histogram | Application logs | 5 min |

### 4.3 Alert Rules

```yaml
alerts:
  - name: "Critical Dead Features"
    condition: "DEAD_FEATURE_COUNT > 10"
    severity: P1
    channels: [pagerduty, slack-critical, email]
    auto_action: "halt_new_entries"
    
  - name: "Feature Drift Alert"
    condition: "FEATURE_DRIFT_PSI > 0.25 FOR 2d"
    severity: P1
    channels: [pagerduty, slack-critical]
    auto_action: "trigger_model_retrain_review"
    
  - name: "SL Hit Rate Degradation"
    condition: "SL_HIT_RATE > 45% AND EXPECTANCY < 0.1%"
    severity: P1
    channels: [pagerduty, slack-trading]
    auto_action: "reduce_position_size_50%"
    
  - name: "Max Drawdown Breach"
    condition: "MAX_INTRADAY_DRAWDOWN > baseline + 1%"
    severity: P1
    channels: [pagerduty, slack-critical, sms]
    auto_action: "circuit_breaker_pause"
    
  - name: "Latency Degradation"
    condition: "LATENCY_P99 > 300ms FOR 10m"
    severity: P2
    channels: [slack-ops, email]
    auto_action: "page_oncall_engineer"
    
  - name: "Expectancy Drop Warning"
    condition: "EXPECTANCY_DROP > 0.15%"
    severity: P2
    channels: [slack-trading]
    auto_action: "notify_quant_team"
    
  - name: "Low SL Calibrator Coverage"
    condition: "SL_CALIBRATOR_COVERAGE < 50%"
    severity: P2
    channels: [slack-ml]
    auto_action: "schedule_backfill"
    
  - name: "Regime Concentration"
    condition: "REGIME_CONCENTRATION_INDEX > 0.35"
    severity: P2
    channels: [slack-trading]
    auto_action: "review_regime_weights"
```

### 4.4 Escalation Procedures

| Severity | Response Time | Escalation Path |
|----------|---------------|-----------------|
| P1 (Critical) | 5 minutes | On-call ML → Trading Lead → CTO |
| P2 (Warning) | 30 minutes | ML Team → Trading Team |
| P3 (Info) | 4 hours | Daily digest email |

---

## 5. HEALTH GATE IMPLEMENTATION

### 5.1 Gate Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    HEALTH GATE SYSTEM                           │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │  GATE 1     │───→│  GATE 2     │───→│  GATE 3     │         │
│  │  Feature    │    │  Model      │    │  Trading    │         │
│  │  Health     │    │  Quality    │    │  Live       │         │
│  └─────────────┘    └─────────────┘    └─────────────┘         │
│         │                  │                  │                 │
│         ▼                  ▼                  ▼                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │  Pre-merge  │    │  Shadow     │    │  Full       │         │
│  │  Check      │    │  Mode       │    │  Deployment │         │
│  └─────────────┘    └─────────────┘    └─────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 Gate 1: Feature Health Gate (Pre-Merge)

**Purpose**: Validate feature contract before any model changes

**Pass Criteria**:
```python
def gate_1_pass():
    return (
        DEAD_FEATURE_COUNT <= 5 AND                    # <= 12.8%
        CONSTANT_FEATURE_COUNT == 0 AND                # 0%
        FEATURE_COVERAGE_PERCENT >= 99% AND
        FEATURE_DRIFT_PSI < 0.1 AND                    # Stable
        MAX_FEATURE_CORRELATION < 0.9 AND              # No multicollinearity
        FEATURE_NULL_RATE < 1%                         # Per feature
    )
```

**Automatic Actions**:
- ✅ PASS: Allow merge to staging
- ❌ FAIL: Block merge, notify agent owner with specific failures

**Progressive Tightening**:
| Phase | Dead Feature Threshold | Trigger |
|-------|----------------------|---------|
| Initial | <= 20 (51%) | Start of integration |
| After 3 stable retrains | <= 14 (36%) | 3 consecutive weeks stable |
| After backfill + coverage | <= 8 (20%) | Coverage >= 95% for 2 weeks |
| Final | <= 5 (13%) | Pre-production |

### 5.3 Gate 2: Model Quality Gate (Shadow Mode)

**Purpose**: Validate model predictions before live trading

**Pass Criteria**:
```python
def gate_2_pass():
    return (
        PRECISION_AT_20 >= 0.52 AND                    # Better than random
        AUC_ROC >= 0.55 AND                            # Discriminative power
        ECE < 0.10 AND                                 # Well-calibrated
        LOG_LOSS < 0.68 AND                            # Prediction quality
        REGIME_PRECISION >= 0.50 IN ALL_REGIMES AND    # Robust across regimes
        REGIME_CONCENTRATION_INDEX < 0.35              # Not regime-dependent
    )
```

**Shadow Mode Requirements** (2-week minimum):
- Generate predictions in parallel with production
- Compare prediction distributions
- Validate latency requirements
- Monitor for errors/exceptions

**Automatic Actions**:
- ✅ PASS: Enable feature flag for 10% traffic
- ❌ FAIL: Extend shadow mode, investigate issues

### 5.4 Gate 3: Trading Live Gate (Gradual Rollout)

**Purpose**: Validate actual trading performance

**Pass Criteria**:
```python
def gate_3_pass():
    return (
        # Entry Quality
        ADVERSE_ENTRY_BPS <= baseline - 1 AND          # Improved entry
        ENTRY_SLIPPAGE_BPS < 8 AND                     # Acceptable slippage
        
        # Stop Quality
        SL_HIT_RATE <= 40% AND                         # Not excessive
        SL_HIT_RATE_CHANGE <= 2% AND                   # Not worse
        SL_EFFICIENCY BETWEEN 0.8 AND 1.2 AND          # Well-calibrated
        
        # Expectancy
        EXPECTANCY_PER_TRADE >= 0.15% AND              # Positive expectancy
        EXPECTANCY_DROP < 0.20% AND                    # Stable
        
        # Win Rate
        OVERALL_WIN_RATE >= 50% AND                    # Better than random
        WIN_RATE_BY_REGIME >= 45% IN ALL_REGIMES AND   # Robust
        
        # Risk
        MAX_INTRADAY_DRAWDOWN <= baseline AND          # No increase
        DAILY_VAR_95 > -2.5% AND                       # Controlled risk
        
        # Operational
        END_TO_END_LATENCY_MS < 150 AND                # Fast enough
        SYSTEM_UPTIME_PERCENT >= 99.9%                 # Reliable
    )
```

**Rollout Stages**:
| Stage | Traffic % | Duration | Gate Check |
|-------|-----------|----------|------------|
| 1 | 10% | 3 days | Basic metrics stable |
| 2 | 25% | 5 days | Expectancy positive |
| 3 | 50% | 7 days | Risk metrics green |
| 4 | 100% | Ongoing | All KPIs maintained |

**Automatic Actions**:
- ✅ PASS: Proceed to next stage
- ⚠️ WARNING: Hold current stage, investigate
- ❌ FAIL: Rollback to previous stage

### 5.5 Gate Failure Response Matrix

| Gate | Failure Scenario | Immediate Action | Investigation |
|------|-----------------|------------------|---------------|
| Gate 1 | Dead features spike | Block merge | Feature pipeline review |
| Gate 1 | Drift detected | Block merge | Data source check |
| Gate 2 | Low precision | Extend shadow | Model architecture review |
| Gate 2 | Poor calibration | Extend shadow | Calibration layer tuning |
| Gate 3 | Entry quality down | Rollback 50% | Entry timing analysis |
| Gate 3 | SL hit rate up | Rollback 50% | SL calibrator review |
| Gate 3 | Expectancy drop | Full rollback | Comprehensive review |
| Gate 3 | DD breach | Circuit breaker | Emergency assessment |

---

## 6. SL CALIBRATOR SPECIFIC METRICS

### 6.1 Calibration Quality Metrics

**Metric: CALIBRATION_SAMPLE_SIZE**
- **Definition**: Number of winners per group for calibration
- **Formula**: `COUNT(winner_trades) per group`
- **Minimum for Calibration**: 10 winners
- **Target**: 30+ winners for robust calibration

**Metric: CALIBRATION_CONFIDENCE_INTERVAL**
- **Definition**: 95% CI width for calibrated SL
- **Formula**: `1.96 × std(sl_distances) / sqrt(n)`
- **Thresholds**:
  - 🟢 Precise: CI width < 10% of SL value
  - 🟡 Moderate: 10-20%
  - 🔴 Imprecise: > 20%

**Metric: CALIBRATION_STABILITY**
- **Definition**: Change in calibrated SL between updates
- **Formula**: `|SL_new - SL_old| / SL_old × 100`
- **Thresholds**:
  - 🟢 Stable: < 10% change
  - 🟡 Moderate: 10-25%
  - 🔴 Unstable: > 25%

### 6.2 Coverage Expansion Tracking

| Milestone | Target Date | Coverage Target | Groups Calibrated |
|-----------|-------------|-----------------|-------------------|
| Phase 1 | Week 1-2 | 20% | 4 groups |
| Phase 2 | Week 3-4 | 40% | 8 groups |
| Phase 3 | Week 5-6 | 60% | 12 groups |
| Phase 4 | Week 7-8 | 80% | 16+ groups |

### 6.3 Hierarchical Fallback Effectiveness

**Metric: FALLBACK_LEVEL_DISTRIBUTION**
- **Definition**: Distribution of fallback levels used
- **Formula**: Percentage at each level (group → parent → global)
- **Target**:
  - Group-level: >= 70%
  - Parent-level: 20-25%
  - Global: < 10%

---

## 7. SUMMARY: ENHANCED KPI CHECKLIST

### 7.1 Revised KPIs (Must Be Green Before Full Go-Live)

| # | KPI | Threshold | Measurement |
|---|-----|-----------|-------------|
| 1 | Dead features | <= 5/39 (12.8%) | Daily count |
| 2 | Constant features | 0% | Hourly check |
| 3 | Feature drift PSI | < 0.1 | Daily calculation |
| 4 | Feature coverage | >= 99% | Real-time |
| 5 | Precision@20 | >= 52% | Daily on last 100 trades |
| 6 | Calibration ECE | < 0.05 | Daily |
| 7 | Entry quality (adverse bps) | <= baseline - 1 bps | Per entry |
| 8 | SL hit rate | <= 40% | Daily |
| 9 | Expectancy per trade | >= 0.15% | Rolling 100 trades |
| 10 | Expectancy drop | < 0.20% | Rolling 50 trades |
| 11 | Overall win rate | >= 50% | Rolling 100 trades |
| 12 | Win rate by regime | >= 45% all regimes | Weekly |
| 13 | Regime concentration | < 0.35 | Weekly |
| 14 | Max intraday drawdown | <= baseline | Real-time |
| 15 | Daily VaR 95 | > -2.5% | Daily |
| 16 | Latency P99 | < 150ms | Hourly |
| 17 | SL calibrator coverage | >= 80% | Daily |
| 18 | System uptime | >= 99.9% | Real-time |

### 7.2 Success Criteria Summary

```
┌─────────────────────────────────────────────────────────────────┐
│                    GO-LIVE APPROVAL CHECKLIST                   │
├─────────────────────────────────────────────────────────────────┤
│  FEATURE HEALTH        [ ] All green for 7 consecutive days     │
│  MODEL QUALITY         [ ] Shadow mode passed (2+ weeks)        │
│  TRADING PERFORMANCE   [ ] 10% rollout stable (3+ days)         │
│  RISK METRICS          [ ] No breaches during rollout           │
│  OPERATIONAL           [ ] Latency and uptime targets met       │
│  SL CALIBRATOR         [ ] Coverage >= 80% or approved plan     │
├─────────────────────────────────────────────────────────────────┤
│  APPROVALS:                                                     │
│  [ ] ML Lead          [ ] Trading Lead         [ ] Risk         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 8. APPENDIX: IMPLEMENTATION NOTES

### 8.1 Metric Storage Schema

```sql
-- Feature Health Table
CREATE TABLE feature_health_metrics (
    timestamp TIMESTAMP,
    dead_feature_count INT,
    dead_feature_percent FLOAT,
    constant_feature_count INT,
    feature_drift_psi FLOAT,
    feature_coverage_percent FLOAT,
    max_feature_correlation FLOAT
);

-- Model Performance Table
CREATE TABLE model_performance_metrics (
    timestamp TIMESTAMP,
    precision_at_10 FLOAT,
    precision_at_20 FLOAT,
    precision_at_50 FLOAT,
    auc_roc FLOAT,
    ece FLOAT,
    log_loss FLOAT
);

-- Trading Performance Table
CREATE TABLE trading_performance_metrics (
    timestamp TIMESTAMP,
    expectancy_per_trade FLOAT,
    expectancy_drop FLOAT,
    win_rate_overall FLOAT,
    sl_hit_rate FLOAT,
    profit_factor FLOAT,
    adverse_entry_bps FLOAT
);

-- Risk Metrics Table
CREATE TABLE risk_metrics (
    timestamp TIMESTAMP,
    max_intraday_drawdown FLOAT,
    daily_var_95 FLOAT,
    daily_var_99 FLOAT,
    regime_concentration_index FLOAT
);
```

### 8.2 Alert Configuration Template

```yaml
# alerts.yaml
feature_health:
  dead_features_critical:
    metric: dead_feature_count
    condition: "> 10"
    severity: critical
    channels: [pagerduty, slack]
    
model_performance:
  low_precision:
    metric: precision_at_20
    condition: "< 0.50"
    severity: warning
    channels: [slack]
    
trading_performance:
  expectancy_drop:
    metric: expectancy_drop
    condition: "> 0.20"
    severity: critical
    channels: [pagerduty, slack, email]
```

---

*Document Version: 1.0*
*Last Updated: 2024*
*Framework Status: Ready for Implementation*
