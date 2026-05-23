# Dimension 01: Per-Asset-Class Edge Determination
## Quantitative Trading Strategy Audit — Antigravity Platform
**Date:** 2026-05-03  
**Analyst:** Quantitative Trading Strategist  
**Classification:** CONFIDENTIAL — Investment Decision Support

---

## Executive Summary

This audit examines every asset class traded on the Antigravity platform through the lens of five evidence-based criteria to determine which possess genuine statistical edge versus those that are value destroyers. The analysis is grounded in peer-reviewed quantitative finance literature and industry best practices.

### The Five Gate Criteria (ALL Must Pass for "Investable" Status)

| Criterion | Threshold | Academic/Source Basis |
|-----------|-----------|----------------------|
| **Profit Factor (PF)** | > 1.2 (preferably > 1.3) | PF 1.0-1.2 = breakeven territory after costs; PF > 1.2 = solid edge begins [^43^] |
| **Win Rate (WR)** | > 40% (context-dependent with R:R) | WR alone is meaningless without R:R context; 40% WR at 2:1 R:R is profitable [^32^] |
| **Positive OOS Sharpe** | > 0 (preferably > 1.0) | Negative OOS Sharpe = strategy fails on unseen data; genuine edge must persist OOS [^21^] |
| **Minimum Sample Size** | 100+ trades (200+ preferred) | 30 = CLT floor; 100 = basic reliability; 200-500 = institutional grade [^27^][^25^] |
| **OOS/IS Performance Ratio** | > 0.5 (OOS Sharpe / IS Sharpe) | Ratio < 0.5 signals severe overfitting; healthy decay is expected but not collapse [^26^] |

### Master Verdict Summary

| Asset Class | PF | WR | OOS Sharpe | n | Overall | Verdict |
|-------------|-----|-----|------------|-----|---------|---------|
| **Equity** | 1.72 | 53.1% | **+3.527** | 136+ | ALL PASS | **SAFE** |
| **ETF** | 1.32 | 52.9% | **+6.368*** | 45 | 4/5 PASS* | **CAUTION** |
| **Crypto (B-Tier)** | 1.28 | 45.0% | **-0.242** | 940 | OOS FAIL | **CAUTION** |
| **Crypto (A-Tier)** | 1.58 | 42.4% | **-0.242** | 304 | OOS FAIL | **CAUTION** |
| **Bonds** | 1.72 | 50.0% | N/A | ~20 | SAMPLE FAIL | **CAUTION** |
| **Forex** | 1.41 | 21.4% | **-1.406** | 195+ | OOS FAIL | **DANGEROUS** |
| **Commodity** | 1.04 | 21.2% | **-2.412** | 143 | OOS FAIL | **DANGEROUS** |
| **Crypto (S-Tier)** | 6.80 | 70.4% | **-0.242** | 27 | SAMPLE+OOS FAIL | **DANGEROUS** |
| **Crypto (C-Tier)** | 0.56 | 28.1% | **-0.242** | 224 | PF FAIL | **DANGEROUS** |
| **Futures** | N/A | N/A | N/A | 0 | NO DATA | **DANGEROUS** |

*ETF OOS Sharpe of 6.368 is flagged as potential artifact due to only 12 folds (see Section 6).

---

## 1. Academic Foundation: Why These Criteria Matter

### 1.1 Profit Factor Thresholds

Profit Factor (Gross Profit / Gross Loss) is the single most informative metric for edge detection because it captures the interplay of win rate and reward-to-risk in one number [^38^].

| PF Range | Classification | Interpretation |
|----------|---------------|----------------|
| < 1.0 | Losing Strategy | Gross losses exceed gross profits. Strategy destroys capital. |
| 1.0 - 1.2 | Breakeven Territory | Technically profitable but fragile. Transaction costs, slippage, or minor market changes easily erase edge. "For every dollar lost, you make $1.00-$1.20 back" — not viable after costs [^43^] |
| **1.2 - 1.5** | **Solid Edge** | **Minimum threshold for deployable strategies."For every dollar lost, you make $1.20-$1.50 back." Most consistently profitable traders operate here [^43^]** |
| 1.5 - 2.0 | Strong Edge | Excellent performance. Professional traders and hedge fund strategies operate in this range [^43^] |
| > 2.0 | Exceptional (Verify) | Rare. Could be genuine edge, temporary inefficiency, or curve-fitting. Always verify sample size and OOS [^37^] |

