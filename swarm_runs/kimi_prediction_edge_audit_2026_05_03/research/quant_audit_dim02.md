# Dimension 02: F-Score vs Score vs Composite Scoring

## Executive Summary

The Antigravity platform employs a multi-layered scoring architecture with **at least five distinct score types** operating across three layers (individual systems, cross-system aggregator, audit dashboard). The user's specific question references an **F-Score of 4/9** (likely Piotroski F-Score displayed as supplementary fundamental data) and **Scores of 0.748/0.703** (ML confidence/consensus scores). Based on empirical correlation analysis from the platform's own Score Calibration Audit (`SCORE_CALIBRATION_AUDIT_2026-04-06.md`), **Forward Win Rate (r=+0.242) is the single most predictive component**, while the raw `ml_score` is actually noise (r=-0.012). The **trust_score >= 5** is the most effective filter, delivering 68-71% win rates versus 37.4% for low-trust picks. Users should **not** rely on F-Score for directional trading signals and should **not** chase the highest confidence scores (0.90+ actually underperforms 0.70-0.79).

---

## 1. Score Type Taxonomy: What Each Score Means

### 1.1 F-Score (Piotroski F-Score) -- 4/9 Displayed

```
Claim: The F-Score of 4/9 is the Piotroski F-Score, a 9-point fundamental accounting 
       scoring system measuring financial health through profitability (4 pts), 
       leverage/liquidity (3 pts), and operating efficiency (2 pts). It is NOT 
       calculated by the Antigravity platform's prediction engine -- it is external 
       fundamental data displayed as context.

Source: Piotroski (2000) "Value Investing: The Use of Historical Financial Statement 
        Information to Separate Winners from Losers"; confirmed by user's 
        "4/9" notation matching Piotroski's 0-9 scale.

Confidence: HIGH

Predictive Power: MODERATE for long-term value investing; POOR for short-term 
                  directional trading. Piotroski's original study showed 23% annual 
                  returns for high F-Score (8-9) value stocks vs. weak (0-2) stocks 
                  [Piotroski 2000]. However:
                  - F-Score 4 = "average/neutral" financial health [StockTitan, Forbes]
                  - F-Score is backward-looking (accounting data) and updated quarterly
                  - Academic evidence shows F-Score effectiveness has decayed 
                    post-publication (McLean & Pontiff 2016: 26% lower out-of-sample, 
                    58% lower post-publication) [CFA UK 2024]
                  - The platform's Score Calibration Audit does NOT list F-Score as 
                    a tracked component, confirming it is not part of the prediction 
                    pipeline

Recommended Threshold: F-Score >= 7 for value investing; F-Score 4-6 is neutral 
                       and should NOT be interpreted as a trading signal. For the 
                       Antigravity platform's short-term trading focus, F-Score 
                       should be treated as supplementary context only.
```

**F-Score Interpretation Scale:**
| Range | Meaning | Trading Relevance |
|-------|---------|-------------------|
| 8-9 | Strong financial health | Mild positive context |
| 7 | Good | Neutral-positive context |
| **4-6** | **Average/neutral** | **No signal value** |
| 0-3 | Weak/deteriorating | Mild negative context |

### 1.2 Score 0.748 / 0.703 -- ML Confidence / Consensus Score

```
Claim: The "Score 0.748" or "Score 0.703" is the platform's ML confidence score, 
       consensus confidence, or pump_probability from one of the ML subsystems 
       (Alpha Engine ml_score, KIMI mlWinProb, Claude Gainer pump_probability, 
       or Cross-System Aggregator blended_conf).

Source: Antigravity GitHub SCORING.md, SCORING_ALPHA.md, SCORING_CONSENSUS.md; 
        Score Calibration Audit 2026-04-06

Confidence: HIGH

Predictive Power: MIXED -- depends entirely on WHICH score and at what threshold:
                  - Raw ml_score: r=-0.012 (NOISE -- essentially random) 
                    [Score Calibration Audit]
                  - ML composite score: r=+0.22 (moderately predictive)
                    [Score Calibration Audit]
                  - Confidence 0.70-0.79 range: 57% WR (SWEET SPOT)
                    [Score Calibration Audit]
                  - Confidence 0.90-1.00: 47% WR (OVERCONFIDENCE PENALTY -- WORSE 
                    than 0.70-0.79 range!)
                    [Score Calibration Audit]
                  - This creates a counter-intuitive "inverted U" where medium 
                    confidence outperforms high confidence

Recommended Threshold: 0.70-0.79 is the empirically optimal confidence band per 
                       the platform's own audit data. AVOID >0.85 (proposed -5 
                       penalty in audit fixes). The user's scores of 0.748 and 
                       0.703 fall squarely in this optimal window.
```

