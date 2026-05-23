# Quantitative Trading Platform Audit: Detailed Content Plan

## Document Metadata
- **Date:** 2026-05-05
- **Source Research:** 14 dimension files, cross-verification matrix, 10 cross-dimension insights, artifact synthesis
- **Total Data Points:** 19 priority points, 8 high-confidence findings, 5 conflict zones
- **Word Count Target:** ~17,000 words across 11 chapters

---

## Chapter 1: Executive Summary & Key Findings (~1,500 words)

### Analytical Angle
The opening chapter delivers the single most important message: the platform has ONE proven asset class with genuine edge, a fundamentally broken scoring system, and faces a binary choice between retail narrow-edge operation or institutional transformation. This chapter must make the reader understand the gravity of findings within 60 seconds.

### Specific Data Points (with numbers)
1. Only Equity passes all 5 investability gates (PF 1.72, OOS Sharpe +3.527, n=136+, WR 53.1%)
2. Seven asset classes should receive ZERO capital allocation; three have negative OOS Sharpe (CRYPTO -0.242, FOREX -1.406, COMMODITY -2.412)
3. R:R 1.5-2.0 band is the ONLY profitable zone (PF 5.81, Kelly +47.2%); R:R >2.0 is catastrophic (PF 0.35)
4. Composite scoring system has 4 inversions out of 9 deciles — not monotonic
5. ml_score has r=-0.012 (pure noise) yet contributes 9-25 points to composite
6. Platform has approximately 5% of institutional infrastructure required
7. 0% of strategies have PSR > 0.95; 0% have DSR > 0.95
8. 99.7% risk of ruin for meme coins; only 0.4% of Pump.fun traders profitable
9. Penny stocks average -24% to -27% annually (Bruggemann et al., Eraker & Ready)
10. Expected returns: 15-25% for disciplined users (Equity only); -20 to -40% for YOLO approach
11. 119,598 commits with 11 contributors including AI agents = governance crisis
12. 5+ copies of outcome_resolver.py creating version-control risk
13. 90-day transformation cost: ~$1,500; ROI: 867%-5,233%
14. 12-month transformation cost: $32,400-78,000; ROI at $500K AUM: 64%-1,400%
15. The resolver fix revealed FOREX PF 0.27 — it didn't fix the strategy
16. trust_score >= 5 delivers 68-71% WR — the only filter users should trust

### Required Tables

**Table 1.1: Five-Gate Verdict Summary (Master Table)**
| Asset Class | PF | WR | OOS Sharpe | n | Verdict |
|-------------|-----|-----|------------|-----|---------|
| Equity | 1.72 | 53.1% | +3.527 | 136+ | SAFE |
| ETF | 1.32 | 52.9% | +6.368* | 45 | CAUTION |
| Crypto B-Tier | 1.28 | 45.0% | -0.242 | 940 | CAUTION |
| Crypto A-Tier | 1.58 | 42.4% | -0.242 | 304 | CAUTION |
| Forex | 1.41 | 21.4% | -1.406 | 195+ | DANGEROUS |
| Commodity | 1.04 | 21.2% | -2.412 | 143 | DANGEROUS |
| Crypto S-Tier | 6.80 | 70.4% | -0.242 | 27 | DANGEROUS |
| Crypto C-Tier | 0.56 | 28.1% | -0.242 | 224 | DANGEROUS |
*ETF OOS Sharpe 6.368 is artifact of only 12 folds

**Table 1.2: The 5 Numbers Every Stakeholder Must Know**
| # | Finding | Implication |
|---|---------|-------------|
| 1 | Equity OOS Sharpe +3.527 is the only genuine edge | 25% Equity allocation max |
| 2 | R:R 1.5-2.0 band PF 5.81 is only profitable zone | Hard floor at 1.5, hard ceiling at 2.0 |
| 3 | elite_score has 4/9 decile inversions | Do NOT trust the headline score |
| 4 | ~5% of institutional infrastructure exists | 90-day/$1,500 MVP needed urgently |
| 5 | 99.7% meme coin risk of ruin | Complete exclusion required |

**Table 1.3: Immediate Actions Matrix**
| Timeframe | Action | Owner | Impact |
|-----------|--------|-------|--------|
| This week | HALT C-Tier crypto (PF 0.56) | Platform ops | Prevents capital destruction |
| This week | Fix HTML comment bug (template.html lines 1813-1825) | Dev team | Stops visible text leak |
| This week | Filter by trust_score >=5, not elite_score | Users | 68-71% WR vs 37-48% |
| 30 days | Implement PSR > 0.95 gate | Quant team | Blocks false discoveries |
| 90 days | Complete 6-gate MVP transformation | Leadership | Achieves minimum institutional status |
| 12 months | Full institutional transformation | Leadership | Credible quant fund quality |

### Key Citations
- HC-1 (Only Equity Has Genuine Statistical Edge)
- HC-2 (R:R 1.5-2.0 Band is Only Profitable Zone)
- HC-3 (Composite Scoring is Fundamentally Broken)
- HC-4 (Meme Coins Should Be Excluded)
- Dim01 Master Verdict Table
- Dim12 Executive Summary (5% infrastructure)
- Cross-Insight 1 (Survivorship Illusion), 2 (Overconfidence Penalty), 9 (Asymmetric Alpha), 10 (Retail vs Institutional Divide)

### Connection to Other Chapters
- Ch1 is the gateway — every subsequent chapter expands on one finding here
- Ch2 expands the asset class verdict with full five-gate analysis
- Ch3 details the broken scoring system
- Ch5 covers the 11 failing strategies
- Ch11 presents the transformation roadmap

---

## Chapter 2: Edge Analysis Per Asset Class (~2,500 words)

### Analytical Angle
This chapter applies a rigorous five-gate framework to every asset class, revealing that only Equity has genuine statistical edge. The analysis exposes overfitting signatures (negative OOS Sharpe), survivorship illusions (S-Tier Crypto n=27), and structural mismatches (Commodity 58% flat exits). The R:R 1.5-2.0 discovery transforms understanding of platform-wide profitability.

### Specific Data Points (with numbers)
1. **Equity (SAFE):** PF 1.72, WR 53.1%, OOS Sharpe +3.527, n=136+, total PnL +233.46%, OOS WR 57.9% (OUTPERFORMS in-sample — opposite of overfitting)
2. **ETF (CAUTION):** PF 1.32, WR 52.9%, OOS Sharpe +6.368 (artifact — only 12 folds, 10.8 decay), n=45 IS trades, estimated true Sharpe 2.0-3.0
3. **Crypto B-Tier (CAUTION):** PF 1.28, WR 45.0%, n=940 (exceeds institutional threshold), "workhorse" status, but negative aggregate OOS Sharpe
4. **Crypto A-Tier (CAUTION):** PF 1.58, WR 42.4%, n=304, PF decaying 1.98 L20 -> 1.23 L100
5. **Forex (DANGEROUS):** PF 0.27 post-fix, WR 21.4%, OOS Sharpe -1.406, n=195+; revealed as broken by resolver fix
6. **Commodity (DANGEROUS):** PF 1.04, WR 21.2%, OOS Sharpe -2.412, n=143, cta_commodity_momentum_term PF 0.02 with 58% flat exits
7. **Crypto S-Tier (DANGEROUS):** PF 6.80, WR 70.4%, n=27 (statistically meaningless), OOS Sharpe -0.242 — hot streak, not edge
8. **Crypto C-Tier (DANGEROUS):** PF 0.56, WR 28.1%, n=224 — capital destruction
9. **Bonds (CAUTION):** PF 1.72, WR 50.0%, n~20 (below minimum), no OOS Sharpe data
10. **Futures (DANGEROUS):** No data at all
11. **R:R 1.5-2.0 band:** PF 5.81, Kelly +47.2%, derived win rate 76.85%, Quarter-Kelly 15.9%
12. **R:R >2.0 band:** PF 0.35 (catastrophic), Full Kelly -22.8%
13. **R:R 1.25-1.5 band:** PF 1.01 (breakeven), Kelly -1.6% (correctly blocked)
14. Recommended allocation: 25% Equity, 5% ETF (pending validation), 70% cash/reserve

