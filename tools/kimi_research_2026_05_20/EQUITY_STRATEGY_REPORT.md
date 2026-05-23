# EQUITY Multi-Strategy Harness Report

**Version:** 2026.5.20  
**Generated:** 2026-05-20  
**Target System:** findtorontoevents.ca/audit  
**Asset Class:** EQUITY (U.S. Listed Stocks)

---

## Executive Summary

This report documents the design, implementation, and statistical validation framework of the `equity_strategy_harness.py` module — a production-ready multi-strategy engine that generates, validates, and ensembles EQUITY trading strategies. The harness addresses the critical performance deficiencies in the current audit pipeline by enforcing rigorous statistical proof on every strategy before it enters the trading decision flow.

### Key Deliverables

| Metric | Value |
|--------|-------|
| Candidate Strategies Generated | **170** |
| Strategy Families | **8** |
| Statistical Tests Per Strategy | **6** |
| Minimum Required Sharpe | **1.0** |
| Maximum Allowed Drawdown | **20%** |
| Significance Threshold (p-value) | **< 0.05** |
| FDR Correction | **Benjamini-Hochberg** |
| Bootstrap Resamples | **10,000** |
| Walk-Forward Folds | **3 rolling folds** |
| Monte Carlo Simulations | **5,000** |

---

## 1. System Architecture

### 1.1 Pipeline Integration

```
STAGE 1: EMIT        -> StrategyGenerator    -> 170 candidate configs
STAGE 2: INGEST      -> BacktestEngine       -> per-symbol backtests  
STAGE 3: ACTIVE GATE -> StatisticalValidator -> Sharpe>1.0, p<0.05, DD<20%
STAGE 4: SMART GATE  -> WalkForward + MC     -> 3-fold + 5k stress test
STAGE 5: ENSEMBLE    -> EnsembleConstructor  -> 5-10 factor-diversified
STAGE 6: EXPORT      -> JSON                 -> findtorontoevents.ca/audit
```

### 1.2 Module Structure

```
equity_strategy_harness.py
|
|-- Constants & Configuration
|   |-- EQUITY_SYMBOLS (55+ liquid names)
|   |-- SECTOR_MAP (11 GICS sectors)
|   |-- Cost model ($0.005/share, 1-3bp slippage)
|   |-- Validation thresholds
|
|-- PriceDataManager
|   |-- load_ohlcv()         -> synthetic or real price feed
|   |-- Sector-specific drift/vol calibration
|
|-- StrategyGenerator
|   |-- 170 configs across 8 families
|   |-- Parameter grid search
|   |-- resolve_signal_generator() factory
|
|-- Signal Generators (37 concrete implementations)
|   |-- EarningsMomentum     (3 classes)
|   |-- FactorBased          (7 classes)
|   |-- TechnicalBreakout    (10 classes)
|   |-- MeanReversion        (5 classes)
|   |-- SectorRotation       (4 classes)
|   |-- InsiderActivity      (2 classes)
|   |-- MarketBreadth        (3 classes)
|   |-- Seasonality          (6 classes)
|
|-- BacktestEngine
|   |-- Vectorized event-driven simulation
|   |-- Commission + slippage model
|   |-- Sharpe, Sortino, MaxDD, Hit-Rate, Profit Factor
|
|-- StatisticalValidator
|   |-- Block-bootstrap Sharpe (10,000 resamples)
|   |-- One-sample t-test (H0: mean return <= 0)
|   |-- Benjamini-Hochberg FDR correction
|   |-- Rolling 3-fold walk-forward
|   |-- Monte Carlo stress test (5,000 permutations)
|
|-- EnsembleConstructor
|   |-- Greedy selection by Sharpe
|   |-- Category diversification (max 2 per family)
|   |-- Sharpe-weighted capital allocation
|
|-- EquityStrategyHarness
|   |-- run_full_pipeline()  -> end-to-end orchestration
|   |-- save_json()          -> audit-compatible export
|
|-- Unit Tests (9 smoke tests)
```

