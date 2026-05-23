# MASTER ACTION PLAN — 2026-05-18

**Document Version:** 2026-05-18-v1  
**Predecessor:** `reports/MASTER_ACTION_PLAN_2026-05-17.md`  
**Classification:** INTERNAL — MONEY-READY SYSTEMS  
**Owner:** Quantitative Portfolio Management  
**Next Review:** 2026-05-19 06:00 UTC

---

## 1. MONEY-READY VERDICT DASHBOARD

| Asset Class | Verdict | WR | PF | n | DSR | PBO | SPA | E(post-cost) | Sized? | Kelly % |
|-------------|---------|------|------|-----|-----|--------|-----|--------------|--------|---------|
| **CRYPTO** | **MONEY_READY** | 66.4% | 2.54 | 195 | 1.0 | 0.007 | PASS | Positive | YES | 25% |
| **COMMODITY** | WATCH | 60.2% | 2.15 | 89 | 1.0 | BLOCKED | PENDING | Positive (pre-cost) | NO | 0% |
| **ETF** | WATCH | 66.7% | 2.25 | 75 | 1.0 | PENDING | PENDING | Positive (pre-cost) | NO | 0% |
| **EQUITY** | INSUFFICIENT_DATA | — | — | 31 (local) | — | — | — | Unknown | NO | 0% |
| **FOREX** | NOT_READY | 33.3% | 0.48 | 45 | — | FAIL | FAIL | Negative | HARD_DISABLE | 0% |
| **BOND** | INSUFFICIENT_DATA | — | — | 1 | — | — | — | Unknown | NO | 0% |
| **FUTURES** | INSUFFICIENT_DATA | — | — | 12 | — | — | — | Unknown | NO | 0% |

### Legend
- **WR** = Win Rate (%) | **PF** = Profit Factor | **n** = Sample size (trades/signals)  
- **DSR** = Deflated Sharpe Ratio | **PBO** = Probability of Backtest Overfitting  
- **SPA** = Superior Predictive Ability test | **E(post-cost)** = Post-cost expected return  
- **Sized?** = Actively receiving capital allocation | **Kelly %** = Fractional Kelly sizing  

### Changes from 2026-05-17
- **ETF n: 71 -> 75** (+4 overnight signals, +5.6% toward n>=100 target)  
- **BOND n: 0 -> 1** (scanner generated first real pick 2026-05-17 23:41 UTC)  
- **FUTURES n: 12** (unchanged — strategies remain blocked)  
- **COMMODITY PBO:** Still BLOCKED by CT=F 65% concentration (no fix yet)  
- **Dashboard UI:** P0.5 Gate Config panel shipped in commit `1686e9cf6cb`

---

## 2. PER-CLASS ACTION PLANS

---

### 2.1 CRYPTO — MONEY_READY (Maintained: 2026-05-17 -> 2026-05-18)

**Verdict Rationale:** Only asset class meeting all seven money-ready criteria. WR=66.4% with PF=2.54 on n=195 provides statistical confidence at alpha=0.05. PBO=0.007 indicates negligible overfitting risk. 25% Kelly sizing is conservative (half-optimal) providing drawdown protection.

#### 2.1.1 MONEY-READY MAINTENANCE (P0)

| ID | Action | Priority | ETA | Owner | Measurable Outcome |
|----|--------|----------|-----|-------|-------------------|
| C-001 | Maintain 25% Kelly position sizing — no increase until n>=250 | P0 | Ongoing | PM | Kelly % stays at 25 |
| C-002 | Per-symbol autopsy on every closed CRYPTO pick — win or loss | P0 | Daily | System | 100% autopsy coverage |
| C-003 | Slippage model validation: compare predicted vs. actual fill on >=10 trades/week | P1 | Weekly | Quant | Slippage forecast error <15% |
| C-004 | Weekend gap risk monitoring — BTC/ETH Sunday open gaps >3% | P1 | Daily | System | Alert within 5min of gap |

#### 2.1.2 STRATEGY INVESTIGATION — quan_engine + rapid_fire (P1)

| ID | Action | Priority | ETA | Owner | Measurable Outcome |
|----|--------|----------|-----|-------|-------------------|
| C-005 | **STRATEGY_INVESTIGATION**: Audit `quan_engine` module for alpha decay vs. live performance | P1 | 2026-05-20 | Quant | Report: predicted vs. actual alpha per signal |
| C-006 | **STRATEGY_INVESTIGATION**: Backtest `rapid_fire` overlay on CRYPTO universe (last 90 days) | P1 | 2026-05-22 | Quant | WR, PF, max consecutive losses, PBO |
| C-007 | Gate decision: Deploy `rapid_fire` to 5% shadow allocation if WR>60% && PF>1.8 | P2 | 2026-05-25 | PM | Go/No-Go recorded in decision log |
| C-008 | Elite source protection audit: verify API keys, rate limits, uptime SLA for all 4 CRYPTO signal sources | P1 | 2026-05-19 | Dev | 100% key validity + SLA compliance |

#### 2.1.3 ELITE SOURCES TO PROTECT

| Source | Signal Type | Uptime SLA | Last Validated | Action |
|--------|-------------|------------|----------------|--------|
| Source A (on-chain) | whale_flow | 99.5% | 2026-05-18 06:00 | Monitor — P0 |
| Source B (exchange) | order_imbalance | 99.9% | 2026-05-18 06:00 | Monitor — P0 |
| Source C (derivatives) | funding_rate | 99.5% | 2026-05-18 06:00 | Monitor — P0 |
| Source D (social) | sentiment_delta | 95.0% | 2026-05-18 06:00 | Monitor — P1, less reliable |

#### 2.1.4 CRYPTO Risk Boundaries (HARD CONSTRAINTS)

- **Max single-position:** 8% of CRYPTO allocation (3.2% of total book at 25% Kelly)
- **Max correlated exposure:** 40% in same-direction BTC/ETH positions
- **Stop-loss:** 6% per position (trailing after 3% profit)
- **Daily loss limit:** 2% of CRYPTO allocation
- **Weekend exposure limit:** 60% of CRYPTO allocation (reduce ahead of Friday close)

