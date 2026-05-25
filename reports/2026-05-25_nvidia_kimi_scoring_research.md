# NVIDIA Integrate — moonshotai/kimi-k2.6 — Stock Algorithm Scoring Research

**Model:** `moonshotai/kimi-k2.6`
**Date:** 2026-05-25
**Endpoint:** https://integrate.api.nvidia.com/v1
**Parameters:** temperature=0.4, max_tokens=8192, stream=True, thinking=True

---

## Q1 — Original ask

**Prompt:**

> Give me a scoring method to determine if an algorithm for predicting stocks is high quality or not?

**Response:**

Here is a comprehensive, 5-pillar scoring framework to evaluate a stock prediction algorithm. It produces an **Algorithmic Quality Score (AQS)** from **0 to 100**, designed to separate statistically robust, economically viable strategies from overfitted or fragile ones.

### The AQS Framework
Each pillar is scored **0–20**. The sum is the final AQS.

| Pillar | Weight | Focus |
| :--- | :--- | :--- |
| **1. Signal Strength** | 20 pts | Is the prediction statistically meaningful? |
| **2. Economic Value** | 20 pts | Does it generate profit after real-world costs? |
| **3. Risk Control** | 20 pts | Can it survive tail events and drawdowns? |
| **4. Robustness** | 20 pts | Does it generalize out-of-sample? |
| **5. Operational Feasibility** | 20 pts | Can it actually be executed? |
| **TOTAL** | **100 pts** | |

---

### Pillar 1: Signal Strength (0–20 pts)
*Measures whether the model truly predicts price movement or just fits noise.*

| Metric | Scoring Rubric | Pts |
| :--- | :--- | :--- |
| **Information Coefficient (IC)** | Rank IC > 0.10 (daily/weekly) | +5 |
| | Rank IC 0.05 – 0.10 | +3 |
| | Rank IC < 0.02 | 0 |
| **Directional Accuracy** | > 58% (if classification) | +4 |
| | 53% – 58% | +2 |
| | ≤ 53% (coin flip) | 0 |
| **Out-of-Sample (OOS) Retention** | OOS R² / In-Sample R² > 0.80 | +5 |
| | OOS R² / IS R² 0.50 – 0.80 | +3 |
| | OOS R² / IS R² < 0.50 | 0 |
| **Alpha Significance** | Alpha t-statistic > 3.0 | +6 |
| | t-stat 2.0 – 3.0 | +3 |
| | t-stat < 2.0 | 0 |

> **Note:** A high win rate with a poor IC usually means the strategy has a few massive losers—IC captures the consistency of the rank prediction.

---

### Pillar 2: Economic Value (0–20 pts)
*Measures whether the signal survives transaction costs and is worth the capital.*

| Metric | Scoring Rubric | Pts |
| :--- | :--- | :--- |
| **Net Sharpe Ratio** (after costs) | > 2.0 | +6 |
| | 1.5 – 2.0 | +4 |
| | 1.0 – 1.5 | +2 |
| | < 1.0 | 0 |
| **Net Return / Turnover** | Generates > $0.50 in net profit per $1 traded (after slippage/commissions) | +4 |
| **Cost Burden** | Transaction costs < 15% of gross alpha | +5 |
| | Costs 15% – 35% | +3 |
| | Costs > 50% | 0 |
| **Marginal Portfolio Value** | Adds > 0.20 to the portfolio’s overall Information Ratio | +5 |
| | Adds 0.10 – 0.20 | +3 |
| | Adds < 0.10 or is redundant | 0 |

---

### Pillar 3: Risk Control (0–20 pts)
*A strategy that predicts well but blows up once a year is worthless.*

| Metric | Scoring Rubric | Pts |
| :--- | :--- | :--- |
| **Maximum Drawdown** | < 10% | +5 |
| | 10% – 20% | +3 |
| | 20% – 30% | +1 |
| | > 30% | 0 |
| **Tail Risk (CVaR / Skew)** | Positive skew, 95% CVaR is manageable | +5 |
| | Neutral skew | +3 |
| | Negative skew + fat tails (blow-up pattern) | 0 |
| **Beta Neutrality** | \|β\| to S&P 500 < 0.1 | +5 |
| | \|β\| 0.1 – 0.4 | +3 |
| | \|β\| > 0.7 | 0 |
| **Volatility Consistency** | Realized vol within ±20% of target across regimes | +5 |
| | Volatile or unpredictable risk profile | 0 |

