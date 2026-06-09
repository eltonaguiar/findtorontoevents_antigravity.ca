# Strategy Failure Analysis Framework
## A Quantitative Perspective on Diagnosing Strategy Decay

**Version:** 1.0  
**Date:** 2026-06-09  
**Status:** CANONICAL -- Single source of truth for strategy failure diagnosis

---

## Executive Summary

When a strategy fails, a Quant team doesn't ask "why did it lose money?" -- they ask **"which component of the edge decayed?"** This framework provides a systematic five-pillar approach to diagnose strategy failures, moving beyond surface-level PnL analysis to root-cause identification.

---

## The Five Pillars of Strategy Failure

### Pillar 1: Statistical Failure (The Overfitting Trap)

**Symptom:** High backtest performance, catastrophic forward performance  
**Root Cause:** Parameter sensitivity ("knife-edge" effect) or lookahead bias in training data

#### Quantitative Checks

| Check | Method | Threshold | Action |
|-------|--------|-----------|--------|
| **Parameter Stability Test** | Vary each parameter ±1-5%, measure WR/PF change | >50% drop in WR = FAIL | Reject strategy; too fragile |
| **Walk-Forward Validation** | 4+ overlapping sleeves, quarterly rebalance | <50% OOS windows positive = FAIL | Demote to paper |
| **Deflated Sharpe Ratio** | López de Prado (2014) adjustment for multiple testing | Deflated Sharpe < 0.5 = FAIL | Reject |
| **Bootstrap P-Value** | Resample trades 10,000x vs null (WR=0.5, PF=1.0) | p > 0.05 = FAIL | Not statistically significant |

#### Implementation
```python
def parameter_stability_test(strategy_params, param_ranges, n_trials=100):
    """Test if small parameter changes cause large performance drops."""
    baseline_wr = run_backtest(strategy_params)
    failures = 0
    for _ in range(n_trials):
        perturbed = {k: v * np.random.uniform(0.95, 1.05) for k, v in strategy_params.items()}
        wr = run_backtest(perturbed)
        if (baseline_wr - wr) / baseline_wr > 0.5:  # 50% drop
            failures += 1
    return failures / n_trials  # Should be < 0.1 for robust strategies
```

---

### Pillar 2: Structural Failure (The Regime Mismatch)

**Symptom:** Strategy works perfectly for months, then enters long drawdown  
**Root Cause:** Market regime shifted (Trending → Mean-Reverting, Low Vol → High Vol)

#### Quantitative Checks

| Check | Method | Threshold | Action |
|-------|--------|-----------|--------|
| **Regime Attribution** | Compare current performance to historical in same regime | Current WR < 50% of historical in regime = FAIL | Pause strategy |
| **Regime Transition Detection** | HMM / Markov regime model on returns | Regime change probability > 80% = ALERT | Reduce allocation |
| **Factor Exposure Drift** | Rolling 60-day factor betas (Market, Momentum, Value, Carry) | Beta correlation < 0.3 vs baseline = FAIL | Strategy mutated |

#### Implementation
```python
def regime_attribution_analysis(strategy_returns, regime_labels, lookback_days=252):
    """Analyze strategy performance conditional on market regime."""
    results = {}
    for regime in ['BULL', 'BEAR', 'SIDEWAYS', 'HIGH_VOL']:
        mask = regime_labels[-lookback_days:] == regime
        if mask.sum() < 30:  # Minimum sample
            continue
        regime_returns = strategy_returns[-lookback_days:][mask]
        results[regime] = {
            'wr': (regime_returns > 0).mean(),
            'avg_return': regime_returns.mean(),
            'sharpe': regime_returns.mean() / regime_returns.std() * np.sqrt(252),
            'n': mask.sum()
        }
    return results
```

---

### Pillar 3: Execution Failure (The Cost Erosion)

**Symptom:** High gross profit, negative net profit  
**Root Cause:** Slippage, commissions, bid-ask spread not modeled

#### Quantitative Checks

| Check | Method | Threshold | Action |
|-------|--------|-----------|--------|
| **Break-Even Slippage** | Max slippage (bps) before strategy becomes unprofitable | < 5 bps = FAIL | Strategy not viable live |
| **Slippage Sensitivity** | PnL vs slippage curve (0-50 bps) | Slope > -0.5% per bp = FAIL | Too sensitive |
| **Implementation Shortfall** | (Signal price - Fill price) / Signal price | > 20 bps median = FAIL | Fix execution |
| **Turnover Cost Drag** | Annual turnover × (commission + spread) | > 50% of gross return = FAIL | Reduce frequency |

#### Implementation
```python
def break_even_slippage(gross_returns, trades_per_year, commission_bps=2, spread_bps=5):
    """Calculate maximum slippage strategy can absorb."""
    gross_annual = np.sum(gross_returns) * (252 / len(gross_returns))
    fixed_costs = trades_per_year * (commission_bps + spread_bps) / 10000
    max_slippage_bps = (gross_annual - fixed_costs) * 10000 / trades_per_year
    return max_slippage_bps  # If < 5, strategy dies on execution
```

