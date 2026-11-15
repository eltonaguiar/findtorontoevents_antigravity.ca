# 04_ELIMINATION_LOG — Strategies and Asset Classes Eliminated

**Date:** 2026-11-15T07:44Z UTC  
**Purpose:** Document how and why each strategy and asset class was eliminated from consideration.

---

## Elimination Framework

A strategy/asset class is eliminated when it fails any of the following:

| Elimination Criterion | Threshold |
|----------------------|-----------|
| Negative expectancy after costs | Net PnL < 0 |
| Win rate too low | WR < 35% (forward test) / < 50% (money-ready gate) |
| Profit factor too low | PF < 1.15 (money-ready gate) |
| Sharpe insufficient | Sharpe < 1.0 (money-ready gate) |
| DSR insufficient | DSR < 0.95 (money-ready gate) |
| PBO too high | PBO > 0.10 (money-ready gate) |
| Max drawdown excessive | DD > 15% (money-ready gate) |
| Insufficient sample | n < 50 (money-ready gate) |
| Structural incompatibility | No viable execution path (e.g., mutual funds daily NAV) |
| Insufficient data | n < 100 (statistical inference floor) |
| Data quality failure | Cohort mismatch, missing resolution_method, stale prices |
| Cost dominance | Costs > 200% of gross profit |
| Protocol block | Mutation-before-kill, keep blocked, not registered |

---

## Asset-Class Elimination Log

### EQUITY — RESEARCH SLOT ONLY (NOT ELIMINATED, NOT DEPLOYED)

| Strategy | Elimination Reason | Gates Passed | Status |
|----------|-------------------|--------------|--------|
| RSI(2) Mean Reversion | Negative expectancy (-118% to -186%), WR 0-17%, Sharpe -8.5 to -18.5, DSR=0.000 | 2/7 | ELIMINATED |
| Dual MA Crossover | 2-5 trades over 5 years, PF=999.0 (statistical artifact), DSR=0.000, PBO=0.999 | 4/7* | ELIMINATED (artifact) |
| Bollinger Mean Reversion | Negative expectancy (-17% to -33%), Sharpe -1.2 to -2.0 | 2-3/7 | ELIMINATED |
| CTA Golden Cross (SPY/QQQ) | SPY gate FAILED (t=1.05, median excess -0.57%), all LONG bias | 4/7* | ELIMINATED |

\* QQQ/EFA DualMA show 4/7 but are statistical artifacts (2-3 trades, PF=999, DSR=0, PBO=0.999).

**Asset class status:** Not eliminated — kept as research slot. But zero strategies are deployable.

**Reason:** EQUITY is the only class with a pre-registered SPY benchmark path, but it FAILED that gate (t=1.05 < 2.0, median excess -0.57%, beat-SPY rate 45.53%). No equity strategy has demonstrated alpha beyond beta.

---

### CRYPTO — BLOCKED (Negative Expectancy)

| Strategy | Elimination Reason | Gates Passed | Status |
|----------|-------------------|--------------|--------|
| EMA Trend Crossover | Negative expectancy (-18% to -130%), Max DD up to 153%, Sharpe negative on 4/5 symbols, DSR < 0.4, PBO > 0.97 | 1-4/7 | ELIMINATED |
| Donchian Breakout | Zero trades on all 5 crypto symbols — strategy never fired | 0/7 | ELIMINATED |
| KIMI Inverse Scanner | TP 2% / SL 3% (R:R 0.67), 28 picks generated, 0 resolved | N/A | ELIMINATED |
| KIMI Baby Strategies (5) | Not tested on real picks | N/A | ELIMINATED |
| Genome Top-3 | All Grade F, conviction 0.0 | N/A | ELIMINATED |
| Prediction Market Consensus | PBO=0.603 >> 0.10 gate, pick_count=0, 0 resolved | N/A | BLOCKED |

