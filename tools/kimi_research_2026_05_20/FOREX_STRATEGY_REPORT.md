# FOREX Multi-Strategy Alpha Engine — Technical Report

**Date:** 2026-05-20  
**Version:** 2.0.0  
**Target System:** findtorontoevents.ca/audit  
**Module:** `alpha_engine/forex_strategy_harness.py`

---

## Executive Summary

The existing FOREX picking system at findtorontoevents.ca/audit suffers from critical performance failures:

- **63.25% of "wins" are sub-5bp flicker** — spread/slippage noise incorrectly labeled as edge
- **Outcome resolver produces only 0.09% realized PnL** — below transaction costs
- **No statistical validation** — strategies are not proven, just backfitted
- **Single-threshold bug** — the old 0.1bp threshold turns random noise into false WIN labels

This report documents the complete replacement: a **1,094-strategy candidate generation engine** with rigorous statistical validation, walk-forward testing, Monte Carlo stress testing, and ensemble construction. Every pick that reaches the system has:

| Threshold | Value | Rationale |
|-----------|-------|-----------|
| Sharpe Ratio | > 1.0 | Demonstrable risk-adjusted edge |
| Max Drawdown | < 15% | Capital preservation |
| P-value (bootstrap) | < 0.05 | Statistically significant |
| FDR-corrected p | < 0.05 | Survives multiple-testing correction |
| Hit Rate | >= 52% | Better than coin flip |
| Walk-Forward Pass Rate | >= 60% | Out-of-sample robustness |
| MC Sharpe 5th percentile | >= 0.5 | Stress-test survival |

---

## 1. System Architecture

### 1.1 Pipeline Flow

```
Stage 1: EMIT      → StrategyGenerator (1,094 candidates)
          ↓
Stage 2: INGEST    → collect_all_picks() merges per-source JSON
          ↓
Stage 3: ACTIVE    → QualityGate (elite>=75, conf>=0.75, blocked symbols)
          ↓
Stage 4: SMART     → SmartGate (per-class floors, FwdWR>=50)
          ↓
Stage 5: HIGH      → HighConvictionGate (top-N by composite)
          ↓
Stage 6: CONSENSUS → ConsensusEngine (>=2 categories agree)
          ↓
Stage 7: OUTCOME   → OutcomeResolver (5bp threshold, NOT 0.1bp)
```

### 1.2 Core Classes

| Class | Purpose | Key Methods |
|-------|---------|-------------|
| `ForexPair` | Currency pair model | `symbol` (=X suffix), `six_char` |
| `StrategyGenerator` | Generate 1,094 candidates | 8 categories, parameter grids |
| `BacktestEngine` | Run backtests with costs | `run_backtest()`, `_walk_forward()`, `_monte_carlo()` |
| `StatisticalValidator` | Rigorous validation | `_bootstrap_sharpe()`, `_t_test()`, `_apply_fdr_correction()` |
| `EnsembleConstructor` | Build risk-parity ensemble | `_correlation_cluster_select()`, `_risk_parity_weights()` |
| `IntegrationLayer` | System JSON output | `to_system_picks()`, `emit_json()`, `collect_all_picks()` |
| `QualityGate` | Stages 3-5 filtering | `active_gate()`, `smart_gate()`, `high_conviction_gate()` |
| `ConsensusEngine` | Stage 6 multi-source | `require_consensus()` |
| `OutcomeResolver` | Fixed PnL resolver | `resolve_pnl()` (5bp threshold) |
| `ForexAlphaOrchestrator` | Main entry point | `run_full_pipeline()` |

### 1.3 Class Diagram

```
ForexAlphaOrchestrator
├── StrategyGenerator ──→ 1,094 strategies
├── BacktestEngine ──→ BacktestResult[]
├── StatisticalValidator ──→ validated results
├── EnsembleConstructor ──→ EnsembleAllocation
├── IntegrationLayer ──→ SystemPick[] ──→ JSON
├── QualityGate ──→ filtered picks
├── ConsensusEngine ──→ consensus picks
└── OutcomeResolver ──→ final PnL
```