**Confidence Score Sweet Spot Analysis:**
| Confidence Range | Win Rate | Notes |
|-----------------|----------|-------|
| 0.70-0.79 | **57.0%** | **OPTIMAL -- empirical sweet spot** |
| 0.90-1.00 | 47.1% | Overconfidence penalty -- AVOID |
| 0.30-0.50 | ~40% | Below baseline |

### 1.3 Composite Scoring -- Elite Score (0-100)

```
Claim: "Composite scoring" in the platform refers to the Alpha Engine's elite_score 
       (0-100 points, 7 weighted components): ML Score (25 pts), Forward WR (25 pts), 
       Confluence (15 pts), Monte Carlo (15 pts), Risk:Reward (10 pts), Volume (5 pts), 
       Regime (5 pts). Grade scale: S (90+), A (75-89), B (60-74), C (45-59), 
       D (30-44), F (<30).

Source: Antigravity GitHub SCORING_ALPHA.md (117 lines, 90 loc)

Confidence: HIGH (direct from platform documentation)

Predictive Power: WEAK overall -- r=+0.10 with actual returns. The elite_score is 
                  only HALF as predictive as ml_composite_score (r=+0.22). Score 
                  Calibration Audit found 4 inversions out of 9 deciles -- the 
                  score is "not monotonic" (higher score does NOT consistently 
                  predict higher WR). D6-D7 (score 30-40) is a "dead zone" where 
                  WR drops to 35-43% despite mid-range scores.

                  Component breakdown from correlation audit:
                  - forward_wr: r=+0.242 (BEST predictor, 25 pts max)
                  - leverage_safety: r=+0.133 (2nd best, only 5 pts max)
                  - ml_score: r=-0.012 (NOISE, yet gets 9-25 pts)
                  - regime_bonus: r=-0.115 (ANTI-PREDICTIVE -- higher bonus = 
                    worse returns!)
                  - 15 components are pure noise (r=0.000)

Recommended Threshold: Per the audit's proposed fixes, the scoring weights should 
                       be dramatically rebalanced: forward_wr should increase from 
                       25 to 55 pts (+37%), regime_bonus should drop from 20 to 5 
                       pts (-75%), ml_score should drop from 9 to 4 pts (-55%).
                       
                       Current: Score >= 60 is "B grade" but delivers only 
                       ~48% WR (failing). Users should filter for:
                       - elite_score >= 75 (A grade) with FORWARD_WR >= 55%
                       - OR ignore elite_score entirely and filter on fwd_wr 50-65 
                         (69.7% WR) + trust >= 5 (68-71% WR)
```

### 1.4 Cross-System Consensus Score (blended_conf)

```
Claim: The Cross-System Aggregator produces a blended_conf score using the formula:
       blended_conf = 0.60 x raw_conf + 0.40 x system_WR (or 0.70 x if WR unknown).
       This is WR-anchored confidence that mixes model confidence with actual 
       historical performance. Additional consensus_boost of +0.03 per agreeing 
       system (max +9%). Hard cap at 0.95.

Source: Antigravity GitHub SCORING_CONSENSUS.md

Confidence: HIGH

Predictive Power: MODERATE. The WR-anchoring (60% model / 40% real WR) is the 
                  correct theoretical approach per academic literature. Balachandran, 
                  Saraph & Ang (2013) showed that ML-enhanced F-Score strategies 
                  with real-performance anchoring deliver 87.5% higher Sharpe ratios 
                  than vanilla F-Score [CFA UK 2024].

Recommended Threshold: blended_conf >= 0.60 with at least MODERATE consensus 
                       (2+ weighted votes). SUPER consensus (>=6 votes) provides 
                       maximum reliability.
```

### 1.5 Beta Confluence Score (5 Pillars, 0-100)