---

### 2.2 COMMODITY — WATCH (Unchanged from 2026-05-17)

**Verdict Rationale:** WR=60.2% and PF=2.15 are money-ready adjacent, but CT=F (WTI Crude Oil) concentration at 65% of signals creates un diversifiable single-name risk. PBO cannot be computed on a single underlying with high autocorrelation. No allocation until concentration <=40%.

#### 2.2.1 CONCENTRATION FIX (P0)

| ID | Action | Priority | ETA | Owner | Measurable Outcome |
|----|--------|----------|-----|-------|-------------------|
| M-001 | **PR-2026-0518-3**: Implement COT lag correction — COT reports are 3-day delayed; mark stale signals | P0 | 2026-05-19 | Quant+Dev | 0 signals with >3day stale COT data |
| M-002 | **Concentration cap**: Hard block CT=F >40% of weekly signal count | P0 | 2026-05-19 | Dev | CT=F <=40% in any rolling 7-day window |
| M-003 | Diversify scanner to include GC=F (Gold), SI=F (Silver), HG=F (Copper), ZC=F (Corn) | P1 | 2026-05-21 | Quant | >=4 distinct underliers generating signals |
| M-004 | Diversify scanner to include CL=F (Brent proxy), NG=F (NatGas), ZW=F (Wheat) | P2 | 2026-05-24 | Quant | >=7 distinct underliers in universe |
| M-005 | Recompute PBO with diversified universe — target PBO <0.10 | P0 | 2026-05-25 | Quant | PBO report with n>=80 diversified |

#### 2.2.2 PAPER PILOT GATE (P1)

| ID | Action | Priority | ETA | Owner | Measurable Outcome |
|----|--------|----------|-----|-------|-------------------|
| M-006 | Paper trading pilot launch — 10% shadow size, all COMMODITY signals | P1 | 2026-05-23 | PM+Dev | Pilot live, fills logged, P&L tracked |
| M-007 | Paper pilot evaluation criteria: WR>55%, PF>1.5, max drawdown <8% | P1 | 2026-05-30 | PM | Go/No-Go for 5% Kelly real-money |
| M-008 | Roll cost model: contango/backwardation impact on hold-period returns | P2 | 2026-05-28 | Quant | Model integrated in post-cost expectancy |

#### 2.2.3 COMMODITY Risk Boundaries (FUTURE — Post Paper Pilot)

- Max single-underlier: 35% of COMMODITY allocation
- Max energy sector: 50% of COMMODITY allocation
- Seasonal overlay: No agricultural positions within 2 weeks of USDA report
- Roll timing: Exit front-month >=5 days before expiry

---

### 2.3 ETF — WATCH (Unchanged from 2026-05-17)

**Verdict Rationale:** WR=66.7% and PF=2.25 are strong, but n=75 falls short of n>=100 threshold for statistical significance at conventional levels. VIX<25 gate needs wiring before MONEY_READY upgrade.

#### 2.3.1 SAMPLE SIZE ACCUMULATION (P0)

| ID | Action | Priority | ETA | Owner | Measurable Outcome |
|----|--------|----------|-----|-------|-------------------|
| E-001 | Accumulate n>=100 — currently 75, need +25 signals | P0 | 2026-05-25 | System | n>=100 validated |
| E-002 | Sector dual momentum scanner: SPY vs. sector ETFs (XLK, XLF, XLE, XLI, XLU, XLP, XLB, XLRE) | P1 | 2026-05-22 | Quant | 8 sector ETFs in signal universe |
| E-003 | Factor ETF expansion: add QQQ, IWM, VTV, VUG, MTUM, QUAL, USMV, VLUE | P2 | 2026-05-28 | Quant | 16 total ETFs in signal universe |
| E-004 | International ETF expansion: EEM, EFA, IEFA, VXUS, EWJ | P3 | 2026-06-05 | Quant | 21 total ETFs in signal universe |

#### 2.3.2 VIX GATE WIRING (P0)

| ID | Action | Priority | ETA | Owner | Measurable Outcome |
|----|--------|----------|-----|-------|-------------------|
| E-005 | **PR-2026-0518-4**: Wire VIX<25 gate — block new ETF positions if VIX>=25 at 09:35 ET | P0 | 2026-05-20 | Dev | Gate active, test with VIX=24.9/25.1 |
| E-006 | VIX gate exception log: record every blocked signal with VIX level | P1 | 2026-05-20 | Dev | 100% blocked signals logged |
| E-007 | VIX gate backtest: how many 2025 winners would have been blocked? | P1 | 2026-05-22 | Quant | Opportunity cost analysis report |

#### 2.3.3 MONEY-READY GATE (P1)

| ID | Action | Priority | ETA | Owner | Measurable Outcome |
|----|--------|----------|-----|-------|-------------------|
| E-008 | Compute PBO on n>=100 sample | P0 | 2026-05-25 | Quant | PBO <0.10 required |
| E-009 | Compute SPA test on n>=100 sample | P0 | 2026-05-25 | Quant | SPA p-value <0.05 required |
| E-010 | Post-cost expectancy model: ETF-specific borrow, spread, commission costs | P1 | 2026-05-24 | Quant | E(post-cost) >0 |
| E-011 | **MONEY_READY evaluation**: Go/No-Go for 15% Kelly sizing | P0 | 2026-05-26 | PM | Decision recorded in gate log |

---

### 2.4 EQUITY — INSUFFICIENT_DATA (Unchanged from 2026-05-17)

**Verdict Rationale:** Local n=31 is far below n>=100 threshold. MySQL sync scheduled for 2026-05-24 will bring historical trade data from production DB. Two symbol blocks (AMD, NIO) due to liquidity/adverse selection concerns. PEAD strategy is the primary path to MONEY_READY.

#### 2.4.1 DATA INFRASTRUCTURE (P0)

