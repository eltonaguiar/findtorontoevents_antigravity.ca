# Statistically Valid Scoring Framework for Prediction System Profitability

## 1. Problem Statement & Design Goals

| Current Issue | Framework Solution |
|---------------|-------------------|
| Score-PnL correlation r = +0.008 | Replace single score with a multi-metric gate system |
| Dashboard survivorship bias | Mandate closed-trade ledger + temporal OOS splits |
| 100+ strategies, no multiplicity correction | Bonferroni for final certification; FDR (BH) for discovery |
| Inflated PF from cherry-picked sub-strategies | Minimum n thresholds + bootstrap confidence intervals |
| Intrabar replay flips 23-24% wins to SL | Conservative slippage model + net-return thresholds |

---

## 2. Minimum Sample Size (n)

A strategy must have sufficient observations to distinguish a true edge from randomness.

### 2.1 Exact Formula (Binomial Power Analysis)
For a strategy with expected win rate `p` vs. baseline `p0 = 0.5` (random coin-flip):

```
n = ceil( (Z_α * sqrt(p0*(1-p0)) + Z_β * sqrt(p*(1-p)))^2 / (p - p0)^2 )
```

Where:
- `Z_α` = 1.96 (two-tailed, α = 0.05)
- `Z_β` = 0.84 (power = 0.80)

**Example:** To detect an edge from 50% → 55% WR:
```
n ≈ 385 trades
```

To detect an edge from 50% → 60% WR:
```
n ≈ 100 trades
```

### 2.2 Profit Factor Specific Rule
PF has a highly skewed sampling distribution. Empirically, require:
- **n ≥ 100** for PF estimate to have a 95% CI width < 0.5
- **n ≥ 200** for strategies with PF < 2.0 (higher variance in lower-PF regimes)

### 2.3 Hard Minimums by Gate
| Gate | Minimum n | Rationale |
|------|-----------|-----------|
| Discovery (FDR screen) | 30 | Bare minimum for any distributional estimate |
| Statistical Validation | 100 | Power = 0.80 to detect 10% WR edge |
| Money-Ready Certification | 200 | Stable bootstrap CI for PF; sufficient for walk-forward folds |

---

## 3. Multiple Testing Correction

With `m` strategies tested simultaneously, the probability of at least one false positive approaches 1.

### 3.1 Bonferroni (Family-Wise Error Rate)
```
α_adj = α / m
```
For `m = 100`, `α = 0.05`: **α_adj = 0.0005**

**Use for:** Final "Money-Ready" certification. Extremely conservative; guarantees ≤ 5% chance of ANY false positive across the entire family.

### 3.2 Benjamini-Hochberg FDR (False Discovery Rate)
1. Sort p-values: `p(1) ≤ p(2) ≤ ... ≤ p(m)`
2. Find largest `k` such that: `p(k) ≤ (k / m) * α`
3. Reject null hypotheses `H(1)` through `H(k)`

**Use for:** Strategy discovery and screening. Controls the *proportion* of false discoveries rather than the probability of any false positive. Recommended `α = 0.10` for discovery.

### 3.3 Storey-Tibshirani q-values (Adaptive FDR)
When the proportion of true null hypotheses `π0` is unknown, estimate it from the p-value distribution and compute q-values. This is more powerful than BH when many strategies are truly null.

**Implementation rule:**
- **Screening phase:** Use BH-FDR at α = 0.10 to filter candidates.
- **Certification phase:** Use Bonferroni at α = 0.05 on the screened subset.

---

## 4. Metric Definitions, Formulas & Thresholds

### 4.1 Win Rate (WR)
```python
WR = count(trade_pnl > 0) / count(all_trades)
```
- **Gross threshold:** > 50%
- **Net threshold:** > 45%
- **Note:** WR alone is meaningless (can be 90% with tiny wins and huge losses).

### 4.2 Profit Factor (PF)
```python
PF = sum(positive_pnls) / abs(sum(negative_pnls))
```
- **Gross threshold:** > 1.5
- **Net threshold:** > 1.2
- **Bootstrap 95% CI lower bound:** > 1.0