```
Claim: The Beta Confluence Score is a 5-pillar composite (Technical 25 pts, 
       On-chain 20 pts, Sentiment 15 pts, Risk/Reward 20 pts, Structure 20 pts).
       Qualified threshold: >= 70.

Source: Antigravity GitHub SCORING_CONSENSUS.md

Confidence: HIGH

Predictive Power: MODERATE when used as a gate. The 5-pillar design follows OECD 
                  composite indicator best practices (Handbook on Constructing 
                  Composite Indicators, 2008). However, no empirical correlation 
                  data is available in the audit for this specific score.

Recommended Threshold: >= 70 ("Qualified"). Used in combination with trust_score 
                       >= 5 and fwd_wr 50-65%.
```

---

## 2. Which Score Is Most Predictive? (Empirical Ranking)

Based on the **Score Calibration Audit (n=3,500 closed picks)** from the platform's own data:

| Rank | Score/Component | Correlation (r) | Predictive Power | Verdict |
|------|----------------|-----------------|------------------|---------|
| 1 | **forward_wr** | **+0.242** | **BEST** | Only metric with meaningful predictive signal |
| 2 | **ml_composite_score** | **+0.220** | MODERATE | Best ML-derived score |
| 3 | leverage_safety | +0.133 | MODERATE | 2nd best but underweighted |
| 4 | source_system | +0.080 | WEAK | Moderate signal |
| 5 | **elite_score** | **+0.100** | **WEAK** | Current composite is half as predictive as ml_composite |
| 6 | market_cap_tier | +0.056 | VERY WEAK | |
| 7 | ml_score | **-0.012** | **NOISE** | Raw ML score is essentially random |
| 8 | regime_bonus | **-0.115** | **ANTI-PREDICTIVE** | Higher bonus = WORSE returns |

### Key Finding: The Composite Score Is BROKEN

The elite_score (the main "composite score" users see) has a critical design flaw: **it is NOT monotonic**. From the audit:
- D4 (score 20-28): 54.9% WR
- D5 (score 28-30): 55.7% WR  
- D6 (score 30-35): 43.1% WR **(INVERSION -- score goes UP, WR goes DOWN)**
- D7 (score 35-40): 35.7% WR **(DEAD ZONE)**
- D8 (score 40-48): 52.0% WR **(RECOVERY)**

**4 inversions out of 9 deciles.** The score frequently goes up while actual win rate goes down.

### What Users Should Actually Filter For

| Filter | Threshold | Win Rate | Evidence |
|--------|-----------|----------|----------|
| **trust_score** | **>= 5** | **68-71%** | Score Calibration Audit, Signal Brackets section |
| **fwd_wr** | **50-65%** | **69.7%** | Score Calibration Audit |
| confidence | 0.70-0.79 | 57.0% | Sweet spot -- optimal band |
| confidence | 0.90+ | 47.1% | AVOID -- overconfidence penalty |
| trust_score | 0-2 | 37.4% | Baseline -- filter OUT |
| Heavy penalty (score<20) | n=988 | 36.5% | Working correctly -- avoid |

---

## 3. Academic Evidence: Fundamental vs ML Scoring

### 3.1 Piotroski F-Score -- Historical Performance

Piotroski's original 2000 study demonstrated 23% annual returns for a long/short strategy buying high F-Score (8-9) and shorting low F-Score (0-1) stocks between 1976-1996 [Piotroski 2000]. Subsequent research:

| Study | Period | Market | Findings |
|-------|--------|--------|----------|
| Piotroski (2000) | 1976-1996 | US | 23.5% CAGR, +7.5% over value |
| Mohr (2012) | incl. 2008 crisis | Eurozone | 24.57% annual long/short, +10.74% market-adjusted |
| Amor-Tapia & Tascon (2016) | OOS | 4 European markets | F-Score survived OOS; newer models did not |
| "Why Piotroski's F-Score No Longer Works" | 1998-2021 | US | **-9.53% annual loss** over last 10 years; **-11.75%** over 20 years |
| Balachandran, Saraph & Ang (2013) | 1977-2010 | US | ML-enhanced F-Score: 87.5% of strategies beat vanilla F-Score Sharpe |
| QuantConnect backtest | 2020-2023 | US | 193.8% total return (43.2% CAGR) vs SPY 49.6% |
| 2024 Springer study | 1973-2016 | US | Macro factors affect F-Score: 2/3 firm-level, 1/3 macro; macro is 5x more important in contractions |