---

## 2. Strategy Catalog (170 Configurations)

### 2.1 Earnings Momentum (28 configs)

| Strategy | Count | Logic | Hold Period |
|----------|-------|-------|-------------|
| `earnings_surprise` | 12 | Z-score of return vs rolling vol exceeds threshold | 5d |
| `earnings_guidance` | 4 | Consecutive up-day streak as guidance proxy | 5d |
| `post_earnings_drift` | 12 | PEAD: drift after large gap relative to vol | 10d |

**Key Parameters:** `vol_lookback` in {10,20,40}, `z_threshold` in {1.0,1.5,2.0,2.5}

### 2.2 Factor Based (33 configs)

| Strategy | Count | Factor Proxy | Hold Period |
|----------|-------|-------------|-------------|
| `value_factor` | 4 | Worst 20% recent return = value tilt | 20d |
| `growth_factor` | 4 | Best 20% 6-12mo momentum | 20d |
| `quality_factor` | 6 | Low vol + positive trend | 20d |
| `lowvol_factor` | 4 | Lowest 10% realised volatility | 20d |
| `momentum_factor` | 9 | 12-1 month momentum (skip recent month) | 20d |
| `smallcap_premium` | 3 | High-volatility proxy for small-cap tilt | 10d |
| `profitability_factor` | 3 | Positive return + shallow drawdown | 20d |

### 2.3 Technical Breakout (33 configs)

| Strategy | Count | Entry Trigger | Hold Period |
|----------|-------|--------------|-------------|
| `resistance_breakout` | 4 | Close above N-day high | 5d |
| `support_bounce` | 4 | Price at N-day low support | 5d |
| `volume_breakout` | 3 | Breakout on 2x avg volume | 5d |
| `gap_fill` | 3 | Fade large overnight gaps | 3d |
| `ma_crossover` | 4 | Fast MA crosses above slow MA | 10d |
| `bollinger_breakout` | 6 | Close above upper BB | 5d |
| `adx_breakout` | 3 | ADX > 25 (trend strength) | 10d |
| `macd_signal` | 3 | MACD line crosses signal | 5d |
| `rsi_overbought_breakout` | 3 | RSI exits oversold (<30) | 3d |

### 2.4 Mean Reversion (28 configs)

| Strategy | Count | Mean Reversion Logic | Hold Period |
|----------|-------|---------------------|-------------|
| `rsi_mean_reversion` | 3 | RSI < 30 long; RSI > 70 short | 3d |
| `bollinger_mean_reversion` | 6 | Price below lower band | 5d |
| `zscore_mean_reversion` | 9 | Z-score of price vs rolling mean | 5d |
| `pair_ratio_mr` | 9 | Log-price z-score reversion | 5d |
| `candlestick_hammer` | 1 | Hammer candlestick pattern | 2d |

### 2.5 Sector Rotation (12 configs)

| Strategy | Count | Rotation Logic | Hold Period |
|----------|-------|---------------|-------------|
| `relative_strength_sector` | 3 | Buy names beating sector median | 20d |
| `sector_momentum_rotation` | 3 | Rotate into high-momentum sector | 20d |
| `sector_mean_reversion` | 3 | Contrarian: buy worst sector | 20d |
| `industry_breadth` | 3 | Price above 50d MA breadth signal | 20d |

### 2.6 Insider Activity (18 configs)

| Strategy | Count | Footprint Proxy | Hold Period |
|----------|-------|----------------|-------------|
| `insider_buy_cluster` | 9 | Consecutive down days + volume spike | 10d |
| `insider_sell_cluster` | 9 | Consecutive up days + climax volume | 5d (short) |

### 2.7 Market Breadth (7 configs)

| Strategy | Count | Breadth Measure | Hold Period |
|----------|-------|----------------|-------------|
| `advance_decline_proxy` | 3 | Fraction of up days in window | 10d |
| `new_highs_proxy` | 3 | Price makes N-day high | 10d |
| `mcclellan_proxy` | 1 | 19/39 EMA oscillator proxy | 10d |