### Required Tables

**Table 2.1: Five-Gate Framework Definition**
| Criterion | Threshold | Academic Basis |
|-----------|-----------|----------------|
| Profit Factor (PF) | > 1.2 (preferably > 1.3) | PF 1.0-1.2 = breakeven after costs |
| Win Rate (WR) | > 40% (context-dependent with R:R) | 40% WR at 2:1 R:R is profitable |
| Positive OOS Sharpe | > 0 (preferably > 1.0) | Negative = strategy fails on unseen data |
| Minimum Sample Size | 100+ trades (200+ preferred) | 200-500 = institutional grade |
| OOS/IS Performance Ratio | > 0.5 | Ratio < 0.5 signals severe overfitting |

**Table 2.2: PF Classification Scale**
| PF Range | Classification | Equity Position |
|----------|---------------|-----------------|
| < 1.0 | Losing Strategy | Destroying capital |
| 1.0 - 1.2 | Breakeven Territory | Fragile, costs erase edge |
| 1.2 - 1.5 | Solid Edge | Minimum deployable threshold |
| 1.5 - 2.0 | Strong Edge | Professional/hedge fund range |
| > 2.0 | Exceptional (Verify) | Rare, check for curve-fitting |

**Table 2.3: R:R Band Analysis — The Profitability Discovery**
| R:R Band | PF | Kelly | Quarter-Kelly | Platform Status | Verdict |
|----------|-----|-------|--------------|-----------------|---------|
| 1.25-1.5 | 1.01 | -1.6% | 0% (BLOCKED) | Correctly blocked | Breakeven |
| 1.5-2.0 | 5.81 | +47.2% | 11.8% (used) | Active | ONLY PROFITABLE ZONE |
| > 2.0 | 0.35 | -22.8% | 0% (BLOCKED) | Correctly blocked | Catastrophic |

**Table 2.4: Recommended Capital Allocation**
| Asset Class | Allocation | Rationale |
|-------------|-----------|-----------|
| Equity | 25% | Only validated edge (PF 1.72, OOS Sharpe +3.527) |
| ETF | 5% (pending validation) | OOS Sharpe artifact — needs 20+ additional folds |
| Cash/Reserve | 70% | Edge is narrow — preserve capital through exclusion |
| All other asset classes | 0% | Negative OOS Sharpe or insufficient sample |

### Key Citations
- Jacquier et al. (2025) — OOS Sharpe replication ratio [^21^]
- Bailey & Lopez de Prado DSR [^49^][^51^]
- Lopez de Prado (2018) — minimum 200-500 trades [^27^]
- PF threshold literature [^43^][^37^][^38^]
- HC-1, HC-2, HC-4, HC-5
- Cross-Insight 1 (Survivorship Illusion), 5 (Structural Decay)

### Connection to Other Chapters
- Ch6 (Penny Stocks) expands wealth-destruction evidence
- Ch7 (Meme Coins) expands the 99.7% risk of ruin
- Ch8 (Risk Management) details Kelly sizing for the R:R 1.5-2.0 band
- Ch9 (User Safety) translates these findings into actionable rules

---

## Chapter 3: Scoring Methodology — F-Score vs Score vs Composite (~1,500 words)

### Analytical Angle
This chapter exposes the platform's scoring system as fundamentally broken through empirical correlation analysis from the platform's own audit data (n=3,500). The composite score is not monotonic, gives maximum weight to the least predictive components, and produces a "dead zone" where higher scores predict LOWER win rates. Users are given a practical workaround (trust_score >= 5, forward_wr 50-65%) while fixes remain unimplemented.

### Specific Data Points (with numbers)
1. **elite_score (composite) is NOT monotonic** — 4 inversions out of 9 deciles
2. **D4 (score 20-28):** 54.9% WR; D5 (score 28-30): 55.7% WR; D6 (score 30-35): 43.1% WR (INVERSION); D7 (score 35-40): 35.7% WR (DEAD ZONE); D8 (score 40-48): 52.0% WR (recovery)
3. **forward_wr:** r=+0.242 — BEST predictor, gets only 25 pts (should get 55)
4. **ml_score:** r=-0.012 — PURE NOISE, gets 9-25 pts (should get 4)
5. **regime_bonus:** r=-0.115 — ANTI-PREDICTIVE, gets 20 pts (should get 5)
6. **ml_composite_score:** r=+0.220 — moderately predictive, underweighted
7. **leverage_safety:** r=+0.133 — 2nd best, gets only 5 pts
8. **15 components are pure noise** (r=0.000)
9. **Confidence 0.70-0.79:** 57% WR (OPTIMAL sweet spot)
10. **Confidence 0.90+:** 47% WR (overconfidence penalty — WORSE than medium confidence)
11. **trust_score >= 5:** 68-71% WR — the MOST effective filter
12. **fwd_wr 50-65:** 69.7% WR — second most effective filter
13. **Proposed weight rebalance:** forward_wr 25->55 pts (+37%), regime_bonus 20->5 pts (-75%), ml_score 9->4 pts (-55%)
14. **Fixes identified but NOT implemented** as of 2026-04-06
15. **F-Score 4/9:** Piotroski F-Score — "average/neutral" financial health, NOT a trading signal, effectiveness decayed 26% post-publication (McLean & Pontiff 2016), 58% lower post-publication
16. **blended_conf:** 0.60 x raw_conf + 0.40 x system_WR — WR-anchored, academically correct approach

### Required Tables

**Table 3.1: Score Component Correlation Rankings (from Score Calibration Audit, n=3,500)**
| Rank | Component | Correlation (r) | Current Points | Verdict |
|------|-----------|-----------------|----------------|---------|
| 1 | forward_wr | +0.242 | 25 | UNDERWEIGHTED by 30 pts |
| 2 | ml_composite_score | +0.220 | N/A | Best ML score |
| 3 | leverage_safety | +0.133 | 5 | 2nd best, severely underweighted |
| 4 | source_system | +0.080 | N/A | Weak signal |
| 5 | elite_score (composite) | +0.100 | N/A | Half as predictive as ml_composite |
| 6 | market_cap_tier | +0.056 | N/A | Very weak |
| 7 | ml_score | -0.012 | 9-25 | PURE NOISE — should be 4 pts |
| 8 | regime_bonus | -0.115 | 20 | ANTI-PREDICTIVE — should be 5 pts |

**Table 3.2: Confidence Score Sweet Spot (Overconfidence Penalty)**
| Confidence Range | Win Rate | Interpretation |
|-----------------|----------|----------------|
| 0.70-0.79 | 57.0% | OPTIMAL — empirical sweet spot |
| 0.80-0.89 | ~52% | Moderate |
| 0.90-1.00 | 47.1% | OVERCONFIDENCE PENALTY — AVOID |

**Table 3.3: Proposed vs Current Weight Rebalance**
| Component | Current Pts | Proposed Pts | Change | Rationale |
|-----------|-------------|--------------|--------|-----------|
| forward_wr | 25 | 55 | +120% | Only meaningful predictive signal |
| ml_score | 9-25 | 4 | -55 to -84% | r=-0.012 is noise |
| regime_bonus | 20 | 5 | -75% | r=-0.115 is anti-predictive |
| leverage_safety | 5 | 10 | +100% | r=+0.133 is 2nd best signal |
| Other components | various | various | Adjusted | Remove 15 noise components |

**Table 3.4: What Users Should ACTUALLY Filter For**
| Filter | Expected WR | Notes |
|--------|-------------|-------|
| trust_score >= 5 | 68-71% | MOST effective single filter |
| forward_wr 50-65% | 69.7% | Best predictive component |
| Confidence 0.70-0.79 | 57% | Sweet spot — NOT 0.90+ |
| ml_score >= 0.90 | 47% | WORSE than medium confidence |
| elite_score >= 75 (A grade) | ~52% | Grade alone is weak |

