# Commodity & Futures Multi-Strategy Alpha Engine
## Comprehensive Strategy Report

**Document ID:** COMM-ALPHA-2026-05-20-v2.0.0  
**Target System:** findtorontoevents.ca/audit  
**Pipeline Stage:** HIGH CONVICTION → CONSENSUS → OUTCOME  
**Asset Class:** COMMODITY / FUTURES (suffix `=F`)  
**Report Date:** 2026-05-20  
**Engine Version:** 2.0.0

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Architecture](#2-system-architecture)
3. [Universe Definition](#3-universe-definition)
4. [Strategy Taxonomy (150+)](#4-strategy-taxonomy)
5. [Signal Generation Framework](#5-signal-generation-framework)
6. [Backtest Engine](#6-backtest-engine)
7. [Statistical Validation](#7-statistical-validation)
8. [Ensemble Construction](#8-ensemble-construction)
9. [Integration with Audit Pipeline](#9-integration-with-audit-pipeline)
10. [Risk Management & Thresholds](#10-risk-management--thresholds)
11. [Performance Expectations](#11-performance-expectations)
12. [Operational Considerations](#12-operational-considerations)
13. [File Structure](#13-file-structure)
14. [Appendix: Strategy Manifest](#14-appendix-strategy-manifest)

---

## 1. Executive Summary

This document describes the **Commodity & Futures Multi-Strategy Alpha Engine**, a production-grade quantitative system that generates, validates, and ensembles 150+ commodity-specific trading strategies. The engine is designed for integration with the findtorontoevents.ca/audit platform's Stage 1-7 pipeline.

### Key Metrics

| Metric | Value |
|--------|-------|
| Total Strategies Generated | 150+ per commodity |
| Commodities Covered | 25 futures contracts |
| Commodity Groups | 6 (Energy, Precious Metals, Base Metals, Grains, Softs, Livestock) |
| Strategy Categories | 12 |
| Minimum Sharpe Threshold | 1.0 |
| Maximum Drawdown Limit | 20% |
| P-Value Threshold | < 0.05 |
| FDR Control (BH) | < 0.10 |
| Walk-Forward Windows | Minimum 4 |
| Ensemble Size | 5-8 strategies |

### Core Innovation

The engine addresses the **66.79% sub-5bp flicker problem** through:
- **PnL WIN threshold**: 5bp (0.0005) minimum per trade
- **PnL sanity cap**: 200% maximum return
- Statistically rigorous validation ensuring only economically meaningful strategies survive

---

## 2. System Architecture

### Pipeline Integration

```
EMIT → INGEST → ACTIVE GATE → SMART GATE → HIGH CONVICTION → CONSENSUS → OUTCOME
                              ↑______________________________↑
                                    THIS ENGINE OPERATES
                                    AT STAGES 5-6
```

### Engine Components

```
┌─────────────────────────────────────────────────────────────┐
│              COMMODITY ALPHA ENGINE v2.0.0                  │
├─────────────────────────────────────────────────────────────┤
│  DATA LAYER          │  Synthetic/Real price + COT + USD    │
├──────────────────────┼──────────────────────────────────────┤
│  SIGNAL GENERATOR    │  150+ strategies × 25 commodities    │
│                      │  (3,750+ backtests per run)          │
├──────────────────────┼──────────────────────────────────────┤
│  BACKTEST ENGINE     │  Roll costs, slippage, TC, sizing    │
├──────────────────────┼──────────────────────────────────────┤
│  VALIDATOR           │  Bootstrap p-values, BH-FDR, WF      │
├──────────────────────┼──────────────────────────────────────┤
│  ENSEMBLE BUILDER    │  Diversified, risk-weighted alloc    │
├──────────────────────┼──────────────────────────────────────┤
│  OUTPUT FORMATTER    │  JSON → audit pipeline integration   │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Universe Definition

### Commodity Coverage (25 Futures Contracts)

#### Energy (6 contracts)
| Symbol | Name | Point Value | Group |
|--------|------|-------------|-------|
| CL=F | WTI Crude Oil | $1,000 | energy |
| BZ=F | Brent Crude Oil | $1,000 | energy |
| NG=F | Natural Gas | $10,000 | energy |
| HO=F | Heating Oil | $42,000 | energy |
| RB=F | RBOB Gasoline | $42,000 | energy |
| QM=F | E-mini Crude | $500 | energy |

#### Precious Metals (5 contracts)
| Symbol | Name | Point Value | Group |
|--------|------|-------------|-------|
| GC=F | Gold | $100 | metals_precious |
| SI=F | Silver | $5,000 | metals_precious |
| PL=F | Platinum | $50 | metals_precious |
| PA=F | Palladium | $100 | metals_precious |
| MGC=F | Micro Gold | $10 | metals_precious |

#### Base Metals (2 contracts)
| Symbol | Name | Point Value | Group |
|--------|------|-------------|-------|
| HG=F | Copper | $25,000 | metals_base |
| ALI=F | Aluminum | $25 | metals_base |

#### Agriculture - Grains (7 contracts)
| Symbol | Name | Point Value | Group |
|--------|------|-------------|-------|
| ZC=F | Corn | $50 | agriculture_grains |
| ZS=F | Soybeans | $50 | agriculture_grains |
| ZW=F | Wheat | $50 | agriculture_grains |
| ZM=F | Soybean Meal | $100 | agriculture_grains |
| ZL=F | Soybean Oil | $600 | agriculture_grains |
| XK=F | Wheat KCBT | $50 | agriculture_grains |

#### Agriculture - Softs (3 contracts)
| Symbol | Name | Point Value | Group |
|--------|------|-------------|-------|
| CC=F | Cocoa | $10 | agriculture_softs |
| KC=F | Coffee | $375 | agriculture_softs |
| SB=F | Sugar | $1,120 | agriculture_softs |

#### Livestock (3 contracts)
| Symbol | Name | Point Value | Group |
|--------|------|-------------|-------|
| LE=F | Live Cattle | $400 | livestock |
| HE=F | Lean Hogs | $400 | livestock |
| GF=F | Feeder Cattle | $500 | livestock |

### Blacklist
- CT=F (Cotton - excluded per system rules)
- GLD (Gold ETF - excluded via ETF blacklist)

---

## 4. Strategy Taxonomy

### Overview: 150+ Strategies Across 12 Categories

| Category | Count | Description |
|----------|-------|-------------|
| Trend Following | 20 | Donchian, ATR, MACD, SuperTrend, ADX, Parabolic SAR, Triple MA, Keltner, Ichimoku |
| Term Structure / Carry | 15 | Backwardation carry, basis momentum, curve roll yield, contango rollup |
| Seasonality | 15 | Monthly patterns, day-of-week, harvest cycles, Chinese New Year, winter heating |
| COT Positioning | 12 | Commercial hedger extremes, non-commercial fade, spread signals |
| Breakout | 15 | Volatility expansion, Bollinger Band, range breakout, momentum ignition |
| Inter-Market Spread | 12 | Gold/silver, WTI/Brent, crack spread, soybean crush |
| Mean Reversion | 12 | RSI, stochastic, CCI, Williams %R, VWAP, 2-day H/L |
| USD Correlation | 10 | Inverse correlation, momentum lead, DXY levels |
| Volatility | 10 | Vol targeting, regime switching, ATR sizing, risk parity |
| Inventory/Data | 8 | Inventory shocks, trend following, EIA/USDA-style signals |
| Multi-Factor | 10 | Trend+carry composites, seasonal+trend, multi-factor scores |
| Momentum | 12 | Time-series (1M-12M), cross-sectional, acceleration, skip-mom |

---

## 5. Signal Generation Framework

### 5.1 Trend Following (20 Strategies)

The trend following module implements robust trend-capture techniques adapted for commodity futures:

**Donchian Channel Breakout** (8 variants: 10/15/20/30/40/50/75/100-day)
- Long when price breaks above N-day high
- Short when price breaks below N-day low
- Proven in commodity markets due to sustained trending behavior

**ATR-Based Trend** (3 variants)
- Position scaled by distance from moving average normalized by ATR
- Risk-adjusted signal prevents oversized positions in volatile periods

**SuperTrend** (1 variant)
- Dynamic support/resistance using ATR bands
- Particularly effective in energy and metals with strong trending

**Additional trend signals:**
- MACD trend (3 variants with different fast/slow/signal periods)
- ADX trend strength (directional movement index)
- Parabolic SAR
- Triple moving average alignment
- Keltner channel breakout
- Ichimoku cloud trend
- Linear regression slope (2 variants: 50, 100 period)

### 5.2 Term Structure / Carry (15 Strategies)

Commodity futures have unique term structure dynamics:

**Backwardation Carry**
- Long commodities in backwardation (near > far = positive roll yield)
- Short commodities in contango (negative roll yield)
- Core driver: convenience yield theory (Brennan-Schwartz, Gabillon)

**Basis Momentum** (4 variants)
- Trade strengthening backwardation or weakening contango
- Rolling basis signals capture changing inventory conditions

**Curve Roll Yield** (3 variants)
- Capture slope changes in futures curve
- Short tenor vs long tenor moving average spreads

### 5.3 Seasonality (15 Strategies)

Commodities exhibit strong seasonal patterns driven by physical supply/demand:

| Pattern | Commodity | Months | Rationale |
|---------|-----------|--------|-----------|
| New Year Gold | GC=F, MGC=F | Jan-Mar | Physical demand, Chinese New Year |
| Summer Driving | CL=F, RB=F | May-Aug | Peak gasoline demand |
| Winter Heating | NG=F, HO=F | Oct-Mar | Cold weather demand |
| Planting Rally | ZC=F, ZS=F, ZW=F | Mar-Jun | Weather risk premium |
| Harvest Pressure | ZC=F, ZS=F, ZW=F | Sep-Nov | Supply glut |
| Harvest Fade | Softs | Variable | Counter-seasonal mean reversion |

### 5.4 COT Positioning (12 Strategies)

Commitment of Traders data provides insight into positioning extremes:

**Commercial Hedger Extreme** (4 variants: z=1.0, 1.5, 2.0, 2.5, 3.0)
- Fade commercial extremes (they hedge at extremes = smart money)
- Commercial net short extreme = bullish signal

**Non-Commercial (Speculator) Fade** (3 variants)
- Fade speculator positioning (dumb money indicator)
- Speculators long extreme = bearish contrarian signal

**COT Spread** (2 variants)
- Commercial vs non-commercial positioning divergence
- Smart money vs dumb money spread

### 5.5 Breakout / Volatility (15 Strategies)

**Volatility Expansion Breakout** (3 variants)
- Enter on ATR expansion beyond recent range
- Captures commodity-specific volatility clustering

**Bollinger Band Breakout** (4 variants)
- 20/30-period with 1.0/2.0/2.5 standard deviations
- Band squeeze detection for pre-breakout positioning

**Range Breakout** (5 variants: 10/20/40/60/100-day)
- Classic N-day high/low breakout
- Adapted for different commodity volatility regimes

### 5.6 Inter-Market Spreads (12 Strategies)

**Gold/Silver Ratio** (GC=F vs SI=F)
- Mean reversion of precious metals ratio
- Z-score based entry/exit

**WTI/Brent Spread** (CL=F vs BZ=F)
- Geographic arbitrage signal
- Quality and transport cost differentials

**Crack Spread** (CL=F vs RB=F + HO=F)
- Refining margin proxy
- 3:2:1 standard ratio

**Soybean Crush Spread** (ZS=F vs ZM=F + ZL=F)
- Processing margin signal
- Agricultural inter-commodity arbitrage

### 5.7 Mean Reversion (12 Strategies)

- RSI mean reversion (3 variants: 10/14/21 period)
- Stochastic oscillator (14,3)
- Commodity Channel Index (20, 50 period)
- Williams %R (14, 20 period)
- Distance from VWAP (20, 50 period)
- 2-day / 3-day high-low reversion

### 5.8 USD Correlation (10 Strategies)

Dollar-denominated commodities exhibit inverse USD correlation:

- Inverse correlation (60/30/90/100/252-day windows)
- USD momentum lead (1-day, 5-day lag)
- DXY overbought/oversold levels (z-score based)
- USD trend regime identification

### 5.9 Volatility Strategies (10 Strategies)

- Volatility targeting (10%, 15%, 20%, 25% targets)
- Volatility regime switching (trend in low vol, MR in high vol)
- ATR-based position sizing (14, 30 period)
- Risk parity signal weighting

### 5.10 Inventory / Data-Driven (8 Strategies)

- Inventory shock (z-score based, 1.5/2.0/2.5 thresholds)
- Inventory trend following
- Build/draw directional signals
- EIA petroleum / USDA crop report style signals

### 5.11 Multi-Factor Composite (10 Strategies)

- Trend + Carry combination (60/40 weighting)
- Seasonal + Trend combination (70/30 weighting)
- Multi-factor scoring (momentum + carry + volatility adj)
- Risk parity momentum weighting
- Enhanced carry variants

### 5.12 Momentum (12 Strategies)

- Time-series momentum (1M/2M/3M/6M/9M/12M lookbacks)
- Cross-sectional momentum (63-day rank)
- Momentum acceleration (momentum of momentum)
- 12-month minus 1-month (skip-month momentum)
- Exponentially weighted momentum (50, 100 span)

---

## 6. Backtest Engine

### Transaction Cost Model

| Cost Component | Value | Notes |
|----------------|-------|-------|
| Commission | 2bp per trade | Futures round-trip |
| Slippage | 1bp per trade | Market impact estimate |
| Roll Cost | Symbol-specific | Quarterly roll (see table) |
| Total per trade | ~3bp + roll | Conservative estimate |

### Roll Cost Assumptions (% per quarter)

| Symbol | Roll Cost | Symbol | Roll Cost |
|--------|-----------|--------|-----------|
| CL=F | 0.15% | GC=F | 0.03% |
| BZ=F | 0.12% | SI=F | 0.08% |
| NG=F | 0.80% | ZC=F | 0.12% |
| HO=F | 0.18% | ZS=F | 0.15% |
| RB=F | 0.20% | ZW=F | 0.12% |

Roll costs are applied daily as a continuous drag proportional to holding period.

### Backtest Formula

```
Strategy Return(t) = Signal(t-1) × Market Return(t) 
                     - |Signal(t) - Signal(t-1)| × (TC + Slippage)
                     - |Signal(t-1)| × Roll_Cost_Daily
```

---

## 7. Statistical Validation

### 7.1 Validation Pipeline

```
┌────────────────────────────────────────────────────────────┐
│                    VALIDATION PIPELINE                      │
├────────────────────────────────────────────────────────────┤
│ 1. Minimum Sharpe Ratio      │  ≥ 1.0                      │
│ 2. Maximum Drawdown          │  ≤ 20%                      │
│ 3. Minimum Annual Return     │  ≥ 5%                       │
│ 4. Bootstrap P-Value         │  < 0.05                     │
│ 5. BH-FDR Correction         │  q < 0.10                   │
│ 6. Walk-Forward Validation   │  Pass (mean Sharpe > 0.5)   │
│ 7. Minimum Trades            │  ≥ 12 per year              │
│ 8. Profit Factor             │  ≥ 1.3                      │
│ 9. PnL WIN Threshold         │  ≥ 5bp per trade            │
│ 10. Sanity Cap               │  ≤ 200% total return        │
└────────────────────────────────────────────────────────────┘
```

### 7.2 Bootstrap Sharpe Significance

For each strategy:
1. Compute observed Sharpe ratio from daily returns
2. Resample returns with replacement 1,000 times
3. Compute Sharpe for each bootstrap sample
4. P-value = fraction of bootstrap Sharpes ≤ 0

### 7.3 Benjamini-Hochberg FDR Control

1. Collect all bootstrap p-values across strategies
2. Sort p-values ascending
3. Find largest k where p_k ≤ (k/m) × α (α = 0.10)
4. Reject null for all p-values up to k

### 7.4 Walk-Forward Cross-Validation

```
Parameters:
  Training window:  504 days (~2 years)
  Testing window:   126 days (~6 months)
  Minimum windows:  4
  Pass criteria:    Mean Sharpe > 0.5 AND ≥50% windows positive
```

The walk-forward test ensures strategies are not overfit to a single market regime.

---

## 8. Ensemble Construction

### 8.1 Selection Criteria

The ensemble constructor uses a greedy algorithm with diversity constraints:

1. **Score strategies** by composite metric:
   ```
   Score = 0.4 × Sharpe + 0.3 × Calmar + 0.2 × (1 - p-value) + 0.1 × WF_Sharpe
   ```

2. **Greedy selection** with diversity enforcement:
   - Maximum 2 strategies per commodity group
   - Maximum 2 strategies per strategy category
   - Target 5-8 strategies total

3. **Risk-parity allocation** proportional to composite score

### 8.2 Diversification Requirements

| Constraint | Limit |
|------------|-------|
| Max per commodity group | 2 |
| Max per strategy category | 2 |
| Minimum commodity groups | 3 |
| Target ensemble size | 5-8 |

---

## 9. Integration with Audit Pipeline

### 9.1 Output Format

The engine produces two JSON files:

**1. Full Output** (`commodity_alpha_output.json`)
- Complete strategy results with all metrics
- Equity curves and trade logs
- Statistical validation details

**2. Audit Format** (`commodity_alpha_output.audit.json`)
- Stage 7 compatible format
- Simplified pick list with allocations
- Direct integration with audit endpoint

### 9.2 Pipeline Stage Mapping

| Engine Component | Pipeline Stage |
|------------------|----------------|
| Strategy Generation | EMIT / INGEST |
| Signal Validation | ACTIVE GATE |
| Backtest Execution | SMART GATE |
| Statistical Validation | HIGH CONVICTION |
| Ensemble Construction | CONSENSUS |
| JSON Output | OUTCOME |

### 9.3 Audit-Compatible JSON Structure

```json
{
  "stage": "CONSENSUS",
  "timestamp": "2026-05-20T00:00:00Z",
  "asset_class": "COMMODITY",
  "symbol_suffix": "=F",
  "ensemble_picks": [
    {
      "symbol": "GC=F",
      "direction": "long",
      "allocation_pct": 25.0,
      "expected_sharpe": 1.35,
      "strategy_id": "COMM_0001",
      "category": "seasonality",
      "win_threshold_bp": 5,
      "sanity_cap_pct": 200
    }
  ],
  "group_exposures": {
    "metals_precious": 50.0,
    "energy": 50.0
  }
}
```

---

## 10. Risk Management & Thresholds

### 10.1 System Rules Integration

| Rule | Value | Source |
|------|-------|--------|
| Symbol suffix | `=F` | Asset class rule |
| Category | "commodity" or "futures" | Futures class |
| Blacklist | CT=F, GLD | Commodity + ETF blacklist |
| Source blocklist | forex_copy_trader | PF 0.31, n=46 |
| PnL WIN threshold | 5bp (0.0005) | Flicker fix |
| PnL sanity cap | 200% | Cap rule |

### 10.2 Position-Level Risk

- Maximum single position: 2x leverage equivalent
- ATR-based sizing for risk control
- Volatility targeting at 15% annualized
- Maximum drawdown halt at 20%

### 10.3 Flicker Fix (66.79% Sub-5bp Issue)

The 5bp minimum win threshold eliminates resolver flicker:
- Strategies with avg trade return < 5bp are rejected
- Prevents micro-profits that create noise in the audit system
- Ensures only economically significant trades are reported

---

## 11. Performance Expectations

### 11.1 Target Metrics (Per Strategy)

| Metric | Target | Minimum |
|--------|--------|---------|
| Annualized Return | 12-20% | 5% |
| Sharpe Ratio | 1.2-2.0 | 1.0 |
| Max Drawdown | -10% to -15% | -20% |
| Win Rate | 45-60% | 40% |
| Profit Factor | 1.4-2.0 | 1.3 |
| Expectancy | 2-5bp | 1bp |

### 11.2 Expected Ensemble Performance

| Metric | Expected |
|--------|----------|
| Annualized Return | 10-15% |
| Sharpe Ratio | 1.3-1.8 |
| Max Drawdown | -12% to -18% |
| Diversification Ratio | 1.5-2.0 |

---

## 12. Operational Considerations

### 12.1 Data Requirements

| Data Type | Frequency | Source |
|-----------|-----------|--------|
| Price data (OHLCV) | Daily | Exchange/feed |
| COT report | Weekly | CFTC |
| Inventory data | Weekly | EIA/USDA |
| USD index | Daily | ICE/feed |
| Term structure | Daily | Exchange |

### 12.2 Execution Frequency

- **Signal generation:** Daily after market close
- **Rebalancing:** Weekly or on signal change
- **Roll execution:** Quarterly, 5 days before expiry
- **Ensemble review:** Monthly

### 12.3 Computational Requirements

| Operation | Estimated Time | Parallelizable |
|-----------|---------------|----------------|
| Data loading | 5-10s | No |
| Signal generation (150×25) | 30-60s | Yes |
| Backtesting (3,750 runs) | 60-120s | Yes |
| Bootstrap validation | 120-300s | Yes |
| Walk-forward tests | 300-600s | Yes |
| Ensemble construction | 1-2s | No |
| **Total** | **~10-15 min** | **Yes** |

---

## 13. File Structure

```
/mnt/agents/output/
├── alpha_engine/
│   └── commodity_strategy_harness.py    # Main engine (1500+ lines)
├── commodity_alpha_output.json           # Full engine output
├── commodity_alpha_output.audit.json    # Audit pipeline format
└── COMMODITY_STRATEGY_REPORT.md         # This document
```

### 13.1 Engine File Structure

```
commodity_strategy_harness.py
├── SECTION 1: Constants & Configuration
├── SECTION 2: Data Structures (dataclasses)
├── SECTION 3: Utility Functions (Sharpe, FDR, WF)
├── SECTION 4: Data Generation (Synthetic)
├── SECTION 5: Signal Generators (150+ strategies)
│   ├── 5.1 Trend Following (20)
│   ├── 5.2 Term Structure / Carry (15)
│   ├── 5.3 Seasonality (15)
│   ├── 5.4 COT Positioning (12)
│   ├── 5.5 Breakout (15)
│   ├── 5.6 Inter-Market Spreads (12)
│   ├── 5.7 Mean Reversion (12)
│   ├── 5.8 USD Correlation (10)
│   ├── 5.9 Volatility (10)
│   ├── 5.10 Inventory/Data (8)
│   ├── 5.11 Multi-Factor (10)
│   └── 5.12 Momentum (12)
├── SECTION 6: Backtest Engine
├── SECTION 7: Statistical Validation
├── SECTION 8: Ensemble Constructor
├── SECTION 9: Main Alpha Engine
├── SECTION 10: Integration Helpers
├── SECTION 11: Unit Tests (10 tests)
└── SECTION 12: Main Execution
```

---

## 14. Appendix: Strategy Manifest

### Complete Strategy List by Category

#### Trend Following (20 strategies)
```
donchian_10, donchian_20, donchian_30, donchian_50, donchian_75, donchian_100
atr_trend (50,2.0), atr_trend_30 (30,1.5), atr_trend_100 (100,2.5)
macd_trend (12,26,9), macd_fast (8,21,5), macd_slow (19,39,9)
supertrend (10, 3.0)
adx_trend (14)
parabolic_sar (0.02, 0.2)
triple_ma (10,30,50)
keltner_break (20,10,2.0)
ichimoku
lr_trend (50), lr_trend_100
```

#### Term Structure / Carry (15 strategies)
```
backwardation_carry
basis_mom_10, basis_mom_20, basis_mom_40, basis_mom_60
curve_roll (20,60), curve_roll_30_90, curve_roll_10_30
contango_rollup
term_rank
carry_trend_50, carry_trend_100, pure_carry, roll_yield_capture
```

#### Seasonality (15 strategies)
```
seasonal_window, seasonal_fade, monthly_pattern, dow_seasonal
seasonal_trend, q1_seasonal, q4_seasonal, harvest_pressure
planting_rally, winter_heating, summer_driving
chinese_new_year, post_harvest, new_year_gold, shoulder_month
```

#### COT Positioning (12 strategies)
```
cot_commercial_1.0, 1.5, 2.0, 2.5, 3.0
cot_noncomm_1.5, 2.0, 3.0
cot_spread, cot_extreme_combined, cot_oi_signal, cot_smart_money
```

#### Breakout (15 strategies)
```
vol_breakout, vol_breakout_fast, vol_breakout_slow
bb_breakout (20,2), bb_breakout_30 (30,2.5), bb_1std, bb_squeeze
range_break_10, 20, 40, 60, 100
month_orb, mom_ignition, mom_ignition_15
```

#### Inter-Market Spreads (up to 12 strategies)
```
gold_silver_ratio (GC vs SI)
wti_brent_spread (CL vs BZ)
crack_spread (CL vs RB+HO)
crush_spread (ZS vs ZM+ZL)
synthetic_spread_mr, spread_momentum
```

#### Mean Reversion (12 strategies)
```
rsi_mr (14,70,30), rsi_mr_10 (10,75,25), rsi_mr_21 (21,65,35)
stoch_mr (14,3)
cci_mr (50), cci_mr_20
williams_r (14), williams_r_20
vwap_mr (20), vwap_mr_50
2day_hl_mr, 3day_hl_mr
```

#### USD Correlation (10 strategies)
```
usd_inverse_corr (60,30,90,100,252)
usd_mom_lead, usd_mom_lead_5
dxy_level, dxy_zscore
usd_trend, usd_strong_inv, usd_vol_regime
```

#### Volatility (10 strategies)
```
vol_target (10%,15%,20%,25%)
vol_regime, vol_regime_fast, vol_regime_slow
atr_sizing (14,30), risk_parity_signal
```

#### Inventory/Data (8 strategies)
```
inventory_shock (1.5,2.0,2.5)
inventory_trend, inv_trend_fast
inv_build, inv_draw, inv_combined
```

#### Multi-Factor (10 strategies)
```
composite_trend_carry, composite_seasonal_trend
multi_factor, multi_factor_2, multi_factor_3
risk_parity_signal, trend_season_carry
factor_mom, enhanced_carry, vol_adj_momentum
```

#### Momentum (12 strategies)
```
tsmom_1m, tsmom_2m, tsmom_3m, tsmom_6m, tsmom_9m, tsmom_12m
xsmom (63), mom_accel, mom_accel_fast
skip_mom (12m-1m), ewm_mom (50,100)
```

---

## Glossary

| Term | Definition |
|------|------------|
| ATR | Average True Range - volatility measure |
| BH-FDR | Benjamini-Hochberg False Discovery Rate |
| COT | Commitment of Traders (CFTC report) |
| Contango | Forward price > spot price (negative roll yield) |
| Backwardation | Forward price < spot price (positive roll yield) |
| Crack Spread | Refining margin (products - crude) |
| Crush Spread | Soybean processing margin |
| PnL | Profit and Loss |
| bp | Basis point (0.01%) |
| WF | Walk-Forward (cross-validation) |
| FDR | False Discovery Rate |

---

*End of Report*
*Generated: 2026-05-20*
*Engine Version: 2.0.0*
