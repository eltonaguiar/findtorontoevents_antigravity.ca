# BOND Multi-Strategy Alpha Engine - Strategy Report

**Date:** 2026-05-20
**Version:** 2.0.0
**Target:** findtorontoevents.ca/audit
**Asset Class:** BOND (Grade F hard block exempt)

---

## Executive Summary

The BOND Multi-Strategy Alpha Engine is a statistically rigorous fixed-income trading system that generates 110+ candidate strategies across 8 bond-specific strategy families. The engine validates each candidate through bootstrapped Sharpe ratio testing, Benjamini-Hochberg false discovery rate correction, and walk-forward cross-validation, ultimately producing a duration-neutral ensemble of 5-7 statistically proven strategies.

### Key Metrics

| Metric | Value |
|--------|-------|
| Bond Universe | 14 ETFs (TLT, IEF, SHY, LQD, AGG, BND, HYG, JNK, SJNK, BKLN, EMB, TIP, MUB, IGIB) |
| Strategy Families | 8 categories |
| Total Strategies Generated | 110+ per symbol |
| Min Sharpe Ratio | 0.8 (bond-adjusted) |
| Max Drawdown Limit | 10% |
| P-value Threshold | 0.05 |
| BH-FDR Threshold | 0.10 |
| Target Ensemble Size | 5-7 strategies |
| Duration Neutrality | Portfolio duration ~5.0 years |

---

## Pipeline Architecture

```
EMIT -> INGEST -> ACTIVE GATE -> SMART GATE -> HIGH CONVICTION -> CONSENSUS -> OUTCOME
    |         |           |          |             |               |           |
    |    Load Data   Generate   Backtest    Statistical    Ensemble      JSON
    |    (Synthetic)  110+       Engine      Validation     Constructor   Output
    |              Strategies   (Duration + (Bootstrap +   (Duration-    (System
    |                         Convexity)   BH-FDR + WF)     Neutral)      Compatible)
```

### Stage 1: Data Ingest

Synthetic bond data is generated with realistic dynamics:
- **Yield-driven price movement** using duration + convexity model
- **Fed cycle simulation** (cutting, hiking, pause phases)
- **GARCH volatility clustering** for realistic yield volatility
- **Credit spread mean reversion** via Ornstein-Uhlenbeck process
- **Seasonal patterns** for municipal bonds
- **VIX and SPY data** for flight-to-quality signals

### Stage 2: Strategy Generation (110+ Strategies)

#### 6.1 Yield Curve Strategies (20 strategies)

| Strategy | Description | Direction |
|----------|-------------|-----------|
| `yield_mom_N` | Trade yield momentum (N-day lookback) | Rates down = Long |
| `yield_zscore_N` | Fade yield extremes via z-score | Mean reversion |
| `flattening` | Position for curve flattening | Duration-dependent |
| `steepening` | Position for curve steepening | Duration-dependent |
| `roll_down` | Capture roll-down yield | Always Long |
| `duration_ext` | Extend duration when rates falling | Long duration |
| `duration_comp` | Compress duration when rates rising | Short/Exit |
| `yield_carry` | Hold high-carry bonds | Carry-ranked |
| `real_rate` | Trade real yield changes | Duration-dependent |
| `barbell_bullet` | Barbell vs bullet preference | Curve-shape |
| `butterfly` | Butterfly trade proxy | Curve hump |

**Edge:** Yield momentum captures persistent trends in rate movements. Z-score fading exploits overreactions to macro events. Roll-down capture provides a structural carry advantage.

#### 6.2 Duration Positioning (15 strategies)

| Strategy | Description | Lookback |
|----------|-------------|----------|
| `rate_mom_N` | Rate momentum positioning | 20-60d |
| `dv01_neutral` | DV01-neutral sizing | 20d vol |
| `convexity_exp` | Long convexity when vol rising | 20d vol |
| `dur_target_N` | Target duration = N years | N/A |
| `rate_cycle` | Fed rate cycle positioning | 60d |
| `trend_dur_neutral` | Trend following with duration adj | 20/100 EMA |
| `macd_dur` | MACD with duration sizing | 12/26/9 |
| `ma_cross_F_S` | Moving average crossover | Various |