### Key Citations
- Score Calibration Audit (n=3,500 closed picks) — Dim02 primary source
- Piotroski (2000) — F-Score original study [Piotroski 2000]
- McLean & Pontiff (2016) — 26% decay post-publication
- Balachandran, Saraph & Ang (2013) — WR-anchoring [CFA UK 2024]
- HC-3 (Composite Scoring is Fundamentally Broken)
- Cross-Insight 2 (Overconfidence Penalty)

### Connection to Other Chapters
- Ch4 (UI/UX) shows how the broken score manifests in the interface
- Ch9 (User Safety) gives users the practical filter workaround
- Ch11 (Transformation) includes scoring system repair in 90-day plan
- Conflict Zone C-1 (ml_score threshold confusion) resolved here

---

## Chapter 4: UI/UX Analysis — Finding the Best Picks (~1,500 words)

### Analytical Angle
The UI chapter demonstrates that the platform's value is capital preservation through exclusion, not pick generation. The best filter combination (Verified Alpha + High Conviction + R:R 1.5+) produces 66-70% WR but shows only 0-2 picks — meaning 192 of 210 picks are gated out. This is a fundamentally different product proposition than users expect. The chapter also documents significant UX violations (three "Smart Picks" elements sharing the same name).

### Specific Data Points (with numbers)
1. **Triple filter (Verified Alpha + High Conviction + R:R 1.5+):** 66-70% WR, 0-2 picks
2. **Best daily driver (Verified Alpha + High Conviction):** 65-68% WR, 3-8 picks
3. **192 of 210 total picks are gated out** by the best filter combination
4. **Verified Alpha alone:** ~62-64% WR (highest single filter)
5. **High Conviction alone:** ~60-64% WR (forward-validated: FWD WR >=55%, score >= floor, >=5 forward trades)
6. **SMART PICKS filter:** ~58-60% WR (strictest per-asset gates)
7. **Trusted filter:** ~55-58% WR (vetted source tier)
8. **High-grade filter:** ~52-55% WR (pick quality gate)
9. **All picks (no filter):** ~45-50% WR (lowest quality floor)
10. **WR >=50% systems yield 64.1% WR** and +1153.51% total PnL
11. **WR <50% systems yield 43.8% WR** but paradoxically +1433.82% total PnL (higher variance)
12. **Three "Smart Picks" UI elements share the same name** — tab, filter toggle, stat metric
13. **Smart Snapshot stat: 48.9%** — below 50%, below random
14. **"High-grade" and "Trusted" are orthogonal dimensions** — pick quality vs source reputation
15. **HTML nested comment bug** in template.html lines 1813-1825 causes visible leaked text on US Equity Picks tab
16. **15+ console.log statements** in JavaScript expose internal architecture
17. **Missing UI elements:** active filter chips, pick counts per filter, confidence tooltips

### Required Tables

**Table 4.1: Single Filter Performance Ranking**
| Filter | Expected WR | Pick Volume | Risk-Adjusted Quality |
|--------|-------------|-------------|----------------------|
| Verified Alpha | ~62-64% | Low-Medium | Highest |
| High Conviction | ~60-64% | Medium | Highest |
| Smart Picks | ~58-60% | Low | High |
| Trusted | ~55-58% | Medium | Good |
| High-grade | ~52-55% | Medium | Moderate |
| R:R 1.5+ | ~50-52% | Medium | Good |
| All picks | ~45-50% | High (210) | Baseline |

**Table 4.2: Filter Combination Matrix**
| Combination | Expected WR | Pick Count | Best For |
|-------------|-------------|-----------|----------|
| Verified Alpha + High Conviction | 65-68% | 3-8 | Best daily driver |
| Verified Alpha + High Conviction + R:R 1.5+ | 66-70% | 0-2 | Highest WR, lowest volume |
| Verified Alpha + Recent | 62-64% | 5-15 | Regular refresh |
| Smart Picks + R:R 1.5+ | 58-60% | 0-3 | Conservative |
| High-grade + Trusted + R:R 1.5+ + Recent | 55-58% | 5-10 | Good volume/quality tradeoff |

**Table 4.3: The Three "Smart Picks" Naming Confusion**
| Element | Type | Behavior | Fix |
|---------|------|----------|-----|
| "Smart Picks" tab | Navigation tab | Standalone pre-filtered view | Rename to "Smart Picks Feed" |
| "Smart Picks" toggle | Filter button | Combinable with other filters | Rename to "Apply Smart Gates" |
| "Smart Picks" stat | Performance metric | Overall health percentage | Rename to "Smart Health Score" |

**Table 4.4: Platform Value Proposition — Pick Generation vs Exclusion**
| Metric | Number | Interpretation |
|--------|--------|----------------|
| Total active picks | 210 | Platform generates many picks |
| After Verified Alpha + HC + R:R 1.5+ | 0-2 | 99% are excluded |
| Picks gated out | 192/210 (91.4%) | Platform's value is EXCLUSION |
| WR of excluded picks | ~40-45% | Below breakeven after costs |
| Capital preserved by exclusion | Significant | Prevents wealth destruction |

### Key Citations
- Dim03 (primary) — all UI/UX analysis
- Dim09 — HTML bug (HC-6)
- HC-8 (Verified Alpha + High Conviction is Optimal UI Path)
- Cross-Insight 8 (Filter Paradox — best filter shows zero picks)
- UX best practices [^33^][^159^][^35^]

### Connection to Other Chapters
- Ch3 provides the scoring data that drives UI filter logic
- Ch9 translates optimal UI path into user decision rules
- Ch10 covers the HTML bug in technical detail
- Ch11 includes UI redesign in transformation plan

---

## Chapter 5: Strategy Diagnosis & Inverse Opportunities (~2,000 words)

### Analytical Angle
This chapter applies academic frameworks (Jegadeesh & Titman, Hong & Stein, Chan, Ali-Daniel-Hirshleifer) to diagnose 11 failing strategies by failure mode. Four strategies are invertible with academic support, two should be permanently banned, and two Tier-2 "orphan" strategies with hidden edge deserve scale-up. The chapter presents the "consensus trap" as a unifying insight.

### Specific Data Points (with numbers)
1. **11 strategies flagged as statistical dropouts** (7d WR >20% below baseline)
2. **Failure mode breakdown:** 4 regime change, 3 adverse selection/crowding, 2 overfitting, 2 structural/breakage
3. **Invertible (4):** myfxbook_retail_contrarian (WR 33% vs 54% baseline, -21pp), futures_momentum (WR 20% vs 45%, -25pp), goldmine_1x_consensus (WR 12% vs 30%, -18pp), MomentumEMA (WR 46% vs 67%, -21pp)
4. **Pause (5):** stocks_rsi2_pullback (WR 42% vs 73%, -31pp), ensemble (WR 30% vs 41%, -11pp), st_obv_support_divergence (WR 46% vs 57%, -11pp), signal_engine_momentum_mut (WR 30% vs 50%, -20pp), cta_commodity_momentum_term (PF 0.02, 58% flat exits)
5. **Ban immediately (2):** unknown (WR 18% vs 34%, -16pp, NO DOCUMENTED LOGIC), gainer_compression_relaxed_mut (WR 8% vs 32%, -24pp, genetic overfitting)
6. **Hidden edge — signal_validation:** PF 2.58, WR 63.0%, n=184 — HIGHEST PF in portfolio, underallocated
7. **Hidden edge — mega_mutation:** PF 3.19, WR 67.9%, n=78 — EXCEPTIONAL PF, underallocated
8. **claude_gainer (emerging):** PF 2.23, WR 56.2%, n=32
9. **rl_agent (too early):** PF 2.54, WR 60.0%, n=5 (insufficient)
10. **Expected portfolio improvement from actions:** 7-day WR from ~30% to 48-55%
11. **Removing 3 banned strategies:** +5pp portfolio WR
12. **Inverting 4 strategies:** +15-20pp on inverted capital
13. **Parameter tweaks on 2 strategies:** +10-15pp on tweaked capital
14. **Scaling Tier-2 hidden edge:** +2-3pp portfolio alpha
15. **forex_rsi2_mean_reversion:** ABANDON for forex, RELOCATE to equities where RSI2 produces 73-80% WR