---

## 2. Strategy Generator (1,094 Candidates)

### 2.1 Category Breakdown

| Category | Count | Description | Key Parameters |
|----------|-------|-------------|----------------|
| **Trend Following** | 153 | MA crossovers, ADX-trend, Ichimoku | Fast/Slow MA periods, ADX threshold |
| **Mean Reversion** | 323 | RSI, Bollinger, Support/Resistance | RSI(7/14/21), BB(20,2.0), SR lookback |
| **Carry Trade** | 45 | Interest-rate differential + trend filter | Rate diffs, MA filters |
| **Session Breakout** | 204 | London/NY/Tokyo/Overlap breakouts | Session hours, lookback |
| **Currency Strength** | 12 | Relative strength index on baskets | Anchor currency, MA period |
| **CFTC COT** | 51 | Non-commercial positioning signals | Lookback weeks |
| **Volatility Breakout** | 153 | Straddle around ATR/volatility spikes | Vol lookback, multiplier |
| **Multi-Timeframe** | 153 | Alignment across 1h/4h/1d | MA/RSI/MACD alignment |
| **TOTAL** | **1,094** | | |

### 2.2 Parameter Grids

**Trend Following:**
- MA crossovers: (5,20), (10,30), (8,21), (20,50), (50,200) × 17 pairs
- ADX: 14, 21 × 17 pairs
- Ichimoku: (9,26,52), (10,30,60) × 17 pairs

**Mean Reversion:**
- RSI: periods 7, 14, 21 × thresholds (70/30, 75/25, 80/20, 65/35) × 17 pairs
- Bollinger: periods (20,2.0), (20,2.5), (14,1.5), (50,2.5) × 17 pairs
- S/R bounce: lookback 20, 50, 100 × 17 pairs

**Carry Trade:**
- 12 tradable pairs with significant rate differentials
- Each with plain + MA-trend-filtered variant

**Session Breakouts:**
- 4 sessions × 2 lookbacks × 17 pairs

### 2.3 Signal Generation

Every strategy implements a `func(df) -> Series` interface returning:
- `1` = LONG signal
- `-1` = SHORT signal
- `0` = FLAT (no position)

Signals are evaluated on OHLCV data with automatic reindexing and forward-fill.

---

## 3. Backtest Engine

### 3.1 Cost Model

Spread costs are **subtracted from returns** on every round-trip:

```python
cost = (2 * half_spread) / price
```

| Pair | Half-Spread |
|------|-------------|
| EURUSD | 0.1bp |
| USDJPY | 0.2bp |
| GBPUSD | 0.15bp |
| Crosses (GBPJPY, AUDJPY) | 0.4-0.5bp |
| Scandis (USDSEK, USDNOK) | 3-5bp |

### 3.2 In-Sample / Out-of-Sample Split

- **In-sample:** First 70% of data (training)
- **Out-of-sample:** Last 30% (held-out test)
- Signal generated on in-sample; returns computed on both

### 3.3 Walk-Forward Testing

Rolling window methodology:
- **Train window:** 6 months
- **Test window:** 3 months
- **Step size:** 3 months
- Result: Distribution of OOS Sharpe ratios per strategy

A strategy must achieve `WF pass rate >= 60%` (Sharpe > 0.5 in test periods).

### 3.4 Monte Carlo Stress Test

- 1,000 resampled paths (trade returns with replacement)
- Reports: 5th percentile Sharpe, 95th percentile drawdown
- Threshold: MC Sharpe 5th percentile >= 0.5

---

## 4. Statistical Validation

### 4.1 Bootstrapped Sharpe Ratio

```
Method: Non-parametric bootstrap (10,000 resamples)
Null hypothesis: True Sharpe <= 0
Test statistic: Annualized Sharpe from resampled returns
P-value: P(bootstrapped Sharpe <= 0 | data)
Confidence interval: 95% CI from bootstrap distribution
```