**Edge:** Duration-adjusted sizing normalizes risk across the curve. Rate cycle positioning captures the directional impact of Fed policy. Convexity exploitation benefits from vol-of-vol in rates markets.

#### 6.3 Credit Spread Strategies (15 strategies)

| Strategy | Description | Trigger |
|----------|-------------|---------|
| `credit_mr` | OAS mean reversion | Z-score > 1.5 |
| `credit_mom_N` | Credit spread momentum | N-day change |
| `credit_cycle` | Credit cycle positioning | OAS trend |
| `default_cycle` | Default cycle proxy | Spread momentum |
| `ig_hy_value` | IG vs HY relative value | OAS z-score |
| `credit_quality_rot` | Quality rotation | OAS percentile |
| `fallen_angel` | Avoidance of downgrades | OAS surge |

**Edge:** Credit spread mean reversion captures the cyclical nature of credit risk pricing. IG/HY relative value rotates into cheaper sectors. Fallen angel avoidance protects against sudden downgrades.

#### 6.4 Inflation Breakeven (10 strategies)

| Strategy | Description | Target |
|----------|-------------|--------|
| `infl_exp` | Inflation expectation trade | TIPS-specific |
| `be_mom_N` | Breakeven momentum | N-day |
| `infl_hedge` | Inflation hedge demand | TIPS vs nominal |
| `tips_nom` | TIPS vs nominal arb | Breakeven level |
| `real_yield` | Real yield trend | Duration-dependent |

**Edge:** TIPS vs nominal relative value captures mispricing in inflation expectations. Breakeven momentum follows trends in inflation sentiment.

#### 6.5 Flight to Quality (10 strategies)

| Strategy | Description | Signal |
|----------|-------------|--------|
| `vix_ftq` | VIX spike -> long Treasuries | VIX z-score |
| `safe_haven` | Safe haven demand | VIX change |
| `eq_bond_ratio` | TLT/SPY ratio mean reversion | Ratio z-score |
| `corr_break` | Bond-equity correlation breakdown | Rolling corr |
| `risk_off_rot` | Risk-off rotation | VIX + SPY |

**Edge:** VIX-based signals capture flight-to-quality flows that benefit Treasuries. TLT/SPY ratio mean reversion exploits relative mispricing between bonds and equities.

#### 6.6 Fed Policy (10 strategies)

| Strategy | Description | Input |
|----------|-------------|-------|
| `fed_dot` | Fed dot plot proxy | Rate path |
| `meeting_cycle` | FOMC cycle positioning | Fed rate trend |
| `fwd_guidance` | Forward guidance trade | Yield curve slope |
| `rate_diff` | Policy rate differential | Fed vs bond yield |
| `fed_pause` | Fed pause signal | Rate volatility |

**Edge:** Fed policy strategies exploit the predictable impact of rate cycles on bond prices. Pause signals capture the "buy the pause" effect in rates markets.

#### 6.7 Municipal Seasonality (10 strategies)

| Strategy | Description | Timing |
|----------|-------------|--------|
| `muni_seasonal` | Muni seasonal pattern | Jan/Dec long |
| `muni_supply` | Supply dynamics | Low-supply months |
| `tax_loss_rebound` | Tax-loss harvesting rebound | Jan effect |
| `muni_call` | Call risk avoidance | Fast rate drops |
| `muni_treasury` | Muni/Treasury relative value | Vol regime |

**Edge:** Municipal bonds exhibit strong seasonality due to tax-sensitive investor behavior. January rebound and supply-driven dynamics provide structural alpha.

#### 6.8 EM Debt Carry (10 strategies)