### Required Tables

**Table 5.1: Strategy Decision Matrix (All 11 Strategies)**
| Strategy | Baseline WR | 7d WR | Delta | Action | Expected WR After | Timeline |
|----------|-------------|-------|-------|--------|-------------------|----------|
| myfxbook_retail_contrarian | 54% | 33% | -21pp | INVERT (anti-retail) | 48-52% | Immediate |
| forex_rsi2_mean_reversion | 49% | 19% | -30pp | RELOCATE to equities | 73% (equities) | Immediate |
| stocks_rsi2_pullback | 73% | 42% | -31pp | PARAMETER TWEAK | 60-65% | 1 week |
| futures_momentum | 45% | 20% | -25pp | INVERT (high-PMP) | 55-60% | Immediate |
| ensemble | 41% | 30% | -11pp | RECOMPOSE | 45-50% | 1 week |
| goldmine_1x_consensus | 30% | 12% | -18pp | INVERT (anti-consensus) | 55-60% | Immediate |
| st_obv_support_divergence | 57% | 46% | -11pp | PARAMETER TWEAK | 52-55% | 2 weeks |
| unknown | 34% | 18% | -16pp | BAN | N/A | Immediate |
| gainer_compression_relaxed_mut | 32% | 8% | -24pp | BAN | N/A | Immediate |
| MomentumEMA | 67% | 46% | -21pp | INVERT (fade EMA) | 55-58% | 1 week |
| signal_engine_momentum_mut | 50% | 30% | -20pp | PAUSE + REBUILD | 50-55% | 2-4 weeks |

**Table 5.2: Tier-2 Hidden Edge Strategies**
| Strategy | WR | PF | n | Assessment | Recommendation |
|----------|-----|-----|-----|------------|----------------|
| signal_validation | 63.0% | 2.58 | 184 | Strong edge, underutilized | Relax threshold 15-20%, scale up |
| mega_mutation | 67.9% | 3.19 | 78 | Very strong edge, underutilized | Increase sizing 2x |
| claude_gainer | 56.2% | 2.23 | 32 | Moderate edge, emerging | Gradually increase allocation |
| rl_agent | 60.0% | 2.54 | 5 | Too early to assess | Paper trade only until n>=30 |

**Table 5.3: Failure Mode Categories with Academic Basis**
| Failure Mode | Count | Academic Basis | Fix Strategy |
|-------------|-------|----------------|--------------|
| Regime Change | 4 | J&T (2001) reversal, Connors RSI2 bear market degradation | Regime filters, VIX gating |
| Adverse Selection/Crowding | 3 | Falck et al. 5pp annual Sharpe decay, Ali-Daniel-Hirshleifer PMP | Invert (anti-consensus) |
| Overfitting | 2 | GT-Score [^33^]: complex parameters fail OOS | GT-Score optimization, rebuild |
| Structural/Breakage | 2 | Fuertes et al. momentum collapse post-financialization | Relocate to different asset class |

**Table 5.4: Inversion Decision Framework**
| Condition | Action | Example |
|-----------|--------|---------|
| Baseline WR >50%, current WR < baseline-15pp, regime-dependent | INVERT with regime conditioning | MomentumEMA, futures_momentum |
| Baseline WR >60%, overfitting suspected | PAUSE, rebuild with GT-Score | signal_engine_momentum_mut |
| Baseline WR <40% OR current WR <20% | ABANDON | unknown, gainer_compression |
| Failure mode = bug or data quality | FIX BUG, reassess | (forex infinite retry) |

### Key Citations
- Jegadeesh & Titman (2001, 2023) — momentum reversal [^22^][^25^]
- Ali, Daniel & Hirshleifer (2017) — PMP Effect [^23^]
- Hong & Stein (1999) — information diffusion [^53^]
- Chan (1988) — contrarian profits [^24^]
- Falck, Rej & Thesmar (SSRN) — strategy decay [^41^]
- Sheppert (2026) — GT-Score [^33^]
- Connors & Alvarez — RSI2 research [^38^][^44^][^45^]
- Fuertes et al. — commodity strategies [^52^]
- Cross-Insight 4 (Consensus Trap)

### Connection to Other Chapters
- Ch2 (Asset Class) provides the aggregate metrics that identify failing strategies
- Ch7 (Backtesting) explains why these strategies failed OOS validation
- Ch8 (Risk) covers position sizing for inverted strategies
- Ch11 (Transformation) includes strategy lifecycle management in roadmap

---

## Chapter 6: Penny Stocks & Meme Coins — High-Risk Deep Dive (~1,500 words)

### Analytical Angle
This chapter combines two structurally similar asset classes that function as wealth-destruction vehicles. Both rely on the "lottery ticket" psychology that attracts retail investors while systematically transferring wealth to insiders. The evidence is overwhelming from 20+ peer-reviewed sources and on-chain data. The recommendation is clear: penny stocks require extreme filtering if included at all; meme coins require complete exclusion.

### Specific Data Points (with numbers)

**Penny Stocks:**
1. Average annual OTC returns: -24% (Eraker & Ready) to -27% (Bruggemann et al.)
2. Median annual return: -37%
3. Aggregate investor losses: $180 billion (Eraker & Ready 2015)
4. Cap-weighted return of sub-$5 stocks: -60% (Verdad Advisors)
5. Sharpe Ratio of sub-$5 stocks: -2.06 vs +0.61 for >$5 stocks
6. Average max drawdown: -99% (sub-$5) vs -54% (>$5)
7. Bid-ask spreads: 1-3% for microcaps vs 0.01-0.05% for S&P 500
8. SEC example: $0.04 bid / $0.10 ask = 60% spread — must rise 15-30% to break even
9. ~50% of SEC manipulation cases involve penny stocks
10. Five-year survival rate: 60-90% depending on venue
11. AQR, Dimensional, Alpha Architect systematically exclude penny stocks
12. Only "most liquid subset" during high-yield spread compression shows outperformance (Verdad Advisors, crisis-timing strategy, not stock-picking)

**Meme Coins:**
13. Only 0.4% of Pump.fun traders realized >$10,000 in profits (13.55M wallets analyzed)
14. 5.7 million meme coins created on Pump.fun
15. Platform earned $398 million in revenue
16. 99.7% risk of ruin for $100 investor (65.6% WR, 5% avg win, -47.2% avg loss)
17. Kelly fraction: -244% (negative expected value)
18. 80-95% of meme coin traders lose money
19. Binance Square: 86.44% unprofitable
20. Academic study: social media investors lose 1% per trade in crypto
21. Pump-and-dump schemes: $7.78M profits extracted, $3.27M realized losses, 17,000+ victim addresses
22. PEPE: 111.2% annual volatility, 301.8% daily volatility peak, max daily gain 34.8%
23. DOGE: 85.7% annual volatility, 2.0x BTC volatility
24. Top 100 addresses hold >70% of supply in most meme coins
25. No retail-accessible strategy has demonstrated positive expectancy

### Required Tables

**Table 6.1: Penny Stock Academic Evidence Summary**
| Study | Period | Finding | Sample |
|-------|--------|---------|--------|
| Bruggemann et al. (2016) | 2001-2010 | -27% avg, -37% median, 2x volatility | 10,000+ OTC stocks |
| Eraker & Ready (2015) | 2000-2008 | -24% avg, $180B aggregate losses | OTC stocks |
| Verdad Advisors (1996-2024) | 1996-May 2024 | -60% cap-weighted, -2.06 Sharpe | Sub-$5 stocks |
| Ang, Shtauber & Tetlock (2013) | Various | Negative risk-adjusted returns persist | OTC stocks |

