# Profitability Plan — Per-Asset-Class Success Criteria, Leakage Avoidance, Root-Cause & Timeframe

**Date:** 2026-11-15
**Author:** finpredict-v4
**Supersedes:** prior plans where evidence changed the conclusion.

---

## 1. The Problem to Solve

The system has struggled for years across all asset classes. The audits established two truths:

1. **Measurement bugs** (forged `TIME_EXIT` rows, stale prices, PnL=0% stale-equal, direction-sign mismatches) contaminated every verdict. → *Our QA gate (`tools/qa_ledger.py`) now catches these.*
2. **No asset class has shown proven alpha** — 0/23 hypotheses survived clean OOS in the peer final plan. → *We must test hypotheses without forward-looking leakage and keep only robust ones.*

This plan defines, per asset class, the **success criteria**, the **leakage rules**, the **root-cause analysis of failed picks**, and the **holding-period (timeframe) fit**.

---

## 2. Anti-Leakage Rules (apply to every test)

Every backtest/hypothesis must obey:

| Rule | Enforcement |
|------|-------------|
| **L1 — No look-ahead** | Signal at day t uses only data ≤ t. All rolling indicators must `shift(1)` before use (the harness does this). |
| **L2 — Out-of-sample split** | Train on first 60%, TEST on last 40% — the test slice is never touched during design (the harness does this). |
| **L3 — Cost-inclusive** | 10bp round-trip on every position change; expense drag on holdings. |
| **L4 — No survivorship** | Benchmark is buy-and-hold (not "best performer"), and the symbol universe is fixed upfront. |
| **L5 — No re-selection on test** | Once a hypothesis fails on the test slice, it is not re-tuned. Kill it. |
| **L6 — Multiple-testing** | Report DSR / PBO for surprise candidate; reject DSR<0.95. |

---

## 3. Per-Asset-Class Success Criteria

A class is **promoted** only if it clears ALL gates on **untouched OOS data** AND a **90-day paper forward test**. Fail = kill.

### 3.1 Mutual Funds / ETFs (Allocation — the deployable core)
- **Goal:** lowest-cost, broad, benchmark-relative allocation; NOT alpha.
- **Success (deploy-scale):** min-cost index fund/ETF (ER ≤0.10%), AUM ≥$1B, turnover ≤20%, passes the QA fund/ETF gates, and the allocation sleeve beats the 60/40 benchmark over 12 months net of fees.
- **Kill:** fund fails any hard gate (load, 12b-1, high ER, thin AUM).

### 3.2 EQUITY (US)
- **Hypotheses (from harness):** `sma200` (SPY/QQQ), `sma50cross`, `mom6`.
- **Success:** on the untouched TEST slice, Sharpe > baseline AND maxDD < baseline (already satisfied for sma200 across SPY/QQQ: Sharpe 0.93/0.97 vs 0.86/0.79). Then 90-day paper, net-of-cost, beats SPY total return.
- **Kill:** fails SPY benchmark (the earlier `NO_ALPHA_BETA` verdict), or fails OOS on anything re-run.

### 3.3 CRYPTO
- **Hypothesis:** `sma200` on liquid majors (BTC passed; ETH failed).
- **Success:** test-slice Sharpe > baseline (BTC: 0.57 vs 0.46), then **forward ( n≥100, PF≥1.3, WR≥55%, cost-inclusive, beats BTC-hold.
- **Kill:** forward PF <1.0 at n=100, or fails the fill/measurement gate (still a blocker).

### 3.4 COMMODITY (GLD)
- **Hypothesis:** `sma200` on GLD (passed: Sharpe 1.01 vs 0.95).
- **Success:** test-slice Sharpe > baseline; forward n≥100, PF≥1.3, cost-inclusive, beats GLD-hold.
- **Kill:** forward PF <1.0 or trend filter underperforms buy-and-hold.

### 3.5 BOND / FOREX / OTHER
- **Hy:** `sma200` on TLT FAILED (negative Sharpe both ways); FOREX unusable (delisted benchmark).
- **Success:** re-test only once data is clean (BOND) / a real benchmark exists (FOREX). Until then **blocked**.

---

## 4. Root-Cause Analysis of Failed Picks

For any class/strategy that fails, we need *why* — not just "it lost." Add a `tools/root_cause_analyzer.py` that, per class, buckets closed picks by:

| Dimension | What it reveals |
|-----------|-----------------|
| **Exit reason** | TP_HIT vs SL_HIT vs TIME_EXIT vs EXPIRED — if TIME_EXIT dominates, holding period is wrong; if SL_HIT dominates with positive drift, stop too tight. |
| **Holding period** | days open. Timeframes should match the class (trend=weeks, allocation=months). If the model trades at the wrong timeframe, it fails. |
| **Direction** | LONG vs SHORT asymmetry (the CRYPTO SHORT bias). |
| **Symbol concentration** | single-symbol HHI — one bad ticker can sink a class. |
| **Price/PnL anomaly** | QA verdicts (unpriced, stale-equal zero, mismatch) that indicate data bugs rather than strategy failure. |
| **Regime segment** | bull vs bear — a strategy that only works in one regime is fragile. |

**Output:** per-class `FAIL_REASON` with the dominant bucket + recommendation (e.g., "SL_HIT 60% → widen stop / switch to TIME_EXIT").

---

## 5. Timeframe Fit Per Asset Class

| Class | Fit timeframe | Why |
|-------|---------------|-----|
| Mutual funds / ETFs | Months (allocation) | Daily NAV; beta capture; no intraday |
| EQUITY (trend) | Weeks–months | sma200/momentum horizon |
| CRYPTO (trend) | Weeks | BTC sma200; NOT scalping |
| COMMODITY (GLD) | Weeks–months | Trend filter |
| BOND | Months | Carry; trend filter failed |
| FOREX | Blocked | Data unusable |

---

## 6. Execution Roadmap (todos)

1. Write this plan + success criteria → commit.
2. Run `tools/hypothesis_test_harness.py` on the full class universe (already done — keep robust only).
3. Build `tools/root_cause_analyzer.py` and run it on closed picks → identify why failures happen.
4. Build the timeframe fit check into the analyzer.
5. Wire the QA gate + forward-tracker + hypothesis harness into a single scheduled CI run.
6. Commit artifacts + results to main.

**Success gate for the whole effort:** at least one asset class (priority: EQUITY trend, then GLD, then BTC) clears all gates on untouched OOS AND passes a 90-day paper forward test, with no forward-looking leakage in the evidence.