| ID | Action | Priority | ETA | Owner | Measurable Outcome |
|----|--------|----------|-----|-------|-------------------|
| Q-001 | **MySQL sync**: Import historical EQUITY picks from production DB (est. n=400+) | P0 | 2026-05-24 | Dev | Sync complete, n validated |
| Q-002 | Post-sync validation: reconcile imported n with manual count | P0 | 2026-05-24 | PM+Dev | Discrepancy <2% |
| Q-003 | Symbol universe definition: S&P 500 + liquid mid-caps (ADV >$50M) | P1 | 2026-05-23 | Quant | Universe file: `config/equity_universe.csv` |

#### 2.4.2 PEAD STRATEGY (P1)

| ID | Action | Priority | ETA | Owner | Measurable Outcome |
|----|--------|----------|-----|-------|-------------------|
| Q-004 | PEAD (Post-Earnings Announcement Drift) backtest: 5-day drift capture | P1 | 2026-05-26 | Quant | WR, PF, PBO on 2024-2025 earnings |
| Q-005 | PEAD signal construction: standardized unexpected earnings (SUE) quintile | P1 | 2026-05-26 | Quant | Signal formula documented |
| Q-006 | PEAD execution: enter 1 hour after earnings, hold 3-5 days | P2 | 2026-05-28 | Quant | Slippage model for AH/PM entries |
| Q-007 | DOW tilt overlay: overweight signals when DOW is in confirmed uptrend (price > 20DMA) | P2 | 2026-05-27 | Quant | DOW regime flag added to signals |

#### 2.4.3 SYMBOL BLOCKS

| Symbol | Block Reason | Review Date | Lift Criteria |
|--------|-------------|-------------|---------------|
| AMD | Liquidity fragmentation (lit vs. dark), adverse selection | 2026-06-01 | ADV>$100M for 10 consecutive days |
| NIO | ADR-specific risk, delisting overhang, wide spreads | 2026-06-15 | SEC audit compliance confirmed |

#### 2.4.4 EQUITY Risk Boundaries (FUTURE)

- Max single-position: 5% of EQUITY allocation
- Max sector concentration: 30% of EQUITY allocation
- Earnings date exit: Close before earnings if position opened >=3 days prior
- AH/PM execution: Only for top 50% ADV names; max 25% of position size

---

### 2.5 FOREX — NOT_READY (Unchanged — HARD_DISABLED)

**Verdict Rationale:** WR=33.3% (below 50% random baseline) and PF=0.48 (losing strategy) make FOREX the weakest asset class. Strategy is HARD_DISABLED — no signals generated, no capital allocated. Path to viability is carry trade backtest + non-JPY SHORT monitoring.

#### 2.5.1 HARD_DISABLE MAINTENANCE (P0)

| ID | Action | Priority | ETA | Owner | Measurable Outcome |
|----|--------|----------|-----|-------|-------------------|
| F-001 | Verify HARD_DISABLE flag is active in all environments (dev/staging/prod) | P0 | 2026-05-18 | Dev | Flag confirmed in all 3 envs |
| F-002 | Weekly audit: confirm zero FOREX signals generated | P0 | Weekly | System | Zero signals log entry |
| F-003 | Document HARD_DISABLE rationale in system log for audit trail | P1 | 2026-05-19 | Dev | Rationale logged with ticket ref |

#### 2.5.2 CARRY TRADE BACKTEST (P1)

| ID | Action | Priority | ETA | Owner | Measurable Outcome |
|----|--------|----------|-----|-------|-------------------|
| F-004 | G10 carry trade backtest: long high-yield (AUD, NZD), short low-yield (JPY, CHF) | P1 | 2026-05-28 | Quant | 10-year backtest WR, PF, max drawdown |
| F-005 | Carry with trend overlay: only take carry in direction of 20DMA | P1 | 2026-05-30 | Quant | Compare raw carry vs. trend-filtered |
| F-006 | Funding cost model: incorporate actual broker swap rates | P2 | 2026-06-02 | Quant | Post-swap expectancy computed |

#### 2.5.3 NON-JPY SHORT MONITORING (P2)

| ID | Action | Priority | ETA | Owner | Measurable Outcome |
|----|--------|----------|-----|-------|-------------------|
| F-007 | Build non-JPY SHORT signal monitor: EUR/USD, GBP/USD shorts when USD index > 20DMA | P2 | 2026-06-05 | Quant | Signal generating, paper-only |
| F-008 | Momentum breakout model: 20-day range break with volume confirmation | P3 | 2026-06-10 | Quant | WR, PF on 3-year backtest |

#### 2.5.4 FOREX MONEY-READY CRITERIA (ALL REQUIRED)

| Criterion | Current | Target | Gap |
|-----------|---------|--------|-----|
| WR | 33.3% | >=55% | +21.7pp |
| PF | 0.48 | >=1.5 | +1.02 |
| n | 45 | >=150 | +105 |
| PBO | FAIL | <0.10 | Significant |
| Post-cost E | Negative | >0 | Major |
| DSR | — | >0.5 | Unknown |

---

### 2.6 BOND — INSUFFICIENT_DATA (Improving — scanner live)

**Verdict Rationale:** Scanner wired 2026-05-17 produced first real pick (n=1). Need n>=20 for preliminary WR/PF, n>=100 for MONEY_READY. UST TSMOM (Time-Series Momentum) is primary strategy thesis.

#### 2.6.1 DATA ACCUMULATION (P0)

| ID | Action | Priority | ETA | Owner | Measurable Outcome |
|----|--------|----------|-----|-------|-------------------|
| B-001 | Accumulate n>=20 (currently n=1) — scanner generating daily | P0 | 2026-05-31 | System | n>=20 validated |
| B-002 | Verify scanner coverage: TLT, IEF, SHY, HYG, LQD, TIP, MUB, EMB | P0 | 2026-05-20 | Quant | All 8 tickers in scan output |
| B-003 | FRED data integration: 10Y yield, yield curve slope, credit spreads | P1 | 2026-05-22 | Quant+Dev | FRED feed active, data validated |

#### 2.6.2 UST TSMOM STRATEGY (P1)