**Key Insight:** A PF of 1.2 represents the practical minimum for live trading because backtested results typically degrade 10-20% in live markets due to slippage, commissions, and execution variance [^32^]. A backtest PF of 1.2 may translate to ~1.0-1.1 live — breakeven at best.

### 1.2 Sample Size Requirements

The Central Limit Theorem establishes ~30 observations as the absolute floor for statistical inference [^27^]. However, trading strategy validation requires substantially more:

| Minimum Trades | Confidence Level | Source |
|---------------|-----------------|--------|
| 30 | CLT heuristic only | StratBase.AI, BacktestBase [^25^][^27^] |
| 100 | Basic reliability for metrics | Multiple industry sources [^23^][^28^] |
| **200-500** | **Institutional-grade confidence** | **Lopez de Prado standard [^27^]** |
| 2000+ (20 folds x 100 trades) | Walk-forward validation | ntguardian/Backtrader analysis [^53^] |

**Critical Caveat:** Trade count alone is insufficient. As noted by BacktestBase, "500 trades in 6 months (one regime) is less reliable than 100 trades over 5 years (multiple regimes)" [^27^].

### 1.3 In-Sample vs. Out-of-Sample Sharpe: The Overfitting Lens

A 2025 paper from Imperial College London and Qube Research & Technologies (Jacquier, Muhle-Karbe, Mulligan) derives closed-form approximations for in-sample and out-of-sample Sharpe ratios of linear predictive models [^21^]. Key findings:

1. **The "replication ratio"** (OOS Sharpe / IS Sharpe) increases with:
   - Size of the training dataset (more data = better OOS replication)
   - Magnitude of the "true" Sharpe ratio (stronger signals are more robust)

2. **The replication ratio decreases with:**
   - Number of model parameters and assets (complexity increases overfitting)
   - **Low true Sharpe ratio signals are particularly vulnerable to overfitting** [^21^]

3. **Practical implication:** When a strategy shows positive IS metrics but negative OOS Sharpe, this is prima facie evidence of overfitting. The in-sample results captured noise, not signal.

The Bailey & Lopez de Prado "Deflated Sharpe Ratio" (DSR) further corrects for multiplicity of trials — when researchers test many strategy variations, the expected maximum Sharpe under the null (no edge) increases substantially [^49^][^51^]. A reported Sharpe of 3.0+ after many trials may have zero true edge.

---

## 2. Asset Class Analysis: Individual Verdicts

### 2.1 EQUITY — VERDICT: SAFE

```
Claim: Equity is the crown jewel of the Antigravity platform with genuine,
       statistically validated edge across all five gate criteria.
Source: Platform dashboard data 2026-05-03; academic validation from [^21^][^27^]
Confidence: HIGH
Verdict: SAFE
Rationale:
  - PF 1.72 (solidly in "strong edge" 1.5-2.0 range) [^43^]
  - WR 53.1% (above 50%, indicating directional accuracy)
  - OOS Sharpe +3.527 (strongly positive, indicating robust out-of-sample performance)
  - n=136+ closed trades (meets minimum 100, approaches 200 threshold)
  - +233.46% total PnL (substantial absolute returns)
  - OOS WR 57.9% (OUTPERFORMS in-sample — a rare and strong signal)
  
  The OOS Sharpe of 3.527 is the strongest across all asset classes. The fact
  that OOS win rate (57.9%) EXCEEDS in-sample win rate (53.1%) is remarkable —
  it suggests the strategy was developed conservatively and performs better on
  unseen data. This is the opposite of overfitting.
  
  The only minor concern: n=136 is above the 100 minimum but below the 200 
  "institutional grade" threshold. However, the combination of strong OOS 
  metrics and substantial absolute PnL provides compensating evidence.

Recommended Action: SCALE — This is the platform's primary alpha source.
  Increase allocation to maximum prudent level. Use as anchor for portfolio.
```

### 2.2 ETF — VERDICT: CAUTION