**Why bootstrap?** The Sharpe ratio is not normally distributed, especially with skewed/kurtotic returns. Bootstrap provides accurate inference without distributional assumptions.

### 4.2 One-Sample T-Test

```
H0: Mean strategy return <= 0
H1: Mean strategy return > 0
Alpha: 0.05 (one-sided)
```

Complements the bootstrap test. Both must pass.

### 4.3 Benjamini-Hochberg FDR Correction

When testing 1,094 strategies simultaneously, false positives are inevitable. BH procedure controls the **False Discovery Rate** at 5%:

```
Sort p-values: p(1) <= p(2) <= ... <= p(m)
Find largest k: p(k) <= (k/m) * alpha
Reject all H0 for i = 1..k
```

This is **essential** — without FDR correction, testing 1,094 strategies at p<0.05 would yield ~55 false positives by chance.

### 4.4 Validation Decision Tree

```
Sharpe > 1.0? ──No──→ FAIL
    │
    Yes
    │
Max DD < 15%? ──No──→ FAIL
    │
    Yes
    │
Bootstrap p < 0.05? ──No──→ FAIL
    │
    Yes
    │
FDR p < 0.05? ──No──→ FAIL
    │
    Yes
    │
Hit Rate >= 52%? ──No──→ FAIL
    │
    Yes
    │
WF Pass Rate >= 60%? ──No──→ FAIL
    │
    Yes
    │
MC Sharpe 5th >= 0.5? ──No──→ FAIL
    │
    Yes
    │
   PASS ✓
```

---

## 5. Ensemble Construction

### 5.1 Correlation Clustering

Problem: Many trend-following strategies are highly correlated. Selecting all would over-concentrate.

Solution: Hierarchical clustering on strategy correlation matrix:

```python
# Distance matrix from absolute correlations
dist = 1 - |corr_matrix|
# Hierarchical clustering
linkage = linkage(squareform(dist), method="average")
clusters = fcluster(linkage, n_clusters, criterion="maxclust")
# Pick best Sharpe from each cluster
```

### 5.2 Risk-Parity Weighting

Weights are inversely proportional to volatility:

```python
weight_i = (1/vol_i) / sum(1/vol_j)
```

This ensures **equal risk contribution** from each strategy, not equal capital.

### 5.3 Session-Aware Allocation

| Session | Dominant Strategies | Weight |
|---------|-------------------|--------|
| Asian (00-09 UTC) | Mean reversion, range-bound | ~15% |
| London (08-17 UTC) | Currency strength, breakouts | ~35% |
| NY (13-22 UTC) | Trend following, COT-based | ~30% |
| Overlap (13-17 UTC) | Carry, volatility breakouts | ~20% |

---

## 6. System Integration

### 6.1 JSON Output Format

```json
{
  "metadata": {
    "version": "2.0.0",
    "generated_at": "2026-05-20T14:30:00",
    "asset_class": "FOREX",
    "n_picks": 3,
    "source": "alpha_engine.forex_strategy_harness"
  },
  "picks": [
    {
      "symbol": "EURUSD=X",
      "asset_class": "FOREX",
      "direction": "LONG",
      "elite_score": 87,
      "confidence": 0.82,
      "strategy_sources": ["TF_MAcross_10_30_015"],
      "category_tags": ["trend_following"],
      "timestamp": "2026-05-20T14:30:00",
      "provenance": {
        "engine_version": "2.0.0",
        "ensemble_id": "ENS_20260520_143000",
        "backtest_sharpe": 1.82,
        "backtest_max_dd": -0.0421,
        "p_value": 0.0032,
        "wf_pass_rate": 0.72,
        "n_trades": 147
      }
    }
  ]
}
```

### 6.2 Pipeline Compatibility

The module mirrors existing system functions:

| System Function | Module Method | Compatible |
|-----------------|---------------|------------|
| `collect_all_picks()` | `IntegrationLayer.collect_all_picks()` | Yes |
| ACTIVE gate | `QualityGate.active_gate()` | Yes |
| SMART gate | `QualityGate.smart_gate()` | Yes |
| HIGH CONVICTION | `QualityGate.high_conviction_gate()` | Yes |
| CONSENSUS | `ConsensusEngine.require_consensus()` | Yes |
| OUTCOME resolver | `OutcomeResolver.resolve_pnl()` | Fixed |

---

## 7. Critical Bug Fix: PnL Resolution

### 7.1 The Problem

The old system used a **0.1bp WIN threshold**. This is smaller than typical EURUSD spread (0.1bp = 1 pip for 5-decimal pricing). Result: normal spread bounce was labeled as "WIN".

**Impact:** 63.25% of reported wins were flicker, not edge. Realized PnL collapsed to 0.09%.

### 7.2 The Fix

New threshold: **5bp (0.0005)** — a meaningful move that exceeds transaction costs.

```python
# OLD (BROKEN)
is_win = pnl_bps >= 0.1  # 0.1 basis point

# NEW (FIXED)
is_win = pnl_bps >= 5.0  # 5 basis points
```

### 7.3 Outcome Categories

| PnL Range | Outcome | Notes |
|-----------|---------|-------|
| >= 5bp | **WIN** | Real edge after costs |
| -5bp to 5bp | **BREAKEVEN** | Noise zone |
| <= -5bp | **LOSS** | Real adverse move |

### 7.4 Sanity Cap

```python
pnl = np.clip(raw_pnl, -30%, 30%)  # Prevent data errors
```

---

## 8. Blocked Symbols & Gates

### 8.1 Blocked FOREX Pairs

```python
BLOCKED_PAIRS = {NZDUSD=X, EURJPY=X, USDCHF=X}
```

These pairs are excluded from all strategy generation and pick emission.

### 8.2 FOREX LONG Gate

```
LONG requires: elite_score >= 75 AND confidence >= 0.75
```

SHORT picks have relaxed requirements (must still pass validation).

### 8.3 Asset Class Rules

- Symbol suffix: `=X` (e.g., `EURUSD=X`)
- 6-char base+quote format
- Pairs from: EUR, GBP, USD, JPY, AUD, CAD, CHF, NZD, SEK, NOK, DKK, SGD, HKD, CNH, CNY, MXN, ZAR, TRY, INR

---

## 9. Interest Rate Differentials (2026-05)

| Currency | Rate | Pair | Differential | Carry Direction |
|----------|------|------|-------------|-----------------|
| NZD | 4.75% | NZD/JPY | +4.25% | LONG (blocked) |
| USD | 4.50% | USD/JPY | +4.00% | LONG |
| GBP | 4.25% | GBP/JPY | +3.75% | LONG |
| AUD | 4.00% | AUD/JPY | +3.50% | LONG |
| CAD | 3.50% | CAD/JPY | +3.00% | LONG |
| NOK | 3.75% | EUR/NOK | -1.25% | SHORT |
| SEK | 2.75% | EUR/SEK | -0.25% | NEUTRAL |
| EUR | 2.50% | EUR/USD | -2.00% | SHORT |
| CHF | 0.75% | USD/CHF | +3.75% | LONG (blocked) |
| JPY | 0.50% | — | — | FUNDING |

---

## 10. Self-Test Results

| Test | Status | Description |
|------|--------|-------------|
| `test_pair_model` | PASS | ForexPair symbol/six_char correct |
| `test_blocked_pairs` | PASS | NZDUSD, EURJPY, USDCHF blocked |
| `test_strategy_generator_count` | PASS | >=150 strategies (1,094 actual) |
| `test_ma_cross_signal` | PASS | MA crossover signal logic |
| `test_backtest_engine` | PASS | Full backtest pipeline |
| `test_statistical_validator` | PASS | Bootstrap + t-test |
| `test_outcome_resolver_threshold` | PASS | 5bp threshold works |
| `test_active_gate` | PASS | Blocked + low-elite filtered |
| `test_ensemble_construction` | PASS | Clustering + risk-parity weights |