---

### Pillar 4: Data Failure (Garbage-In/Garbage-Out)

**Symptom:** Impossible win rates (99%), sudden inexplicable PnL jumps  
**Root Cause:** Lookahead bias, API failures, corporate action mishandling

#### Quantitative Checks

| Check | Method | Threshold | Action |
|-------|--------|-----------|--------|
| **Timestamp Cross-Reference** | Signal timestamp vs exchange OHLCV | > 1% signals use future data = FAIL | Audit data pipeline |
| **Data Integrity Audit** | Compare multiple data sources (Yahoo, Polygon, CCXT) | > 0.5% price discrepancy = ALERT | Switch primary source |
| **Survivorship Bias Check** | Include delisted symbols in backtest | Performance drop > 20% = FAIL | Fix universe |
| **Corporate Action Handling** | Verify split/dividend adjustments | Unadjusted data in backtest = FAIL | Re-run with adjusted |

#### Implementation
```python
def data_integrity_audit(signals, exchange_data, tolerance_bps=50):
    """Cross-reference signal timestamps with exchange data."""
    mismatches = 0
    for sig in signals:
        ex_row = exchange_data[
            (exchange_data.symbol == sig.symbol) & 
            (exchange_data.timestamp == sig.timestamp)
        ]
        if len(ex_row) == 0:
            mismatches += 1
            continue
        # Check if signal used future data
        if sig.entry_price > ex_row.high.max() or sig.entry_price < ex_row.low.min():
            mismatches += 1
    return mismatches / len(signals)
```

---

### Pillar 5: Risk Management Failure (The Tail Risk Event)

**Symptom:** Single trade or cluster wipes out months of profit  
**Root Cause:** Poor position sizing, correlation blindness, missing circuit breakers

#### Quantitative Checks

| Check | Method | Threshold | Action |
|-------|--------|-----------|--------|
| **Effective Beta** | Portfolio beta to market (rolling 60d) | > 1.5 = FAIL | Reduce net exposure |
| **Concentration Risk** | Herfindahl-Hirschman Index (HHI) of positions | HHI > 0.25 = FAIL | Diversify |
| **Correlation Spike** | Max pairwise correlation in portfolio | > 0.7 for >5 pairs = ALERT | Hedge / reduce |
| **Kelly Fraction** | Optimal f vs actual position size | Actual > 0.5 × Kelly = FAIL | Reduce size |
| **Circuit Breaker Test** | Simulate -20% day; portfolio loss | > 10% portfolio loss = FAIL | Add stops |

#### Implementation
```python
def risk_management_audit(positions, returns, lookback=60):
    """Comprehensive risk management checks."""
    # Effective beta
    market_returns = get_market_returns(lookback)
    portfolio_returns = (positions * returns).sum(axis=1)
    beta = np.cov(portfolio_returns, market_returns)[0,1] / np.var(market_returns)
    
    # Concentration (HHI)
    weights = np.abs(positions.iloc[-1]) / np.abs(positions.iloc[-1]).sum()
    hhi = np.sum(weights ** 2)
    
    # Correlation spike
    corr_matrix = returns.iloc[-lookback:].corr()
    np.fill_diagonal(corr_matrix.values, 0)
    high_corr_pairs = (corr_matrix > 0.7).sum().sum() / 2
    
    return {
        'effective_beta': beta,
        'hhi': hhi,
        'high_corr_pairs': high_corr_pairs,
        'max_position_pct': weights.max() * 100,
        'passes': beta < 1.5 and hhi < 0.25 and high_corr_pairs < 5
    }
```

---

## Integrated Failure Diagnosis Workflow

```
STRATEGY FAILURE DETECTED
         │
         ▼
┌────────────────────────┐
│  RUN ALL 5 PILLARS     │
│  IN PARALLEL           │
└───────────┬────────────┘
            │
    ┌───────┼───────┐
    ▼       ▼       ▼
PILLAR 1  PILLAR 2  PILLAR 3
Statistical Structural Execution
    │       │       │
    ▼       ▼       ▼
PILLAR 4  PILLAR 5
Data      Risk
            │
            ▼
┌────────────────────────┐
│  ROOT CAUSE REPORT     │
│  - Primary pillar      │
│  - Contributing factors│
│  - Recommended action  │
└────────────────────────┘
```

### Decision Matrix

| Primary Pillar | Action |
|----------------|--------|
| Statistical | **KILL** — Strategy is overfit; no amount of tuning fixes this |
| Structural | **PAUSE** — Wait for regime to revert; maintain separate genomes per regime |
| Execution | **FIX** — Improve execution (VWAP, TWAP, limit orders); re-evaluate |
| Data | **AUDIT** — Fix data pipeline; re-run backtests with clean data |
| Risk | **REDUCE** — Cut position sizes; add circuit breakers; diversify |

---

## Dashboard Integration

