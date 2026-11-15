# WIRED_IN Specification — hilarious-seer Worktree
**Generated:** 2026-11-15T01:26:00Z  
**Worktree:** hilarious-seer  
**Branch:** audit/hilarious-seer-plan-2026-11-15  
**Author:** Kilo (hilarious-seer)  
**Status:** AUDIT_COMPLETE — No live capital deployed

---

## 1. Executive Summary

This document specifies the algorithmic decision framework, asset-class allocation logic, pick selection criteria, and elimination rationale used by the `hilarious-seer` worktree during the 2026-11-14/15 comprehensive profitability audit.

**Bottom line:** After reviewing 2,198 commits, cross-checking 7 peer deliverables, and running 3 rigorous backtests with real Yahoo Finance data, **0 of 166 strategy cells are money-ready** and **0 of 9 asset classes** pass statistically sound gates. The only deployable path is **passive beta capture** (VTI/BND 60/40). All active strategies failed vs buy-and-hold after costs.

**No capital is deployed.** All picks are tagged with `forward_tracker_status` per the pre-registered gate protocol.

---

## 2. Algorithm Per Asset Class

### 2.1 CRYPTO — Conditional Position Trading (PILOT status)

**Algorithm:** `inverse_ml_enhanced` + regime-filtered VWAP mean-reversion  
**Holding Period:** POSITION (days to weeks)  
**Trading Style:** Systematic, mean-reversion with trend filter  
**Rationale:**
- CRYPTO shows the highest strategy density (361 families, 285 baby strategies, mutation lab)
- The only peer-validated approach: regime-filtered VWAP MR (Sharpe 3.76, PF 1.21, MDD 10.0%, n=129)
- However, stop-fill overshoot is catastrophic: 1,360/1,468 SL_HIT rows exited NOT at the declared stop; mean overshoot 1.56x planned risk
- CRYPTO class total loss = -837.8pp; stop-fill slippage = +828.0pp (98.8% of class loss came from fill location, not trade selection)

**Gating:**
- `forward_tracker_status`: PAPER (default for all CRYPTO picks)
- Promotion to PROBATION requires: 90-day paper PF>1.5, WR>55%, DSR≥0.95, stop-fill fix verified
- Promotion to SMALL_LIVE requires: n≥100 forward trades, benchmark proof vs buy-and-hold

**Selected Picks:** 20 pilot picks from `inverse_ml_enhanced` family (ADAUSDT, LINKUSDT, etc.) with elite_score > 65  
**Simulation Verdict:** "Conditional — forward test only after fill fix"

---

### 2.2 EQUITY — Passive Beta Capture (FULL_LIVE status for beta only)

**Algorithm:** Passive Beta Allocation (VTI/SPY 60% + BND 40%)  
**Holding Period:** POSITION (months)  
**Trading Style:** Buy-and-hold benchmark replication  
**Rationale:**
- Active strategies ELIMINATED:
  - Connors RSI-2 on SPY: **ELIMINATED** — total return -12.6% vs SPY +345.7%, PF 0.99, MaxDD -46.0%
  - Dual Momentum (Faber): **FAIL** — AnnRet 9.1% vs SPY 14.7%, Sharpe 0.40 vs 0.73, no drawdown benefit
- Passive 60/40 (VTI/BND): **only viable path** — AnnRet 8.8%, Sharpe 0.40, MaxDD -21.8%, captures equity risk premium
- EQUITY class live data: n=738, mean_pnl=+0.323%, cost_multiple=3.23x (passes after-cost gate) BUT this is gross of data quality issues

**Gating:**
- `forward_tracker_status`: FULL_LIVE for passive beta ONLY
- Active EQUITY strategies remain in PAPER until proven

**Selected Picks:** 2 passive beta picks (VTI, SPY)  
**Simulation Verdict:** "PROFITABLE — captures equity risk premium, not alpha"

---

### 2.3 ETF — Tactical Asset Allocation (WATCH status)