---

### Pillar 4: Robustness & Statistical Integrity (0–20 pts)
*Separates real edges from curve-fitting.*

| Metric | Scoring Rubric | Pts |
| :--- | :--- | :--- |
| **Walk-Forward History** | > 5 years of OOS or live data | +5 |
| | 2 – 5 years | +3 |
| | < 1 year | 0 |
| **Regime Stability** | Profitable in bull, bear, and high-vol regimes | +5 |
| | Profitable in only 2 regimes | +2 |
| | Bull-market only | 0 |
| **Parameter Stability** | Performance robust to ±20% parameter perturbation | +5 |
| | Fragile to small changes | 0 |
| **Multiple Testing Correction** | Survives Bonferroni/Benjamini-Hochberg correction (p < 0.05) | +5 |
| | Uncorrected p-values only | 0 |

---

### Pillar 5: Operational Feasibility (0–20 pts)
*A model is only as good as your ability to trade it.*

| Metric | Scoring Rubric | Pts |
| :--- | :--- | :--- |
| **Lookahead/Survivorship Bias** | Fully audited, bias-free data | +5 |
| | Unaudited or suspected bias | **-20 & Disqualify** |
| **Capacity & Scalability** | Strategy works at target AUM (e.g., >$10M) | +5 |
| | Capacity-constrained / micro-cap only | +2 |
| **Latency Sensitivity** | Works on daily/weekly close (low freq) | +5 |
| | Requires microsecond infrastructure | +2 (higher burden) |
| **Turnover Efficiency** | Turnover aligns with alpha half-life (not trading noise) | +5 |
| | Excessive churn relative to signal decay | 0 |

---

### Final Score Interpretation

| Score | Verdict | Action |
| :--- | :--- | :--- |
| **90 – 100** | **Institutional Grade** | Ready for significant capital deployment. |
| **80 – 89** | **Production Ready** | Solid, but monitor for alpha decay. |
| **70 – 79** | **Conditional Viable** | Deploy with tight risk limits; investigate weaknesses. |
| **60 – 69** | **High Risk** | Likely overfitted or economically marginal. Do not deploy. |
| **< 60** | **Reject** | Fails on statistical, risk, or operational grounds. |

---

### Critical Red Flags (Automatic Disqualifiers)
Even if a backtest looks good, **immediately reject** or cap the score at **< 50** if:
1. **Lookahead bias** is present (e.g., using future data to predict the past).
2. **No out-of-sample period** exists. A backtest-only score is capped at 50 points maximum, regardless of in-sample metrics.
3. **Sharpe > 3.0 with no economic explanation.** Extraordinary Sharpe ratios in equity prediction usually mean data leakage or overfitting.
4. **Negative skew with high kurtosis.** The strategy makes small gains and has rare, catastrophic losses.
5. **In-sample R² is high but OOS R² is near zero.** This is a classic overfit.

### Quick Formula Summary
```
AQS = Signal(20) + Economic(20) + Risk(20) + Robustness(20) + Operations(20)
```

**Pro Tip:** If you only have a backtest and no OOS data, the highest possible score is **50/100**. The gap between a backtest score and a live-tracked score is usually **20–30 points** of slippage, alpha decay, and unrealized costs. Never trust a model that scores well on Pillar 1 but fails on Pillar 4.

---

## Q2 — Concrete formula

**Prompt:**

> Now give me ONE concrete scoring formula that combines the dimensions you listed into a single 0-100 score. Specify explicit weights, exact metric thresholds, and the minimum-sample-size floor below which the score should be treated as unreliable. Return as pseudocode plus a worked example on a hypothetical algorithm with Sharpe 1.2, Sortino 1.8, max drawdown 18%, win-rate 56% on n=240 trades.

**Response:**



---

## Q3 — Per-asset-class weights

**Prompt:**

> Our dashboard scores algorithms across CRYPTO, EQUITY, COMMODITY, FOREX, BOND, ETF asset classes. How should the weights in your single-score formula differ per asset class? E.g. should CRYPTO weight risk-adjusted-return higher because of higher volatility? Give a 6x10 weight matrix (6 asset classes × your 10 dimensions) with one-line justification per cell that you change.

**Response:**



---

## Q4 — Deploy thresholds