### 2.8 Seasonality (11 configs)

| Strategy | Count | Calendar Effect | Hold Period |
|----------|-------|----------------|-------------|
| `january_effect` | 1 | Small-cap rally in January | 20d |
| `earnings_season` | 2 | Long during earnings months | 20d |
| `tax_loss_harvesting` | 3 | Buy beaten-down names Dec/Jan | 10d |
| `turn_of_month` | 1 | Last day + first 3 days of month | 5d |
| `summer_doldrums` | 1 | Avoid/short Aug-Sep | 20d |
| `october_reversal` | 3 | October bear-market low reversal | 20d |

---

## 3. Backtest Engine

### 3.1 Transaction Cost Model

```
total_cost = slippage + commission

slippage = 1 bp  for large-cap (AAPL, MSFT, GOOGL, ...)
slippage = 3 bp  for mid-cap  (COIN, RIOT, MARA, HUT, ...)

commission = $0.005 / share
           = $0.005 / avg_price  (as fraction of notional)
```

### 3.2 Performance Metrics

| Metric | Formula | Interpretation |
|--------|---------|---------------|
| Total Return | (Final - Initial) / Initial | Raw strategy performance |
| Annualized Return | mean(daily_ret) * 252 | Return scaled to 1 year |
| Volatility | std(daily_ret) * sqrt(252) | Risk measure |
| **Sharpe Ratio** | (AnnReturn - Rf) / Vol | **Primary selection criterion** |
| Sortino Ratio | AnnReturn / DownsideVol | Return per unit downside risk |
| Max Drawdown | max(peak - trough) / peak | Worst peak-to-trough decline |
| Hit Rate | # winning trades / # total trades | Trade accuracy |
| Profit Factor | |sum(wins)| / |sum(losses)| | Gross profit / gross loss |

### 3.3 Risk-Free Rate

Set to **4.5%** annual (approximate 3-month T-bill rate as of 2026-05-20).

---

## 4. Statistical Validation Framework

### 4.1 Six-Layer Validation Gate

Every strategy must pass ALL six gates to enter the ensemble:

```
GATE 1: Bootstrapped Sharpe > 1.0
    -> 10,000 block-bootstrap resamples
    -> Circular block bootstrap (block size = n/20)
    -> Must: mean_sharpe > 1.0

GATE 2: t-test p-value < 0.05
    -> H0: mean daily return <= 0
    -> H1: mean daily return > 0
    -> One-sample one-sided t-test
    -> Must: p < 0.05

GATE 3: Max Drawdown < 20%
    -> Rolling peak-to-trough calculation
    -> Must: max_dd < 0.20

GATE 4: Walk-Forward Validation
    -> 3 rolling folds over time series
    -> Each fold Sharpe > 0.5
    -> Guards against time-period luck

GATE 5: Monte Carlo Stress Test
    -> 5,000 random permutations of returns
    -> 5th percentile Sharpe > 0
    -> Ensures robustness to path reshuffling

GATE 6: Benjamini-Hochberg FDR
    -> q-value < 0.05
    -> Controls false discovery rate across 170 tests
```

### 4.2 Why These Thresholds?

| Threshold | Rationale |
|-----------|-----------|
| Sharpe > 1.0 | Industry standard for "good" strategies; filters noise |
| p-value < 0.05 | 95% confidence that outperformance is non-random |
| MaxDD < 20% | Institutional risk tolerance; prevents ruin |
| WF Sharpe > 0.5 | Ensures consistency across sub-periods |
| MC 5th %ile > 0 | Strategy survives randomization stress |
| q-value < 0.05 | FDR correction for multiple testing (170 strategies) |

### 4.3 Multiple Testing Correction

