# 03_BACKTEST_RESULTS — Backtest & Research Documentation

**Date:** 2026-11-15T07:44Z UTC  
**Purpose:** Document what was backtested, researched, and how results were obtained.

---

## 1. Simulation Backtest (This Worktree)

### Script
`01_simulation_backtest.py` (referenced from `2026-11-15_AM_profitability_plan/parallel_agent_worktree/01_asset_class_plans/`)

### Data Source
- yfinance (Yahoo Finance adjusted close, dividends + splits)
- 7 equity ETFs: SPY, QQQ, IWM, DIA, VTI, EFA, EEM
- 5 crypto symbols: BTC-USD, ETH-USD, SOL-USD, XRP-USD, ADA-USD
- Period: 2020-01-01 → 2025-12-31 (~6 years, 1,500-2,200 daily bars per symbol)

### Cost Model
- Commission: 1 bps per side
- Slippage: 1 bps per side
- Round-trip cost: 4 bps total
- Applied to every trade (entry + exit)

### Strategies Tested

| # | Strategy | Type | Asset Class | Parameters |
|---|----------|------|-------------|------------|
| 1 | RSI(2) Mean Reversion | Mean reversion / swing | Equity | RSI(2)<10 & close>EMA(200); TP=2×ATR, SL=1×ATR, max 10 bars, LONG only |
| 2 | Dual MA Crossover | Trend following | Equity | MA(50)×MA(200) crossover; max 60 bars, LONG only |
| 3 | Bollinger Mean Reversion | Mean reversion / swing | Equity | Close<lower BB(20,2)+RSI(14)<30; exit at mid BB; max 10 bars, LONG only |
| 4 | Donchian Breakout | Trend following | Crypto | 20-day high breakout entry; sell below 20-day low | ATR-based TP/SL |
| 5 | EMA Trend Crossover | Trend following | Crypto | EMA(20)×EMA(50) crossover | ATR-based TP/SL |

### Walk-Forward Design
- 5 folds, expanding window
- 1 year train / 1 year test per fold
- Fixed start date (2020-01-01), expanding train window
- Parameters fixed before testing (no optimization)

### Results File
`01_asset_class_plans/simulation_results_2026-11-15.json` (referenced from `2026-11-15_AM_profitability_plan/`)

### Key Result
**0/37 strategy×symbol combos passed all 7 money-ready gates.**

---

## 2. Parallel Simulation (Buffy/Codebuff)

**Location:** `2026-11-15_1233AM_winning-strategies/buffy/10_simulations/`

### Script
`tools/sim_path_forward.py`

### Data Source
- Yahoo adjusted close (dividends + splits)
- 2004-12 → 2026-11 monthly; 2001-01 → 2026-11 daily; BTC 2014-09 → 2026-11
- Real T-bill cash (^IRX)

### Cost Model
- 6 bps/side equity
- 15 bps/side crypto
- Cash earns real T-bill rate
- 2× cost stress test applied

### Strategies Tested (8 pre-registered, no parameter search)

| Strategy | Type | Result |
|----------|------|--------|
| BH_SPY | Buy-and-hold beta core | PROFITABLE (10.76% CAGR, DSR 0.99) |
| SIXTY_FORTY | 60/40 portfolio | BEATEN BY BENCHMARK (-3.03%/yr) |
| FABER10_SPY | 10-month SMA overlay | RISK REDUCTION ONLY (-0.09%/yr excess, -21.8% vs -50.8% MDD) |
| DUALMOM_2 | Dual momentum (2 asset) | REJECTED (-2.57%/yr) |
| DUALMOM_3 | Dual momentum (3 asset) | REJECTED (OOS -6.34%, regime overfit) |
| RSI2_SPY | RSI(2) swing rule | REJECTED (0.21% CAGR, DSR 0.00) |
| BTC_BH | BTC buy-and-hold | BETA, NOT SKILL (51% CAGR vs SPY) |
| BTC_TREND200 | BTC 200-day trend | PROMISING BUT UNPROVEN (DSR 0.84) |

### Key Result
**0 active rules beat their matched-exposure benchmark.** Only beta core is profitable.

---

## 3. Prior Audit Findings (final_v3/final_v4)

**Location:** `final_v3/quant-audit-2026-11-14/` and `final_v4/flaxen-hair_2026-11-14T2304/`

### Key Findings

| Finding | Value |
|---------|-------|
| 0/23 hypotheses | across 4 protocol versions survived clean out-of-sample, effective-N, capital, and execution gates |
| Information coefficient | ≈ 0 |
| Win rates | near 40% |
| All 9 asset classes | return `sizing_allowed: false` |
| 0/166 strategy×class×direction cells | pass all money-ready gates |
| CRYPCO expectancy | -5.86%, CI [-4.96%, -4.38%] — statistically significant NEGATIVE |
| Overall closed-pick WR | 45.6% (below 50% across all classes) |
| EXPIRED→WON mislabeling | dashboard CRYPCO Smart Picks 78.93% vs DB raw 39.38% |
| All 3,500 closed rows | missing valid `resolution_method` |