| Strategy | Description | Signal |
|----------|-------------|--------|
| `em_carry` | EM carry trade | Spread percentile |
| `em_mom_N` | EM momentum with vol filter | N-day ret + vol |
| `em_risk_prem` | EM risk premium cycle | Spread level |
| `em_dollar` | USD sensitivity proxy | Yield change |
| `em_vol_time` | EM vol timing | Vol regime |

**Edge:** EM carry captures the high yield differential over developed markets. Volatility timing reduces drawdowns during EM stress periods.

#### 6.9 Trend Following (10 strategies)

| Strategy | Description | Parameters |
|----------|-------------|------------|
| `donchian_N` | Donchian channel breakout | N-day lookback |
| `bb_trend` | Bollinger band trend | 20d/2std |
| `keltner` | Keltner channel | 20 EMA/2 ATR |
| `adx_trend` | ADX trend strength | 14d |
| `ichimoku` | Ichimoku trend | 9/26 |

#### 6.10 Mean Reversion (10 strategies)

| Strategy | Description | Parameters |
|----------|-------------|------------|
| `rsi_mr` | RSI mean reversion | 14d, 30/70 |
| `stoch_mr` | Stochastic oscillator | 14/3 |
| `cci_mr` | CCI mean reversion | 20d |
| `williams_r` | Williams %R | 14d |
| `vwap_mr` | VWAP reversion | 20d |

---

## Backtest Engine

### Duration and Convexity Accounting

The backtest engine explicitly accounts for bond-specific risk characteristics:

```
P&L = Position * (Market Return / Duration_Factor)
     + Position * (0.5 * Convexity * Yield_Change^2)
     + Position * (Coupon / 252)       [carry]
     - |Position_Change| * (TC + Slippage)
```

**Duration Factor:** Normalizes returns to an intermediate duration (6 years), so long-duration bonds (TLT) don't dominate P&L.

**Convexity Adjustment:** Adds second-order price change from yield movements, benefiting long-duration bonds when yields are volatile.

**Carry:** Daily coupon accrual provides a positive drift to all bond positions.

### Transaction Costs

| Cost Component | Value |
|----------------|-------|
| Transaction Cost | 1 bp per trade |
| Slippage | 0.5 bp per trade |
| Total Round-Trip | 3 bp |

---

## Statistical Validation

### Thresholds

| Metric | Threshold | Rationale |
|--------|-----------|-----------|
| Sharpe Ratio | >= 0.80 | Bond-adjusted (lower vol) |
| Max Drawdown | <= 10.0% | Conservative for fixed income |
| P-value | < 0.05 | Standard significance |
| BH-FDR | Rejected | Controls false discovery rate |
| Annual Return | >= 2.0% | Beat cash |
| Profit Factor | >= 1.20 | Favorable risk/reward |
| Trades/Year | >= 6 | Minimum sample size |
| PnL Sanity Cap | <= 50% | Outlier protection |

### Bootstrap Sharpe P-value

Studentized bootstrap with 10,000 resamples. Two-sided test against zero Sharpe.

### Benjamini-Hochberg FDR

Controls family-wise error rate across all strategy tests. Alpha = 0.10.

### Walk-Forward Validation

- Training: 504 days (~2 years)
- Testing: 63 days (~3 months)
- Minimum windows: 4
- Pass: Mean Sharpe > 0.3, >= 40% positive windows

---

## Ensemble Construction

### Duration-Neutral Portfolio

The ensemble targets a portfolio duration of ~5.0 years (intermediate):

```
Weight_i = 0.70 * (Strategy_Score / Total_Score)
         + 0.30 * (Duration_Neutral_Factor)

Duration_Neutral_Factor = 1 / (1 + |D_i - 5.0| / 5.0)
```

### Diversification Constraints

| Constraint | Limit |
|------------|-------|
| Max strategies | 7 |
| Min strategies | 5 |
| Max per sector | 2 |
| Max per category | 2 |
| Max per duration bucket | 2 |