**Asset class status:** BLOCKED. CRYPCO expectancy -5.86%, CI [-4.96%, -4.38%] — statistically significant NEGATIVE.

---

### ETF — BLOCKED (Cohort Mismatch + Zero Live Picks)

| Strategy | Elimination Reason | Status |
|----------|-------------------|--------|
| All ETF active strategies | Cohort mismatch (official PF 0.022 vs registry PF 1.788), zero live picks, 267% of average PnL is cost | BLOCKED |
| etf_faber_tactical | 1 closed pick (QQQ, LOST at -0.01%), WR=0%, PF=0.00 | ELIMINATED |
| etf_dual_momentum | Not tested on real picks | NOT TESTED |
| etf_sector_momentum | Not tested on real picks | NOT TESTED |
| etf_risk_parity_rotation | Not tested on real picks | NOT TESTED |
| etf_trend_following | Not tested on real picks | NOT TESTED |
| etf_rsi2_pullback | Not tested on real picks | NOT TESTED |
| etf_sector_dual_momentum | Not tested on real picks | NOT TESTED |
| etf_cross_sectional_momentum | Not tested on real picks | NOT TESTED |

**Asset class status:** BLOCKED. Zero live picks, cohort mismatch, no strategy passes any gate.

---

### MUTUAL FUNDS — NOT REGISTERED AS ACTIVE PICK CLASS

| Strategy | Elimination Reason | Status |
|----------|-------------------|--------|
| Mutual funds as active picks | Structurally incompatible: daily NAV only, no intraday TP/SL, next-NAV execution, load/12b-1 costs, frequent-trading limits | ELIMINATED (as active picks) |
| Mutual funds as passive allocation | NOT eliminated — recommended for passive core allocation | RECOMMENDED |

**Asset class status:** Zero production infrastructure. Not registered as an asset class (class id = -1).

**Valid as:** Passive core allocation (60% US equity, 20% international, 20% bonds/T-bills, ER ≤0.09%, turnover ≤20%, track record ≥10 years, no load, no 12b-1).

---

### FOREX — BLOCKED (Negative Expectancy)

| Strategy | Elimination Reason | Status |
|----------|-------------------|--------|
| All Forex strategies | Historical PF 0.27 (sub-floor), recent PF 0.85, WR 32-40%, high n but negative expectancy, MDD 82% | ON MUTATION PROTOCOL |
| multi_asset_copytrader (FOREX) | 160 picks, WR 12.5% (win/total), PF 0.6596 | BLOCKED |

**Asset class status:** BLOCKED. Negative expectancy, no path to profitability.

---

### FUTURES — BLOCKED (All Force-Closed Toxic, Stale)

| Strategy | Elimination Reason | Status |
|----------|-------------------|--------|
| multi_asset_copytrader | 31 picks, all force-closed toxic (pnl=$0), WR=0%, stale 246 days | BLOCKED |
| futures_momentum | WR=2%, n=202, both directions broken | BLOCKED |

**Asset class status:** BLOCKED. Stale (246 days since last pick), insufficient n (13 policy-clean), failing DSR (0.0075), all closed_picks picks are zero-PnL force-closes.

---

### BOND — BLOCKED (Insufficient Data)

| Strategy | Elimination Reason | Status |
|----------|-------------------|--------|
| All Bond strategies | n=1 official, n=35 registry (below n≥100 floor) | BLOCKED |
| bond_duration_rotation | n=1 official | BLOCKED |
| bond_credit_spread_mean_reversion | n=1 official | BLOCKED |
| bond_yield_curve_slope | n=1 official | BLOCKED |
| bond_ust_tsmom | n=1 official | BLOCKED |
| bond_mean_reversion | n=1 official | BLOCKED |
| bond_yield_momentum | n=1 official | BLOCKED |

**Asset class status:** BLOCKED. n=1 cannot support statistical inference. Need yield/duration data pipeline and n≥100.