### Fixes Applied (D-1 through D-10)

| Fix | Description | Status |
|-----|-------------|--------|
| D-1 | Fix Horizon Harness | NOT yet applied (MIN_WINDOWS=4 not enforced) |
| D-2 | Fix Gap-Fill Pricing | Applied in `universal_pick_resolver.py` |
| D-3 | Fix Per-Class Cost Gate Integration | Applied in `hc_gates_python.py` |
| D-4 | Fix After-Cost Net Per-Trade | Applied in `dashboard_generator.py` |
| D-5 | Add SubQ Comparison | Not executed |
| D-6 | Walk-Forward with Purged/Embargoed Windows | Not implemented |
| D-7 | Block-Bootstrap CI on Net Expectancy | Not implemented |
| D-8 | DSR with Cumulative Trial Count | Not implemented |
| D-9 | PBO Calculation | Not implemented |
| D-10 | SPA Test | Not implemented |

---

## 4. Research Methodology

### Pre-Registration Protocol
- All strategies pre-registered before backtesting (no parameter search)
- Strategy registry recorded in script
- Adding a strategy invalidates DSR and must be recorded as a new trial

### Statistical Gates Applied

| Gate | Threshold | Purpose |
|------|-----------|---------|
| Profit Factor | ≥ 1.15 | Gross profits exceed gross losses by 15%+ |
| Win Rate | ≥ 50% | Majority of trades profitable |
| Sharpe Ratio | ≥ 1.0 | Positive risk-adjusted return |
| DSR | ≥ 0.95 | Confidence Sharpe > 0 after multiple testing |
| PBO | ≤ 0.10 | Low probability of backtest overfitting |
| Max Drawdown | < 15% | Capital preservation |
| Trades | ≥ 50 | Sufficient sample for inference |

### Data Quality Checks
- PnL=0% validation against real market data
- Blank-field flags (entry, exit, TP/SL, status, resolution_method)
- Open positions >72h detection
- Cost leakage detection
- Cross-ledger reconciliation (money_ready_verdict vs pf_registry)

---

## 5. What Was NOT Tested

| Asset Class/Strategy | Reason Not Tested |
|---------------------|-------------------|
| ETF active strategies | Cohort mismatch (official PF 0.022 vs registry 1.788), zero live data |
| Forex strategies | On mutation-before-kill protocol, historical PF 0.27 |
| Commodity strategies | COT gate failed 4/4, 422% cost ratio, low n |
| Bond strategies | n=1 official, n=35 registry, no data pipeline |
| Mutual funds as active picks | Structurally incompatible (daily NAV, no intraday TP/SL) |
| Meme/Penny Stock | n=10/n=1, toxic |
| Day trading / scalping | Costs dominate, data granularity insufficient, multiple testing penalty |

---

## 6. Reproducibility

To reproduce my simulation:
```bash
python3 2026-11-15_AM_profitability_plan/parallel_agent_worktree/01_asset_class_plans/run_simulation_backtest.py
```

To reproduce Buffy's backtest:
```bash
python3 tools/sim_path_forward.py
```

Both use yfinance data and produce JSON output with full statistics.

---

## 7. Summary of All Backtest Results

| Asset Class | Best Strategy | Best WR | Best PF | Best Sharpe | Best DSR | Best PBO | Gates Passed |
|-------------|---------------|---------|---------|-------------|----------|----------|--------------|
| EQUITY | QQQ DualMA | 100.0% (n=2) | 999.0 (artifact) | +3.25 | 0.000 | 0.999 | 4/7 (artifact) |
| CRYPTO | ADA-USD EMA Trend | 46.67% | 0.889 | -0.304 | 0.383 | 0.979 | 4/7 |
| ETF | QQQ Faber Tactical | 0.0% | 0.00 | N/A | N/A | N/A | 0/7 |
| FOREX | multi_asset_copytrader | 13.64% | 0.6596 | N/A | N/A | N/A | 0/7 |
| FUTURES | multi_asset_copytrader | 0.00% | undefined | N/A | N/A | N/A | 0/7 |
| BOND | bond_duration_rotation | 0.00% | 0.000 | N/A | N/A | N/A | 0/7 |
| COMMODITY | multi_asset_copytrader | 0.00% | undefined | N/A | N/A | N/A | 0/7 |
| Mutual Funds | None | N/A | N/A | N/A | N/A | N/A | Not registered |
| PENNY_STOCK | skyrocket_detector | 0.00% | undefined | N/A | N/A | N/A | Not wired to production |

**Bottom line: No strategy passes all 7 money-ready gates. No asset class is proven profitable.**