| ID | Action | Priority | ETA | Owner | Measurable Outcome |
|----|--------|----------|-----|-------|-------------------|
| B-004 | UST TSMOM signal: 12-month momentum on TLT, long/flat based on 10MA crossover | P1 | 2026-05-25 | Quant | Backtest 2015-2025 |
| B-005 | Duration rotation: shift TLT <-> IEF <-> SHY based on yield curve regime | P2 | 2026-05-30 | Quant | 3-regime model (steep, flat, inverted) |
| B-006 | Credit spread filter: no HY exposure if BAML OAS > 500bps | P2 | 2026-06-02 | Quant | Filter active in simulation |

#### 2.6.3 FRED_API_KEY (P1)

| ID | Action | Priority | ETA | Owner | Measurable Outcome |
|----|--------|----------|-----|-------|-------------------|
| B-007 | Obtain FRED_API_KEY from St. Louis Fed | P1 | 2026-05-20 | Ops | Key active, rate limit tested |
| B-008 | Integrate FRED API into data pipeline: `fred/series/observations` endpoint | P1 | 2026-05-22 | Dev | Daily auto-pull at 09:00 ET |
| B-009 | FRED-derived features: yield curve, real rate, term premium proxy | P2 | 2026-05-25 | Quant | Feature matrix in `features/bond_fred.parquet` |

#### 2.6.4 BOND Risk Boundaries (FUTURE)

- Max duration exposure: 10-year equivalent (cap TLT at 50% of BOND allocation)
- Fed meeting blackout: No new positions 48 hours before FOMC
- Yield shock limit: Close all positions if 10Y yield moves >20bps in 1 session
- Credit quality: Investment grade only (HY via HYG only if OAS <400bps)

---

### 2.7 FUTURES — INSUFFICIENT_DATA (Blocked — Deprioritized)

**Verdict Rationale:** n=12 is statistically meaningless. Strategies are blocked pending completion of CRYPTO, ETF, and COMMODITY MONEY_READY upgrades. No dedicated resources allocated.

#### 2.7.1 BLOCKED STATUS (P2)

| ID | Action | Priority | ETA | Owner | Measurable Outcome |
|----|--------|----------|-----|-------|-------------------|
| U-001 | Maintain BLOCKED status — no strategy development | P2 | Until Q3 2026 | PM | Zero resource allocation |
| U-002 | Quarterly review: assess if n>=50 from accidental signal overlap | P3 | 2026-07-01 | System | n count report |
| U-003 | Strategy template: define `FuturesStrategy` base class for future use | P3 | 2026-06-15 | Dev | Base class in `strategies/futures/base.py` |

#### 2.7.2 FUTURES UNBLOCK CRITERIA

| Criterion | Required | Current | Status |
|-----------|----------|---------|--------|
| CRYPTO stable at 25% Kelly | >=30 days | 1 day | NOT MET |
| ETF MONEY_READY | YES | WATCH | NOT MET |
| COMMODITY MONEY_READY | YES | WATCH | NOT MET |
| Available developer capacity | >=1 FTE | 0 FTE | NOT MET |
| Risk framework v2 complete | YES | In progress | NOT MET |

---

## 3. CROSS-CLASS INFRASTRUCTURE

### 3.1 Active Infrastructure Initiatives

| ID | Initiative | Priority | ETA | Status | Blocks |
|----|-----------|----------|-----|--------|--------|
| X-001 | **Post-cost expectancy gate**: Compute E(post-cost) for every signal before sizing | P0 | 2026-05-22 | IN PROGRESS | All MONEY_READY upgrades |
| X-002 | **Regime conditioning**: Macro regime classifier (growth, inflation, risk-on/off) | P0 | 2026-05-25 | IN PROGRESS | ETF, COMMODITY allocation |
| X-003 | **MDD/CVaR monitor**: Real-time max drawdown and 95% CVaR tracking | P0 | 2026-05-24 | IN PROGRESS | All sized classes |
| X-004 | **Per-symbol autopsy**: Automated post-trade analysis for every closed position | P0 | 2026-05-20 | IN PROGRESS | All classes |
| X-005 | **Slippage model v2**: Exchange-specific, size-dependent slippage forecasting | P1 | 2026-05-28 | IN PROGRESS | CRYPTO, ETF |
| X-006 | **Concentration gate**: Hard cap any single name >X% of class allocation | P0 | 2026-05-19 | IN PROGRESS | COMMODITY CT=F |
| X-007 | **M-034 (Meta-label model)**: ML-based position sizing using meta-labels | P1 | 2026-06-05 | IN PROGRESS | All classes |
| X-008 | **Meta label gate**: Only size signals with primary_probability > threshold | P1 | 2026-06-05 | IN PROGRESS | All classes |
| X-009 | **FRED_API_KEY**: St. Louis Fed API for macro data (yields, spreads) | P1 | 2026-05-20 | OPEN | BOND strategy |
| X-010 | **P0.5 Gate Config panel**: Dashboard UI for editing gate thresholds live | P0 | 2026-05-18 | **SHIPPED** `1686e9cf6cb` | Dashboard |

### 3.2 Post-Cost Expectancy Gate (X-001) — Detail

**Purpose:** Prevent positive-pre-cost signals from receiving allocation when costs turn E negative.

```
E(post-cost) = (WR * avg_win) - ((1-WR) * avg_loss) - total_costs

total_costs = commission + spread + borrow_fee + slippage + funding
```

| Asset Class | Commission | Spread | Borrow | Slippage | Funding | Current E(pre-cost) | Est. E(post-cost) |
|-------------|------------|--------|--------|----------|---------|---------------------|-------------------|
| CRYPTO | 0.05% | 0.02% | — | 0.08% | 0.01%/8h | +2.8% | +2.4% |
| COMMODITY | 0.02% | 0.01% | — | 0.05% | 0.02%/day | +1.5% | +1.1% |
| ETF | 0.01% | 0.01% | 0.3% | 0.03% | — | +1.2% | +0.7% |
| EQUITY | 0.01% | 0.01% | 0.5% | 0.04% | — | Unknown | Unknown |
| FOREX | 0.00% | 0.01% | — | 0.005% | swap | Negative | Negative |
| BOND | 0.01% | 0.02% | — | 0.03% | — | Unknown | Unknown |

### 3.3 Regime Conditioning (X-002) — Detail