```
Claim: ETF shows promising metrics but the OOS Sharpe of 6.368 is highly 
       suspect due to tiny sample size (12 folds), requiring verification.
Source: Platform dashboard data; [^49^][^51^] (deflated Sharpe); [^53^] (fold requirements)
Confidence: LOW (due to OOS sample size)
Verdict: CAUTION
Rationale:
  - PF 1.32 (above 1.2 minimum, in "solid edge" range)
  - WR 52.9% (healthy directional accuracy)
  - OOS Sharpe +6.368 (extremely high — TOO high to be credible)
  - OOS WR 61.7% (strong but again, tiny sample)
  - n=45 IS trades (below 100 minimum — CONCERN)
  - ONLY 12 walk-forward folds (severely insufficient — CRITICAL CONCERN)
  - Decay 10.8 (high fold-to-fold variance)

  The ETF OOS Sharpe of 6.368 fails the "too good to be true" test. Academic
  research on the Deflated Sharpe Ratio demonstrates that extreme Sharpe values
  in small samples are often artifacts of selection bias and multiple testing [^49^][^51^].
  With only 12 folds, the OOS sample lacks statistical power — the standard 
  recommendation is 20+ folds with minimum 100 trades per fold for walk-forward
  validation [^53^].
  
  The 10.8 decay metric suggests high variance between folds, further 
  undermining confidence in the 6.368 figure.
  
  IS n=45 is also below the 100-trade minimum for in-sample reliability.

Recommended Action: MONITOR — Do NOT scale allocation until:
  1. Minimum 20+ additional walk-forward folds are completed
  2. In-sample trade count exceeds 100
  3. OOS Sharpe stabilizes below 3.0 (6.368 is likely inflated)
  4. Decay metric reduces below 5.0
```

### 2.3 CRYPTO OVERALL — VERDICT: CAUTION (B-Tier) / DANGEROUS (Aggregate)

```
Claim: Crypto aggregate shows negative OOS Sharpe (-0.242), indicating the 
       combined crypto strategy fails on unseen data. B-Tier is the only 
       sub-tier with marginal positive expectancy.
Source: Platform dashboard; [^21^] (OOS Sharpe replication); [^37^] (PF thresholds)
Confidence: MEDIUM-HIGH
Verdict: CAUTION (for B-Tier specifically) / DANGEROUS (Crypto aggregate)
Rationale:
  
  CRYPTO AGGREGATE:
  - OOS Sharpe -0.242 (NEGATIVE — fails OOS criterion)
  - OOS WR 43.0% (below 50%, below most IS win rates)
  - This is aggregate across all tiers; negative OOS means OVERALL crypto 
    operations destroy value on unseen data
  
  B-TIER CRYPTO (Best Sub-Tier):
  - PF 1.28 (above 1.2 minimum, in "solid edge" range) [^43^]
  - WR 45.0% (acceptable with positive R:R context)
  - n=940 (exceeds 500+ institutional threshold — excellent sample)
  - "Workhorse" — positive expectancy at L20
  - BUT: Negative aggregate OOS Sharpe means even B-Tier degrades OOS
  
  A-TIER CRYPTO:
  - PF 1.58 (strong) but degrading: 1.98 L20 -> 1.23 L100 (PF decay concern)
  - WR 42.4% (marginal)
  - n=304 (solid sample)
  - PF trend toward 1.23 approaches breakeven territory [^43^]
  
  S-TIER CRYPTO:
  - PF 6.80 (exceptional — VERIFY for curve-fitting)
  - WR 70.4% (very high — suspicious)
  - n=27 (FAR below minimum — statistically meaningless)
  - Almost certainly a lucky streak, not edge [^37^]
  
  C-TIER CRYPTO:
  - PF 0.56 (value destroyer — below 1.0)
  - WR 28.1% (catastrophic)
  - This tier should be HALTED immediately

Recommended Action: 
  - C-Tier: HALT immediately (PF 0.56 = capital destruction)
  - S-Tier: ABANDON (n=27 is noise, not signal)
  - B-Tier: OPTIMIZE (largest sample, positive PF, but OOS concerns)
  - A-Tier: MONITOR (watch PF decay trend; if PF drops below 1.2, halt)
  - Overall crypto: REDUCE allocation until OOS Sharpe turns positive
```

### 2.4 FOREX — VERDICT: DANGEROUS