### 4.3 Sharpe Ratio (Annualized)
```python
excess_returns = daily_returns - risk_free_rate  # risk_free = 0.02/252 for daily
daily_sharpe = mean(excess_returns) / std(excess_returns)
Sharpe = daily_sharpe * sqrt(252)
```
- **Gross threshold:** > 1.0
- **Net threshold:** > 0.5
- **Bootstrap 95% CI lower bound:** > 0

### 4.4 Sortino Ratio
```python
# Minimum Acceptable Return (MAR) = risk_free_rate
downside_returns = min(0, daily_return - MAR)^2
downside_deviation = sqrt(mean(downside_returns))
Sortino = mean(excess_returns) / downside_deviation * sqrt(252)
```
- **Gross threshold:** > 1.5
- **Net threshold:** > 0.8

### 4.5 Calmar Ratio
```python
CAGR = (ending_value / starting_value)^(1/years) - 1
MaxDrawdown = max(peak - trough) / peak
Calmar = CAGR / MaxDrawdown
```
- **Threshold:** > 1.0 (requires at least 1 year of history)

### 4.6 Deflated Sharpe Ratio (DSR)
Lopez de Prado (2018). Computes the probability that the observed Sharpe is > 0 after adjusting for:
- Non-normality (skew, kurtosis)
- Sample length
- Number of trials (multiple testing)

```python
# Simplified implementation (see Python file for exact numerical integration)
DSR = probability_that_true_SR > 0 | (SR_hat, T, skew, kurt, V, m)
```
Where:
- `SR_hat` = observed Sharpe
- `T` = sample size (number of returns)
- `skew` = skewness of returns
- `kurt` = excess kurtosis
- `V` = variance of Sharpe ratios across all tested strategies
- `m` = total number of strategies tested

- **Threshold:** > 0.95 (95% confidence that true Sharpe > 0)

---

## 5. Validation Protocol: Lucky vs. Genuine

### 5.1 Bootstrap Validation
**Purpose:** Estimate confidence intervals for PF and Sharpe without parametric assumptions.

**Method:**
1. Collect trade returns `R = [r1, r2, ..., rn]`
2. Resample with replacement 10,000 times to create `R*_1, R*_2, ..., R*_10000`
3. For each resample, calculate `PF*` and `Sharpe*`
4. Compute percentile-based 95% CI

**Pass Criteria:**
```python
pf_ci_lower = percentile(bootstrap_pf_distribution, 2.5)
sharpe_ci_lower = percentile(bootstrap_sharpe_distribution, 2.5)

PASS if pf_ci_lower > 1.0 AND sharpe_ci_lower > 0
```

### 5.2 Walk-Forward Analysis (WFA)
**Purpose:** Detect overfitting by testing on chronologically distinct periods.

**Method:**
1. Divide history into `k = 10` contiguous folds
2. For fold `i` in `[2, k]`:
   - **Train:** folds `1` through `i-1` (parameter discovery / IS)
   - **Test:** fold `i` (OOS)
3. Record OOS metrics for each fold

**Pass Criteria:**
```python
profitable_folds = count(fold_pf > 1.0 for fold in folds)
mean_oos_pf = mean(fold_pf for fold in folds)

PASS if (profitable_folds / k >= 0.6) AND (mean_oos_pf > 1.2)
```

### 5.3 Out-of-Sample (OOS) Holdout
**Purpose:** Final test on unseen data, simulating real-world deployment.

**Method:**
1. Temporal split: first 70% = IS, last 30% = OOS
2. Calculate all metrics on OOS subset only
3. **Critical:** OOS metrics must be calculated *without* any parameter tuning on OOS data

**Pass Criteria:**
```python
PASS if (OOS_PF > 1.2) AND (OOS_Sharpe > 0.5) AND (OOS_WR > 0.45)
```

---

## 6. Money-Ready Threshold (Transaction Costs & Slippage)

Gross metrics are fantasy. Money-ready metrics deduct realistic costs.

### 6.1 Cost Model
```python
# Per-trade cost deduction
total_cost_pct = commission_pct + spread_bps/10000 + slippage_pct

# Slippage model (volatility-adjusted)
base_slippage = 0.0005  # 5 bps
volatility_penalty = 0.1  # scales with realized vol
realized_vol = std(returns, lookback=20)
slippage_pct = base_slippage + (volatility_penalty * realized_vol)
```