**Table 6.2: Meme Coin Volatility Comparison (365-day data)**
| Asset | Ann. Volatility | Max Daily Gain | Max Daily Loss | Skewness |
|-------|----------------|---------------|----------------|----------|
| BTC | 42.6% | 12.2% | -14.0% | -0.21 |
| DOGE | 85.7% | 22.1% | -22.1% | +0.36 |
| SHIB | 71.0% | 13.4% | -18.9% | +0.08 |
| PEPE | 111.2% | 34.8% | -27.5% | +1.10 |

**Table 6.3: Pump.fun Profit Distribution (13.55M wallets)**
| Outcome | Percentage |
|---------|-----------|
| Realized >$10,000 profit | 0.4% |
| Profitable (any amount) | ~13% |
| Breakeven | ~1-5% |
| Unprofitable | 80-95% |
| Risk of ruin ($100) | 99.7% |

**Table 6.4: Recommended PENNY Asset Class Rules (If Included)**
| Rule | Specification |
|------|--------------|
| Minimum daily volume | $1M+ |
| Maximum bid-ask spread | <2% |
| Exchange requirement | Exchange-listed only |
| Minimum price | >$1 |
| Maximum per-pick position | 2% |
| Maximum total allocation | 5% |
| Mandatory overlay | Crisis-timing only (high-yield spread compression) |

### Key Citations
- Bruggemann et al. (2016) — OTC market quality
- Eraker & Ready (2015) — $180B aggregate losses
- Verdad Advisors (1996-May 2024) — sub-$5 stock performance
- Nam & Skillicorn (2023) — pump-and-dump detection (85% accuracy)
- Pump.fun Dune Analytics — 13.55M wallets, 0.4% profitable
- Binance Square — 86.44% unprofitable
- Memecoin Fragility Framework (arXiv 2512.00377) — ME2F
- HC-4 (Meme Coins Should Be Excluded)
- HC-5 (Penny Stocks Are Wealth Destruction)

### Connection to Other Chapters
- Ch1 introduces the 99.7% risk of ruin and -24% to -27% annual returns
- Ch2 covers the asset class verdict (both get 0% allocation)
- Ch8 covers position sizing (both get 0% Kelly allocation)
- Ch9 gives users the 30-second rule ("CLOSE THE TAB")

---

## Chapter 7: Backtesting Methodology — From Retail to Institutional (~1,500 words)

### Analytical Angle
The backtesting chapter reveals a systematic gap between the platform's methodology and institutional standards. Negative OOS Sharpe for 3 of 4 asset classes is prima facie evidence of overfitting. The absence of CPCV, PSR/DSR, and multiple testing correction means false discoveries are guaranteed. The resolver fix cautionary tale (measurement fix != strategy fix) is central to the narrative.

### Specific Data Points (with numbers)
1. **Negative OOS Sharpe for 3 of 4 asset classes:** CRYPTO -0.242, FOREX -1.406, COMMODITY -2.412
2. **ETF OOS Sharpe 6.368 is artifact:** only 12 folds (need 20+), 10.8 decay, estimated true Sharpe 2.0-3.0
3. **Only Equity has positive OOS Sharpe:** +3.527 (exceeds institutional threshold of +1.5)
4. **No CPCV (Combinatorial Purged Cross-Validation):** Lopez de Prado 2018 — the single most important institutional innovation, entirely absent
5. **Platform uses single walk-forward path** = 1 backtest path vs institutional 30-280 paths
6. **No PSR/DSR validation deployed:** 0% of strategies have PSR > 0.95, 0% have DSR > 0.95
7. **With 50+ strategies tested, expected false discovery rate exceeds 50%** without multiple testing correction
8. **No multiple testing correction:** Bonferroni, Holm, or Benjamini-Hochberg absent
9. **No bootstrap validation:** 10,000-path bootstrap for Sharpe CI missing
10. **5+ copies of outcome_resolver.py** create version-control risk
11. **Only 12 walk-forward folds for ETF** — severely underpowered vs 20+ minimum
12. **"THIN" strategies flagged with <50 trades** vs 200-500 institutional minimum
13. **72.7% of picks still open at 24h** — tracking window creates systematic bias
14. **27.3% of picks hit TP or SL within 24h**
15. **6 days post-resolver-fix is 4-8x too short** for evaluation
16. **5 new swarm engines deployed in same window** = attribution problem
17. **Free data sources (yfinance) inflate returns 1-4% annually** through survivorship bias
18. **No transaction cost modeling** — backtested returns are fiction

### Required Tables

**Table 7.1: Current vs Institutional Backtesting Standards**
| Dimension | Current Platform | Institutional Standard | Gap |
|-----------|-----------------|----------------------|-----|
| Walk-forward splits | 60% IS / 40% OOS, 12 folds | CPCV with N>=6, k>=2 | Critical |
| Minimum trades | 50 (crypto), 100 (equity) | 200-500 per asset class | Critical |
| PSR threshold | Not implemented | PSR > 0.95 required | Critical |
| DSR threshold | Not implemented | DSR > 0.95 required | Critical |
| Bootstrap CI | Not implemented | 10,000 paths, BCa method | Critical |
| Multiple testing | Not implemented | Bonferroni/Holm/BH | High |
| Transaction costs | Generic spread only | Per-asset with market impact | High |
| Pick resolution rate | 27.3% within 24h | >80% within tracking window | High |
| Code maintenance | 5+ copies of resolver | Single source of truth | Medium |

**Table 7.2: CPCV Path Count by Configuration**
| N (groups) | k (test) | Paths | Path Diversity |
|------------|----------|-------|----------------|
| 6 | 2 | 5 | Low |
| 10 | 3 | 30 | Medium |
| 15 | 5 | 105 | High |
| 20 | 7 | 280 | Very High |

**Table 7.3: Minimum Evaluation Timeline for Resolver Fix**
| Confidence Level | Minimum Trades | Est. Calendar Days | Assessment |
|-----------------|---------------|-------------------|------------|
| Bare minimum | 100 closed | 14-20 days | Gross failure detection only |
| Recommended | 200 closed | 28-40 days | Basic WR/PF stability |
| Institutional | 500 closed | 70-100 days | Regime resilience |
| Full regime coverage | 500+ across regimes | 90-180 days | Deployment decisions |

**Table 7.4: The Cost of Backtesting Failures**
| Failure | Annual Cost at $100K Capital | Probability |
|---------|------------------------------|-------------|
| Deploying negative-OOS strategies | $5,000-10,000 | 60% |
| No transaction cost modeling | $3,000-5,000 (overconfidence losses) | 70% |
| Survivorship bias (1-4% inflated returns) | $1,000-4,000 (misallocated capital) | 80% |
| False discoveries (50%+ FDR) | $2,500-7,500 | 50% |

### Key Citations
- Lopez de Prado (2018) — Advances in Financial Machine Learning
- Bailey & Lopez de Prado (2012, 2014) — PSR and DSR
- Harvey & Liu (2014) — multiple testing in backtesting
- Jacquier et al. (2025) — OOS Sharpe replication ratio
- HC-7 (6 days insufficient)
- Cross-Insight 3 (Resolver Revelation), 7 (Free Data Trap)

### Connection to Other Chapters
- Ch2 provides the OOS Sharpe numbers that drive this analysis
- Ch5 explains which strategies failed and why
- Ch10 covers the code quality issues (5+ copies of resolver)
- Ch11 presents the roadmap to fix backtesting infrastructure

---

## Chapter 8: Risk Management & Position Sizing (~1,000 words)

### Analytical Angle
The risk chapter delivers two seemingly contradictory truths: (1) the current sizing framework is mathematically sound with near-zero ruin probability, AND (2) there are critical gaps in the kill switch ladder that need immediate attention. The Kelly mathematics are deterministic and reproducible — the edge comes from the R:R 1.5-2.0 band, not from leverage.