**Prompt:**

> Give me three hard cutoff bands on your 0-100 score: DEPLOY (real money), RESEARCH (paper trade only), JUNK (kill). For each band, list the specific gate conditions (e.g. 'Sharpe>=1.0 AND maxDD<=20% AND n>=200 AND Bonferroni-p<0.05') that must ALSO be true beyond the composite score. The goal is a 1-glance Y/N promotion decision for findtorontoevents.ca/audit's 'is this algorithm real-money-grade?' verdict.

**Response:**

### Audit-Grade Promotion Logic

**Override Rule:** A composite score is *recommendable* only if it clears every hard gate for that band.  
**Kill Switch:** Any JUNK trigger overrides the composite score to **JUNK**, regardless of points.

---

### 1. DEPLOY — “Real-Money Grade”
**Score Range:** `80 – 100`  
**ALL of the following must be TRUE:**

| # | Gate Condition | Dimension | Rationale |
|---|----------------|-----------|-----------|
| 1 | `Sharpe(net) >= 1.0` | RAR | Must pay for risk and funding costs after slippage. |
| 2 | `Sortino(net) >= 1.5` | RAR | Penalizes downside volatility specifically. |
| 3 | `maxDD <= 20%` | RC | Investors rarely tolerate >20% drawdown in systematic mandates. |
| 4 | `n >= 200` (trades) OR `>= 24 months` daily | RB | Minimum statistical power to trust the Sharpe. |
| 5 | `Bonferroni_p < 0.05` (or `t_stat > 3.0`) | AS | Survives multiple-testing correction; not a lucky backtest. |
| 6 | `OOS_R2 / IS_R2 >= 0.60` | RB | In-sample edge must largely replicate out-of-sample. |
| 7 | `abs(Beta) <= 0.30` | RC | Must not be a disguised beta/leverage product. |
| 8 | `CostBurden < 30%` of gross alpha | EV | Alpha must survive realistic transaction costs. |
| 9 | `BiasAudit == PASS` (no lookahead/survivorship) | OF | Hard disqualifier if data integrity is compromised. |
| 10 | `WinRate >= 53% OR RankIC >= 0.05` | SS | Must show genuine directional or rank-prediction edge. |

**1-Glance Verdict:** `IF score>=80 AND (1..10 all TRUE) THEN "DEPLOY" ELSE downgrade.`

---

### 2. RESEARCH — “Paper Trade Only”
**Score Range:** `60 – 79`  
**ALL of the following must be TRUE to escape JUNK:**

| # | Gate Condition | Dimension | Rationale |
|---|----------------|-----------|-----------|
| 1 | `Sharpe(net) >= 0.5` | RAR | Enough to justify continued investigation. |
| 2 | `Sortino(net) >= 0.8` | RAR | Downside risk must be reasonably controlled. |
| 3 | `maxDD <= 35%` | RC | Tolerable in a research sandbox, not client capital. |
| 4 | `n >= 100` (trades) OR `>= 12 months` daily | RB | Minimum to detect a signal, but not yet trustworthy. |
| 5 | `p_value < 0.05` (uncorrected, `t_stat > 2.0`) | AS | Statistically suggestive, but not yet proven under correction. |
| 6 | `OOS_period >= 20%` of total history | RB | Must have *some* out-of-sample validation. |
| 7 | `abs(Beta) <= 0.60` | RC | Can have mild directional tilt, but not pure beta. |
| 8 | `CostBurden < 60%` of gross alpha | EV | Must not be entirely eaten by costs. |
| 9 | `BiasAudit == PASS` | OF | Same hard rule: no compromised data. |
| 10 | `WinRate >= 50% OR RankIC >= 0.02` | SS | At least a marginal edge above random. |

**1-Glance Verdict:** `IF 60<=score<=79 AND (1..10 all TRUE) THEN "RESEARCH" ELSE "JUNK".`

---

### 3. JUNK — “Kill / Do Not Trade”
**Score Range:** `0 – 59` **OR** any automatic kill trigger below.

**ANY one of these triggers = instant JUNK, even if score > 80:**