**Key insight from CFA UK (2024)**: "Both Piotroski's F-Score and Mohanram's G-Score were the only ones surviving an out-of-sample backtesting delivering statistically significant alpha despite the other rejected models being developed at a later date." However, McLean & Pontiff (2016) documented "alpha decay" of 26% out-of-sample and 58% post-publication [CFA UK 2024].

### 3.2 ML Confidence Scores -- Performance

| Study | Approach | Result |
|-------|----------|--------|
| Balachandran et al. (2013) | Linear Regression, Logistic, SVM on F-Score features | 87.5% of ML strategies delivered higher Sharpe than vanilla F-Score; SVM particularly strong |
| Mneirji & Hornfeldt (2025) | XGBoost confidence 0-10 | ML model outperformed buy-and-hold by avoiding losses in volatile periods |
| Hybrid Ensemble Study (2025) | Voting/Stacking ensembles | Stacking: MAE 0.0332, a20=0.70; Voting: MAE 0.0347, a20=0.68 |
| Transfer Learning Study (2026) | Fusion + Transfer | Transfer Learning achieved highest R-squared, lowest MAE/MSE/RMSE |
| Technical+Fundamental+Macro (2025) | RF, GB, XGBoost | Stage 1 (technical only): 62-78% accuracy; Stage 2 (+fundamental+macro): 90%+ accuracy; XGBoost: 96-98% |

### 3.3 Composite Score Aggregation -- Best Practices

The OECD Handbook on Constructing Composite Indicators (2008) recommends:
1. **Equal weighting** performs well vs. complex methods
2. **Geometric aggregation** for non-compensability (prevents one strong indicator from masking weakness)
3. **Linear aggregation** (weighted sum) is most common but allows full compensability
4. **Correlation audit** -- "check whether indicators dominate (correlation > 0.95), are under-represented (-0.5 < r < 0.5), or negatively related (r < -0.5)"

The Antigravity platform's score follows weighted linear aggregation (elite_score = sum of weighted components), which is standard but has the documented compensability problem where a high regime_bonus (which is anti-predictive) can mask a low forward_wr (which is the best predictor).

---

## 4. Is "Composite Scoring" Documented in the Platform?

**YES.** The term "composite scoring" is extensively documented across the platform's GitHub repository:

| Document | Lines | Description |
|----------|-------|-------------|
| `SCORING.md` | 394 lines | Master document covering all scoring systems |
| `SCORING_ALPHA.md` | 117 lines | Alpha Engine elite_score (7 components, 0-100) |
| `SCORING_CONSENSUS.md` | 57 lines | Cross-system aggregator (trust-weighted voting, Beta Confluence) |
| `SCORING_KIMI.md` | 90+ lines | KIMI mlWinProb (0-1.0) with confluence scoring |
| `SCORING_AUDIT.md` | 80+ lines | Audit dashboard (health scores, pick quality grades) |
| `SCORE_CALIBRATION_AUDIT_2026-04-06.md` | 82 lines | Empirical correlation analysis of all components |

The user's "Score 0.748" is most likely the **ml_score** component (0-1.0, multiplied by 25 to get 0-25 pts in the elite_score), or the **blended_conf** from the consensus aggregator (0-1.0, capped at 0.95), or **pump_probability** from Claude Gainer ML (0-1.0).

---

## 5. Recommendations for Users

### 5.1 Ignore F-Score for Trading Decisions

```
Claim: F-Score 4/9 is neutral/average and has NO predictive value for the platform's 
       short-term trading signals. It is fundamental context, not a trading signal.
Action: Do NOT use F-Score to filter picks. Focus on forward-tested metrics instead.
```

### 5.2 Target the Confidence Sweet Spot (0.70-0.79)

```
Claim: The platform's own audit data shows confidence 0.70-0.79 delivers 57% WR 
       while 0.90+ delivers only 47% WR. This "overconfidence penalty" is a 
       well-documented phenomenon in ML calibration.
Action: Target picks with confidence 0.70-0.79. AVOID >0.85.
```

### 5.3 Prioritize Forward WR + Trust Score Over Composite Score