| Regime | Definition | CRYPTO | COMMODITY | ETF | EQUITY |
|--------|-----------|--------|-----------|-----|--------|
| Risk-On | VIX<20, HY spreads <300bps | Full size | Full size | Full size | Full size |
| Risk-Off | VIX>30, HY spreads >500bps | 50% size | 25% size | Block new | Block new |
| Inflation | Breakeven >2.5%, rising | Reduce | Overweight GC=F | Underweight LT bonds | Overweight real assets |
| Growth-Scare | 10Y-2Y <0, ISM <50 | Reduce | Reduce energy | Defensive sectors | Quality tilt |

---

## 4. NEW: PICK TRACEABILITY SYSTEM

### 4.1 Overview

The Pick Traceability System is a new infrastructure layer providing full auditability for every pick generated, filtered, executed, and closed across all asset classes. It replaces ad-hoc logging with structured, queryable pick lifecycle records.

### 4.2 Functional Specification

#### 4.2.1 Active/Closed Picks Visibility (PR-T1)

| Feature | Description | Priority |
|---------|-------------|----------|
| Active picks dashboard | Real-time view of all open positions with P&L, sizing, stop levels | P0 |
| Closed picks archive | Historical view with actual entry/exit, slippage, outcome | P0 |
| Pick reasoning | Structured field: why was this pick generated (signal type, source, timestamp) | P0 |
| Pick timeline | Event log: generated -> filtered? -> sized -> entered -> modified -> closed | P0 |

#### 4.2.2 Symbol Universe Management (PR-T2)

| Feature | Description | Priority |
|---------|-------------|----------|
| Per-class universe | Defined, versioned symbol lists per asset class | P0 |
| Universe diff | Track additions/removals with timestamp and reason | P1 |
| Liquidity filter | Auto-remove symbols below ADV threshold | P1 |
| Universe health score | % of universe generating signals in last 30 days | P2 |

#### 4.2.3 Filter Traceback (PR-T3)

| Feature | Description | Priority |
|---------|-------------|----------|
| Rejection reason | Every filtered pick must have a structured rejection code | P0 |
| Filter cascade | Show which filter stage rejected the pick (gate order) | P0 |
| Filter statistics | Per-filter: rejection count, rejection rate, false positive estimate | P1 |
| Filter audit trail | Who changed filter thresholds, when, and why | P1 |

**Rejection Codes (Initial Set):**

| Code | Description | Asset Classes |
|------|-------------|---------------|
| FT-001 | PBO above threshold | All |
| FT-002 | Concentration limit exceeded | COMMODITY, EQUITY |
| FT-003 | VIX gate blocked | ETF |
| FT-004 | Macro regime mismatch | All |
| FT-005 | Insufficient sample size for strategy | All |
| FT-006 | Post-cost expectancy negative | All |
| FT-007 | Symbol block list | EQUITY |
| FT-008 | Meta-label probability below threshold | All |
| FT-009 | COT data stale >3 days | COMMODITY |
| FT-010 | Hard disable active | FOREX |

#### 4.2.4 "What-If" Simulation (PR-T4)

| Feature | Description | Priority |
|---------|-------------|----------|
| Relaxed filter run | Re-run filtered picks with relaxed thresholds | P1 |
| Opportunity cost | P&L foregone due to filtering | P1 |
| Filter sensitivity | Which filter thresholds have highest opportunity cost | P2 |
| A/B filter test | Run two filter configs in parallel, compare outcomes | P2 |

#### 4.2.5 Pick Lifecycle Logger (PR-T5)

```
Table: pick_lifecycle
- pick_id (UUID, PK)
- asset_class (ENUM)
- symbol (VARCHAR)
- signal_timestamp (DATETIME)
- signal_source (VARCHAR)
- signal_type (VARCHAR)
- raw_signal_score (FLOAT)
- filter_results (JSON) — {filter_name: {passed: bool, reason: string}}
- final_verdict (ENUM: accepted, filtered, paper, shadow)
- sizing (JSON) — {kelly_fraction, position_size, max_position}
- entry (JSON) — {timestamp, price, slippage_actual}
- exit (JSON) — {timestamp, price, slippage_actual, reason}
- pnl_gross (FLOAT)
- pnl_net (FLOAT)
- autopsy (JSON) — {prediction_error, regime, notes}
- created_at (DATETIME)
- updated_at (DATETIME)
```

### 4.3 Implementation PRs

| PR ID | Title | Scope | Files | ETA |
|-------|-------|-------|-------|-----|
| **PR-T1** | Pick Traceability Core | Active/closed picks dashboard + API | `api/picks.py`, `dashboard/picks_view.tsx` | 2026-05-22 |
| **PR-T2** | Symbol Universe Manager | Per-class universe + version control | `config/universe_manager.py`, `db/migrations/003_universe.sql` | 2026-05-24 |
| **PR-T3** | Filter Traceback Engine | Structured rejection + cascade logging | `filters/traceback.py`, `db/migrations/004_filter_log.sql` | 2026-05-26 |
| **PR-T4** | What-If Simulator | Relaxed filter re-run + opportunity cost | `simulation/what_if.py`, `api/simulate.py` | 2026-05-28 |
| **PR-T5** | Pick Lifecycle Logger | Core logging module + DB migration | `core/pick_lifecycle_logger.py`, `db/migrations/005_pick_lifecycle.sql` | 2026-05-20 |

### 4.4 Dependencies

- PR-T5 (core logger) must merge before PR-T1, PR-T3
- PR-T2 (universe) must merge before PR-T3 (traceback references universe)
- PR-T4 (simulator) depends on PR-T3 (needs filter cascade data)

### 4.5 Rollout Plan

| Phase | PRs | Date | Milestone |
|-------|-----|------|-----------|
| 1 | PR-T5 | 2026-05-20 | Logging active for all new picks |
| 2 | PR-T1 | 2026-05-22 | Dashboard visible to PM |
| 3 | PR-T2 | 2026-05-24 | Symbol universe versioned |
| 4 | PR-T3 | 2026-05-26 | Full filter traceback available |
| 5 | PR-T4 | 2026-05-28 | What-if simulation live |

---

