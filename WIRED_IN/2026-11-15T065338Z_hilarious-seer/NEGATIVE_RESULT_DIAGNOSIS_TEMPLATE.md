# Negative Result Diagnosis Template
## How to interpret and act on strategies that fail the proof standard

---

## 1. Failure Signature Classification

For every dead candidate, record the **highest-numbered gate it passed** + the **first gate it failed**:

| Candidate | Passed gates | Failed at gate | Failure signature | Recommended action |
|-----------|-------------|----------------|-------------------|-------------------|
| Example_A | 1,2,3,4,5,6,7,8 | 9 (no forward test) | Near-miss: all statistical gates pass, needs time | Pre-register forward test, extend to 90 days |
| Example_B | 1,2,3 | 4 (Monte Carlo fails) | Edge too small / too few trades | Lower turnover or abandon |
| Example_C | 1 | 2 (WFO fails) | Severe overfitting | Permanently reject; don't mutate |
| Example_D | 1,2,3,4,5,6,7 | 8 (shuffle control fails) | **BUG or leak** | Fix pipeline, re-test from scratch |

---

## 2. Failure Signature → Pivot Matrix

### Signature A: Fails at Gate 4 (Monte Carlo)
**What it means:** The edge exists in-sample but doesn't survive bootstrapping. Too few trades, or edge is too small relative to variance.

**Diagnostic questions:**
- Is n < 100? → Sample size problem
- Is win rate > 55% but PF < 1.3? → Small edge, high variance
- Does block bootstrap fail worse than plain? → Serial correlation in losses

**Pivots (in order):**
1. Lower turnover: weekly instead of daily rebalancing
2. Basket trade: combine 5-10 signals to reduce variance
3. Extend history: get more data if available
4. **If none work → abandon this signal family permanently**

---

### Signature B: Fails at Gate 5 (Friction Model)
**What it means:** Gross edge exists but dies after realistic costs.

**Diagnostic questions:**
- What is breakeven cost level? Is it within reach of retail brokers?
- Is turnover > 20x/year? → Too high for retail
- Are we trading illiquid names? → Spread is the killer

**Pivots (in order):**
1. Reduce turnover: longer hold periods
2. Use limit orders / maker rebates where possible
3. Switch instrument: futures instead of ETFs for tax/cost efficiency
4. **If breakeven < 5bps → abandon; edge is unharvestable**

---

### Signature C: Fails at Gate 2 (Walk-Forward)
**What it means:** Parameters are unstable. Classic overfitting or regime dependence.

**Diagnostic questions:**
- Do optimal parameters change wildly across windows? → Overfitting
- Does performance drop to zero in OOS? → Curve-fit
- Does it work only in one regime? → See Signature F

**Pivots (in order):**
1. Reduce parameter count: simpler models
2. Fix parameters at " consensus" values (e.g., 200-day MA) and re-test
3. **If still fails → permanently reject; the signal has no robustness**

---

### Signature D: Fails at Gate 8 (Shuffle Control)
**What it means:** The pipeline has a bug or leak. This is actually the **best** failure because it's fixable.

**Diagnostic questions:**
- Are features computed using future data? → Look-ahead bias
- Is the target variable shifted incorrectly? → Label leakage
- Are we using adjusted close for entry but unadjusted for exit? → Data bug

**Pivots:**
1. Audit every line of feature engineering for chronological purity
2. Re-run with a "no-signal" control (random entries)
3. **Fix and re-test from scratch; don't tweak parameters**

---

### Signature E: Fails at Gate 6 (Statistical Significance)
**What it means:** The signal is indistinguishable from noise.

**Diagnostic questions:**
- Is t-stat < 1.5? → No edge
- Does CI include zero? → Inconclusive at best
- Is the effect size tiny (< 1% annualized)? → Not worth pursuing

**Pivots:**
1. **Permanently reject this signal class**
2. Do not test variants (e.g., 150-day instead of 200-day MA)
3. Move to entirely different signal family

---

### Signature F: Fails at Gate 7 (Regime Robustness)
**What it means:** Conditional edge — works in some regimes, fails in others.

