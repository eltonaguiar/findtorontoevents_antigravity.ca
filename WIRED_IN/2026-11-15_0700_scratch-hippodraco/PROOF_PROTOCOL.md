# PROOF_PROTOCOL.md — Pre-Registered Forward-Test Protocol
Generated: 2026-11-15T08:00Z UTC  
Repository: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/  
Protocol version: 1.0  
Status: Template — to be completed per candidate before any forward test begins  

> **Rule:** No strategy may be called "profitable" or recommended for real-money deployment unless it passes ALL 10 proof gates below, in order, on a pre-registered, forward-tested basis.  
> **Rule:** Any parameter change after seeing forward-test results constitutes a new hypothesis and must re-enter the full pipeline from §2.

---

## 1. Candidate Identification

| Field | Value |
|-------|-------|
| Strategy name | |
| Asset class / instrument | |
| Timeframe / holding period | |
| Entry logic | |
| Exit logic / TP-SL | |
| Position sizing / risk mgmt | |
| Statistical / ML methods | |
| Hypothesis ID | |
| Registration date | |
| Registered by | |

---

## 2. Pre-Registration (Before Any Data Is Seen)

### 2.1 Hypothesis Statement

**Economic rationale:**  
> [Describe the economic mechanism that should produce an edge. Cite academic literature or prior market observation.]

**Expected direction:** LONG / SHORT / BOTH  
**Expected holding period:** [days / weeks / months]  
**Expected win rate:** [%]  
**Expected profit factor:**  
**Expected max drawdown:** [%]

### 2.2 Data Specification

| Item | Specification |
|------|---------------|
| Price source | |
| Price type (close / OHLCV / tick) | |
| Adjustments (splits / dividends / corporate actions) | |
| Timezone | |
| Start date | |
| End date (in-sample cutoff) | |
| Out-of-sample start date | |
| Survivorship bias handling | |
| Delisted instrument handling | |

### 2.3 Signal Construction

| Parameter | Value | Range tested | Justification |
|-----------|-------|--------------|---------------|
| Entry trigger | | | |
| Exit trigger | | | |
| TP level | | | |
| SL level | | | |
| Position size | | | |
| Lookback windows | | | |
| Threshold values | | | |

### 2.4 Cost Model

| Component | Value | Basis |
|-----------|-------|-------|
| Commission (per side) | | |
| Slippage (per side) | | |
| Spread | | |
| Funding / borrow | | |
| Tax (Canadian) | | |
| Total round-trip cost | | |
| Breakeven cost level | | |
| Margin of safety | | |

### 2.5 Benchmark

| Benchmark | Rationale |
|-----------|-----------|
| Primary | |
| Secondary | |
| Risk-free rate | |

---

## 3. Proof Standard — 10 Gates (Must Pass ALL)

| Gate | Requirement | Threshold | Result | Pass/Fail |
|------|-------------|-----------|--------|-----------|
| G1 | Temporal discipline — features computed only from past data; no look-ahead | Strict chronological split | | |
| G2 | Walk-forward optimization with embedded OOS windows | WFE > 0.6; parameter-stability heatmap | | |
| G3 | Multiple-testing correction — state total configs tried | DSR ≥ 0.95; PBO ≤ 0.10; Bonferroni/Holm applied | | |
| G4 | Monte Carlo resampling — block-bootstrap trade sequences | % paths positive after costs > 95%; 5th-percentile worst case > 0 | | |
| G5 | Full friction model — spread, commission, slippage, funding, tax | Cost-adjusted PF ≥ 1.15 after all costs | | |
| G6 | Statistical significance — bootstrap CI for mean excess return | CI excludes zero; t-stat > 2.0; p < 0.05 | | |
| G7 | Regime robustness — bull/bear/sideways × high/low vol | Positive expectancy in majority of regimes | | |
| G8 | Shuffle control — permuted prices must NOT reproduce performance | Shuffled performance < real performance | | |
| G9 | Pre-registered forward test — defined protocol, duration, rules, thresholds | n ≥ 100 closed picks over ≥ 3 months | | |
| G10 | Reproducibility — fixed seeds, versioned data, documented formulas, runnable code | Reproducible by independent party | | |

---

## 3.1 Walk-Forward Specification