With 170 candidate strategies, even at alpha=0.05 we'd expect ~8.5 false positives by chance. The Benjamini-Hochberg procedure controls the **False Discovery Rate** — the expected proportion of falsely rejected null hypotheses among all rejections.

```
Procedure:
1. Sort p-values: p(1) <= p(2) <= ... <= p(m)
2. Find largest k: p(k) <= (k/m) * alpha
3. Reject H0 for all i <= k
```

This is more powerful than Bonferroni (which would require p < 0.05/170 = 0.00029) while still controlling error rates.

---

## 5. Ensemble Construction

### 5.1 Selection Algorithm

```python
1. Filter: keep only strategies where passed == True
2. Sort:  descending by Sharpe ratio
3. Greedy select while maintaining:
    - Max 2 strategies per category (factor diversification)
    - Max 10 strategies total
    - Min 5 strategies (or warn if insufficient)
4. Allocate capital by Sharpe weighting:
    weight_i = sharpe_i / sum(all_sharpes)
```

### 5.2 Diversification Constraints

| Constraint | Value | Purpose |
|------------|-------|---------|
| Max per category | 2 | Prevent factor concentration |
| Max total | 10 | Manageable oversight |
| Min total | 5 | Statistical power |
| Capital weighting | Sharpe-proportional | Risk-adjusted sizing |

### 5.3 Output Format (Audit Integration)

```json
{
  "strategy_uid": "abc123...",
  "strategy_name": "momentum_factor",
  "category": "factor_based",
  "weight": 0.25,
  "capital_allocation_pct": 25.0,
  "expected_return": 0.18,
  "expected_sharpe": 1.35,
  "symbols": ["AAPL", "MSFT", ...],
  "sector_breakdown": {"Technology": 0.4, "Financials": 0.3, ...},
  "meta": {
    "params": {"lookback_long": 240, "lookback_skip": 20},
    "hold_period": 20,
    "p_value": 0.003421,
    "q_value": 0.008234,
    "boot_sharpe_p05": 0.85,
    "max_drawdown": 0.12,
    "hit_rate": 0.58,
    "num_trades": 145
  },
  "timestamp_utc": "2026-05-20T14:30:00Z",
  "version": "2026.5.20"
}
```

---

## 6. Known Symbol Universe

### 6.1 Large-Cap (35 names)

AAPL, MSFT, GOOGL, GOOG, AMZN, TSLA, META, NVDA, AMD, NFLX, DIS, BA, ORCL, JPM, GS, V, MA, BAC, UNH, XOM, JNJ, WMT, PG, HD, ABBV, PFE, KO, PEP, COST, TMO, AVGO, CRM, GS, LLY, CVX, NKE

### 6.2 Mid-Cap (20+ names)

PYPL, SQ, COIN, MSTR, RIOT, MARA, HUT, BITF, INTC, QCOM, MU, LRCX, KLAC, UBER, LYFT, ABNB, ROKU, SNOW, PLTR, DDOG, NET, ZM, DOCU, SHOP, SPOT, TWLO, OKTA, CRWD, FTNT, PANW, CYBR, ZS, SPLK, NOW, VEEV, TEAM

### 6.3 Sector Distribution

| Sector | Count | Representative Symbols |
|--------|-------|----------------------|
| Technology | 22 | AAPL, MSFT, NVDA, AMD, AVGO, ORCL, CRM |
| Communication | 6 | GOOGL, GOOG, META, NFLX, DIS, ROKU |
| Consumer Discretionary | 8 | AMZN, TSLA, HD, NKE, ABNB, SHOP |
| Financials | 7 | JPM, GS, V, MA, BAC, PYPL, SQ |
| Health Care | 6 | UNH, JNJ, PFE, LLY, TMO, VEEV |
| Consumer Staples | 5 | WMT, PG, KO, PEP, COST |
| Industrials | 3 | BA, UBER, LYFT |
| Energy | 2 | XOM, CVX |

---

## 7. Integration with Audit Pipeline

### 7.1 Stage Mapping

