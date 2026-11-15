# STRATEGY_SHORTLIST.md — Template

## 1. Executive Summary
- **Audit date:** YYYY-MM-DD
- **Total candidates evaluated:** N
- **Verdict summary:**
  - **PROVEN (passes Phase 4):** N
  - **PROMISING (meets some Phase 4 gates, forward-test recommended):** N
  - **REJECTED (fails Phase 4 decisively):** N

---

## 2. Ranking Methodology
Explain the scoring or ranking system used (e.g., composite score across Sharpe, PF, regime robustness, sample size, cost-adjusted return).

---

## 3. Candidate Strategies

### Candidate #1: [Strategy Name]

#### 3.1 Identity
- **Asset class(es):**
- **Timeframe(s):**
- **Entry logic:**
- **Exit logic:**
- **TP / SL parameters:**
- **Position sizing / risk management:**
- **Benchmark:**

#### 3.2 Phase 4 Proof Checklist

| Gate | Status (PASS / FAIL / PARTIAL) | Evidence / Notes |
|------|-------------------------------|------------------|
| 1. Temporal discipline | | |
| 2. Walk-forward optimization | | |
| 3. Multiple-testing correction | | |
| 4. Monte Carlo resampling | | |
| 5. Full friction model | | |
| 6. Statistical significance | | |
| 7. Regime robustness | | |
| 8. Control experiment (permuted data) | | |
| 9. Pre-registered forward test | | |
| 10. Reproducibility | | |

#### 3.3 Phase 5 Metrics

| Metric | Value | Benchmark comparison |
|--------|-------|---------------------|
| CAGR | | |
| Ann. volatility | | |
| Sharpe | | |
| Sortino | | |
| Calmar | | |
| Max drawdown | | |
| Avg drawdown | | |
| Recovery time | | |
| Win rate | | |
| Profit factor | | |
| Expectancy / trade | | |
| Avg win / avg loss | | |
| Payoff ratio | | |
| Longest losing streak | | |
| Avg holding period | | |
| Skewness | | |
| Kurtosis | | |
| Serial autocorrelation | | |
| Net vs. gross return | | |
| vs. Buy-and-hold | | |
| vs. Risk-free | | |

#### 3.4 Parameter Sensitivity
- **Optimal parameter set:**
- **Stability heatmap:** [describe or attach]
- **Break-even cost level:**
- **Margin of safety:**

#### 3.5 Regime Breakdown

| Regime | n trades | WR | PF | Sharpe | Significant? |
|--------|----------|-----|-----|--------|--------------|
| Bull | | | | | |
| Bear | | | | | |
| Sideways | | | | | |
| High vol | | | | | |
| Low vol | | | | | |

#### 3.6 Monte Carlo Results
- **% of bootstrapped paths positive after costs:**
- **5th percentile worst-case return:**
- **95th percentile best-case return:**
- **Median terminal equity:**

#### 3.7 Failure Modes Assessed
List which of the 10 failure modes were checked and ruled out.

#### 3.8 Verdict
- [ ] **PROVEN** — passes all Phase 4 gates
- [ ] **PROMISING** — passes ≥6 gates, forward test recommended
- [ ] **REJECTED** — fails ≥3 gates decisively

#### 3.9 Recommended Next Step
- If PROVEN: capital deployment protocol
- If PROMISING: forward-test protocol (duration, rules, decision thresholds)
- If REJECTED: reason for rejection and whether mutation could salvage

#### 3.10 Code Reference
- `backtest_code/[strategy_name]_backtest.py`
- `data/[strategy_name]_data_manifest.json`

---

### Candidate #2: [Strategy Name]
[Same structure as Candidate #1]

---

## 4. Cross-Candidate Comparison Matrix

| Candidate | Asset class | Timeframe | Sharpe | PF | MaxDD | Regime robust | Cost-adj. positive | Forward-test ready |
|-----------|-------------|-----------|--------|-----|-------|---------------|--------------------|--------------------|
| #1 | | | | | | | | |
| #2 | | | | | | | | |

---

## 5. Rejected Strategies (Summary)

| Strategy | Asset class | Primary rejection reason | File path |
|----------|-------------|--------------------------|-----------|
| | | | |

---

## 6. Gaps Remaining
What asset-class / strategy-type combinations have NOT been tried and should be?

---

## 7. One-Page Executive Summary
> **Which asset class(es):**
> **Which timeframe(s):**
> **Which TP/SL and other parameters:**
> **Exactly why we can claim profitability:**
> **Capital deployment recommendation:**

---

## Appendix A: Runnable Code Index
| Strategy | File path | Random seed | Data version | Last run date |
|----------|-----------|-------------|--------------|---------------|
| | | | | |

## Appendix B: Forward-Test Protocol
Link to `PROOF_PROTOCOL.md` or inline the pre-registered protocol here.