| Trigger | Condition | Why It Kills |
|---------|-----------|--------------|
| A | `Sharpe(net) < 0.0` | Negative risk-adjusted return; better to hold cash. |
| B | `maxDD > 50%` | Recovery requires 100% gain; unacceptable tail risk. |
| C | `n < 60` | Insufficient sample; score is statistically unreliable. |
| D | `BiasAudit == FAIL` | Data leakage invalidates every other metric. |
| E | `OOS_R2 / IS_R2 < 0.30` | Severe overfit; model will likely fail live. |
| F | `CostBurden > 90%` of gross alpha | Economically null; net alpha is noise. |
| G | `NetAnnualizedReturn <= 0%` after costs | No value generation. |
| H | `AnyMonthlyDrawdown > 40%` | Blow-up risk; strategy is fragile. |

**1-Glance Verdict:** `IF (A OR B OR C OR D OR E OR F OR G OR H) THEN "JUNK".`

---

### Pseudocode for the Audit Dashboard

```python
def audit_verdict(score, metrics):
    # metrics = dict with all gates above
    
    # --- KILL SWITCHES (JUNK overrides) ---
    if metrics['sharpe_net'] < 0.0: return "JUNK", "Kill: negative net Sharpe"
    if metrics['max_dd'] > 0.50: return "JUNK", "Kill: drawdown >50%"
    if metrics['n'] < 60: return "JUNK", "Kill: n<60"
    if metrics['bias_audit'] == "FAIL": return "JUNK", "Kill: data bias detected"
    if metrics['oos_is_r2_ratio'] < 0.30: return "JUNK", "Kill: severe overfit"
    if metrics['cost_burden'] > 0.90: return "JUNK", "Kill: costs eat alpha"
    if metrics['net_ann_return'] <= 0.0: return "JUNK", "Kill: non-positive net return"
    if metrics['max_monthly_dd'] > 0.40: return "JUNK", "Kill: monthly blow-up"
    
    # --- DEPLOY GATES ---
    deploy_gates = (
        metrics['sharpe_net'] >= 1.0 and
        metrics['sortino_net'] >= 1.5 and
        metrics['max_dd'] <= 0.20 and
        metrics['n'] >= 200 and
        metrics['bonferroni_p'] < 0.05 and
        metrics['oos_is_r2_ratio'] >= 0.60 and
        abs(metrics['beta']) <= 0.30 and
        metrics['cost_burden'] < 0.30 and
        metrics['bias_audit'] == "PASS" and
        (metrics['win_rate'] >= 0.53 or metrics['rank_ic'] >= 0.05)
    )
    
    if score >= 80 and deploy_gates:
        return "DEPLOY", "Real-money grade"
    elif score >= 80 and not deploy_gates:
        return "RESEARCH", "Score high but fails deploy gate"
    
    # --- RESEARCH GATES ---
    research_gates = (
        metrics['sharpe_net'] >= 0.5 and
        metrics['sortino_net'] >= 0.8 and
        metrics['max_dd'] <= 0.35 and
        metrics['n'] >= 100 and
        metrics['p_value'] < 0.05 and
        metrics['oos_fraction'] >= 0.20 and
        abs(metrics['beta']) <= 0.60 and
        metrics['cost_burden'] < 0.60 and
        metrics['bias_audit'] == "PASS" and
        (metrics['win_rate'] >= 0.50 or metrics['rank_ic'] >= 0.02)
    )
    
    if 60 <= score <= 79 and research_gates:
        return "RESEARCH", "Paper trade only"
    
    # --- DEFAULT ---
    return "JUNK", "Fails minimum gates"
```

---

### Worked Example (Revisited)
**Hypothetical Algorithm:** Sharpe 1.2, Sortino 1.8, maxDD 18%, win-rate 56%, `n = 240`.

| Gate | Value | Pass? |
|------|-------|-------|
| Sharpe(net) | 1.2 | ✅ >= 1.0 |
| Sortino | 1.8 | ✅ >= 1.5 |
| maxDD | 18% | ✅ <= 20% |
| n | 240 | ✅ >= 200 |
| Bonferroni-p | assume 0.03 | ✅ < 0.05 |
| OOS/IS R² | assume 0.65 | ✅ >= 0.60 |
| abs(Beta) | assume 0.15 | ✅ <= 0.30 |
| CostBurden | assume 20% | ✅ < 30% |
| BiasAudit | PASS | ✅ |
| WinRate | 56% | ✅ >= 53% |

**Result:** `Score = 81.3` (from prior formula) + **ALL DEPLOY gates pass** → **`DEPLOY`** ✅.

---