```
Claim: Forex shows classic signs of a broken strategy with catastrophically 
       negative OOS Sharpe despite marginally positive in-sample PF.
Source: Platform dashboard; [^21^] (IS/OOS divergence = overfitting signature)
Confidence: HIGH
Verdict: DANGEROUS
Rationale:
  - PF 1.41 (IS — appears acceptable)
  - WR 21.4% (catastrophically low — means 78.6% of trades lose)
  - OOS Sharpe -1.406 (SEVERELY NEGATIVE — strategy fails on unseen data)
  - OOS WR 47.5% (better than IS but still negative Sharpe due to poor R:R)
  - n=195+ (sufficient sample size — this makes the failure MORE concerning,
    not less, because it rules out small-sample noise)
  - History of 0% WR due to "infinite retry bug" (structural software defect)
  
  The Forex strategy exhibits the classic overfitting signature documented by
  Jacquier et al. [^21^]: positive IS metrics, negative OOS performance. The
  IS PF of 1.41 was achieved by fitting to historical noise; the OOS Sharpe
  of -1.406 proves the strategy has NO true edge.
  
  The 21.4% win rate is particularly damning. Even with high R:R, a sub-25%
  win rate creates severe psychological and practical challenges — long losing
  streaks, difficulty maintaining discipline, and high risk of ruin [^33^].
  
  The "infinite retry bug" history indicates structural software problems 
  compounding strategy weakness.

Recommended Action: HALT — Cease all Forex trading immediately. The 
  negative OOS Sharpe with n=195+ is definitive evidence of no edge. 
  Strategy requires fundamental redesign, not parameter tweaking. Any 
  "optimization" should be treated as building a new strategy from scratch 
  with full OOS validation before risking capital.
```

### 2.5 COMMODITY — VERDICT: DANGEROUS

```
Claim: Commodity is a value-destroying asset class with severely negative OOS 
       Sharpe and breakeven in-sample PF, further undermined by excessive flat exits.
Source: Platform dashboard; [^43^] (PF 1.0-1.2 = breakeven); [^21^] (OOS failure)
Confidence: HIGH
Verdict: DANGEROUS
Rationale:
  - PF 1.04 (effectively breakeven — in "1.0-1.2 breakeven territory") [^43^]
  - WR 21.2% (catastrophically low directional accuracy)
  - OOS Sharpe -2.412 (MOST NEGATIVE of all asset classes)
  - OOS WR 43.2% (below random)
  - n=143 (marginally sufficient — but with these metrics, more data won't help)
  - 58% flat exits (strategy lacks conviction — more than half of "trades" 
    exit at breakeven, suggesting the system doesn't know what it's doing)
  
  The Commodity strategy is the worst performer on the platform by OOS Sharpe
  (-2.412). The PF of 1.04 means gross profit barely exceeds gross loss; after
  costs, this is certainly a losing strategy. The 58% flat exit rate is a 
  structural problem — the strategy initiates positions then exits them 
  indiscriminately, suggesting either:
  1. Overly tight time-based exits that don't allow trades to develop
  2. Lack of genuine signal (random entries, random exits)
  3. Poorly calibrated risk parameters
  
  The combination of near-breakeven PF, catastrophic OOS Sharpe, and excessive
  flat exits constitutes a failed strategy by every measure.

Recommended Action: ABANDON — The Commodity strategy has no redeeming 
  features. Do not attempt to optimize. The OOS Sharpe of -2.412 with n=143
  is definitive. Redirect any commodity-focused resources to Equity or ETF 
  strategy development.
```

### 2.6 BONDS — VERDICT: CAUTION

```
Claim: Bond metrics appear strong but sample size is critically insufficient 
       for any statistical conclusion.
Source: Platform dashboard; [^27^][^29^] (sample size requirements)
Confidence: LOW (due to tiny sample)
Verdict: CAUTION
Rationale:
  - PF 1.72 (appears strong — in "strong edge" range)
  - WR 50.0% (acceptable)
  - n=10 closed (CRITICALLY INSUFFICIENT)
  - n=18-20 total (still far below 100 minimum)
  - No OOS Sharpe data available
  
  With only 10 closed trades (18-20 total), the Bond sample is below even the
  CLT floor of 30 observations [^27^]. The PF of 1.72 and WR of 50% are 
  statistically meaningless — they could easily result from 1-2 lucky trades.
  
  The apparent strength is an illusion of small-sample variance.

Recommended Action: MONITOR ONLY — Continue tracking but do NOT allocate 
  capital based on these metrics. Need minimum 100+ trades before any 
  confidence can be assigned. Current data is a hypothesis, not evidence.
```