| Audit Stage | Harness Component | Output |
|------------|-------------------|--------|
| EMIT | `StrategyGenerator` | 170 configs with metadata |
| INGEST | `BacktestEngine.run()` | Per-symbol backtest results |
| ACTIVE GATE | `StatisticalValidator.validate()` | Sharpe, p-value, drawdown checks |
| SMART GATE | `walk_forward()` + `monte_carlo()` | Sub-period + stress validation |
| HIGH CONVICTION | `apply_fdr_correction()` | q-value filtering |
| CONSENSUS | `EnsembleConstructor.build()` | Diversified ensemble of 5-10 |
| OUTCOME | `save_json()` | `equity_ensemble_output.json` |

### 7.2 JSON Output Schema

The final output JSON contains three top-level sections:

```json
{
  "harness_version": "2026.5.20",
  "timestamp_utc": "2026-05-20T14:30:00Z",
  "summary": {
    "configs_generated": 170,
    "backtests_run": 2550,
    "strategies_passed": <N>,
    "ensemble_size": <M>,
    "thresholds": { ... }
  },
  "ensemble": [ ... ],
  "all_validated": [ ... ]
}
```

### 7.3 Running the Harness

```bash
# Full pipeline (all symbols)
python equity_strategy_harness.py --out equity_ensemble_output.json

# Subset of symbols
python equity_strategy_harness.py --symbols AAPL MSFT GOOGL AMZN

# Run unit tests
python equity_strategy_harness.py --test
```

### 7.4 Python API

```python
from equity_strategy_harness import EquityStrategyHarness

# Initialize
harness = EquityStrategyHarness(symbols=["AAPL", "MSFT", "GOOGL"])

# Run full pipeline
payload = harness.run_full_pipeline()

# Save for audit ingestion
harness.save_json(payload, "/path/to/equity_ensemble_output.json")

# Access ensemble
for alloc in payload["ensemble"]:
    print(f"{alloc['strategy_name']}: weight={alloc['weight']:.2%}")
```

---

## 8. Cost Model Details

### 8.1 Slippage by Market Cap

| Bucket | Symbols | Slippage |
|--------|---------|----------|
| Large-Cap | AAPL, MSFT, GOOGL, JPM, V, MA, ... | 1 bp |
| Mid-Cap | COIN, RIOT, MARA, HUT, BITF, ... | 3 bp |

### 8.2 Commission Structure

```
Commission: $0.005 per share (institutional tier)

Example for $10,000 notional on $100 stock:
    Shares: 100
    Commission: 100 * $0.005 = $0.50
    Commission as %: 0.50 / 10,000 = 0.005%

Example for $10,000 notional on $50 stock:
    Shares: 200
    Commission: 200 * $0.005 = $1.00
    Commission as %: 1.00 / 10,000 = 0.01%
```

### 8.3 PnL Integration

The harness outputs `elite_score` metadata compatible with the ACTIVE GATE:

```
Elite Score >= 55:   Strategy passes gate
Grade F:             Hard block (exemptions available)
PnL WIN threshold:   5 bp (0.0005)
PnL sanity cap:      500%
```

---

## 9. Extending the Harness

### 9.1 Adding New Strategies

```python
class MyCustomSignal(SignalGenerator):
    def __call__(self, ohlcv: pd.DataFrame) -> pd.Series:
        # Your signal logic here
        sig = pd.Series(0, index=ohlcv.index, dtype=float)
        sig[my_condition] = 1
        return sig * self.cfg.direction.value

# Register
StrategyGenerator.SIGNAL_REGISTRY["my_custom"] = MyCustomSignal

# Add to generator
def _add_my_family(self):
    for param in [1, 2, 3]:
        self._configs.append(StrategyConfig(
            name="my_custom", category=StrategyCategory.FACTOR_BASED,
            params={"param": param}, lookback=20, hold_period=5,
        ))
```

### 9.2 Using Real Price Data

Replace `PriceDataManager._synthetic_ohlcv()` with a real data source:

```python
class RealDataManager(PriceDataManager):
    def load_ohlcv(self, symbol, start, end):
        # Query your database / API
        df = query_your_data_warehouse(symbol, start, end)
        return df
```

### 9.3 Custom Validation Thresholds

```python
from equity_strategy_harness import (
    StatisticalValidator, MIN_SHARPE, MAX_DRAWDOWN
)

# Override thresholds
MIN_SHARPE = 1.5          # More selective
MAX_DRAWDOWN = 0.15       # Tighter risk

validator = StatisticalValidator(n_bootstrap=20_000)  # More resamples
```

---

## 10. Quality Assurance

### 10.1 Unit Test Coverage

| Test | Description |
|------|-------------|
| Config hash stability | UID determinism across runs |
| Data manager output | Valid OHLCV DataFrame structure |
| Config count | 170+ strategies generated |
| Signal values | Only {-1, 0, 1} emitted |
| Backtest metrics | All fields populated correctly |
| Validator logic | passed flag set correctly |
| FDR correction | q-value computed and applied |
| Ensemble construction | Output type and weights valid |
| End-to-end pipeline | Full execution without errors |

### 10.2 Known Limitations

1. **Synthetic data**: Current implementation uses synthetic GBM paths. Production deployment requires real OHLCV data.
2. **Signal proxy quality**: Factor signals (value, quality, profitability) use price-based proxies. Production should use fundamental data (book value, earnings, ROE).
3. **Single-symbol backtests**: Each config runs per symbol. True factor strategies should be evaluated cross-sectionally.
4. **No transaction volume limit**: Assumes all signals can be filled. Large AUM may hit capacity constraints.
5. **Static parameters**: Parameter grids are fixed. Adaptive/optimal parameter selection is a future enhancement.

### 10.3 Future Enhancements

- [ ] Real-time data feed integration (Polygon, IEX, Alpaca)
- [ ] Cross-sectional ranking for factor strategies
- [ ] Machine learning overlay (gradient boosting for signal combination)
- [ ] Regime detection (HMM for bull/bear/sideways)
- [ ] Dynamic position sizing (Kelly criterion)
- [ ] Correlation-aware ensemble weighting
- [ ] Out-of-sample validation with expanding window
- [ ] Live paper-trading bridge

---

## 11. Appendix: Mathematical Details

### 11.1 Sharpe Ratio

```
Sharpe = (E[R_p] - R_f) / sigma_p

Where:
    E[R_p] = mean daily strategy return * 252
    R_f    = risk-free rate (4.5%)
    sigma_p = std daily strategy return * sqrt(252)
```

### 11.2 Block Bootstrap

```
1. Divide return series into overlapping blocks of length b
2. Sample blocks with replacement until length n is reached
3. Concatenate blocks -> bootstrap sample
4. Compute Sharpe on bootstrap sample
5. Repeat 10,000 times -> distribution of Sharpe ratios
```

Block size b = max(5, n/20) preserves local time-series structure (volatility clustering).

### 11.3 Benjamini-Hochberg FDR

```
Given m hypotheses with ordered p-values p(1) <= ... <= p(m):

Find largest k such that: p(k) <= (k/m) * alpha

Reject H_0 for all i = 1, ..., k

q-value for each test = min_{i>=j} { m*p(i)/i }
```

### 11.4 Maximum Drawdown

```
DD_t = (peak_t - P_t) / peak_t
where peak_t = max(P_1, ..., P_t)

MaxDD = max_t(DD_t)
```

### 11.5 Sortino Ratio

```
Sortino = E[R_p] / sigma_d

Where sigma_d = sqrt( E[min(R_p - E[R_p], 0)^2] ) * sqrt(252)
```

---

## 12. Change Log

| Version | Date | Changes |
|---------|------|---------|
| 2026.5.20 | 2026-05-20 | Initial release: 170 strategies, 6-layer validation, ensemble constructor |

---

*End of Report*
