# multi_asset_cot — DB Audit Report
**Date:** 2026-05-14 | **Reason:** Verify PF=21.86 isn't a data artifact from 92.7% CT=F concentration

---

## 1. System Snapshot

| Field | Value |
|---|---|
| Name | `multi_asset_cot` |
| Asset Class | COMMODITY |
| Status | monitoring |
| Last Signal | 2026-05-12T21:58 UTC |

## 2. Aggregate Metrics

| Metric | Value | Flag |
|---|---|---|
| Resolved Picks | 102 | |
| Wins / Losses | 96W / 6L | |
| Win Rate | 94.1% | ⚠️ Extremely high |
| Total PnL % | +428.97% | ⚠️ 4.3× return on 102 trades |
| Avg Win | 4.68% | |
| Avg Loss | 3.43% | ⚠️ Avg loss nearly equals avg win |
| Profit Factor | 21.86 | ⚠️ Off the charts |
| Max Drawdown | 17.83% | |
| Calmar Ratio | 59.43 | ⚠️ 10× typical "excellent" threshold |
| Expectancy | 4.21 | |

## 3. Concentration Analysis

| Symbol | Wins | Losses | WR | PnL | Share of Total |
|---|---|---|---|---|---|
| **CT=F** (Cotton) | 91 | 5 | 94.8% | +406.58 | **92.7%** |
| ZW=F (Wheat) | 5 | 0 | 100% | +27.29 | 6.2% |
| KC=F (Coffee) | 0 | 1 | 0% | −4.91 | 1.1% |

**Verdict on concentration:** The PF=21.86 is almost entirely driven by the CT=F position. Without CT=F, the system would show ~5 trades with modest profit. The PF is NOT a diversified edge — it's a single-symbol, single-direction bet.

## 4. Directional Bias

| Direction | Wins | Losses | WR |
|---|---|---|---|
| **SHORT** | 95 | 5 | **95.0%** |
| LONG | 0 | 1 | 0.0% |

The system is **100% short-biased** on cotton. It has never taken a winning long trade. This is not a statistical edge — it's a bet that cotton futures go down, which happened to work during the backtest window.

## 5. Red Flags

### 🔴 PF=21.86 is Not a Generalizable Edge
- A 95% short win rate on a single commodity over 102 trades is statistically implausible without one of:
  1. **Data leakage** (forward-looking COT data used in backtest)
  2. **Look-ahead bias** (COT reports released Friday, but trade entered before that)
  3. **Temporary regime** (cotton downtrend alignment that won't persist)

### 🔴 avg_win ≈ avg_loss (4.68% vs 3.43%)
A genuine edge typically shows asymmetric R:R (winners >> losers). Here, winners are only 1.36× larger than losers. The 94.1% WR is doing ALL the heavy lifting. If WR regresses to even 60%, the system goes deeply negative.

### 🔴 cap_value_pct = 500.0
Extremely high cap — effectively uncapped. If this were lowered to a realistic value (e.g., 100%), the PF would drop sharply because the rare losses might be capped while wins enjoy the full move.

### 🔴 No audited WR
`audited_wr_pct: null`, `audited_wr_coverage: 0` — this system has never been through the independent audit pipeline. The 94.1% WR is self-reported.

### 🟡 COT data timing risk
COT reports are released Fridays at 3:30 PM ET with data as of Tuesday. If the backtest enters trades before the report is available (look-ahead bias), the entire edge is an artifact.

## 6. Monte Carlo Validation

The `cot_step7_ror_mc.json` file confirms 10,000 bootstrap simulations ran. However, bootstrap resampling of the SAME trades doesn't test for data leakage — it only tests whether the PnL sequence is path-dependent. A Monte Carlo on leaked data will still look good.

## 7. Verdict

### 🔴 The PF=21.86 IS a data artifact — but not from concentration alone.

The artifact is caused by the **intersection of three factors:**

1. **92.7% single-symbol concentration** (CT=F) — the PF collapses without it
2. **100% short-only bias** — never taken a winning long; this is directional luck, not skill
3. **Likely COT data leakage** — 95% short WR on a single futures contract with avg_win ≈ avg_loss is the fingerprint of a backtest using data not available at trade time

### Recommendation: P1 — Flag for walk-forward audit before any paper/live use.

The system should be marked with `requires_walkforward_audit` in the quality gates and excluded from Smart Picks / High Conviction until:
1. The COT data pipeline is audited for look-ahead bias
2. A clean walk-forward (train on pre-2025, test on 2025-2026) confirms OOS performance
3. The system demonstrates at least one winning LONG trade

---

## 8. Action Items

- [ ] **P1:** Add `multi_asset_cot` to `REQUIRES_WALKAHEAD_AUDIT` in `audit_trail/quality_gates.py`
- [ ] **P1:** Run COT data pipeline audit — verify report release dates vs trade entry timestamps
- [ ] **P2:** Run walk-forward split (pre-2025 train / 2025+ test)
- [ ] **P2:** Flag as `toxic_concentration` in dashboard UI until diversified
- [ ] **P3:** Lower `cap_value_pct` from 500 → 100 for realism