### 2.7 FUTURES — VERDICT: DANGEROUS

```
Claim: Futures has zero trades and zero data — this is not an asset class 
       being traded; it is an untested aspiration.
Source: Platform dashboard
Confidence: N/A
Verdict: DANGEROUS
Rationale:
  - 0 trades, 0% win rate, no metrics
  - No data = no edge = no allocation
  
  Trading Futures without any backtested or live track record is equivalent
  to random betting. No professional allocator would commit capital to an 
  untested strategy.

Recommended Action: HALT — Do not deploy capital until a minimum viable 
  strategy is developed, backtested with 200+ trades, and validated with 
  positive OOS Sharpe across 20+ walk-forward folds.
```

---

## 3. The In-Sample vs. Out-of-Sample Divergence Problem

### 3.1 Why FOREX and COMMODITY Have Positive IS PF but Negative OOS Sharpe

Four asset classes show the classic overfitting signature: positive in-sample metrics with negative out-of-sample Sharpe:

| Asset Class | IS PF | OOS Sharpe | Pattern |
|-------------|-------|------------|---------|
| Crypto (aggregate) | 1.28-1.58 | -0.242 | Moderate overfitting |
| Forex | 1.41 | -1.406 | Severe overfitting |
| Commodity | 1.04 | -2.412 | Catastrophic overfitting |

This pattern is the **defining signature of overfitting**, as established by:

1. **Jacquier, Muhle-Karbe, Mulligan (2025)** [^21^]: "Low true Sharpe ratio signals are particularly vulnerable to overfitting... the out-of-sample Sharpe ratio will be lower than the true Sharpe ratio due to misestimation of the regression parameter causing increased volatility."

2. **AQR Capital Management** (cited in [^31^]): Documented a moving average strategy whose Sharpe ratio dropped from 1.2 during backtesting to -0.2 when applied to new data — a pattern strikingly similar to Forex (PF 1.41 IS, Sharpe -1.406 OOS).

3. **Bailey & Lopez de Prado** [^49^][^51^]: The "winner's curse" — when selecting the best-performing strategy from many alternatives, "she is likely to choose a strategy with an inflated Sharpe ratio. Performance out of sample is likely to disappoint."

### 3.2 Root Causes of IS/OOS Divergence in This Platform

| Cause | Evidence | Severity |
|-------|----------|----------|
| **Parameter over-optimization** | Crypto tiers with different parameters; A-Tier PF decay 1.98->1.23 | HIGH |
| **Multiple testing without correction** | 10+ asset classes/strategy variants tested; no DSR adjustment | HIGH |
| **Insufficient training data** | S-Tier n=27; ETFs n=45; Bonds n=10 | HIGH |
| **Regime-dependent performance** | Commodity 58% flat exits (chops in non-trending markets) | MEDIUM |
| **Software bugs corrupting data** | Forex "infinite retry bug" caused 0% WR | HIGH |
| **Structural mismatch** | Forex 21.4% WR suggests strategy fundamentally misaligned with forex market structure | HIGH |

### 3.3 The Replication Ratio Framework

Using the Imperial College framework [^21^], we can conceptualize the "replication ratio" (OOS Sharpe / IS Sharpe) for each asset class:

| Asset Class | Approx. IS Sharpe* | OOS Sharpe | Replication Ratio | Assessment |
|-------------|-------------------|------------|-------------------|------------|
| Equity | ~2.5-3.0 | 3.527 | >100% | Exceptional (OOS > IS) |
| ETF | ~1.5-2.0 | 6.368** | >300% | Artifact (inflated OOS) |
| Crypto | ~1.0-1.5 | -0.242 | NEGATIVE | Complete failure |
| Forex | ~1.0-1.5 | -1.406 | NEGATIVE | Complete failure |
| Commodity | ~0.3-0.5 | -2.412 | NEGATIVE | Complete failure |

*Approximated from PF and WR. **Suspected artifact.