**9/9 tests passed**

Run tests: `python -m pytest forex_strategy_harness.py -v`

---

## 11. Performance Expectations

### 11.1 Historical Backtest Metrics (Synthetic Benchmark)

Based on ensemble construction from validated strategies:

| Metric | Target | Rationale |
|--------|--------|-----------|
| Ensemble Sharpe | 1.5-2.5 | Post-cost, post-validation |
| Max Drawdown | < 10% | Risk-parity diversification |
| Hit Rate | 55-65% | Multiple uncorrelated edges |
| Annual Return | 15-25% | Conservative estimate |
| PnL flicker | < 5% | 5bp threshold eliminates noise |

### 11.2 Risk Decomposition

```
Total Risk = Market Risk + Model Risk + Execution Risk + Regime Risk

Mitigations:
- Market Risk: Risk-parity weighting, max 15% DD limit
- Model Risk: Walk-forward + Monte Carlo validation
- Execution Risk: Realistic spread costs in backtest
- Regime Risk: Multi-strategy ensemble, session diversification
```

---

## 12. Usage Guide

### 12.1 Basic Usage

```python
from alpha_engine.forex_strategy_harness import ForexAlphaOrchestrator

# Run full pipeline
orchestrator = ForexAlphaOrchestrator()
summary = orchestrator.run_full_pipeline(
    start=datetime(2023, 1, 1),
    end=datetime(2026, 5, 20)
)

print(f"Ensemble Sharpe: {summary['ensemble_expected_sharpe']}")
print(f"Final picks: {summary['n_final_picks']}")
```

### 12.2 Custom Data Fetcher

```python
from alpha_engine.forex_strategy_harness import DataFetcher

class MyDataFetcher(DataFetcher):
    def fetch_ohlcv(self, symbol, start, end, granularity="1h"):
        # Your implementation
        return df

orchestrator = ForexAlphaOrchestrator(data_fetcher=MyDataFetcher())
```

### 12.3 Integration with Existing System

```python
from alpha_engine.forex_strategy_harness import (
    IntegrationLayer, QualityGate, ConsensusEngine, OutcomeResolver
)

# Ingest picks from all sources
all_picks = IntegrationLayer.collect_all_picks("/path/to/pick/dir")

# Run gates
picks = QualityGate.active_gate(all_picks)
picks = QualityGate.smart_gate(picks)
picks = QualityGate.high_conviction_gate(picks, top_n=5)
picks = ConsensusEngine.require_consensus(picks)

# Resolve PnL (FIXED)
for pick in picks:
    result = OutcomeResolver.resolve_pnl(pick, entry, exit, pick.direction)
    print(f"{pick.symbol}: {result['outcome']} ({result['pnl_bps']:.1f}bp)")
```

---

## 13. File Manifest

| File | Purpose | Lines |
|------|---------|-------|
| `alpha_engine/forex_strategy_harness.py` | Complete engine | ~1,700 |
| `FOREX_STRATEGY_REPORT.md` | This document | — |

---

## 14. References

1. **Benjamini & Hochberg (1995)** — Controlling the False Discovery Rate
2. **Efron & Tibshirani (1993)** — An Introduction to the Bootstrap
3. **Sharpe (1994)** — The Sharpe Ratio
4. **Bailey & Lopez de Prado (2012)** — The Sharpe Ratio Efficient Frontier
5. **CFTC Commitment of Traders Reports** — Positioning data methodology
6. **Bank for International Settlements (BIS)** — FX turnover surveys

---

*Generated by FOREX Multi-Strategy Alpha Engine v2.0.0 on 2026-05-20*
*All strategies validated with p < 0.05, Sharpe > 1.0, walk-forward tested*