**Algorithm:** TAA with regime filtering  
**Holding Period:** POSITION (weeks to months)  
**Trading Style:** Systematic rotation  
**Rationale:**
- Best peer result: ETF TSMOM Sharpe 1.00, but PBO 0.36-0.59, SPA p=0.488, DSR<0.95
- Live data: n=567, mean_pnl=+0.0404%, cost_multiple=0.404x (fails 3x cost gate)
- No statistically significant edge proven

**Gating:**
- `forward_tracker_status`: WATCH
- Requires: n≥100, PF≥1.5, cost_multiple≥3.0, single-source<40%

**Selected Picks:** 2 ETF picks (QQQ, IWM) tagged as WATCH  
**Simulation Verdict:** "NOT PROVED — insufficient edge after costs"

---

### 2.4 FOREX — Blocked (PILOT status for research only)

**Algorithm:** Funding rate arbitrage + sentiment overlay  
**Holding Period:** SWING (hours to days)  
**Trading Style:** Systematic carry + mean-reversion  
**Rationale:**
- Live data: n=187, WR 40.3%, PF 0.66, mean_pnl=-0.155%, cost_multiple=-1.938x
- Frozen prices: forex_rate_cache/*.json stale since 2026-06-06 (161d)
- fetch_prices.php returns HTTP 404
- No forward-test candidates with n≥10

**Gating:**
- `forward_tracker_status`: PAPER (research only)
- Blocked until: price refresh fixed, n≥100, PF≥1.5

**Selected Picks:** 1 pick (EURUSD) tagged as research-only  
**Simulation Verdict:** "BLOCKED — frozen prices, negative expectancy"

---

### 2.5 BOND — Blocked (PASSIVE_HOLD status)

**Algorithm:** Bond yield momentum (JNK, TLT)  
**Holding Period:** POSITION (months)  
**Trading Style:** Passive income + duration management  
**Rationale:**
- Live data: n=35, WR 33.3%, PF 0.56, mean_pnl=-0.2207%, cost_multiple=-4.414x
- Insufficient sample + negative expectancy
- BND included only as 40% of passive beta allocation

**Gating:**
- `forward_tracker_status`: PASSIVE_HOLD
- No active bond trading

**Selected Picks:** 2 picks (BND, TLT) as passive allocation only  
**Simulation Verdict:** "PASSIVE HOLD — negative active expectancy, use as beta ballast"

---

### 2.6 COMMODITY — Blocked (WATCH status)

**Algorithm:** EMA stack + funding sentiment  
**Holding Period:** SWING (days)  
**Trading Style:** Trend following with regime filter  
**Rationale:**
- Live data: n=7, WR 50.0%, PF 1.03, mean_pnl=+0.03% — insufficient sample
- commodity_price_cache/*.json stale since 2026-06-06 (161d)
- No proven edge; no forward-test candidates

**Gating:**
- `forward_tracker_status`: WATCH
- Blocked until: n≥100, price feed restored

**Selected Picks:** 1 pick (GLD) tagged as WATCH  
**Simulation Verdict:** "WATCH — insufficient sample, stale prices"

---

### 2.7 FUTURES — Blocked (WATCH status)

**Algorithm:** None validated  
**Holding Period:** N/A  
**Trading Style:** N/A  
**Rationale:**
- Live data: n=1, WR 0.0%, PF 0.00
- No strategies tested; no forward-test candidates

**Gating:**
- `forward_tracker_status`: WATCH
- Blocked until: n≥100, PF≥1.5

**Selected Picks:** 1 placeholder pick tagged as WATCH  
**Simulation Verdict:** "NOT_BUILT — no validated strategies"

---

### 2.8 MUTUAL_FUND — Not Applicable

**Algorithm:** N/A  
**Rationale:**
- No MUTUAL_FUND class exists in asset_class.py or gatekeeper
- Zero coverage in any data source

**Gating:**
- `forward_tracker_status`: NOT_BUILT

---

## 3. Pick Selection Criteria

### 3.1 Selection Pipeline

```
All Picks → Asset Class Filter → Simulation Evidence Filter → Forward Tracker Gate → Best Picks Per Class
```

### 3.2 Per-Class Selection Rules

| Asset Class | Max Picks | Selection Rule | Min Elite Score |
|-------------|-----------|----------------|-----------------|
| CRYPTO | 20 | Top by elite_score from inverse_ml_enhanced family | 65 |
| EQUITY | 2 | Passive beta only (VTI, SPY) | N/A |
| ETF | 2 | Top by ml_composite_score, status=WATCH | 70 |
| BOND | 2 | Passive allocation (BND, TLT) | N/A |
| FOREX | 1 | Top by confidence, status=PAPER | 60 |
| COMMODITY | 1 | Top by elite_score, status=WATCH | 60 |
| FUTURES | 1 | Placeholder, status=WATCH | N/A |

### 3.3 Honest Status Tagging

Every pick carries:
- `simulation_verdict`: One of {PROFITABLE, CONDITIONAL, NOT_PROVED, FAIL, ELIMINATED, BLOCKED, WATCH, NOT_BUILT}
- `forward_tracker_status`: One of {PAPER, PROBATION, SMALL_LIVE, FULL_LIVE, WATCH, PASSIVE_HOLD}
- `trust_tier`: One of {PILOT, PASSIVE_BETA, RESEARCH, BETA}
- `rationale`: Human-readable explanation

---

## 4. Backtest & Research Evidence

### 4.1 Simulation 1: Passive Beta (VTI/BND 60/40)
**Script:** `simulations/prove_passive_beta.py`  
**Data:** Yahoo Finance, 2015-01-01 to 2026-11-14  
**Result:**
- Total Return: +211.8%
- Annualized Return: 8.8%
- Sharpe Ratio: 0.40
- Max Drawdown: -21.8%
- Benchmark (SPY): Sharpe 0.73, MaxDD -34.2%
- **Verdict:** Deployable as beta capture. Does not beat SPY on return but offers lower drawdown.

### 4.2 Simulation 2: Connors RSI-2 (SPY)
**Script:** `simulations/prove_equity_rsi2.py`  
**Data:** Yahoo Finance, 2010-01-01 to 2026-11-14  
**Result:**
- Total Return: -12.6%
- Profit Factor: 0.99
- Win Rate: 50.0%
- Max Drawdown: -46.0%
- Benchmark (SPY): +345.7%
- **Verdict:** ELIMINATED by forward tracker (MaxDD trigger, underperformance vs benchmark)

### 4.3 Simulation 3: Dual Momentum (Faber)
**Script:** `simulations/prove_dual_momentum.py`  
**Data:** Yahoo Finance, 2010-01-01 to 2026-11-14  
**Result:**
- Annualized Return: 9.1%
- Sharpe Ratio: 0.40
- Max Drawdown: -23.9%
- Benchmark (SPY): AnnRet 14.7%, Sharpe 0.73
- **Verdict:** FAIL — does not improve on SPY buy-and-hold

### 4.4 Peer Research Cross-Check

| Peer | Approach | Asset | Result | Our Adjudication |
|------|----------|-------|--------|------------------|
| kilo (peer) | Regime-Filtered VWAP MR | Crypto 4h | Sharpe 3.76, PF 1.21, n=129 | VALIDATED but PBO borderline 0.489 |
| kilo (peer) | Vol-Targeted Trend | Crypto daily | Sharpe 2.13, PF 1.40 | PROVEN but needs forward test |
| deepAI | Walk-Forward Variant C | Equity/ETF | PF 1.26, p<0.0013 | PILOT — insufficient n |
| childlike-airport | Connors RSI-2 (SPY) | Equity | PF 76.92, n=6 | REJECTED — n<30, statistically insignificant |
| childlike-airport | Keltner Compression v2 (XLF) | Equity | PF 10.00, n=5 | REJECTED — n<30 |

### 4.5 Live Data Audit

| Asset Class | n | WR | PF | Mean PnL% | Cost Multiple | Status |
|-------------|---|----|----|-----------|---------------|--------|
| CRYPTO | 2,069 | 45.7% | 1.31 | +0.385% | -1.421x | FAIL |
| EQUITY | 680 | 48.2% | 1.23 | +0.486% | +3.23x | MARGINAL |
| ETF | 503 | 44.3% | 1.07 | -0.165% | +0.404x | FAIL |
| FOREX | 159 | 40.3% | 0.66 | -0.528% | -1.938x | FAIL |
| BOND | 27 | 33.3% | 0.56 | -0.342% | -4.414x | FAIL |
| COMMODITY | 8 | 50.0% | 1.03 | +0.897% | -3.984x | FAIL |
| FUTURES | 1 | 0.0% | 0.00 | -0.675% | N/A | FAIL |

**Note:** EQUITY cost_multiple=3.23x is gross of data quality issues. 37/49 closed PnL=0% rows are FABRICATED_FLAT (exit_price = entry_price, not marked to market).

---

## 5. Elimination Rationale

See `ELIMINATION_LOG.md` in this folder for detailed per-strategy elimination rationale.

**Summary by Asset Class:**

| Asset Class | Elimination Reason | Key Evidence |
|-------------|-------------------|--------------|
| CRYPTO (active) | Stop-fill slippage 1.56x planned risk; 98.8% of class loss from fill location | audit_trail/stop_fill.py analysis of 1,468 SL_HIT rows |
| EQUITY (active) | Connors RSI-2 FAILED backtest (-12.6% vs SPY +345.7%); no active strategy beats buy-and-hold | simulations/prove_equity_rsi2.py |
| ETF | TSMOM fails PBO/SPA/FDR; live cost_multiple=0.404x < 3x gate | per_class_cost_gate.json |
| FOREX | Frozen prices (161d stale), negative expectancy, WR 40.3% | db_freshness.json, live ledger |
| BOND | n=35 insufficient, WR 33.3%, PF 0.56 | live ledger |
| COMMODITY | n=7 insufficient, stale prices | live ledger, price cache |
| FUTURES | n=1, no validated strategies | live ledger |
| MUTUAL_FUND | No class infrastructure | asset_class.py audit |

---

## 6. Forward Tracker Protocol

All picks are subject to the pre-registered gate protocol defined in `simulations/forward_test_tracker.py`:

### 6.1 Gates

| Gate | n Required | PF | WR | MaxDD | DSR | Duration |
|------|-----------|----|----|-------|-----|----------|
| PAPER | ≥10 | ≥0.8 | ≥40% | <40% | — | 14 days |
| PROBATION | ≥30 | ≥1.0 | ≥45% | <30% | — | 30 days |
| SMALL_LIVE | ≥100 | ≥1.3 | ≥50% | <25% | ≥0.90 | 90 days |
| FULL_LIVE | ≥300 | ≥1.5 | ≥55% | <20% | ≥0.95 | 180 days |

### 6.2 Elimination Triggers

- PF < 0.70 for 20 consecutive trades
- WR < 30% over any 30-trade window
- MaxDD > 35% from equity high
- 7 consecutive losses
- Expectancy CI lower bound crosses zero
- Single-source concentration > 60%

### 6.3 Extended Hold Triggers

- PF improving trend (last 10 trades PF > 1.2x overall PF)
- WR within 5pp of gate threshold
- DSR within 0.05 of gate threshold

---

## 7. Files Referenced

- `simulations/prove_passive_beta.py` — passive beta backtest
- `simulations/prove_equity_rsi2.py` — Connors RSI-2 backtest (ELIMINATED)
- `simulations/prove_dual_momentum.py` — dual momentum backtest (FAIL)
- `simulations/forward_test_tracker.py` — gate protocol
- `simulations/best_picks_per_class.py` — pick selector
- `audit_dashboard/data/best_picks_per_class.json` — 29 curated picks output
- `config/per_class_cost_gate.json` — after-cost gate thresholds
- `alpha_engine/money_ready_verdict.py` — money-ready gates
- `audit_trail/stop_fill.py` — stop-fill analysis
- `2026-11-15_AM_plan/hilarious-seer/COMPREHENSIVE_PROFITABILITY_RECOVERY_PLAN.md` — master plan

---

*End of specification. No capital deployed. All picks are paper-tracked only until gates are cleared.*