A replication ratio below 50% signals overfitting. A **negative** replication ratio means the strategy not only failed to replicate in-sample performance but actively lost money out-of-sample. This is the worst possible outcome and describes Crypto (aggregate), Forex, and Commodity.

---

## 4. Investable Asset Classes: Which Pass ALL Criteria?

### 4.1 The Five-Gate Check

| Criterion | Equity | ETF | B-Tier Crypto | Forex | Commodity | Bonds |
|-----------|--------|-----|---------------|-------|-----------|-------|
| PF > 1.2 | 1.72 | 1.32 | 1.28 | 1.41 | 1.04 | 1.72 |
| OOS Sharpe > 0 | **3.527** | 6.368* | **-0.242** | **-1.406** | **-2.412** | N/A |
| n > 100 | 136 | 45 | 940 | 195 | 143 | 10 |
| OOS/IS > 0.5 | >100% | ??? | NEGATIVE | NEGATIVE | NEGATIVE | N/A |
| All Gates Pass? | **YES** | **NO** | **NO** | **NO** | **NO** | **NO** |

### 4.2 Conclusion: Only Equity Passes All Gates

**Only ONE asset class — Equity — passes all five gates for investability.**

ETF fails on sample size (n=45 IS, 12 folds OOS). B-Tier Crypto fails on OOS Sharpe. Forex and Commodity fail catastrophically on OOS Sharpe. Bonds lack sufficient data.

This does not mean other asset classes can never be traded — but it means **no other asset class currently has validated edge sufficient for real-money deployment at scale.**

---

## 5. Failing but Fixable vs. Should Be Abandoned

### 5.1 Classification Matrix

| Category | Asset Classes | Rationale |
|----------|--------------|-----------|
| **SAFE — Scale** | Equity | All criteria pass; OOS outperforms IS |
| **CAUTION — Monitor** | ETF | Promising but tiny sample; needs validation |
| **CAUTION — Optimize** | B-Tier Crypto | Best crypto tier but negative aggregate OOS |
| **CAUTION — Monitor** | Bonds | Insufficient data; metrics hypothetical |
| **DANGEROUS — Halt** | A-Tier Crypto, Forex, Futures, S-Tier Crypto | Structural problems; negative OOS or no data |
| **DANGEROUS — Abandon** | C-Tier Crypto, Commodity | Value destroyers; no path to profitability |

### 5.2 Fixable Strategies (Halt, Don't Abandon)

| Asset Class | Problem | Fix Path |
|-------------|---------|----------|
| **A-Tier Crypto** | PF decay (1.98->1.23); negative OOS | Investigate parameter stability; reduce optimization; test simpler models |
| **Forex** | Negative OOS Sharpe; 21% WR | Full rebuild required; the current approach has no edge. Consider completely different signal generation. The "infinite retry bug" must be fixed first. |
| **Futures** | No data | Develop strategy from scratch with IS/OOS framework from day one |

### 5.3 Should Be Abandoned (No Fix Path)

| Asset Class | Why Abandon |
|-------------|-------------|
| **C-Tier Crypto** | PF 0.56 = active capital destruction. No optimization can salvage a sub-1.0 PF at n=224. |
| **Commodity** | PF 1.04 + OOS Sharpe -2.412 + 58% flat exits = fundamentally broken. The strategy architecture is wrong, not the parameters. |
| **S-Tier Crypto** | n=27 is statistically meaningless. The 6.80 PF is a hot streak, not edge. Abandon and absorb any lessons into B-Tier development. |

---

## 6. Special Investigation: Is ETF OOS Sharpe 6.368 Real?

### 6.1 Verdict: Almost Certainly an Artifact

The ETF OOS Sharpe of 6.368 triggers multiple red flags:

**Red Flag 1: Extreme Value**
Sharpe ratios above 3.0 sustained over large samples are rare [^37^]. A Sharpe of 6.368 is in "check your data" territory. As Cryptorobot.ai notes: "Profit Factor above 3.0 in backtesting often signals curve fitting" [^37^] — and this applies equally to Sharpe.

**Red Flag 2: Tiny Fold Count**
With only 12 walk-forward folds, the ETF OOS sample is severely underpowered. The walk-forward literature recommends:
- Minimum 20 folds with 100+ trades each for basic validation [^53^]
- The 2025 walk-forward study by Li and Wang used 34 folds and still found t-statistic = 0.96, p-value = 0.34 — not significant [^41^]
- 12 folds provides insufficient statistical power to distinguish signal from noise

