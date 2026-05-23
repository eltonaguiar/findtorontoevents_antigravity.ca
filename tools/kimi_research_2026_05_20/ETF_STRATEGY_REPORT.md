# ETF Multi-Strategy Alpha Engine — Technical Report

**System:** findtorontoevents.ca/audit Stage 1-7 Pipeline  
**Date:** 2026-05-20  
**Version:** 2.1.0  
**Author:** Quantitative ETF Strategist  
**Status:** Production-Ready

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Architecture](#system-architecture)
3. [ETF Universe & Compliance](#etf-universe--compliance)
4. [Strategy Families](#strategy-families)
5. [Backtest Engine](#backtest-engine)
6. [Statistical Validation Framework](#statistical-validation-framework)
7. [Ensemble Construction](#ensemble-construction)
8. [Pipeline Integration](#pipeline-integration)
9. [Performance Metrics](#performance-metrics)
10. [Risk Management](#risk-management)
11. [Implementation Details](#implementation-details)
12. [Appendices](#appendices)

---

## Executive Summary

The ETF Multi-Strategy Alpha Engine (`etf_strategy_harness.py`) is a production-grade quantitative system that generates, validates, and selects statistically proven ETF trading strategies. The system:

- **Generates 600+ strategy variants** across 8 strategy families
- **Backtests each variant** with realistic cost modelling (expense ratios, tracking error)
- **Validates via bootstrapped Sharpe ratios** with Benjamini-Hochberg FDR correction
- **Constructs a diversified ensemble** of 5-8 top picks across different ETF categories
- **Outputs system-compatible JSON** for downstream pipeline stages

### Key Thresholds & Constraints

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Min Sharpe Ratio | 1.0 | Statistically significant risk-adjusted return |
| Max Drawdown | 15% | Capital preservation limit |
| Max P-Value | 0.05 | 95% confidence level |
| BH-FDR Q | 0.05 | False discovery rate control |
| PnL Win Threshold | 5 bps (0.05%) | Minimum economically meaningful trade |
| PnL Sanity Cap | 200% | Explosion protection |
| Ensemble Size | 5-8 | Diversification without dilution |

### Blacklist Enforcement

- **IWM (Russell 2000):** Grade F hard block — excluded from all strategies
- **GLD (Gold):** Grade F hard block — excluded from all strategies

---

## System Architecture

### Stage 1-7 Pipeline Integration

```
EMIT ──────► INGEST ──────► ACTIVE GATE ──────► SMART GATE ──────► HIGH CONVICTION ──────► CONSENSUS ──────► OUTCOME
  │              │                │                   │                    │                  │               │
  │         (this engine)     Liquidity         Statistical        Position sizing     Cross-asset       Final P&L
  │         Generate 600+     filtering         validation         & risk limits       reconciliation    attribution
  │         strategies        (spread, vol)     (Sharpe, FDR)      (Kelly, VaR)        (ensemble vote)   & reporting
```

The engine operates at the **EMIT → INGEST** boundary, producing the initial signal set that feeds downstream gates.

### Module Structure

```
etf_strategy_harness.py
├── Constants & Configuration
├── Enums (SignalType, StrategyFamily, Grade)
├── Data Containers (Signal, BacktestResult, EnsemblePick)
├── Data Generator (multivariate GBM with sector correlations)
├── Utility Functions (Sharpe, Sortino, Calmar, VaR, CVaR, MDD)
├── Statistical Tests (Bootstrap, BH-FDR, Grade Assignment)
├── Signal Generators (8 families, fully vectorized)
├── Backtest Engine (vectorized, cost-aware)
├── StrategyHarness (orchestrator: generate → validate → ensemble)
├── Unit Tests (PyTest-compatible)
└── CLI Entrypoint
```

---

## ETF Universe & Compliance

### Complete Universe (18 ETFs)

| Ticker | Category | Expense Ratio | Tracking Error | Status |
|--------|----------|---------------|----------------|--------|
| SPY | US Equity — Broad | 0.09% | 0.05% | Tradeable |
| QQQ | US Equity — Tech | 0.20% | 0.10% | Tradeable |
| DIA | US Equity — Large Cap | 0.16% | 0.10% | Tradeable |
| VTI | US Equity — Total Market | 0.03% | 0.03% | Tradeable |
| VOO | US Equity — S&P 500 | 0.03% | 0.03% | Tradeable |
| ARKK | US Equity — Disruptive | 0.75% | 0.50% | Tradeable |
| XLF | US Sector — Financial | 0.10% | 0.08% | Tradeable |
| XLE | US Sector — Energy | 0.10% | 0.08% | Tradeable |
| XLK | US Sector — Technology | 0.10% | 0.08% | Tradeable |
| SLV | Commodity — Precious | 0.50% | 0.30% | Tradeable |
| USO | Commodity — Energy | 0.79% | 1.00% | Tradeable |
| EEM | Emerging Markets | 0.68% | 0.50% | Tradeable |
| EFA | Developed Markets | 0.32% | 0.30% | Tradeable |
| SQQQ | Inverse Leveraged | 0.89% | 2.00% | Tradeable |
| TQQQ | Leveraged (3x) | 0.89% | 2.00% | Tradeable |
| UVXY | Volatility | 0.89% | 5.00% | Tradeable |
| ~~IWM~~ | ~~Russell 2000~~ | ~~0.19%~~ | ~~0.15%~~ | **BLACKLISTED** |
| ~~GLD~~ | ~~Gold~~ | ~~0.40%~~ | ~~0.20%~~ | **BLACKLISTED** |

### Category Taxonomy

```
US_EQ_BROAD           ─ SPY, VTI, VOO
US_EQ_TECH            ─ QQQ
US_EQ_LARGE           ─ DIA
US_EQ_TOTAL           ─ VTI
US_EQ_SP500           ─ VOO
US_EQ_DISRUPTIVE      ─ ARKK
US_SECTOR_FINANCIAL   ─ XLF
US_SECTOR_ENERGY      ─ XLE
US_SECTOR_TECH        ─ XLK
COMMODITY_PRECIOUS    ─ SLV
COMMODITY_ENERGY      ─ USO
EM_EQ                 ─ EEM
DM_EQ                 ─ EFA
INVERSE_LEVERAGED     ─ SQQQ
LEVERAGED             ─ TQQQ
VOLATILITY            ─ UVXY
```

---

## Strategy Families

### Family 1: Sector Rotation (35 parameter variants)

**Logic:** Rank sector ETFs by N-day momentum. Go long the top third, short the bottom third. Hold for `holding_period` days.

**Tickers:** XLF, XLE, XLK  
**Parameters:**
- `lookback`: {5, 10, 15, 20, 30, 40, 60} days
- `holding_period`: {3, 5, 10, 15, 20} days

**Why it works:** Sector momentum persists over 1-12 month horizons due to slow-moving capital reallocation and institutional herding.

---

### Family 2: Index Trend Following (30 parameter variants)

**Logic:** Price > N-day SMA × 1.01 → LONG. Price < SMA × 0.99 → SHORT.

**Tickers:** SPY, QQQ, DIA, VTI, VOO  
**Parameters:**
- `sma_period`: {20, 30, 50, 100, 150, 200} days

**Why it works:** Time-series momentum in equity indices is one of the most robust anomalies, documented across 100+ years of data (Moskowitz & Grinblatt, 1999; Hurst et al., 2013).

---

### Family 3: Inverse & Leveraged ETF Timing (75 parameter variants)

**Logic:**
- **UVXY:** Fade spikes (mean reversion), short contango decay
- **TQQQ:** Follow momentum (go long on rallies, short on drops)
- **SQQQ:** Fade rallies (structural decay exploitation)

**Tickers:** SQQQ, TQQQ, UVXY  
**Parameters:**
- `lookback`: {3, 5, 10, 15, 20} days
- `threshold`: {1%, 2%, 3%, 5%, 8%}

**Why it works:** Leveraged and inverse ETFs suffer from volatility decay (compounding effects). UVXY has persistent contango drag of ~5-10% per month.

---

### Family 4: NAV Premium/Discount Arbitrage (80 parameter variants)

**Logic:** When ETF trades at premium > threshold → SHORT (premium collapses). When discount > threshold → LONG (discount narrows).

**Tickers:** All 16 tradeable ETFs  
**Parameters:**
- `threshold`: {0.1%, 0.3%, 0.5%, 1.0%, 2.0%}

**Why it works:** ETF premiums/discounts are mean-reverting due to the creation/redemption arbitrage mechanism. Authorized participants profit from closing deviations.

---

### Family 5: Flow-Based Strategies (192 parameter variants)

**Logic:** Volume > N× average volume → follow the price direction (institutional flow signal).

**Tickers:** All 16 tradeable ETFs  
**Parameters:**
- `volume_lookback`: {10, 20, 30} days
- `multiplier`: {1.5×, 2.0×, 2.5×, 3.0×}

**Why it works:** Large volume spikes often indicate informed institutional trading. Following "smart money" flow generates alpha (Ben-David et al., 2018).

---

### Family 6: Cross-Asset ETF Spreads (96 parameter variants)

**Logic:** Trade the ratio between paired ETFs when the Z-score deviates from its mean.

**Pairs:**
- SLV / USO (precious metals vs energy)
- EEM / EFA (emerging vs developed markets)
- XLE / XLF (energy vs financial sector)
- XLK / XLF (tech vs financial sector)
- EEM / XLK (emerging vs tech)
- EFA / SPY (developed vs US broad)

**Parameters:**
- `lookback`: {10, 20, 30, 40} days
- `z_threshold`: {1.0, 1.5, 2.0, 2.5} standard deviations

**Why it works:** Cointegrated asset pairs exhibit mean-reverting spreads. Statistical arbitrage profits from temporary dislocations.

---

### Family 7: Volatility Regime Strategies (20 parameter variants)

**Logic:**
- UVXY spike > threshold → SHORT (fade the fear)
- UVXY contango (drift < -0.5% daily) → structural SHORT

**Ticker:** UVXY  
**Parameters:**
- `lookback`: {10, 15, 20, 30} days
- `spike_threshold`: {3%, 5%, 8%, 10%, 15%}

**Why it works:** VIX futures are in contango ~80% of the time. UVXY, which holds front-month VIX futures, decays at ~5-10% per month due to daily rolldown.

---

### Family 8: Factor ETF Rotation (6 parameter variants)

**Logic:** Use sector ETFs as factor proxies. Long the best-performing factor, short the worst.

**Factor Proxies:**
- XLF = Value
- XLK = Growth
- ARKK = Momentum/Quality

**Parameters:**
- `lookback`: {10, 15, 20, 30, 40, 60} days

**Why it works:** Factor premiums (value, momentum, quality) exhibit time-varying performance. Dynamic rotation captures the best-performing factor while hedging the worst.

---

## Backtest Engine

### Vectorized Execution

All strategies are implemented using fully vectorized pandas/numpy operations:
- No Python loops in the hot path
- Position series generated via boolean indexing and rolling windows
- Return calculation via element-wise multiplication

### Cost Modelling

#### 1. Expense Ratio Drag
```
daily_drag = expense_ratio / 252
```
Deducted from daily returns. Ranges from 0.03% (VTI/VOO) to 0.89% (UVXY/SQQQ/TQQQ) annually.

#### 2. Tracking Error
```
daily_te_noise ~ N(0, tracking_error / sqrt(252))
```
Stochastic cost simulating deviation between ETF return and underlying index return.

#### 3. PnL Win Threshold
Trades with |PnL| < 5 bps are set to zero. Eliminates economically meaningless micro-trades.

#### 4. PnL Sanity Cap
Individual daily returns are clipped to [-200%, +200%]. Prevents numerical explosions from data errors or extreme events.

### Signal Processing

- **Entry:** Signal strength (0.0-1.0) determines position size
- **Holding:** Positions held for configurable `holding_period` days
- **Exit:** Position closed after holding period or on opposing signal
- **Position clipping:** All positions bounded to [-1, 1]

---

## Statistical Validation Framework

### Step 1: Preliminary Hard Filters

| Filter | Threshold | Purpose |
|--------|-----------|---------|
| Sharpe Ratio | >= 1.0 | Risk-adjusted return significance |
| Max Drawdown | < 15% | Capital preservation |
| P-Value | < 0.05 | 95% confidence vs random |
| Grade | Not F | Composite quality gate |
| Min Trades | >= 5 | Statistical sufficiency |

### Step 2: Bootstrapped Sharpe Ratio

```python
for i in range(10_000):
    sample = random.choice(returns, replace=True)
    sharpe_i = calc_sharpe(sample)
```

- **Null Hypothesis:** True Sharpe <= 0
- **P-Value:** Proportion of bootstrapped Sharpes <= 0
- **95% CI:** Percentiles [2.5, 97.5] of bootstrap distribution

### Step 3: Benjamini-Hochberg FDR Correction

Controls the False Discovery Rate when testing 600+ strategies simultaneously:

```
1. Sort p-values: p_1 <= p_2 <= ... <= p_m
2. Find largest k where p_k <= (k/m) * q
3. Reject H_0 for all i <= k
```

Without BH-FDR, we'd expect ~30 false positives at alpha=0.05 with 600 tests. BH-FDR limits false discoveries to 5% of rejected hypotheses.

### Step 4: Walk-Forward Validation

5-fold cross-validation on contiguous time blocks:
- Ensures strategy performance is not due to data snooping
- Validates robustness across different market regimes
- Strategies must be profitable in >= 60% of folds

### Grade Assignment

| Grade | Sharpe | Max DD | P-Value | Win Rate |
|-------|--------|--------|---------|----------|
| A | >= 1.5 | < 10% | < 0.01 | > 55% |
| B | >= 1.2 | < 12% | < 0.03 | > 52% |
| C | >= 1.0 | < 15% | < 0.05 | > 50% |
| D | >= 0.7 | < 20% | < 0.10 | — |
| F | < 0.7 | >= 20% | >= 0.10 | — |

---

## Ensemble Construction

### Diversification Enforcement

No two ensemble picks may share the same category. This guarantees exposure to distinct risk premia.

### Composite Scoring

```
Composite Score = 0.5 * Sharpe + 0.3 * Calmar + 0.2 * (1 - P-Value)
```

### Weight Allocation

```
Weight_i = Composite_i / sum(Composite_j for all j)
```

### Selection Algorithm

```
1. Sort validated strategies by Sharpe (descending)
2. For each strategy:
   a. Skip if category already used
   b. Add to ensemble
   c. Mark category as used
3. Stop when 8 picks reached or list exhausted
4. Normalize weights to sum to 100%
```

---

## Pipeline Integration

### JSON Output Schema

```json
{
  "meta": {
    "system": "ETF Alpha Engine",
    "version": "2.1.0",
    "timestamp": "2026-05-20T00:00:00",
    "pipeline_stage": "EMIT → INGEST",
    "universe": ["SPY", "QQQ", ...],
    "blacklist": ["IWM", "GLD"]
  },
  "parameters": {
    "min_sharpe": 1.0,
    "max_drawdown": 0.15,
    "max_pvalue": 0.05,
    "fdr_q": 0.05,
    ...
  },
  "ensemble": [
    {
      "rank": 1,
      "strategy_id": "sector_rot_l20_h5_XLE",
      "etf": "XLE",
      "category": "US_SECTOR_ENERGY",
      "direction": "LONG",
      "allocation_weight": 0.25,
      "expected_return": 0.185,
      "expected_sharpe": 1.42,
      "grade": "C",
      "composite_score": 0.823
    },
    ...
  ],
  "validated_strategies": [...],
  "statistics": {
    "total_backtested": 609,
    "validated_count": 7,
    "ensemble_size": 5,
    "categories_covered": ["DM_EQ", "US_SECTOR_TECH", ...]
  },
  "compliance": {
    "blacklist_adhered": true,
    "grade_f_blocked": true,
    "min_sharpe_adhered": true
  }
}
```

### Downstream Integration Points

| Field | Consumer Stage | Usage |
|-------|---------------|-------|
| `ensemble[].etf` | ACTIVE GATE | Liquidity filter |
| `ensemble[].direction` | SMART GATE | Signal confirmation |
| `ensemble[].allocation_weight` | HIGH CONVICTION | Position sizing |
| `ensemble[].expected_sharpe` | CONSENSUS | Weighted voting |
| `compliance.*` | OUTCOME | Audit trail |

---

## Performance Metrics

### Computed for Every Strategy

| Metric | Formula | Interpretation |
|--------|---------|----------------|
| Sharpe Ratio | (AnnReturn - Rf) / AnnVol | Risk-adjusted return |
| Sortino Ratio | (AnnReturn - Rf) / DownsideDev | Tail-risk-adjusted return |
| Calmar Ratio | AnnReturn / MaxDrawdown | Return per unit drawdown |
| Max Drawdown | max(peak - trough) / peak | Worst peak-to-trough loss |
| Win Rate | # winning trades / total | Hit rate |
| Profit Factor | gross profit / gross loss | Payoff ratio |
| VaR (95%) | 5th percentile of returns | 1-day downside at 95% confidence |
| CVaR (95%) | mean of returns below VaR | Expected shortfall |
| Skewness | 3rd standardized moment | Tail asymmetry |
| Kurtosis | 4th standardized moment | Tail fatness |
| Expense Drag | ER / 252 × 252 | Annual cost impact |
| Tracking Error Cost | TE / sqrt(252) × 252 | Annual tracking cost |

---

## Risk Management

### Individual Strategy Risk
- Max drawdown cap: 15%
- Daily PnL sanity cap: 200%
- Minimum trade threshold: 5 bps

### Portfolio-Level Risk
- Maximum 1 pick per category (diversification)
- Position weights sum to 100%
- No concentration above 35%

### Compliance Checks
- `blacklist_adhered`: No blacklisted ETFs in ensemble
- `grade_f_blocked`: No Grade-F strategies pass
- `min_sharpe_adhered`: All picks meet minimum Sharpe

---

## Implementation Details

### Dependencies

```
pandas >= 1.5.0
numpy >= 1.23.0
scipy >= 1.10.0
```

### Execution

```bash
# Run the full pipeline
python etf_strategy_harness.py

# Run unit tests
pytest etf_strategy_harness.py

# Import as module
from etf_strategy_harness import ETFStrategyHarness
harness = ETFStrategyHarness()
output = harness.run()
```

### Custom Data Input

```python
import pandas as pd
from etf_strategy_harness import ETFStrategyHarness

# Load your own price data
my_data = pd.read_parquet("my_etf_data.parquet")
# Must have MultiIndex columns: (ticker, field) where field in ['close', 'volume', 'nav']

harness = ETFStrategyHarness(data=my_data)
output = harness.run()
```

### Configuration Overrides

All parameters are module-level constants and can be overridden:

```python
import etf_strategy_harness as ese
ese.MIN_SHARPE = 0.8          # Relax Sharpe requirement
ese.MAX_DRAWDOWN = 0.20       # Allow larger drawdowns
ese.BOOTSTRAP_ITERATIONS = 5000  # Faster bootstrapping
```

---

## Appendices

### Appendix A: Strategy Count by Family

| Family | Variants | Tickers per Variant | Total Results |
|--------|----------|--------------------:|---------------|
| Sector Rotation | 35 | 3 | ~105 |
| Index Trend | 30 | 1 | ~30 |
| Inverse/Leveraged | 75 | 1 | ~75 |
| NAV Arbitrage | 80 | 1 | ~80 |
| Flow Based | 192 | 1 | ~192 |
| Cross-Asset Spread | 96 | 2 | ~192 |
| Volatility Regime | 20 | 1 | ~20 |
| Factor Rotation | 6 | 2-3 | ~15 |
| **Total** | **534** | — | **~609** |

### Appendix B: References

1. Moskowitz, T.J. & Grinblatt, M. (1999). "Do Industries Explain Momentum?" *Journal of Finance*, 54(4), 1249-1290.
2. Hurst, B., Ooi, Y.H. & Pedersen, L.H. (2013). "Demystifying Managed Futures." *Journal of Investment Management*, 11(3), 42-58.
3. Ben-David, I., Franzoni, F. & Moussawi, R. (2018). "Do ETFs Increase Volatility?" *Journal of Finance*, 73(6), 2471-2535.
4. Benjamini, Y. & Hochberg, Y. (1995). "Controlling the False Discovery Rate." *Journal of the Royal Statistical Society*, 57(1), 289-300.
5. Efron, B. & Tibshirani, R.J. (1993). *An Introduction to the Bootstrap*. Chapman & Hall.

### Appendix C: Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-05-15 | Initial release |
| 2.0.0 | 2026-05-18 | Vectorized backtest engine, 8 strategy families |
| 2.1.0 | 2026-05-20 | Full vectorization, BH-FDR, pipeline JSON output |

---

*This report was auto-generated by the ETF Multi-Strategy Alpha Engine v2.1.0 on 2026-05-20.*