### Specific Data Points (with numbers)
1. **Overall Risk Score: 6.5/10** (ADEQUATE with material gaps)
2. **Kelly sizing: 8.5/10** — mathematically sound
3. **Cross-asset diversification: 5.2/10** — weak
4. **Kill switch ladder: 6.0/10** — missing daily loss limit, consecutive loss halt, vol circuit
5. **Quarter-Kelly 11.8% for R:R 1.5-2.0** — mathematically verified, conservative (uses ~75% of calculated Quarter-Kelly)
6. **P(Ruin) under current sizing: effectively 0%** with 10% DD hard halt
7. **Monte Carlo (10,000 paths):** 0% halted, median final equity 2.564x after 252 trades
8. **Median max DD:** 1.1%; 95th percentile max DD: 1.8%; P(Max DD >= 10%): 0.0%
9. **ETF-Equity correlation: 0.85** — should count as ONE position for concentration limits
10. **Crypto internal correlation: 0.65** — all crypto tiers should be aggregated
11. **Bond-Equity correlation: -0.40** — the ONLY true negative correlation (hedge)
12. **Forex correlation with all assets: ~0.10** — the best diversification instrument
13. **True independent bets: ~4** (not 9)
14. **Crypto C-Tier Quarter-Kelly: -5.3%** (correctly blocked at 0%)
15. **Contrarian C-Tier (if validated):** effective PF = 1/0.56 = 1.79, reverse Quarter-Kelly = +6.0%
16. **Three critical gaps in kill switch:** No daily loss limit (2-3% standard), no consecutive loss halt (5-7 losses), no volatility circuit breaker (VIX >40)

### Required Tables

**Table 8.1: Risk Dimension Scores**
| Dimension | Score | Verdict |
|-----------|-------|---------|
| Kelly Sizing by R:R Band | 8.5/10 | Mathematically sound |
| Asset Class Position Sizing | 7.0/10 | Reasonable, minor adjustments |
| C-Tier Handling (PF 0.56) | 9.0/10 | Correctly blocked at 0% |
| Cross-Asset Diversification | 5.2/10 | Partial; concentration risk |
| Position Distribution | 6.5/10 | Too concentrated in S-Tier |
| Probability of Ruin | 2.1/10 | Very low — sizing is conservative |
| R:R >2.0 Handling | 9.0/10 | Correctly blocked |
| Kill Switch Ladder | 6.0/10 | Missing 3 critical elements |
| **OVERALL** | **6.5/10** | **ADEQUATE with material gaps** |

**Table 8.2: Correlation Matrix (Literature-Based)**
| Asset | BTC/ETH | Crypto A | Equity | Forex | Commodity | Bond | ETF |
|-------|---------|----------|--------|-------|-----------|------|-----|
| BTC/ETH | 1.00 | 0.65 | 0.45 | 0.10 | 0.15 | -0.05 | 0.40 |
| Equity | 0.45 | 0.35 | 1.00 | 0.15 | 0.30 | -0.40 | **0.85** |
| Bond | -0.05 | -0.03 | -0.40 | 0.05 | -0.20 | 1.00 | -0.35 |
| Forex | 0.10 | 0.08 | 0.15 | 1.00 | 0.10 | 0.05 | 0.12 |

**Table 8.3: Kill Switch — Current vs Enhanced**
| Feature | Current | Enhanced | Gap |
|---------|---------|----------|-----|
| 1st DD threshold (5% -> 50% size) | Yes | Yes | None |
| 2nd DD threshold (10% full halt) | Yes | Yes | None |
| Asset-specific halt | Yes (PF<0.80@5days) | Yes | None |
| **Daily loss limit (2% warn, 3% halt)** | **NO** | **YES** | **Critical** |
| **Consecutive loss halt (5-7 losses)** | **NO** | **YES** | **High** |
| **Volatility circuit breaker (VIX>40)** | **NO** | **YES** | **High** |
| Recovery protocol | NO | 50% recovery to resume | Medium |

**Table 8.4: Monte Carlo Ruin Probability (10,000 paths, 252 trades)**
| Metric | Value |
|--------|-------|
| Median final equity (1yr) | 2.564x (+156.4%) |
| 10th percentile | 2.360x (+136.0%) |
| Worst case | 2.074x (+107.4%) |
| Halted (hit 10% DD) | 0.0% |
| Median max DD | 1.1% |
| 95th percentile max DD | 1.8% |
| P(Max DD >= 10%) | 0.0% |

### Key Citations
- Kelly criterion mathematics (deterministic)
- Frazzini, Israel & Moskowitz (2017) — transaction costs
- HC-2 (R:R 1.5-2.0 band confirmation)
- Conflict Zone C-5 (Kill switch adequate vs gaps — resolved as both true)

### Connection to Other Chapters
- Ch2 provides the R:R band analysis that drives Kelly calculations
- Ch9 translates position sizing into user-facing rules
- Ch11 includes kill switch enhancements in transformation roadmap

---

## Chapter 9: User Safety Guide — What to Invest Real Money In (~1,500 words)

### Analytical Angle
The user safety chapter translates all technical findings into actionable, plain-language rules. The core insight: a disciplined retail investor using ONLY equity picks with strict filters has a realistic path to 15-25% annually, but most users will lose money because they override filters, chase dangerous asset classes, and size incorrectly. The "30-second decision rule" and signal alpha decay curve are the key deliverables.

### Specific Data Points (with numbers)
1. **Expected returns — Disciplined (Equity only, strict filters, Quarter-Kelly):** 15-25% annually, 8-12% max drawdown, ~70% probability
2. **Expected returns — Moderate (Equity + Crypto B-Tier + ETF):** 12-20% annually, 12-18% max DD, ~60% probability
3. **Expected returns — Casual (mixed, loose filters):** 5-10% annually, 15-25% max DD, ~50% probability
4. **Expected returns — YOLO (everything including DANGEROUS):** -20 to -40% annually, 40-60% max DD, ~80% probability
5. **30-second decision rule:**
   - Equity with ml_score >= 0.90 = GREAT IDEA
   - Crypto B-Tier L20 with R:R 1.5-2.0 = CAUTION
   - Commodity/Forex/C-Tier/Meme = CLOSE THE TAB
6. **Practical minimum starting capital: $5,000** (below this, transaction costs eat the edge)
7. **Ideal starting capital: $25,000+**
8. **Signal alpha decay:** Hours 0-48 = peak strength; Hours 48-120 = viable but degraded; Hours 120+ = edge approaching random
9. **Best entry window: within 48 hours** of signal generation
10. **S&P 500 benchmark: ~10% annually with zero effort**
11. **Platform edge requires 2-3 hours/week, emotional discipline, and platform dependency**
12. **Honest answer: For most people, index funds are better**
13. **Maximum position sizes:** Equity 11.8%, Crypto B-Tier 5%, ETF 5%, Bond 5%, Commodity 0%, Forex 0%
14. **5-layer safety ladder:** Single position cap -> Asset class cap (40%) -> CAUTION assets cap (50%) -> DANGEROUS = 0% -> 20% cash reserve

### Required Tables

**Table 9.1: Expected Returns by Discipline Level**
| Scenario | Annual Return | Max Drawdown | Probability |
|----------|---------------|--------------|-------------|
| Disciplined: Equity only, strict filters, Quarter-Kelly | 15-25% | 8-12% | ~70% |
| Moderate: Equity + Crypto B + ETF, strict filters | 12-20% | 12-18% | ~60% |
| Casual: Mixed, loose filters | 5-10% | 15-25% | ~50% |
| YOLO: Everything including DANGEROUS | -20 to -40% | 40-60% | ~80% |

**Table 9.2: The 30-Second Decision Rule**
| Asset Class + Condition | Action |
|------------------------|--------|
| Equity with ml_score >= 0.90 | GREAT IDEA — proceed |
| Crypto B-Tier L20 with R:R 1.5-2.0 | CAUTION — strict sizing |
| ETF/Bond with verified signals | CAUTION — small positions only |
| Commodity / Forex / C-Tier / Meme | CLOSE THE TAB — do not trade |