## 5. CONVERGENCE MAP

Items appearing in >=3 consecutive daily plans (2026-05-14 through 2026-05-18):

| Item | First Seen | Days Appearing | Status | Target Resolution |
|------|-----------|----------------|--------|-------------------|
| CRYPTO 25% Kelly maintenance | 2026-05-14 | 5 | ONGOING | Until n>=250 |
| COMMODITY CT=F concentration | 2026-05-14 | 5 | **STUCK** — needs PR-2026-0518-3 | 2026-05-19 |
| ETF n>=100 target | 2026-05-14 | 5 | IN PROGRESS (75/100) | 2026-05-25 |
| EQUITY MySQL sync | 2026-05-15 | 4 | SCHEDULED | 2026-05-24 |
| FOREX HARD_DISABLE | 2026-05-14 | 5 | ACTIVE | Until criteria met |
| BOND scanner wiring | 2026-05-14 | 5 | DONE (n=1 achieved) | 2026-05-31 for n>=20 |
| FUTURES blocked | 2026-05-14 | 5 | ACTIVE | Q3 2026 earliest |
| Post-cost expectancy gate | 2026-05-15 | 4 | IN PROGRESS | 2026-05-22 |
| Regime conditioning | 2026-05-16 | 3 | IN PROGRESS | 2026-05-25 |
| MDD/CVaR monitor | 2026-05-15 | 4 | IN PROGRESS | 2026-05-24 |
| FRED_API_KEY | 2026-05-16 | 3 | OPEN | 2026-05-20 |
| Slippage model | 2026-05-15 | 4 | IN PROGRESS | 2026-05-28 |

### Stuck Items Requiring Escalation

| Item | Days Stuck | Escalation Path | Resolution Required By |
|------|-----------|-----------------|----------------------|
| COMMODITY CT=F concentration | 5 days | PR-2026-0518-3 merge | 2026-05-19 |
| FRED_API_KEY procurement | 3 days | Ops team ticket | 2026-05-20 |
| FUTURES resource allocation | 5 days | Q2 planning review | 2026-06-01 |

---

## 6. 30/60/90 DAY ROADMAP

### 30 Days (by 2026-06-17)

| Asset Class | Target | Key Deliverables |
|-------------|--------|-----------------|
| **CRYPTO** | Stable at 25% Kelly, n>=220 | Strategy investigation report; rapid_fire shadow results |
| **COMMODITY** | PAPER PILOT live | Concentration cap enforced; n>=60 diversified; PBO computed |
| **ETF** | MONEY_READY evaluation | n>=100; VIX gate live; PBO+SPA passed; 15% Kelly or stay WATCH |
| **EQUITY** | n>=100 imported | MySQL sync done; PEAD backtest complete; symbol universe defined |
| **FOREX** | Strategy path defined | Carry backtest complete; Go/No-Go for further investment |
| **BOND** | n>=20 achieved | UST TSMOM backtest; FRED feed active |
| **FUTURES** | Remain BLOCKED | No change |
| **Infra** | Pick Traceability v1 | PR-T1 through PR-T5 merged; dashboard live |

### 60 Days (by 2026-07-17)

| Asset Class | Target | Key Deliverables |
|-------------|--------|-----------------|
| **CRYPTO** | Evaluate 35% Kelly increase | If n>=300 && max drawdown <8%; per-symbol autopsy v2 |
| **COMMODITY** | MONEY_READY or extended WATCH | Paper pilot results; 10% Kelly if WR>55% && PF>1.5 |
| **ETF** | Stable MONEY_READY or MONEY_READY achieved | 15-20% Kelly; sector rotation active |
| **EQUITY** | MONEY_READY evaluation | n>=150; PEAD live with 10% Kelly shadow |
| **FOREX** | Paper pilot if carry results positive | Non-JPY SHORT monitor live; first paper trades |
| **BOND** | MONEY_READY evaluation | n>=80; UST TSMOM live with 5% Kelly shadow |
| **FUTURES** | Evaluate unblock | If 3 classes MONEY_READY + capacity available |
| **Infra** | M-034 meta-label model | ML-based sizing active; regime classifier v2 |

### 90 Days (by 2026-08-17)

| Asset Class | Target | Key Deliverables |
|-------------|--------|-----------------|
| **CRYPTO** | 40% Kelly or maintain 35% | Full automation; 24/7 monitoring; slippage model v2 validated |
| **COMMODITY** | 15-20% Kelly | Diversified across 6+ underliers; roll cost model integrated |
| **ETF** | 20% Kelly | Full sector rotation; international ETF overlay |
| **EQUITY** | 15-20% Kelly | PEAD + DOW tilt live; AMD/NIO blocks reviewed |
| **FOREX** | Evaluate MONEY_READY or maintain NOT_READY | Full strategy suite backtested; Go/No-Go |
| **BOND** | 10-15% Kelly | Duration rotation active; credit spread filter validated |
| **FUTURES** | Evaluate unblock | Unblock criteria check; strategy development begins if unblocked |
| **Infra** | Full v2 platform | End-to-end pick traceability; real-time risk; automated reporting |

### Target Portfolio Allocation (90-Day Vision)

```
CRYPTO:     35-40%  (MONEY_READY, highest confidence)
ETF:        15-20%  (MONEY_READY, diversifier)
EQUITY:     10-15%  (MONEY_READY, PEAD-driven)
COMMODITY:  10-15%  (MONEY_READY or WATCH)
BOND:       5-10%   (MONEY_READY or WATCH)
FOREX:      0%      (NOT_READY or early PAPER)
FUTURES:    0%      (BLOCKED)
CASH:       5-10%   (Opportunistic reserve)
```

---

## 7. TODAY'S SESSION FOCUS (2026-05-18)

### 7.1 Commit Targets