### 6.2 Net Return Calculation
```python
# Deduct costs from each trade
net_trade_return = gross_trade_return - total_cost_pct

# Recalculate all metrics using net returns
net_pf = sum(max(0, net_trade_return)) / abs(sum(min(0, net_trade_return)))
net_sharpe = sharpe(net_daily_returns)
net_sortino = sortino(net_daily_returns)
```

### 6.3 Money-Ready Gates
| Metric | Gross Threshold | Net Threshold | Bootstrap CI Lower |
|--------|----------------|---------------|-------------------|
| PF | > 1.5 | > 1.2 | > 1.0 |
| Sharpe | > 1.0 | > 0.5 | > 0 |
| WR | > 50% | > 45% | > 40% |
| Sortino | > 1.5 | > 0.8 | > 0.5 |
| DSR | — | > 0.95 | — |

---

## 7. Direction Bias Scoring (LONG vs. SHORT)

Many strategies exhibit asymmetric performance. A valid framework must score directions separately.

### 7.1 Directional Subsetting
```python
long_trades = [t for t in trades if t['direction'] == 'LONG']
short_trades = [t for t in trades if t['direction'] == 'SHORT']
```

### 7.2 Minimum Per-Direction Sample
- `n_long >= 30` and `n_short >= 30` for bias detection
- If one direction has `n < 30`, mark as "insufficient data" for that side

### 7.3 Direction Bias Metrics
```python
pf_long = profit_factor(long_trades)
pf_short = profit_factor(short_trades)

# Normalized bias score: -1.0 (pure short) to +1.0 (pure long)
pf_bias = (pf_long - pf_short) / (pf_long + pf_short)

wr_long = win_rate(long_trades)
wr_short = win_rate(short_trades)
wr_bias = (wr_long - wr_short) / (wr_long + wr_short)
```

### 7.4 Bias Flags
| Condition | Flag | Action |
|-----------|------|--------|
| \|pf_bias\| > 0.3 AND both n >= 30 | DIRECTIONAL | Report separate LONG/SHORT scores |
| n_long < 30 OR n_short < 30 | INSUFFICIENT_DATA | Do not compute bias; require more trades |
| \|pf_bias\| <= 0.3 AND both n >= 30 | BALANCED | Report unified score |

### 7.5 Direction-Specific Certification
A strategy can be certified as "LONG-ONLY" or "SHORT-ONLY" if:
- One direction passes all gates (PF > 1.5, Sharpe > 1.0, etc.)
- The other direction has `n < 30` OR fails Gate 1 (bootstrap CI for PF includes 1.0)

---

## 8. Pass/Fail Gate Structure

Strategies progress through 6 gates. Failure at any gate halts progression.

```
┌─────────────────────────────────────────────────────────────┐
│  GATE 0: DATA QUALITY                                       │
│  - Complete trade log (entry, exit, direction, PnL)         │
│  - No missing prices                                        │
│  - n >= 30 (discovery) or n >= 100 (validation)             │
└─────────────────────────────────────────────────────────────┘
                            ▼ PASS
┌─────────────────────────────────────────────────────────────┐
│  GATE 1: STATISTICAL SIGNIFICANCE                           │
│  - Bootstrap 95% CI: PF_lower > 1.0                         │
│  - Bootstrap 95% CI: Sharpe_lower > 0                       │
│  - p-value < α_corrected (Bonferroni or BH)                 │
└─────────────────────────────────────────────────────────────┘
                            ▼ PASS
┌─────────────────────────────────────────────────────────────┐
│  GATE 2: ROBUSTNESS (Walk-Forward)                          │
│  - >= 60% profitable WFA folds                              │
│  - Mean OOS PF across folds > 1.2                           │
└─────────────────────────────────────────────────────────────┘
                            ▼ PASS
┌─────────────────────────────────────────────────────────────┐
│  GATE 3: PROFITABILITY (Gross)                              │
│  - PF > 1.5                                                 │
│  - Sharpe > 1.0                                             │
│  - WR > 50%                                                 │
│  - Sortino > 1.5                                            │
└─────────────────────────────────────────────────────────────┘
                            ▼ PASS
┌─────────────────────────────────────────────────────────────┐
│  GATE 4: MONEY-READY (Net, After Costs)                     │
│  - Net PF > 1.2                                             │
│  - Net Sharpe > 0.5                                         │
│  - Net WR > 45%                                             │
│  - DSR > 0.95                                               │
└─────────────────────────────────────────────────────────────┘
                            ▼ PASS
┌─────────────────────────────────────────────────────────────┐
│  GATE 5: DIRECTION VALIDATION                               │
│  - If DIRECTIONAL flag: both sides must pass Gate 4, OR     │
│    strategy is explicitly certified as SINGLE-DIRECTION     │
│  - If BALANCED: unified score must pass Gate 4              │
└─────────────────────────────────────────────────────────────┘
                            ▼ PASS
                    [MONEY-READY CERTIFIED]
```