**Table 9.3: Maximum Position Sizes (Hard Caps)**
| Asset Class | Max Position | Conditions |
|-------------|-------------|------------|
| Equity (L50) | 11.8% | Only at R:R 1.5-2.0; reduce to 5% at R:R < 1.5 |
| Crypto B-Tier (L20) | 5.0% | Hard cap regardless of conviction |
| ETF (L20-L50) | 5.0% | 10-day hard stop required |
| Bond | 5.0% | Small sample uncertainty |
| Commodity | 0.0% | No allocation |
| Forex | 0.0% | No allocation |
| Crypto C-Tier | 0.0% | 5% lifetime cap if gambling |
| Meme Coins | 0.0% | 5% lifetime cap if gambling |

**Table 9.4: Signal Alpha Decay Curve**
| Time Window | Signal Quality | Action |
|-------------|---------------|--------|
| 0-48 hours | Peak strength | Best entry window |
| 48-120 hours | Viable but degraded | Acceptable with reduced size |
| 120+ hours | Edge approaching random | Do not enter |

**Table 9.5: Red Flag Checklist — STOP If You See These**
| Red Flag | Meaning | Action |
|----------|---------|--------|
| R:R < 1.5 or R:R > 2.0 | Outside profitable band | Do not enter |
| ml_score < 0.90 | Below accuracy threshold | Do not enter |
| Tracking time < 120 hours | Insufficient data | Wait |
| Commodity/Forex/C-Tier/Meme | Statistically negative edge | Close it |
| "Verified Alpha" but <20 historical picks | Unproven strategy | Size at 50% or skip |
| Position size > 11.8% | Overexposure | Trim immediately |

### Key Citations
- Dim11 (primary source)
- HC-1, HC-2, HC-4, HC-5, HC-8
- Cross-Insight 9 (Asymmetric Alpha — edge is narrow but real)
- Conflict Zone C-1 resolution (ml_score vs confidence score distinction)

### Connection to Other Chapters
- Ch2 provides the asset class verdicts that drive the 30-second rule
- Ch3 provides the scoring data (trust_score >= 5, forward_wr 50-65%)
- Ch4 provides the optimal UI filter path
- Ch8 provides the Kelly sizing mathematics
- Ch11 presents the alternative (index funds for most people)

---

## Chapter 10: Technical Issues & Bug Fixes (~800 words)

### Analytical Angle
This short chapter documents one confirmed bug (nested HTML comment), one governance issue (console.log statements), and one code maintenance risk (5+ copies of outcome_resolver.py). The overall HTML health is good (balanced script tags, unique IDs, proper escaping) — this is a surgical fix, not a rewrite.

### Specific Data Points (with numbers)
1. **Primary bug location:** audit_dashboard/template.html, lines ~1813-1825
2. **Bug type:** Nested HTML comment with premature terminator
3. **Root cause:** HTML does not support nested comments; parser treats first `-->` inside `` `<\!-- ... -->` `` as comment end
4. **Visible leaked text:** "` inside this block -- HTML does not support nested comments and the inner `-->` would close the outer. -->"
5. **Fix:** Replace entire multi-line comment with single `<!-- UEPS mount point -->`
6. **Script tags:** 11 open, 11 close — BALANCED
7. **HTML IDs:** All unique — no duplicates
8. **HTML entities:** Properly escaped throughout (`&lt;`, `&gt;`, `&mdash;`, `&ndash;`, `&middot;`, `&ge;`, `&le;`)
9. **Console.log statements:** 15+ occurrences exposing internal architecture
10. **5+ copies of outcome_resolver.py** — fix may not be applied to all copies
11. **119,598 commits with 11 contributors including AI agents** (KIMI, Claude, Cursor, Copilot)
12. **No CI/CD pipeline** — no automated testing
13. **No testing framework** — manual verification only

### Required Tables

**Table 10.1: HTML Health Check Summary**
| Metric | Count | Status |
|--------|-------|--------|
| Script tags (open) | 11 | Balanced |
| Script tags (close) | 11 | Balanced |
| Duplicate IDs | 0 | Clean |
| HTML entity escaping | All proper | Clean |
| Nested comment bugs | 1 | Fix required |
| console.log statements | 15+ | Cleanup needed |

**Table 10.2: Bug Fix Options**
| Option | Fix | Risk | Recommendation |
|--------|-----|------|----------------|
| A | Replace with `<!-- UEPS mount point -->` | Zero | RECOMMENDED |
| B | Replace `-->` with HTML entity in comment | Low | Acceptable |
| C | Use `-- >` workaround | Low | Acceptable |

**Table 10.3: Code Governance Issues**
| Issue | Severity | Impact |
|-------|----------|--------|
| 5+ copies of outcome_resolver.py | Critical | Fix may not apply to all copies |
| 15+ console.log statements | Low | Exposes internal architecture |
| 119,598 commits, AI agents without review | Critical | Quality control failure |
| No CI/CD pipeline | High | No automated testing |
| No testing framework | High | Manual verification only |

### Key Citations
- Dim09 (primary) — exact line numbers, root cause analysis
- Dim10 — 5+ copies of outcome_resolver.py
- Dim12 — AI agent governance crisis
- HC-6 (HTML nested comment bug confirmed)

### Connection to Other Chapters
- Ch4 covers the UX implications of the HTML bug
- Ch7 covers the backtesting implications of 5+ resolver copies
- Ch11 includes CI/CD and governance framework in transformation plan

---

## Chapter 11: Transformation Roadmap — What a Quant Hedge Fund Would Change (~1,500 words)

### Analytical Angle
The closing chapter presents a binary choice: stay retail-focused with narrow edge, or commit to institutional transformation. The gap analysis is stark (~5% of infrastructure) but the path is clear. Six non-negotiable hard gates define the 90-day MVP. The cost/benefit analysis shows transformation pays for itself through avoided losses alone.

### Specific Data Points (with numbers)
1. **Platform has approximately 5% of institutional infrastructure**
2. **Only 5% of strategies have n >= 200**
3. **0% of strategies have PSR > 0.95**
4. **0% of strategies have DSR > 0.95**
5. **Six non-negotiable hard gates for 90-day MVP:**
   - PSR > 0.95
   - DSR > 0.95
   - n >= 200
   - Transaction costs modeled
   - Single source of truth (consolidate resolver)
   - Correlation guard active
6. **90-day transformation cost: ~$1,500**
7. **90-day ROI: 867%-5,233%**
8. **12-month transformation cost: $32,400-78,000**
9. **12-month ROI at $500K AUM: 64%-1,400%**
10. **12-month ROI at $2M AUM: 250%-5,600%**
11. **Expected annual cost of NOT transforming: $12,500-25,000** minimum
12. **Renaissance Technologies discards 99%+ of tested signals**
13. **Renaissance: 40TB/day ingested, 50,000 CPU cores, 150 Gbps connectivity**
14. **Renaissance: 150,000-300,000 trades/day, 0.002-0.003% transaction costs**
15. **Renaissance: ~90 PhDs in mathematics, physics, computer science**
16. **Two Sigma: BigQuery warehouse, dbt for "data as code", research-to-production pipeline**
17. **Citadel: Central Risk Project (CEO-level risk oversight)**
18. **90-day monthly infrastructure cost: ~$430/month**
12-month monthly cost: ~$3,050-6,850/month
19. **Week-by-week plan:** Weeks 1-2 (Foundation), 3-4 (Transaction costs), 5-6 (Risk framework), 7-8 (Bootstrap CI), 9-10 (Execution simulation), 11-12 (Audit/compliance)
20. **Data cost: Polygon.io $199/mo + CCData $149/mo = ~$348/mo minimum**

### Required Tables