```
Claim: forward_wr (r=+0.242) and trust_score >=5 (68-71% WR) are the two most 
       predictive filters available. The composite elite_score is broken (not 
       monotonic, 4/9 decile inversions).
Action: Use these filters IN ORDER:
        1. trust_score >= 5          (biggest impact: 68-71% WR)
        2. fwd_wr 50-65%             (69.7% WR in this band)
        3. confidence 0.70-0.79      (57% WR sweet spot)
        4. R:R >= 1.5                (risk management)
        5. Beta Confluence >= 70     (additional quality gate)
```

### 5.4 The Composite Score Needs Repair

```
Claim: Per the audit's proposed fixes (not yet implemented as of 2026-04-06):
       - forward_wr weight: 25 -> 55 pts (+37%) [best predictor is underweighted]
       - regime_bonus: 20 -> 5 pts (-75%) [anti-predictive component is overweighted]
       - ml_score: 9 -> 4 pts (-55%) [noise component is overweighted]
       - Add trust_score gate at 5: +15 bonus [biggest single improvement]
       - Add overconfidence penalty: -5 for conf > 0.85
Action: Users should mentally reweight the elite_score until fixes are deployed:
        - Discount regime and regime_bonus contributions heavily
        - Add +20-30 pts mentally if trust >= 5
        - Require fwd_wr >= 50% regardless of headline score
```

---

## 6. Summary Table: Score Comparison

| Dimension | F-Score (Piotroski) | Score 0.748/0.703 | Composite (elite_score) |
|-----------|---------------------|-------------------|------------------------|
| **What** | Fundamental accounting score (0-9) | ML confidence / consensus (0-1.0) | 7-component weighted sum (0-100) |
| **Source** | External financial statements | Platform ML subsystems | Alpha Engine aggregator |
| **Scale** | 0-9 | 0.000-1.000 | 0-100 |
| **Correlation with WR** | Not tracked by platform | -0.012 (raw) / +0.22 (composite) | +0.10 (weak, non-monotonic) |
| **Predictive?** | Not for short-term | Sweet spot at 0.70-0.79 | Broken -- needs repair |
| **User Action** | Ignore for trading | Target 0.70-0.79, avoid >0.85 | Supplementary only; verify fwd_wr |
| **Best Threshold** | N/A (context only) | 0.70-0.79 | >=75 IF fwd_wr >= 55% |

---

## Sources

1. [^23] Antigravity GitHub: `SCORING.md` (2026-03-16) -- Master scoring reference
2. [^84] Antigravity GitHub: `SCORING_ALPHA.md` -- Elite Scorer 7-component breakdown
3. [^83] Antigravity GitHub: `SCORING_CONSENSUS.md` -- Cross-system aggregator formulas
4. [^175] Antigravity GitHub: `SCORE_CALIBRATION_AUDIT_2026-04-06.md` -- Empirical correlation analysis (n=3,500)
5. [^218] Antigravity GitHub: `QUANT_FORENSIC_AUDIT_REPORT.md` (2026-04-11) -- Full system audit
6. [^155] OldSchoolValue: Piotroski F-Score methodology
7. [^34] StableBread: "Why Piotroski's F-Score No Longer Works" -- post-publication decay evidence
8. [^28] CFA UK: "Evolution of Fundamental Scoring Models" -- ML enhancement of F-Score, alpha decay
9. [^41] Springer (2024): "Piotroski's Fscore under varying economic conditions" -- macro sensitivity
10. [^32] AIMS Press (2025): "Leveraging hybrid ensemble models" -- ensemble vs. single model performance
11. [^37] MDPI (2026): "Flexible Target Prediction" -- Transfer Learning vs. Fusion vs. Ensemble
12. [^25] OECD (2008): "Handbook on Constructing Composite Indicators" -- aggregation methodology
13. Piotroski, J. (2000). "Value Investing: The Use of Historical Financial Statement Information to Separate Winners from Losers." *Journal of Accounting Research*, 38, 1-41.
14. McLean, R.D. & Pontiff, J. (2016). "Does Academic Research Destroy Stock Return Predictability?" *Journal of Finance*, 71(1), 5-32.
15. Balachandran, S., Saraph, P. & Ang, E. (2013). "Enhancing Piotroski's F-Score Strategy Using Machine Learning Techniques."

---

*Analysis completed: 2026-04-22*
*Evidence base: 3,500+ closed picks from platform audit, 8 academic studies, full GitHub repository documentation*