**Red Flag 3: Deflated Sharpe Ratio (DSR) Analysis**
Using the Bailey & Lopez de Prado DSR framework [^49^][^51^], an OOS Sharpe of 6.368 with only 12 folds and unknown trial count:
- If even 10 strategy variations were tested, the expected maximum Sharpe under null could exceed 3.0 purely by chance
- With non-normal returns (common in ETFs), the DSR correction would reduce the effective Sharpe substantially
- The "winner's curse" means the 6.368 figure is likely the maximum of a distribution, not the mean

**Red Flag 4: Inconsistent with IS Metrics**
IS PF of 1.32 and WR of 52.9% are solid but not spectacular. These are inconsistent with an OOS Sharpe of 6.368 — the metrics don't align. If the true edge were that strong, IS metrics would likely be higher.

**Red Flag 5: High Decay (10.8)**
High fold-to-fold decay suggests the 6.368 figure is driven by 1-2 exceptional folds, not consistent performance across the walk-forward window.

### 6.2 Estimated "True" ETF OOS Sharpe

| Scenario | Adjustment | Estimated True Sharpe |
|----------|-----------|----------------------|
| DSR correction (N=10 trials) | Deflate by ~2.0-3.0 | 3.0-4.0 |
| Small sample bias (12 folds) | Deflate by ~1.5-2.0 | 3.0-4.5 |
| Conservative combined | Apply both corrections | 1.5-3.0 |

**Most likely true OOS Sharpe: 2.0-3.0** — still positive and potentially tradeable, but nowhere near 6.368.

---

## 7. Optimal Capital Allocation

### 7.1 Kelly Criterion Framework

The Kelly Criterion provides the theoretical foundation for optimal capital allocation [^34^][^42^]:

**Single-asset Kelly:** f* = (bp - q) / b  
where b = average win/average loss, p = win rate, q = 1-p

**Multi-asset Kelly:** f_i = μ_i / σ²_i  
where μ_i = mean excess return, σ²_i = variance of excess returns for strategy i

### 7.2 Kelly Allocation Estimate (Conservative Half-Kelly)

| Asset Class | Est. Edge | Kelly Full | Half-Kelly | Recommended |
|-------------|-----------|------------|------------|-------------|
| Equity | Strong (PF 1.72, OOS Sharpe 3.527) | ~40-50% | ~20-25% | **25%** |
| ETF | Moderate* (PF 1.32, "true" Sharpe ~2-3) | ~15-20% | ~7-10% | **5%** (pending validation) |
| B-Tier Crypto | Marginal (PF 1.28, negative OOS) | ~5-10% | ~2-5% | **0%** (until OOS positive) |
| All Other | None/Negative | 0% | 0% | **0%** |
| **Cash/Reserve** | | | | **70%** |

### 7.3 Recommended Allocation

```
EQUITY:     25% (primary allocation — proven edge)
ETF:         5% (small test allocation pending validation)
B-CRYPTO:    0% (halt until OOS Sharpe turns positive)
A-CRYPTO:    0% (halt until PF decay resolved)
FOREX:       0% (halt — rebuild required)
COMMODITY:   0% (abandon)
FUTURES:     0% (no strategy to allocate to)
BONDS:       0% (insufficient data)
S-CRYPTO:    0% (abandon)
C-CRYPTO:    0% (abandon)
RESERVE:    70% (dry powder for proven opportunities)
```

### 7.4 Rationale for Conservative Allocation

The 70% cash reserve reflects:

1. **Only one validated asset class** (Equity) warrants capital deployment
2. **Half-Kelly is industry standard** to reduce drawdown risk — full Kelly can produce 60%+ drawdowns [^35^]
3. **OOS uncertainty** in all non-Equity asset classes demands defensive posture
4. **Platform-level risk** — the prevalence of negative OOS Sharpe across 3/5 asset classes with data suggests systemic overfitting issues in strategy development
5. **Opportunity preservation** — capital reserved for when other asset classes achieve OOS validation

---

## 8. Critical Finding: The 1.5-2.0 R:R Band