**Table 11.1: Gap Analysis — Current vs Renaissance/Two Sigma/Citadel**
| Dimension | Renaissance | Two Sigma | Citadel | Current Platform | Gap |
|-----------|-------------|-----------|---------|------------------|-----|
| Data Processing | 40TB/day, 50K CPUs | BigQuery, dbt | Enterprise | Free APIs (yfinance) | Massive |
| Signal Validation | 99%+ discarded, p<0.01 | Research-to-prod pipeline | Cross-asset risk | No PSR/DSR | Existential |
| Transaction Costs | 0.002-0.003% | Modeled | Full TCA | None modeled | Massive |
| Talent | ~90 PhDs | Cross-functional teams | Elite risk team | 11 contributors + AI agents | Large |

**Table 11.2: Six Hard Gates for 90-Day MVP**
| Gate | Criterion | Why Non-Negotiable |
|------|-----------|-------------------|
| 1 | PSR > 0.95 | 95% confidence true Sharpe > benchmark |
| 2 | DSR > 0.95 | Corrects for multiple testing bias |
| 3 | n >= 200 | Minimum institutional-grade sample |
| 4 | Transaction costs modeled | Backtests without costs are fiction |
| 5 | Single source of truth | One outcome_resolver.py, not five |
| 6 | Correlation guard active | Prevents hidden concentration |

**Table 11.3: 90-Day Cost Breakdown**
| Category | 90-Day Cost |
|----------|------------|
| Data subscriptions (Polygon + CCData + FRED) | ~$1,050 |
| Infrastructure (VPS, TimescaleDB) | ~$300 |
| Tools & APIs (VectorBT, monitoring) | ~$150 |
| **Total** | **~$1,500** |

**Table 11.4: Cost/Benefit Analysis**
| Scenario | Cost | Benefit | ROI |
|----------|------|---------|-----|
| 90-day MVP | $1,500 | $13,000-80,000/year avoided losses | 867%-5,233% |
| 12-month at $500K AUM | $32,400-78,000 | $50,000-500,000/year | 64%-1,400% |
| 12-month at $2M AUM | $32,400-78,000 | $200,000-2M/year | 250%-5,600% |
| Status quo (no transformation) | $12,500-25,000/year losses | None | Negative |

**Table 11.5: Week-by-Week 90-Day Implementation**
| Weeks | Focus | Key Deliverables |
|-------|-------|-----------------|
| 1-2 | Foundation | PSR/DSR gates, data subscriptions, protected branch, CI/CD |
| 3-4 | Transaction costs | Per-asset cost models, re-run all backtests |
| 5-6 | Risk framework | Correlation guard, VaR, daily loss limit, regime detection |
| 7-8 | Bootstrap CI | 10,000-path bootstrap, strategy health monitoring |
| 9-10 | Execution | Market impact model, paper trading, OMS-lite |
| 11-12 | Audit/compliance | Immutable audit trail, trade reconstruction, compliance templates |

**Table 11.6: What Renaissance Would Do Differently — Top 5**
| Principle | Renaissance Practice | Platform Gap |
|-----------|---------------------|--------------|
| Data-first philosophy | Start with data, not models | Free-tier data poisoning all analysis |
| 99% rejection rate | Discard signals without statistical significance | Deploying negative OOS Sharpe strategies |
| Infrastructure investment | 30% of effort to infrastructure | 0% CI/CD, 0% testing framework |
| No interference rule | 150K-300K trades/day, zero human override | Manual overrides not logged |
| Capacity limits | Medallion capped at $10-15B | No strategy-level AUM caps |

### Key Citations
- Dim12 (primary) — full gap analysis and transformation plan
- Renaissance Technologies [^302^][^303^]
- Two Sigma [^320^][^321^]
- Citadel [^323^]
- Bailey & Lopez de Prado PSR/DSR
- Cross-Insight 6 (AI Agent Governance Crisis), 10 (Retail vs Institutional Divide)
- Conflict Zone C-3 (Crypto S-Tier handling — resolved as "don't abandon, don't scale")

### Connection to Other Chapters
- Ch1 introduces the 5% infrastructure finding
- Ch7 details the backtesting gaps to be fixed
- Ch8 details the risk framework gaps to be fixed
- Ch10 details the code quality issues to be fixed
- This chapter closes the report with a concrete action plan

---

## Appendix Content Plan

### Appendix A: Summary Statistics Table (All Asset Classes)
All PF, WR, OOS Sharpe, n, Kelly Quarter, recommended allocation, verdict in one master table.

### Appendix B: Score Component Correlation Matrix
Full correlation table from Score Calibration Audit (n=3,500) with all components.

### Appendix C: Strategy Decision Matrix (All 11 + Orphaned)
Complete strategy table with baseline WR, 7d WR, delta, failure mode, action, expected WR, timeline.

### Appendix D: Kill Switch Ladder (Current vs Enhanced)
Side-by-side comparison with all 10 levels.

### Appendix E: 90-Day Implementation Timeline
Gantt-style week-by-week deliverables with hard gates.

### Appendix F: Academic Source Index
50+ citations organized by topic (asset edge, scoring, backtesting, risk, penny stocks, meme coins, strategy, transformation).

---

## Cross-Chapter Connection Map

| Chapter | Forward Connections | Backward Dependencies |
|---------|-------------------|----------------------|
| Ch1 (Executive) | All chapters | Synthesis of all findings |
| Ch2 (Asset Edge) | Ch6, Ch7, Ch8, Ch9 | Ch1 overview |
| Ch3 (Scoring) | Ch4, Ch9, Ch11 | Ch1 overview |
| Ch4 (UI/UX) | Ch9, Ch10, Ch11 | Ch3 scoring data |
| Ch5 (Strategy) | Ch7, Ch8, Ch11 | Ch2 asset metrics |
| Ch6 (Penny/Meme) | Ch9 | Ch2 verdict |
| Ch7 (Backtesting) | Ch10, Ch11 | Ch2 OOS data, Ch5 strategy failures |
| Ch8 (Risk) | Ch9, Ch11 | Ch2 R:R band analysis |
| Ch9 (User Safety) | Ch11 | Ch2, Ch3, Ch4, Ch8 |
| Ch10 (Tech Issues) | Ch11 | Ch4 HTML bug, Ch7 resolver copies |
| Ch11 (Transformation) | — | All prior chapters |

## Data Point Coverage Checklist

### Priority 1 Foundation (Must Include — All 8 Covered)
- [x] Ch1, Ch2: Only Equity passes 5 gates (PF 1.72, OOS Sharpe +3.527)
- [x] Ch1, Ch2, Ch8: R:R 1.5-2.0 band PF 5.81
- [x] Ch1, Ch3: Composite scoring broken (4/9 inversions)
- [x] Ch1, Ch11: ~5% institutional infrastructure, 0% PSR>0.95
- [x] Ch1, Ch6: 99.7% meme coin risk of ruin, 0.4% Pump.fun profitable
- [x] Ch1, Ch6: Penny stocks -24% to -27% annually
- [x] Ch1, Ch7, Ch10: Resolver fix revealed FOREX PF 0.27
- [x] Ch1, Ch10, Ch11: 119K commits, AI agents without review

### Priority 2 Actionable (All 6 Covered)
- [x] Ch4, Ch9: Optimal UI path (Verified Alpha + HC + R:R 1.5+ = 66-70% WR)
- [x] Ch3, Ch9: trust_score >=5 and forward_wr 50-65% = 68-71% WR
- [x] Ch5: 11 failing strategies, 4 invertible, 2 ban, 2 hidden-edge
- [x] Ch8: Kelly Quarter 11.8% for R:R 1.5-2.0 band
- [x] Ch11: Six hard gates for 90-day MVP
- [x] Ch4, Ch10: HTML bug fix (template.html lines 1813-1825)

### Priority 3 Context (All 5 Covered)
- [x] Ch7: 6 days post-fix is 4-8x too short
- [x] Ch7: 5 new swarm engines = attribution problem
- [x] Ch7, Ch11: Free data sources inflate returns 1-4%
- [x] Ch9: Expected returns 15-25% disciplined vs -20 to -40% YOLO
- [x] Ch4, Ch9: Platform value is exclusion, not pick generation