### Composite Scoring

```
Score = 0.35 * Sharpe
      + 0.25 * Calmar
      + 0.20 * (1 - P_value)
      + 0.10 * WF_Sharpe_Mean
      + 0.10 * Duration_Neutral_Bonus
```

---

## System Integration

### Output Format

The engine produces two JSON files:

1. **bond_premium_signals.json** - Full engine output
2. **bond_signals_for_audit.json** - System-compatible format for findtorontoevents.ca/audit

### Signal Schema

```json
{
  "symbol": "TLT",
  "direction": "LONG",
  "confidence": 0.82,
  "allocation_pct": 18.5,
  "expected_sharpe": 1.25,
  "category": "yield_curve",
  "asset_class": "BOND",
  "grade": "A",
  "effective_duration": 17.5,
  "strategy_name": "yield_mom_20_TLT",
  "timestamp": "2026-05-20T15:00:00"
}
```

### Pipeline Stage Mapping

| Stage | Description |
|-------|-------------|
| EMIT | Strategy signal generation (110+ per symbol) |
| INGEST | Data loading and synthetic data generation |
| ACTIVE GATE | Backtest execution with duration/convexity |
| SMART GATE | Statistical validation (Sharpe, p-value, FDR) |
| HIGH CONVICTION | Walk-forward validation |
| CONSENSUS | Ensemble construction (duration-neutral) |
| OUTCOME | JSON output for audit ingestion |

---

## Asset Class Rules

| Rule | Value |
|------|-------|
| Grade | F (hard block exempt) |
| PnL WIN Threshold | 5 bp (0.0005) |
| PnL Sanity Cap | 50% |
| Blocked Symbols | None |

---

## Risk Management

### Position Limits

- Max position size: 150% of capital (for duration-neutrality)
- Individual strategy cap: 30% of portfolio
- Sector concentration limit: 40%

### Drawdown Controls

- Strategy-level max DD: 10%
- Portfolio-level target DD: < 7%
- Circuit breaker: Halt if DD > 12% over 20 days

### Duration Management

- Target portfolio duration: 5.0 +/- 1.5 years
- Long duration max: 30% allocation
- Short duration min: 20% allocation

---

## Performance Expectations

### Target Portfolio Metrics

| Metric | Target |
|--------|--------|
| Annualized Return | 4-6% |
| Volatility | 3-5% |
| Sharpe Ratio | 0.8-1.5 |
| Max Drawdown | < 8% |
| Calmar Ratio | > 0.7 |
| Win Rate | 50-60% |
| Effective Duration | 5.0 +/- 1.5 |

---

## Implementation Notes

### Dependencies

```
pandas >= 1.5.0
numpy >= 1.23.0
scipy >= 1.10.0
scikit-learn >= 1.2.0
```

### Running the Engine

```python
from bond_strategy_harness import run_bond_engine

# Full universe
output = run_bond_engine()

# Custom symbols
output = run_bond_engine(
    symbols=["TLT", "IEF", "LQD", "HYG"],
    start_date="2020-01-01",
    end_date="2026-05-20",
)
```

### Unit Tests

```python
from bond_strategy_harness import TestBondAlphaEngine
results = TestBondAlphaEngine.run_all_tests()
```

9 unit tests covering: bond universe, synthetic data generation, signal generation (110+ strategies), backtest engine, statistical validation, duration-neutral weights, bootstrap p-values, BH-FDR correction, and price change estimation.

---

## File Outputs

| File | Description |
|------|-------------|
| `/mnt/agents/output/alpha_engine/bond_strategy_harness.py` | Main engine (production-ready) |
| `/mnt/agents/output/alpha_engine/bond_premium_signals.json` | Full engine results |
| `/mnt/agents/output/alpha_engine/bond_signals_for_audit.json` | System-compatible signals |
| `/mnt/agents/output/BOND_STRATEGY_REPORT.md` | This report |