---

### COMMODITY — BLOCKED (Copy-Trader Claims Debunked)

| Strategy | Elimination Reason | Status |
|----------|-------------------|--------|
| multi_asset_copytrader | All 186 picks force-closed toxic (pnl=0), zero resolved trades. WR=93.8% claim debunked on 2026-05-16 as pre-dedup artifact | BLOCKED |
| multi_asset_cot | Same toxic pattern, not in closed_picks | BLOCKED |

**Asset class status:** BLOCKED. No commodity copy-trader candidate is viable.

---

### PENNY_STOCK — BLOCKED (Lottery Ticket)

| Strategy | Elimination Reason | Status |
|----------|-------------------|--------|
| skyrocket_detector | Not wired to production, MAX_PRICE=20 not $2-5, count=0 | BLOCKED |
| penny_stock_strategy_harness | Zero callers outside itself | BLOCKED |
| All penny/meme stock | n=10/n=1, WR 0-42%, PF 0.000-0.85 | BLOCKED |

**Asset class status:** BLOCKED. Lottery ticket with extreme bid-ask spreads, pump-and-dump risk, illiquidity, no fundamental edge, survivorship bias. Expected value negative after costs.

---

## Integrated Elimination Summary

| Category | Count |
|----------|-------|
| Strategies backtested and eliminated | 6+ (RSI2 Equity, DualMA Equity, Bollinger Equity, EMA Trend Crypto, Donchian Crypto, KIMI Inverse Scanner, COT Contrarian standalone) |
| Asset classes blocked (subset-level) | COMMODITY copy-trader (all force-closed toxic), FOREX copy-trader, FUTURES copy-trader, ETF (cohort mismatch), Bond (insufficient data), Meme/Penny Stock |
| Asset classes not built | Mutual Funds as active picks |
| Asset classes as research slots | EQUITY, CRYPCO (prediction markets shadow) |
| Strategies passing all money-ready gates | 0 |
| Asset classes money-ready | 0 |

---

## Why No Asset Class Is Proven Profitable

### Primary Reason: No Statistical Edge

- **Information coefficient ≈ 0** — no correlation between predicted and actual returns
- **DSR ≈ 0** for nearly all strategies — no confidence any Sharpe > 0
- **PBO ≈ 0.999** — near-certain that any apparent edge is overfitting
- **Win rates near 40%** — below 50% break-even for most strategies
- **Profit factors < 1.0** for most strategies — gross losses exceed gross profits

### Secondary Reason: Costs Dominate Edge

- Round-trip costs (4 bps in simulation, higher in real markets) exceed average edge for most strategies
- RSI(2) swing rule: doubling costs turns it negative
- ETF: 267% of average PnL is cost
- Commodity: 422% cost ratio

### Tertiary Reason: Structural Incompatibility

- **Mutual funds:** daily NAV, no intraday TP/SL, load/12b-1 costs
- **Bonds:** n=1, insufficient data
- **Commodity:** n=7-229, no contract identity pipeline
- **Meme/Penny Stock:** n=10/n=1, toxic

---

## The Only Capital Deployment Recommendation

**Low-cost index ETF/MF passive allocation** (outside the prediction system):

| Sleeve | Allocation | Example Funds | Rationale |
|--------|-----------|---------------|-----------|
| US Equity Index | 60% | FXAIX (0.015% ER, $0 min), SWTSX (0.03% ER, $0 min) | Equity risk premium, ER ≤0.09% |
| International Equity | 20% | VTIAX | Diversification, ER ≤0.10% |
| Bonds / T-Bills | 20% | VBTLX | Ballast, income, ER ≤0.20% |

**Expected outcome:** Market beta + bond income minus ~0.05-0.10% cost drag. Positive expected return over multi-year horizons. Not alpha. Not from the prediction system.

This is the **only** capital deployment recommendation. All prediction-system asset classes are blocked.