| Commit | Description | Priority | ETA | Owner |
|--------|-------------|----------|-----|-------|
| `1686e9cf6cb` | **SHIPPED**: feat(dashboard): P0.5 Gate Config panel | P0 | DONE | Dev |
| `2026-0518-a` | **PR-2026-0518-5**: `pick_lifecycle_logger.py` core + DB migration (PR-T5) | P0 | 14:00 UTC | Dev |
| `2026-0518-b` | **PR-2026-0518-2**: CRYPTO quan_engine audit + rapid_fire investigation blocks | P1 | 16:00 UTC | Quant |
| `2026-0518-c` | **PR-2026-0518-3**: COMMODITY COT lag correction + concentration cap | P0 | 18:00 UTC | Quant+Dev |
| `2026-0518-d` | **PR-2026-0518-4**: ETF VIX<25 gate wire-up | P0 | 20:00 UTC | Dev |
| `2026-0518-e` | **PR-2026-0518-1**: EQUITY symbol universe manager + filter traceback scaffold | P1 | 22:00 UTC | Dev |

### 7.2 Validation Checklist (End of Day)

- [ ] Gate Config panel confirmed working in production dashboard
- [ ] `pick_lifecycle` table created in DB with all columns
- [ ] CRYPTO: quan_engine audit report saved to `investigations/quan_engine_2026-05-18.md`
- [ ] COMMODITY: CT=F concentration cap enforced in simulation mode
- [ ] ETF: VIX gate responds correctly to test inputs (24.9=pass, 25.1=block)
- [ ] EQUITY: symbol universe CSV created with >=200 tickers
- [ ] Master plan updated and committed to `reports/MASTER_ACTION_PLAN_2026-05-18.md`

### 7.3 Metrics to Capture Today

| Metric | Target | Measurement |
|--------|--------|-------------|
| CRYPTO signals generated | >=3 | Signal count by 23:59 UTC |
| ETF n accumulated | 75->77 | End-of-day count |
| COMMODITY diversified signals | >=2 non-CT=F | Scanner output |
| BOND scanner picks | >=1 | End-of-day count |
| System uptime | 100% | Monitoring dashboard |

---

## 8. OPEN DECISIONS

Decisions requiring human/Portfolio Authority action before proceeding:

| ID | Decision | Requester | Options | Impact | Required By | Status |
|----|----------|-----------|---------|--------|-------------|--------|
| D-001 | **COMMODITY paper pilot capital** | PM | $0 (defer) / $50K (10% shadow) / $100K (20% shadow) | M-006 blocked until decided | 2026-05-22 | OPEN |
| D-002 | **CRYPTO Kelly increase to 35%** | Quant | Stay 25% / Increase to 35% / Await n>=250 | C-001 sizing | 2026-05-25 | OPEN — pending n>=220 |
| D-003 | **FRED_API_KEY procurement** | Ops | Apply for key / Use alternative source (YF) | B-007, B-008, X-009 | 2026-05-20 | **ESCALATED** |
| D-004 | **AMD/NIO block lift criteria** | PM | Keep blocks / Relax to warnings / Remove | Q symbol universe | 2026-05-24 | OPEN |
| D-005 | **rapid_fire shadow allocation** | PM | 0% / 5% / 10% of CRYPTO allocation | C-007 | 2026-05-25 | OPEN — pending C-006 results |
| D-006 | **FUTURES Q2 resource allocation** | PM | 0 FTE / 0.5 FTE / 1 FTE | U-003, unblock criteria | 2026-06-01 | OPEN |
| D-007 | **ETF MONEY_READY Go/No-Go** | PM | WATCH (stay) / MONEY_READY (15% Kelly) / PAPER PILOT | E-011 | 2026-05-26 | OPEN — pending n>=100 |
| D-008 | **per_class_trainer shadow mode data collection** | Quant | Continue collection / Process now / Abort | Training data volume | 2026-05-22 | OPEN |
| D-009 | **Pick Traceability priority** | PM | P0 (this sprint) / P1 (next sprint) / P2 (backlog) | PR-T1 through PR-T5 timeline | 2026-05-18 | **DECIDED: P0** |

### Decision Log (Updated 2026-05-18)

| Date | Decision | Outcome | Rationale |
|------|----------|---------|-----------|
| 2026-05-18 | Pick Traceability priority | **P0** | Required for audit compliance and filter optimization |
| 2026-05-18 | P0.5 Gate Config panel | **SHIPPED** | Enables PM to adjust thresholds without dev intervention |

---

## 9. PR SET FOR TODAY (2026-05-18)

### PR-2026-0518-1: Pick Traceability Core

| Field | Detail |
|-------|--------|
| **Title** | `feat(traceability): Pick Lifecycle Logger + DB migration` |
| **Scope** | Core pick logging infrastructure — every pick gets a lifecycle record |
| **Files** | `core/pick_lifecycle_logger.py`, `db/migrations/005_pick_lifecycle.sql`, `config/logger_config.yaml` |
| **Tests** | Unit: 100% coverage on logger; Integration: end-to-end pick lifecycle |
| **Acceptance** | 1) DB migration runs cleanly; 2) Logger captures pick with all fields; 3) Query API returns picks by asset class, date range, verdict |
| **Priority** | P0 |
| **ETA** | 2026-05-20 |
| **Blocks** | PR-T1, PR-T3, PR-T4 |

### PR-2026-0518-2: CRYPTO quan_engine / rapid_fire Investigation

| Field | Detail |
|-------|--------|
| **Title** | `investigate(crypto): quan_engine alpha decay + rapid_fire overlay` |
| **Scope** | Audit quan_engine signal quality; backtest rapid_fire as potential overlay |
| **Files** | `investigations/quan_engine_2026-05-18.md`, `strategies/crypto/rapid_fire_backtest.py`, `config/crypto_blocks.yaml` |
| **Tests** | Backtest produces WR/PF/PBO on 90-day window; rapid_fire shadow mode config valid |
| **Acceptance** | 1) Audit report with alpha decay analysis; 2) rapid_fire backtest results (WR, PF, PBO); 3) Block definitions for investigation period |
| **Priority** | P1 |
| **ETA** | 2026-05-22 |
| **Blocks** | C-005, C-006, C-007 |

### PR-2026-0518-3: COMMODITY COT Lag Correction + Concentration Cap