| Parameter | Value |
|-----------|-------|
| In-sample window | |
| Out-of-sample window | |
| Number of folds | |
| Recalibration frequency | |
| Parameter stability metric | |
| WFE target | > 0.6 |

---

## 3.2 Multiple-Testing Correction

| Item | Value |
|------|-------|
| Total configurations tried (project-wide) | |
| Bonferroni-adjusted alpha | |
| Holm-adjusted alpha | |
| DSR | |
| PBO | |
| White's Reality Check p-value | |

---

## 3.3 Monte Carlo / Block Bootstrap

| Parameter | Value |
|-----------|-------|
| Number of bootstrap paths | |
| Block length (for autocorrelation) | |
| % of paths positive after costs | |
| 5th-percentile worst case | |
| 95% CI for mean excess return | |
| Lower CI bound > 0 | |

---

## 3.4 Regime Splits

| Regime | Period | Net return | Win rate | PF | Positive? |
|--------|--------|------------|----------|-----|-----------|
| Bull market | | | | | |
| Bear market | | | | | |
| Sideways market | | | | | |
| High volatility | | | | | |
| Low volatility | | | | | |

---

## 3.5 Shuffle Control

| Test | Real performance | Shuffled performance | Pass? |
|------|-----------------|---------------------|-------|
| Same pipeline on permuted prices | | | |

---

## 4. Forward-Test Protocol (Pre-Registered)

### 4.1 Forward-Test Definition

| Parameter | Value |
|-----------|-------|
| Start date | |
| End date (planned) | |
| Minimum duration | 3 months |
| Minimum closed trades | n ≥ 100 |
| Tracking URL / dashboard | |
| Decision thresholds | |

### 4.2 Forward-Test Kill Switches

| Trigger | Value | Action |
|---------|-------|--------|
| Drawdown halt | -15% (monthly) / -30% (annual) | Halt all trading |
| Win rate floor | < 45% over rolling 20 trades | Review / pause |
| PF floor | < 1.0 over rolling 50 trades | Halt |
| Consecutive losses | 8 | Pause and review |
| No trades | 14 calendar days | Review / dormant |

### 4.3 Forward-Test Tracking Columns

| Column | Description |
|--------|-------------|
| timestamp | ISO 8601 UTC |
| asset | Symbol / pair |
| regime | Bull / bear / sideways |
| direction | LONG / SHORT / FLAT |
| expected_return | Predicted % return |
| TP | Take-profit price |
| SL | Stop-loss price |
| horizon | Expected holding period |
| confidence | Model confidence (0-1) |
| actual_outcome | Realized % return |
| hit_miss | TP hit / SL hit / time exit |
| link_to_trade_log | File path or URL |

### 4.4 Forward-Test Evaluation Rules

| Condition | Action |
|-----------|--------|
| Pass all 10 gates on forward data | Candidate advances to sizing review |
| Fail any gate on forward data | Candidate rejected; do not deploy |
| Fail any kill-switch trigger | Immediate halt |
| Parameter change after seeing results | New hypothesis; re-enter full pipeline |

---

## 5. Reproducibility Checklist

| Item | Status |
|------|--------|
| Fixed random seeds documented | |
| Data version / hash recorded | |
| Exact formulas documented | |
| Runnable code provided | |
| Independent re-execution possible | |

---

## 6. Final Verdict (Fill In Exactly One)

| Verdict | Criteria | Candidates |
|---------|----------|------------|
| PROVEN | Passes ALL 10 gates on forward-tested data | None in this repo |
| PROMISING | Passes temporal discipline, shuffle, walk-forward, friction; fails only sample size | EQUITY `stocks_rsi2_pullback` (n=78, needs n≥100) |
| REJECT | Fails any of gates 1-8 (temporal, shuffle, walk-forward, friction, significance, regime, multiple testing) | All other strategies in this repo |

**Current status: No candidate qualifies as PROVEN or PROMISING.** EQUITY `stocks_rsi2_pullback` is the closest near-miss (n=78, PF 1.11, WR 44.9%) but fails the SPY benchmark gate (t=1.05, median excess -0.57%) and n < 100.

---

## 7. Sign-Off

| Role | Name | Date |
|------|------|------|
| Lead Quant | | |
| Statistician | | |
| Governance | | |

---