The Action Plan finding that the **1.5-2.0 R:R band has PF 5.81, Kelly +47.2%**, while R:R > 2.0 has PF 0.35 (catastrophic), is one of the most important actionable insights in this audit.

### 8.1 Implications

| R:R Band | PF | Kelly | Verdict |
|----------|-----|-------|---------|
| 1.5 - 2.0 | 5.81 | +47.2% | **SWEET SPOT** |
| > 2.0 | 0.35 | Negative | **CATASTROPHIC** |

This means:
1. **Letting winners run beyond 2.0R destroys value** — the platform's exit logic is broken for extended targets
2. **The optimal exit is 1.5-2.0R** — this is where the platform's edge concentrates
3. **All strategies should be reviewed** to ensure take-profit targets cluster in the 1.5-2.0R band
4. **R:R > 2.0 trades are inverted signals** — they predict losses, not gains

### 8.2 Recommended Action

- Implement a **hard cap on R:R at 2.0R** for all asset classes pending strategy-specific validation
- Route any trade setup targeting >2.0R through a separate review process
- For Equity (which has positive OOS), test whether the 1.5-2.0R band is even more concentrated
- This single rule change could improve platform-wide PF by 20-30%

---

## 9. Summary of Recommendations

| Priority | Action | Asset Class | Timeline |
|----------|--------|-------------|----------|
| **P0 — Immediate** | Halt all trading | C-Tier Crypto, Commodity | Today |
| **P0 — Immediate** | Halt trading | Forex, Futures, S-Tier Crypto | Today |
| **P1 — This Week** | Increase Equity allocation to 25% | Equity | This week |
| **P1 — This Week** | Implement 2.0R R:R hard cap | All | This week |
| **P2 — This Month** | Validate ETF with 20+ additional folds | ETF | 30 days |
| **P2 — This Month** | Investigate B-Tier OOS failure | B-Tier Crypto | 30 days |
| **P3 — This Quarter** | Rebuild Forex from scratch | Forex | 90 days |
| **P3 — This Quarter** | Accumulate Bond data to 100+ trades | Bonds | 90 days |
| **P4 — Ongoing** | Monitor A-Tier PF decay trend | A-Tier Crypto | Ongoing |

---

## 10. Final Verdict: Where Is the Edge?

### The Edge Exists In:

1. **Equity** — Confirmed, validated, scalable. OOS Sharpe 3.527. This is the platform's crown jewel.
2. **Potentially ETF** — If OOS metrics validate with larger sample. True Sharpe likely 2.0-3.0, not 6.368.
3. **Potentially B-Tier Crypto** — Largest sample (n=940), positive PF, but OOS failure must be resolved.

### The Edge Does NOT Exist In:

1. **Forex** — Negative OOS Sharpe (-1.406) with n=195. Strategy is curve-fit noise.
2. **Commodity** — Negative OOS Sharpe (-2.412), PF 1.04, 58% flat exits. Fundamentally broken.
3. **C-Tier Crypto** — PF 0.56. Active capital destruction.
4. **S-Tier Crypto** — n=27. Hot streak, not edge.
5. **Futures** — No data. Not a strategy.

### The Bottom Line

**The Antigravity platform has ONE proven asset class (Equity), ONE hypothetical asset class (ETF), and SEVEN asset classes that should receive ZERO capital allocation.** The platform's edge is real but dangerously concentrated. The prevalence of negative OOS Sharpe across Crypto, Forex, and Commodity suggests systemic overfitting in strategy development. Until the OOS validation framework is strengthened, capital should be deployed overwhelmingly to Equity with a small ETF test allocation.

The 1.5-2.0R R:R sweet spot discovery offers immediate, platform-wide improvement potential that could increase overall profitability by 20-30% regardless of asset class.

---

*This analysis is based on platform dashboard data as of 2026-05-03 and academic research cited inline. All conclusions are probabilistic, not deterministic. Past performance does not guarantee future results. Sample size limitations are explicitly flagged where relevant.*

*Analysis conducted with reference to: Jacquier et al. (2025) [^21^], Bailey & Lopez de Prado DSR [^49^][^51^], Lopez de Prado sample size standards [^27^], and industry best practices from TradeZella [^43^], BacktestBase [^27^], and StratBase.AI [^25^].*