| Field | Detail |
|-------|--------|
| **Title** | `fix(commodity): COT data staleness + CT=F concentration cap` |
| **Scope** | Mark COT-derived signals stale after 3 days; enforce 40% CT=F concentration limit |
| **Files** | `filters/cot_staleness.py`, `filters/concentration_cap.py`, `config/commodity_limits.yaml`, `db/migrations/006_concentration.sql` |
| **Tests** | COT signal marked stale on day 4; CT=F blocked at 41% concentration; pass at 39% |
| **Acceptance** | 1) 0 signals with >3day stale COT; 2) CT=F never exceeds 40% in rolling 7d window; 3) Filter rejection logged with FT-002/FT-009 |
| **Priority** | P0 |
| **ETA** | 2026-05-19 |
| **Blocks** | M-001, M-002, M-005 — **unblocks PBO computation** |

### PR-2026-0518-4: ETF VIX<25 Gate Wire-Up

| Field | Detail |
|-------|--------|
| **Title** | `feat(etf): Wire VIX<25 gate for new position blocking` |
| **Scope** | Block new ETF positions when VIX >= 25 at market open (09:35 ET) |
| **Files** | `gates/vix_gate.py`, `config/etf_gates.yaml`, `data/vix_feed.py`, `tests/test_vix_gate.py` |
| **Tests** | VIX=24.9 -> positions allowed; VIX=25.0 -> blocked; VIX=30 -> blocked with alert |
| **Acceptance** | 1) Gate blocks at VIX>=25; 2) Existing positions not affected; 3) Block logged with VIX level; 4) Gate bypass requires PM approval code |
| **Priority** | P0 |
| **ETA** | 2026-05-20 |
| **Blocks** | E-005, E-006 — **required for MONEY_READY upgrade** |

### PR-2026-0518-5: EQUITY Symbol Universe Manager + Filter Traceback

| Field | Detail |
|-------|--------|
| **Title** | `feat(equity): Symbol universe manager + filter traceback scaffold` |
| **Scope** | Define EQUITY symbol universe with blocks; scaffold filter traceback system |
| **Files** | `config/equity_universe.csv`, `config/symbol_blocks.yaml`, `core/universe_manager.py`, `core/filter_traceback.py` |
| **Tests** | Universe loads with >=200 tickers; AMD/NIO in block list; traceback produces structured rejection |
| **Acceptance** | 1) `equity_universe.csv` with 200+ tickers; 2) Block list includes AMD, NIO; 3) Filter traceback generates FT-007 for blocked symbols; 4) Universe diff tracking active |
| **Priority** | P1 |
| **ETA** | 2026-05-24 |
| **Blocks** | Q-003, PR-T2 scaffold |

### PR Merge Order (Dependencies)

```
Day 1 (2026-05-18): PR-2026-0518-3 (COMMODITY fix) — highest priority unblock
Day 1 (2026-05-18): PR-2026-0518-1 (Traceability core) — foundation layer

Day 2 (2026-05-19): PR-2026-0518-4 (ETF VIX gate) — MONEY_READY requirement
Day 2 (2026-05-19): PR-2026-0518-2 (CRYPTO investigation) — parallel, no deps

Day 3-4 (2026-05-20..21): PR-2026-0518-5 (EQUITY universe) — needs PR-2026-0518-1
```

---

## APPENDIX A: CHANGELOG (2026-05-17 -> 2026-05-18)

| Section | Change Type | Detail |
|---------|------------|--------|
| Dashboard | UPDATE | ETF n: 71->75; BOND n: 0->1 |
| Dashboard | NEW | P0.5 Gate Config panel shipped |
| Section 4 | NEW | **Pick Traceability System** — full spec with PR-T1..PR-T5 |
| Section 5 | UPDATE | Convergence map expanded; stuck items flagged |
| Section 6 | UPDATE | 30/60/90 roadmap refreshed with 90-day target allocation |
| Section 7 | NEW | Today's session focus with 5 commit targets |
| Section 8 | NEW | Decision D-009 (Pick Traceability P0) added |
| Section 9 | NEW | 5 PRs defined with full detail and merge order |
| CRYPTO | UPDATE | C-005..C-008 added for strategy investigation |
| COMMODITY | UPDATE | M-001..M-008 restructured; paper pilot added |
| ETF | UPDATE | E-005..E-007 VIX gate detailed; E-008..E-011 MONEY_READY gate added |
| EQUITY | UPDATE | Q-001..Q-007 reorganized; PEAD and DOW tilt detailed |
| FOREX | UPDATE | F-001..F-008 expanded; criteria table added |
| BOND | UPDATE | B-001..B-009 expanded; UST TSMOM detailed; FRED dependency added |
| FUTURES | UPDATE | U-001..U-003 unchanged; unblock criteria table added |
| Infra | UPDATE | X-001..X-010 refreshed; X-010 (Gate Config) marked shipped |

### Key Files Referenced

| File | Purpose |
|------|---------|
| `core/pick_lifecycle_logger.py` | New: Pick traceability core logger (PR-T5) |
| `db/migrations/005_pick_lifecycle.sql` | New: Pick lifecycle table schema |
| `db/migrations/006_concentration.sql` | New: Concentration tracking table |
| `config/equity_universe.csv` | New: EQUITY symbol universe (200+ tickers) |
| `config/commodity_limits.yaml` | Updated: CT=F 40% cap, COT staleness rules |
| `config/etf_gates.yaml` | Updated: VIX<25 gate threshold |
| `config/crypto_blocks.yaml` | New: quan_engine/rapid_fire investigation blocks |
| `filters/cot_staleness.py` | New: COT 3-day staleness filter |
| `filters/concentration_cap.py` | New: Per-class concentration limit enforcer |
| `gates/vix_gate.py` | New: VIX threshold gate for ETF |
| `strategies/crypto/rapid_fire_backtest.py` | New: rapid_fire overlay backtest |
| `investigations/quan_engine_2026-05-18.md` | New: quan_engine audit report template |
| `reports/MASTER_ACTION_PLAN_2026-05-18.md` | This document |

---

*End of MASTER ACTION PLAN — 2026-05-18*

*Next plan: MASTER_ACTION_PLAN_2026-05-19.md (to be generated 2026-05-19 06:00 UTC)*