The following visualizations should be added to the Audit Dashboard to enable real-time failure diagnosis:

### 1. Parameter Stability Heatmap
- X-axis: Parameters (RSI period, EMA fast/slow, ATR multiplier, etc.)
- Y-axis: Strategies
- Color: % WR drop from ±5% parameter perturbation
- **Red = fragile (knife-edge)**

### 2. Regime-Conditional Performance Matrix
- Rows: Strategies
- Columns: Regimes (BULL, BEAR, SIDEWAYS, HIGH_VOL)
- Cells: WR, PF, Sharpe with bootstrap 95% CI
- **Highlight: Strategies with no regime where WR > 55%**

### 3. Slippage Sensitivity Curves
- X-axis: Slippage (0-50 bps)
- Y-axis: Net PnL / Gross PnL ratio
- One line per strategy
- **Break-even point marked**

### 4. Data Quality Scorecard
- Per-symbol data freshness
- Multi-source price discrepancy %
- Lookahead bias detection rate
- **Red flags for symbols with >1% issues**

### 5. Risk Dashboard
- Real-time effective beta
- HHI concentration index
- Pairwise correlation heatmap
- Circuit breaker status (green/yellow/red)

---

## Automation: Continuous Failure Monitoring

```python
# Run every 4 hours via GitHub Actions
def continuous_failure_monitor():
    """Automated strategy health check."""
    alerts = []
    
    for strategy in get_active_strategies():
        # Pillar 1: Statistical
        if not check_walk_forward_valid(strategy):
            alerts.append(f"{strategy}: FAILED walk-forward validation")
        
        # Pillar 2: Structural
        regime_perf = regime_attribution_analysis(strategy)
        current_regime = get_current_regime()
        if regime_perf[current_regime]['wr'] < 0.45:
            alerts.append(f"{strategy}: Underperforming in {current_regime} regime")
        
        # Pillar 3: Execution
        be_slippage = break_even_slippage(strategy)
        if be_slippage < 5:
            alerts.append(f"{strategy}: Break-even slippage only {be_slippage:.1f} bps")
        
        # Pillar 4: Data
        data_quality = data_integrity_audit(strategy)
        if data_quality > 0.01:
            alerts.append(f"{strategy}: {data_quality*100:.1f}% data integrity issues")
        
        # Pillar 5: Risk
        risk = risk_management_audit(strategy)
        if not risk['passes']:
            alerts.append(f"{strategy}: Risk limits breached (beta={risk['effective_beta']:.2f}, HHI={risk['hhi']:.3f})")
    
    if alerts:
        send_discord_alert("\n".join(alerts), severity="HIGH")
    
    return alerts
```

---

## Historical Case Studies (From This System)

| Strategy | Primary Pillar | Root Cause | Resolution |
|----------|---------------|------------|------------|
| `quan_engine_scalp` | Statistical + Execution | 2,512 trades, -427% PnL; TP/SL too tight for noise | **KILLED** — removed from all systems |
| `alpha_factor_composite` | Statistical | -8.93% avg return; overfit to backtest | **DEMOTED** — paper only |
| `TRXUSDT` (symbol) | Data + Risk | 96.8% of all losses; toxic symbol | **BANNED** — added to blocked registry |
| `st_rsi_momentum_confluence` | — | 65.1% WR, PF 2.53 — **PASSES ALL PILLARS** | **PROMOTED** to Tier 1 |

---

## Appendix: Quick Reference Card

```
STRATEGY FAILURE? → RUN 5-PILLAR DIAGNOSIS

1. STATISTICAL: Parameter stability? Walk-forward? Deflated Sharpe? Bootstrap p-value?
   → FAIL = KILL

2. STRUCTURAL: Regime attribution? Factor drift? HMM regime prob?
   → FAIL = PAUSE (wait for regime reversion)

3. EXECUTION: Break-even slippage? Implementation shortfall? Turnover cost?
   → FAIL = FIX execution or KILL if <5 bps

4. DATA: Timestamp cross-ref? Multi-source check? Survivorship? Corp actions?
   → FAIL = AUDIT pipeline, re-run backtests

5. RISK: Effective beta? HHI? Correlation spike? Kelly fraction? Circuit breakers?
   → FAIL = REDUCE size, add hedges, diversify

OUTPUT: Root cause report → Action → Track resolution
```

---

## References

1. López de Prado, M. (2014). "The Deflated Sharpe Ratio." *Journal of Portfolio Management*.
2. Bailey, D. et al. (2017). "The Probability of Backtest Overfitting." *Journal of Financial Data Science*.
3. Rockafellar, R.T. & Uryasev, S. (2000). "Optimization of Conditional Value-at-Risk." *Journal of Risk*.
4. Marcos López de Prado (2018). "Advances in Financial Machine Learning." Wiley.
5. Aronson, D. (2007). "Evidence-Based Technical Analysis." Wiley.

---

*This framework is mandatory for all strategy demotions per `docs/PERFORMANCE_CHARTER.md` §8.*