### 8.1 Scoring Output Schema
```json
{
  "strategy_id": "strategy_042",
  "certification_status": "MONEY_READY",
  "gates": {
    "gate_0_data_quality": "PASS",
    "gate_1_statistical_significance": "PASS",
    "gate_2_walk_forward": "PASS",
    "gate_3_gross_profitability": "PASS",
    "gate_4_money_ready": "PASS",
    "gate_5_direction_validation": "PASS"
  },
  "metrics": {
    "gross": {"pf": 1.8, "sharpe": 1.2, "wr": 0.56, "sortino": 1.8, "calmar": 1.2},
    "net": {"pf": 1.35, "sharpe": 0.72, "wr": 0.51, "sortino": 1.1},
    "bootstrap_ci": {"pf_lower": 1.15, "sharpe_lower": 0.35},
    "dsr": 0.97,
    "walk_forward": {"profitable_folds": 8, "total_folds": 10, "mean_oos_pf": 1.45},
    "oos": {"pf": 1.55, "sharpe": 0.95, "wr": 0.53}
  },
  "direction": {
    "flag": "DIRECTIONAL",
    "pf_bias": 0.42,
    "long": {"n": 150, "pf": 2.1, "sharpe": 1.5},
    "short": {"n": 85, "pf": 1.2, "sharpe": 0.4}
  },
  "multiple_testing": {
    "m": 150,
    "p_value": 0.0003,
    "alpha_bonferroni": 0.00033,
    "bonferroni_pass": true,
    "fdr_q_value": 0.02,
    "fdr_pass": true
  }
}
```

---

## 9. Implementation Notes

### 9.1 Survivorship Bias Prevention
- **Do NOT filter closed trades by profitability before scoring.**
- All trades in the ledger must be evaluated, including:
  - Expired trades (pnl = 0)
  - SL hits
  - Manual closures
- The only valid filter is temporal (date range), never outcome-based.

### 9.2 Intrabar Replay Adjustment
Given that 23-24% of "wins" flip to SL-first on intrabar inspection:
- Apply a **conservative slippage penalty** (+10 bps) to all winning trades.
- Or: reduce gross win PnL by 24% * average_win_size before calculating PF.
- This is captured in the `slippage_pct` model above.

### 9.3 Re-calculation Frequency
- **Discovery scores:** Recalculate daily for all strategies with n >= 30.
- **Validation scores:** Recalculate weekly for strategies passing Gate 0.
- **Money-ready certification:** Recalculate monthly; requires 200+ trades and 3+ months of history.

---

## 10. Summary Table: Thresholds at a Glance

| Metric | Discovery | Validation | Gross Profit | Money-Ready (Net) | Bootstrap CI Lower |
|--------|-----------|------------|--------------|-------------------|-------------------|
| **n (trades)** | >= 30 | >= 100 | >= 100 | >= 200 | — |
| **PF** | > 1.2 | > 1.3 | > 1.5 | > 1.2 | > 1.0 |
| **Sharpe** | > 0.3 | > 0.7 | > 1.0 | > 0.5 | > 0 |
| **WR** | > 45% | > 48% | > 50% | > 45% | > 40% |
| **Sortino** | > 0.5 | > 1.0 | > 1.5 | > 0.8 | > 0.5 |
| **Calmar** | — | > 0.5 | > 1.0 | > 0.8 | — |
| **DSR** | — | > 0.90 | > 0.95 | > 0.95 | — |
| **WFA Folds Profitable** | — | >= 50% | >= 60% | >= 60% | — |
| **OOS PF** | — | > 1.1 | > 1.3 | > 1.2 | — |
| **Multiple Testing** | BH-FDR α=0.10 | BH-FDR α=0.10 | Bonferroni α=0.05 | Bonferroni α=0.05 | — |
