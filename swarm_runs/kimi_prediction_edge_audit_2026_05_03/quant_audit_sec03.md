## 3. The Broken Scoring System: F-Score vs Score vs Composite

The Antigravity dashboard displays at least five distinct scores: F-Score ("4/9"), Score ("0.748" or "0.703"), Composite Score, elite_score, and blended_conf. Each carries a different scale and a different relationship to actual trading outcomes. The platform's correlation audit on 3,500 closed picks reveals the most prominently displayed score is only weakly predictive ($r=+0.10$), while the metric buried deepest in the component layer is the strongest ($r=+0.242$) [^175^]. This section disambiguates each score, demonstrates why the composite fails as a monotonic predictor, and establishes a filter hierarchy grounded in empirical win-rate data.

### 3.1 What Each Score Measures

#### 3.1.1 F-Score (4/9): Piotroski F-Score — Fundamental Context, Not a Trading Signal

The F-Score of "4/9" is the Piotroski F-Score, a nine-point fundamental accounting metric from 2000 [^155^]. A score of 4 is "average/neutral." The F-Score is **not calculated by the platform**—it is external data shown as context. Piotroski's original study showed 23.5% annual returns for high F-Score stocks [^28^], but a 2021 study reported **-9.53% annual losses** over the prior decade due to alpha decay [^34^]. The Score Calibration Audit does not track F-Score, confirming its exclusion from the prediction pipeline [^175^]. For short-term trading, F-Score 4 carries no predictive value.

#### 3.1.2 Score (0.748/0.703): ML Confidence — Model Prediction Confidence on a 0-1.0 Scale

The "Score 0.748" or "0.703" is the platform's ML confidence score, sourced from the Alpha Engine's ml_score, KIMI's mlWinProb, or the Cross-System Aggregator's blended_conf [^84^][^83^]. These values sit in the empirically optimal band of 0.70-0.79, delivering a 57.0% win rate [^175^]. **This is not a composite score**—it is raw confidence output from a single ML model. It follows an inverted-U pattern: the 0.90-1.00 band delivers only 47.1% win rate, an "overconfidence penalty" of 10 percentage points below the sweet spot [^175^]. Raw ml_score correlates with win rate at $r=-0.012$ (noise), while the ML composite achieves $r=+0.220$ [^175^]. Users should target 0.70-0.79 and avoid >0.85.

#### 3.1.3 Composite Score (elite_score): Weighted Combination with a Documented Formula

The composite score (elite_score) aggregates seven components on a 0-100 scale: ML Score (25 points), Forward WR (25 points), Confluence (15 points), Monte Carlo (15 points), Risk:Reward (10 points), Volume (5 points), and Regime (5 points) [^84^]. Yet the Score Calibration Audit found elite_score correlates with actual returns at only $r=+0.10$—half as predictive as ml_composite_score ($r=+0.220$) and less than half as predictive as forward_wr ($r=+0.242$) [^175^]. The composite assigns weight to anti-predictive components while underweighting the strongest signal, a structural problem analyzed in Section 3.3.

#### 3.1.4 Visual Hierarchy: Which Score to Use for Which Decision

| Dimension | F-Score (Piotroski) | Score 0.748/0.703 | Composite (elite_score) |
|-----------|---------------------|-------------------|------------------------|
| **What it measures** | Fundamental accounting health (0-9 scale) | ML model confidence / consensus (0-1.0 scale) | 7-component weighted sum (0-100 scale) |
| **Source** | External financial statements; not computed by platform | Platform ML subsystems (Alpha Engine, KIMI, Claude Gainer) | Alpha Engine aggregator |
| **Correlation with actual WR** | Not tracked by platform | -0.012 (raw ml_score) / +0.220 (ML composite) [^175^] | +0.100 (weak, non-monotonic) [^175^] |
| **Predictive validity** | None for short-term directional trading | Sweet spot at 0.70-0.79 (57% WR); inverted U pattern [^175^] | Broken — 4 inversions across 9 deciles [^175^] |
| **User action** | Ignore for trading decisions; context only | Target 0.70-0.79 band; avoid >0.85 | Supplementary only; verify forward_wr independently |
| **Best threshold** | N/A (context only) | 0.70-0.79 (empirical sweet spot) [^175^] | >=75 only if forward_wr >=55% |

These three scores answer different questions. F-Score asks about financial health; Score asks about ML confidence; Composite asks about multi-dimensional rating. Only the Score, when filtered to 0.70-0.79, carries a direct empirical relationship to win rate. The F-Score is external context; the composite is a synthetic metric whose components require independent verification.

### 3.2 Why the Composite Score Is Not Monotonic

A predictive score should be monotonic: each increment should correspond to equal or higher probability of success. The elite_score fails this test, with **four inversions across nine deciles**—points where a higher score predicts a lower win rate [^175^].

| Decile | Score Range | Win Rate | Direction | Status |
|--------|-------------|----------|-----------|--------|
| D1 | 0-12 | 36.5% | Baseline | Working — heavy penalty correct |
| D2 | 12-18 | 41.2% | Rising | Expected |
| D3 | 18-20 | 48.3% | Rising | Expected |
| D4 | 20-28 | 54.9% | Rising | Expected |
| D5 | 28-30 | 55.7% | Rising | Expected — local peak |
| D6 | 30-35 | 43.1% | **Falling** | **INVERSION #1** |
| D7 | 35-40 | 35.7% | **Falling** | **INVERSION #2 — Dead Zone** |
| D8 | 40-48 | 52.0% | **Rising** | **INVERSION #3 — Recovery from dead zone** |
| D9 | 48-60+ | 47.8% | **Falling** | **INVERSION #4 — Overconfidence penalty** |