**Diagnostic questions:**
- Which regime(s) work? Bull/bear/high-vol/low-vol?
- Is the working regime predictable ex-ante?
- Can we build a regime detector with independent validation?

**Pivots (in order):**
1. Pre-register a regime-conditional strategy: "trade only in Regime X"
2. Build and validate the regime detector separately
3. Re-test the combined system as a NEW candidate
4. **If regime detector fails its own proof standard → abandon**

---

### Signature G: Near-Miss (Passes 1-8, Fails 9 or 10)
**What it means:** Statistically valid edge, but not yet proven live.

**Diagnostic questions:**
- How many trades in the sample? n > 200 is ideal
- Is the edge consistent across sub-periods?
- What is the minimum capital required?

**Pivots:**
1. **Pre-register forward test immediately** — this is the most promising category
2. Define exact rules, duration, and decision thresholds BEFORE starting
3. Run 90-day paper trade with live tracking
4. If forward test passes → deploy with small capital, scale gradually

---

## 3. Near-Miss Handling Protocol

A "near-miss" is defined as: **passes gates 1-5, fails only at 6, 7, or 9 due to sample size**.

**DO:**
- Extend the backtest window if more data exists
- Lower the strategy frequency to increase n (daily → weekly)
- Combine multiple near-misses into a portfolio if they are uncorrelated
- Re-enter as a NEW pre-registered candidate

**DON'T:**
- Tweak parameters until significance appears
- Cherry-pick sub-periods that look good
- Lower the significance threshold

**Decision rule:**
```
If (t-stat > 1.0) AND (effect_size > 0) AND (all other gates pass):
    → Extend sample or forward-test
Else:
    → Reject permanently
```

---

## 4. When to Pivot to Passive Allocation

If **zero** directional strategies pass gate 6 (significance), the honest conclusion is:

> "We could not find a statistically significant directional edge in any asset class tested."

This is a **legitimate, valuable finding**. The next step is not to keep searching — it's to pivot.

### Passive Allocation Pivot

**What it is:** Instead of claiming alpha, build and prove a disciplined allocation strategy.

**Examples:**
- 60/40 VTI/BND with quarterly rebalancing
- Risk-parity across 4-6 asset classes
- Factor-tilted index portfolios (value, momentum, low-vol)
- Target-date glide paths

**Why it can still be a product:**
- Expected return is the weighted average of asset returns — provable, not speculative
- Sharpe ratio of a diversified portfolio is measurable
- Tax-efficient rebalancing is a genuine value-add
- The proof standard shifts from "beat the market" to "deliver the risk premium efficiently"

**Proof standard for passive strategies:**
1. Show historical performance of the allocation (not backtested, just historical)
2. Prove the rebalancing adds value vs. buy-and-hold (rebalancing bonus literature)
3. Model the tax drag and show after-tax expected returns
4. Compare to a naive benchmark (e.g., 100% SPY)
5. Pre-register the rebalancing rules and execute them mechanically

**The dashboard becomes:**
- "Current allocation" instead of "active picks"
- "Expected risk/return" based on historical asset class data
- "Rebalancing alerts" when allocation drifts > 5%
- "Tax-loss harvesting opportunities"

---

## 5. Summary Decision Tree

```
For each candidate:
    Did it fail at gate 8 (shuffle)?
        → YES: Fix bug, re-test
    Did it fail at gate 2 (WFO)?
        → YES: Permanently reject
    Did it fail at gate 6 (significance)?
        → YES: Permanently reject this signal family
    Did it fail at gate 5 (friction)?
        → YES: Lower turnover or abandon
    Did it fail at gate 7 (regime)?
        → YES: Consider regime-conditional version
    Did it pass gates 1-8?
        → YES: Pre-register forward test immediately
    
If NO candidates pass gate 6:
    → Document negative result
    → Pivot to passive allocation
    → Stop searching for directional alpha
```

---

## 6. Documentation Requirements

Every negative result must be recorded with:
- Candidate name and file path
- Exact failure gate
- Failure signature classification
- Recommended pivot (or "permanently reject")
- Date of rejection
- Author

This prevents re-testing the same dead strategies in 6 months.