The D5-to-D7 progression is particularly damaging: win rate collapses from 55.7% to 35.7%—a 20-percentage-point decline despite a 12-point score increase. D6-D7 functions as a "dead zone" where mid-range scores mask poor performance [^175^]. D8 recovers to 52.0% before D9 falls to 47.8%, meaning the score zigzags rather than improves monotonically. Such a pattern cannot serve as a reliable filtering threshold.

#### 3.2.2 The Overconfidence Penalty

The D9 inversion reflects the same overconfidence penalty seen in raw ML confidence. Highly confident predictions react to regime_bonus ($r=-0.115$) or noise features that inflate the composite while degrading outcomes [^175^]. The 0.70-0.79 band's 57.0% win rate outperforms the 0.90+ band's 47.1% by 10 percentage points, confirming that medium-confidence predictions paradoxically achieve greater accuracy [^175^].

### 3.3 Inverted Weights

The composite's non-monotonicity stems from a weighting scheme that inverts the empirical correlation ranking: the strongest predictors receive modest weights, while anti-predictive components receive substantial allocations.

#### 3.3.1 Component Correlation vs. Weight Allocation

| Component | Correlation ($r$) with WR | Current Weight | Predictive Signal | Proposed Weight | Proposed Change |
|-----------|--------------------------|----------------|-------------------|-----------------|-----------------|
| **forward_wr** | **+0.242** | 25 pts | Best predictor | **55 pts** | +120% |
| leverage_safety | +0.133 | 5 pts | Moderate positive | 10 pts | +100% |
| source_system | +0.080 | N/A | Weak positive | 5 pts | — |
| elite_score (composite) | +0.100 | Aggregate | Weak (non-monotonic) [^175^] | N/A | Rebuild formula |
| ml_composite_score | +0.220 | 25 pts | Moderate positive | 15 pts | -40% |
| **ml_score (raw)** | **-0.012** | **9-25 pts** | **Noise** | **4 pts** | **-56%** |
| market_cap_tier | +0.056 | N/A | Negligible | 5 pts | — |
| **regime_bonus** | **-0.115** | **20 pts** | **Anti-predictive** | **5 pts** | **-75%** |
| (15 components) | 0.000 | Various | Pure noise | 0-1 pts each | Eliminate |

Three structural problems are visible. **forward_wr**—the best predictor at $r=+0.242$—receives only 25 points, identical to the random ml_score. **regime_bonus** at $r=-0.115$ is actively harmful: it predicts worse returns, yet commands 20 points that inflate the composite when picks are weakest. Fifteen components carry zero correlation ($r=0.000$) yet consume aggregate weight [^175^].

#### 3.3.2 Proposed Weight Rebalance

The audit's proposed fix: forward_wr increases from 25 to 55 points (+120%), regime_bonus collapses from 20 to 5 points (-75%), and raw ml_score drops from 9 to 4 points (-56%) [^175^]. Until deployed, users should mentally reweight the elite_score by discounting regime_bonus and requiring forward_wr >=55% regardless of headline composite value.

### 3.4 What Users Should Actually Filter By

The trust_score >=5 filter delivers 68-71% win rate [^175^]—substantially higher than the composite's peak decile of 55.7%. It captures source quality, track record, and cross-system agreement. Forward_win_rate in the 50-65% band delivers 69.7% win rate [^175^], the second most effective filter. The Risk:Reward 1.5-2.0 band—identified as the sole profitable zone with Profit Factor 5.81—provides the tertiary gate. Confidence in the 0.70-0.79 band adds a fourth layer at 57.0% win rate, though the inverted-U pattern means it must be range-bound.

#### 3.4.1 Filter Hierarchy

| Rank | Filter | Threshold | Expected WR | Pick Count | Evidence Source |
|------|--------|-----------|-------------|------------|-----------------|
| **1** | **trust_score** | **>= 5** | **68-71%** | Moderate | Score Calibration Audit, Signal Brackets [^175^] |
| **2** | **forward_wr** | **50-65%** | **69.7%** | Moderate | Score Calibration Audit [^175^] |
| 3 | confidence (ML) | 0.70-0.79 | 57.0% | High | Empirical sweet spot [^175^] |
| 4 | Risk:Reward | 1.5-2.0 | 55-60% (band-dependent) | Moderate | Shadow data: PF 5.81 at 1.5-2.0 |
| 5 | Beta Confluence | >= 70 | Not empirically tested | Low | Theoretical quality gate [^83^] |
| — | confidence | 0.90+ | 47.1% | High | Overconfidence penalty — avoid [^175^] |
| — | trust_score | 0-2 | 37.4% | High | Filter OUT — worse than random [^175^] |

The hierarchy reveals a counter-intuitive finding: the platform's most prominent scores are not its most predictive filters. The trust_score and forward_wr filters—sitting lower in the UI—outperform headline scores by 10-20 percentage points. A user relying on the composite's "S" or "A" grade would select picks that underperform a trust_score >=5 threshold by 15-25 percentage points. The scoring architecture is broken in both its internal weighting and its presentation, directing users toward the least reliable metrics.

Users should treat the composite as a starting point, not a decision criterion. Any pick with elite_score below 75 should be discarded unless it passes trust_score >=5 and forward_wr 50-65% gates. The user's scores of 0.748 and 0.703 fall in the optimal confidence band, but confidence alone should never override a failing trust_score or forward_wr. The scoring system adds noise; the filter hierarchy subtracts it.
