# Research Artifact Synthesis: Quantitative Audit Report

## Date: 2026-05-05
## Scope: 12 research dimensions, 10 cross-cutting insights, cross-verification matrix, source document
## Total Research Artifacts: 14 files + 1 source document

---

# PART 1: PER-DIMENSION EXTRACTION

---

## Dimension 01: Asset Class Edge Analysis

**3-5 Most Important Data Points:**
1. **Only Equity passes all 5 investability gates** (PF 1.72, OOS Sharpe +3.527, n=136+). Every other asset class fails at least one criterion. [Dim01, Section 4.2]
2. **Negative OOS Sharpe for 3 major asset classes:** Crypto aggregate -0.242, Forex -1.406, Commodity -2.412 — these are definitive overfitting signatures. [Dim01, Master Verdict Table]
3. **The 1.5-2.0 R:R band has PF 5.81, Kelly +47.2%** while R:R > 2.0 has PF 0.35 (catastrophic). This single finding transforms platform-wide profitability. [Dim01, Section 8]
4. **ETF OOS Sharpe 6.368 is almost certainly an artifact** — only 12 folds, 10.8 decay, inconsistent with IS metrics. Estimated true Sharpe: 2.0-3.0. [Dim01, Section 6]
5. **Recommended allocation: 25% Equity, 5% ETF (pending validation), 70% cash/reserve.** All other asset classes get 0%. [Dim01, Section 7.3]

**Key Conclusion:** The platform has ONE proven asset class (Equity) with genuine statistical edge. Seven asset classes should receive ZERO capital allocation. The edge is real but dangerously concentrated.

**Confidence Level:** HIGH — supported by 5-gate framework, academic literature (Jacquier et al. 2025, Bailey & Lopez de Prado DSR), and platform's own data.

---

## Dimension 02: Scoring Methodology (F-Score vs Score)

**3-5 Most Important Data Points:**
1. **The elite_score (composite) is NOT monotonic** — 4 inversions out of 9 deciles. Higher score does NOT consistently predict higher WR. D6-D7 (score 30-40) is a "dead zone" where WR drops to 35-43%. [Dim02, Section 1.3]
2. **forward_wr has r=+0.242 (BEST predictor, 25 pts)** but ml_score has r=-0.012 (NOISE, yet gets 9-25 pts). regime_bonus is ANTI-PREDICTIVE (r=-0.115). The scoring weights are inverted from optimal. [Dim02, Empirical Ranking Table]
3. **Confidence sweet spot at 0.70-0.79 delivers 57% WR; 0.90+ delivers only 47% WR** — the "overconfidence penalty" means medium-confidence predictions outperform high-confidence ones. [Dim02, Section 1.2]
4. **trust_score >= 5 is the most effective filter** at 68-71% WR, far superior to any ml_score threshold. [Dim02, Section 2]
5. **Proposed weight rebalance:** forward_wr 25->55 pts (+37%), regime_bonus 20->5 pts (-75%), ml_score 9->4 pts (-55%). Fixes identified but NOT implemented as of 2026-04-06. [Dim02, Section 1.3]

**Key Conclusion:** The composite scoring system is fundamentally broken — it gives the most weight to the least predictive components and is not monotonic. Users should filter by trust_score >= 5 and forward_wr 50-65% instead of the headline score.

**Confidence Level:** HIGH — based on Score Calibration Audit of n=3,500 closed picks from the platform's own data.

---

## Dimension 03: UI/UX Analysis

**3-5 Most Important Data Points:**
1. **Triple filter (Verified Alpha + High Conviction + R:R 1.5+) produces 66-70% WR** but shows only 0-2 picks. Best daily driver: Verified Alpha + High Conviction at 65-68% WR with 3-8 picks. [Dim03, Section 3.2]
2. **192 of 210 total picks are gated out** by the best filter combination. The platform's value is capital preservation through exclusion, not pick generation. [Dim03, Section 3.2]
3. **Three "Smart Picks" UI elements share the same name** (tab, filter toggle, stat) but have different behaviors — a significant UX violation causing user confusion. [Dim03, Section 4.3]
4. **The "Verified Alpha" filter produces the highest WR (~64.1%)** when combined with WR >=50% gate. "Trusted" and "High-grade" are orthogonal dimensions (pick quality vs source reputation). [Dim03, Sections 2.2, 5]
5. **HTML nested comment bug in template.html lines 1813-1825** causes visible leaked text on US Equity Picks tab. Fix: replace with single `<!-- UEPS mount point -->`. [Dim03, Section 9; Dim09]

**Key Conclusion:** The optimal UI path is Verified Alpha + High Conviction with R:R 1.5+ for conservative users, but the current UI has significant naming confusion and missing feedback (active filter chips, pick counts per filter).

**Confidence Level:** MEDIUM-HIGH — filter WR estimates are logical deductions from platform data; UX issues are directly observable.

---

## Dimension 04: Strategy Failure Analysis

**3-5 Most Important Data Points:**
1. **11 strategies flagged as statistical dropouts** (7d WR >20% below baseline). Categorized: 4 regime change, 3 adverse selection/crowding, 2 overfitting, 2 structural/breakage. [Dim04, Executive Summary]
2. **4 strategies are invertible with high conviction:** myfxbook_retail_contrarian, futures_momentum, goldmine_1x_consensus, MomentumEMA. Academic basis: Jegadeesh & Titman momentum reversal, Chan contrarian literature. [Dim04, Individual Strategy Diagnosis]
3. **2 strategies should be permanently abandoned:** unknown (undocumented logic, 18% WR), gainer_compression_relaxed_mut (32% baseline WR, overfitted). [Dim04, Strategy Decision Matrix]
4. **cta_commodity_momentum_term has PF 0.02 with 58% flat exits** — the strategy finds no real setups. Should invert to term structure carry per Fuertes et al. [Dim04, Per-Asset Class Analysis]
5. **Hidden edge in Tier-2 strategies:** signal_validation (PF 2.58, n=184) and mega_mutation (PF 3.19, n=78) have the highest profit factors but are underallocated. [Dim04, Orphaned Strategies Section]

**Key Conclusion:** Most failing strategies can be fixed through inversion (anti-consensus), regime filters, or parameter tweaks. Three should be banned immediately. Four should be inverted. Two Tier-2 hidden-edge strategies deserve increased allocation.

**Confidence Level:** HIGH for individual diagnoses; MEDIUM for inversion estimates (needs paper trading validation).

---

## Dimension 05: Backtesting Methodology

**3-5 Most Important Data Points:**
1. **Negative OOS Sharpe for 3 of 4 asset classes** with data (CRYPTO -0.242, FOREX -1.406, COMMODITY -2.412). This indicates strategies failing on unseen data — the hallmark of overfitting. [Dim05, Section 1.1]
2. **No combinatorial purged cross-validation (CPCV)** — the single most important institutional backtesting innovation (Lopez de Prado 2018) is entirely absent. Platform uses single walk-forward path = 1 backtest path vs institutional 30-280 paths. [Dim05, Section 2.2]
3. **No PSR/DSR validation deployed.** Strategies are accepted without probabilistic Sharpe ratio or deflated Sharpe ratio testing. With 50+ strategies tested, expected false discovery rate exceeds 50% without correction. [Dim05, Sections 4, 6]
4. **5+ copies of outcome_resolver.py** create version-control risk and inconsistent backtest results. Dim10 confirms fix may not be applied to all copies. [Dim05, Section 1.1; Dim10]
5. **Only 12 walk-forward folds for ETF** — severely underpowered vs 20+ fold minimum. "THIN" strategies flagged with <50 trades vs 200-500 institutional minimum. [Dim05, Sections 2.1, 4]

**Key Conclusion:** The platform's backtesting infrastructure is retail-grade to sub-institutional. The absence of CPCV, PSR/DSR, and multiple testing correction means false discoveries are guaranteed. A fundamental overhaul is required before institutional capital deployment.

**Confidence Level:** HIGH — based on Lopez de Prado (2018), Harvey & Liu (2014), Bailey & Lopez de Prado (2014) — canonical institutional standards.

---

## Dimension 06: Penny Stock Analysis

**3-5 Most Important Data Points:**
1. **Average annual OTC returns: -24% to -27%. Median: -37%.** Bruggemann et al. (2016) study of 10,000+ OTC stocks from 2001-2010. Aggregate investor losses: $180 billion (Eraker & Ready 2015). [Dim06, Section 1.1]
2. **Bid-ask spreads for microcaps: 1-3% vs 0.01-0.05% for S&P 500.** SEC example: $0.04 bid / $0.10 ask = 60% spread. A stock must rise 15-30% just to break even on costs. [Dim06, Section 4]
3. **Only the "most liquid subset" during high-yield spread compression shows statistically significant outperformance** — this is a crisis-timing strategy, not stock-picking alpha. (Verdad Advisors 1996-May 2024). [Dim06, Section 5]
4. **Professional firms (AQR, Dimensional, Alpha Architect) systematically exclude penny stocks.** Larry Swedroe: "An efficient way to improve expected performance is to systematically exclude penny stocks." [Dim06, Section 6.1]
5. **Recommended: Create PENNY as separate, restricted asset class** with mandatory filters ($1M+ daily volume, <2% spread, exchange-listed, price >$1), 2% max per pick, 5% total allocation cap. [Dim06, Section 6.3]

**Key Conclusion:** Penny stocks are wealth-destruction vehicles for most investors (-24% to -27% annually). If included at all, they require extreme filtering, crisis-timing overlay, and strict position limits. Default should be exclusion.

**Confidence Level:** HIGH — based on 20+ peer-reviewed academic sources, SEC regulatory data, and practitioner research.

---

## Dimension 07: Meme Coin Analysis

**3-5 Most Important Data Points:**
1. **Only 0.4% of Pump.fun traders realized >$10,000 in profits.** 13.55 million wallets analyzed. 5.7 million meme coins created. Platform earned $398 million in revenue. [Dim07, Section 4.1]
2. **99.7% risk of ruin** for $100 investor with shadow-data parameters (65.6% WR, 5% avg win, -47.2% avg loss). Kelly fraction: -244% (negative expected value). [Dim07, Sections 5.1, 6.5]
3. **80-95% of meme coin traders lose money** per cross-validation of multiple sources (Binance Square: 86.44% unprofitable; academic study: social media investors lose 1% per trade in crypto). [Dim07, Section 4.3]
4. **Pump-and-dump schemes extracted $7.78M in profits while causing $3.27M in realized losses** across 17,000+ victim addresses. Creators and early gainers profit; retail provides exit liquidity. [Dim07, Section 1.3]
5. **No retail-accessible strategy has demonstrated positive expectancy.** Belcastro's 902% return requires institutional ML infrastructure and uses in-sample historical data only. [Dim07, Section 6]

**Key Conclusion:** Meme coins should be COMPLETELY EXCLUDED from the quantitative system. The 65.6% WR with -12.96% avg PnL pattern (small wins, catastrophic losses) is structurally negative-EV. Risk of ruin approaches certainty (99.7%).

**Confidence Level:** HIGH — based on Dune Analytics on-chain data (13.55M wallets), academic studies, and market manipulation research.

---

## Dimension 08: Risk Management

**3-5 Most Important Data Points:**
1. **Overall Risk Score: 6.5/10 (ADEQUATE with material gaps).** Kelly sizing is mathematically sound (8.5/10) but cross-asset diversification is weak (5.2/10) and kill switch ladder has critical gaps (6.0/10). [Dim08, Executive Summary]
2. **Quarter-Kelly 11.8% for R:R 1.5-2.0 band is conservative and correct** — mathematically verified. Platform uses ~75% of calculated Quarter-Kelly, which is prudent. [Dim08, Section 1]
3. **Probability of ruin: effectively 0%** under current sizing with 10% DD hard halt. Monte Carlo (10,000 paths): 0% halted, median final equity 2.564x after 252 trades. [Dim08, Section 6]
4. **Three critical gaps in kill switch ladder:** No daily loss limit (2-3% industry standard), no consecutive loss halt (5-7 losses), no volatility circuit breaker (VIX >40). [Dim08, Section 8]
5. **ETF and Equity are highly correlated (0.85)** — should count as ONE position for concentration limits. All Crypto tiers should be aggregated (internal correlation 0.65). True independent bets: ~4 (not 9). [Dim08, Section 4]

**Key Conclusion:** The risk framework has a solid mathematical foundation with near-zero ruin probability, but material gaps in diversification monitoring, daily loss limits, and the kill switch ladder need immediate attention.

**Confidence Level:** HIGH — Kelly mathematics are deterministic; Monte Carlo results are reproducible.

---

## Dimension 09: HTML Bug

**3-5 Most Important Data Points:**
1. **Primary bug: nested HTML comment in template.html lines 1813-1825** causes premature comment terminator, leaking visible text on US Equity Picks tab. [Dim09, Section 1]
2. **Root cause:** HTML does not support nested comments. The parser treats the first `-->` inside `` `</--> ... -->` `` as comment end, exposing remaining text. [Dim09, Section 1.3]
3. **Fix: Replace multi-line comment with `<!-- UEPS mount point -->`** (Option A — cleanest, removes developer comment with zero user value). [Dim09, Section 1.4]
4. **Script tags balanced (11 open, 11 close).** All HTML IDs unique. HTML entities properly escaped throughout. Overall HTML health is good except for this one bug. [Dim09, Secondary Findings]
5. **15+ console.log statements** in JavaScript expose internal architecture details. Should be wrapped in debug flags for production. [Dim09, Finding 5]

**Key Conclusion:** One medium-severity HTML bug causing visible text leak on US Equity Picks tab. Easy fix. Otherwise, HTML health is good. Console.log cleanup recommended for production.

**Confidence Level:** HIGH — exact line numbers identified, root cause confirmed, fix validated.

---

## Dimension 10: Code Change Impact

**3-5 Most Important Data Points:**
1. **6 days is categorically insufficient** to evaluate any trading strategy change. Need 200-500 trades = 3-8 weeks at current velocity. [Dim10, Section 2]
2. **The resolver fix was tracking-only, not strategy-improving.** It revealed true performance, didn't improve it. FOREX PF 0.27 was already losing money — the bug just hid it. "Like fixing a broken speedometer." [Dim10, Section 3]
3. **5 new swarm engines deployed in the same window** create fundamental attribution problem — cannot isolate resolver fix effects from new engine effects. [Dim10, Section 4.2]
4. **5+ copies of outcome_resolver.py** means fix may not be applied everywhere; backtest processes may still use buggy versions. [Dim10, Section 4.3]
5. **Minimum evaluation dates:** 2026-05-18 (14 days, gross directional), 2026-06-01 (30+ days, meaningful PF/WR), 2026-08-01 (90+ days, institutional-grade). [Dim10, Section 7.1]

**Key Conclusion:** The resolver fix successfully eliminated a measurement bug but revealed that FOREX strategies are deeply unprofitable (PF 0.27). 6 days is 4-8x too short for evaluation. The 5 new engines create an attribution problem.

**Confidence Level:** HIGH — statistical minimum requirements are non-negotiable mathematical facts.

---

## Dimension 11: User Safety Guide

**3-5 Most Important Data Points:**
1. **Expected returns for disciplined user (Equity only, strict filters, Quarter-Kelly): 15-25% annually** with 8-12% max drawdown. For moderate approach (Equity + Crypto B + ETF): 12-20% with 12-18% DD. [Dim11, Section 5]
2. **The 30-second decision rule:** Equity with ml_score >= 0.90 = GREAT IDEA; Crypto B-Tier L20 with R:R 1.5-2.0 = CAUTION; Commodity/Forex/C-Tier/Meme = CLOSE THE TAB. [Dim11, Section 1]
3. **Signal alpha decays post-entry:** Hours 0-48 = peak strength; Hours 48-120 = viable but degraded; Hours 120+ = edge approaching random. Best entry within 48 hours. [Dim11, Section 7]
4. **Practical minimum starting capital: $5,000.** Below this, transaction costs eat the edge. Ideal: $25,000+. [Dim11, FAQ]
5. **Honest answer: For most people, index funds are better.** S&P 500 returns ~10% with zero effort. Platform's "Disciplined" scenario gives 15-25% but requires 2-3 hours/week, emotional discipline, and platform dependency. [Dim11, FAQ]

**Key Conclusion:** A disciplined retail investor using ONLY equity picks with strict filters has a realistic path to 15-25% annual returns. But most users will lose money because they override filters, chase DANGEROUS asset classes, and size positions incorrectly. The platform's edge is real but narrow and requires discipline.

**Confidence Level:** HIGH — based on all prior dimension analyses; expected returns derived from platform's own Equity statistics.

---

## Dimension 12: Hedge Fund Transformation

**3-5 Most Important Data Points:**
1. **Platform has approximately 5% of institutional infrastructure** required for quantitative trading. Only 5% of strategies have n >= 200. 0% have PSR > 0.95. 0% have DSR > 0.95. [Dim12, Executive Summary; Appendix B KPIs]
2. **Six non-negotiable hard gates for 90-day MVP:** PSR > 0.95, DSR > 0.95, n >= 200, transaction costs modeled, single source of truth, correlation guard active. [Dim12, Section 8.3]
3. **119,598 commits with 11 contributors including AI agents** (KIMI, Claude, Cursor, Copilot) is a code quality crisis, not a feature. 5+ copies of outcome_resolver.py. No CI/CD. No testing framework. [Dim12, Section 6.1]
4. **90-day transformation cost: ~$1,500.** 12-month transformation cost: $32,400-78,000. ROI of 90-day: 867%-5,233%. ROI of 12-month at $500K AUM: 64%-1,400%. [Dim12, Sections 8.4, 9.5, 10]
5. **Renaissance Technologies discards 99%+ of tested signals.** This platform currently deploys signals with negative OOS Sharpe. "A high rejection rate is a sign of scientific discipline." [Dim12, Section 11.2]

**Key Conclusion:** The platform faces a binary choice: stay retail-focused with narrow edge, or commit to a 90-day/$1,500 MVP transformation to achieve "minimum viable institutional" status. The status quo is already expensive — it consumes capital on strategies that don't work.

**Confidence Level:** MEDIUM-HIGH — gap analysis is based on publicly available information about Renaissance/Two Sigma/Citadel; 5% estimate is reasonable but approximate.

---

# PART 2: CROSS-CUTTING ANALYSIS

---

## Top 5 Themes Across All Dimensions

### Theme 1: The Edge Is Real But Extremely Narrow
- **Equity OOS Sharpe +3.527** is the only genuinely validated edge [Dim01]
- **R:R 1.5-2.0 band PF 5.81** is the only profitable configuration [Dim01, Dim08]
- **trust_score >= 5 at 68-71% WR** is the only reliable filter [Dim02]
- Platform's value is capital preservation through exclusion, not pick generation [Dim03]
- Disciplined users can achieve 15-25% annually; undisciplined users lose money [Dim11]
- **Confidence:** HIGH — convergent evidence across 6+ dimensions

### Theme 2: The Scoring System Is Fundamentally Broken
- **elite_score is not monotonic** with 4/9 decile inversions [Dim02]
- **ml_score (r=-0.012) is pure noise** yet gets 9-25 points [Dim02]
- **regime_bonus is anti-predictive** (r=-0.115) yet gets 20 points [Dim02]
- Proposed fixes identified but NOT implemented as of 2026-04-06 [Dim02]
- Dim11 warns users to ignore the headline score and filter by forward_wr instead
- **Confidence:** HIGH — based on platform's own Score Calibration Audit (n=3,500)

### Theme 3: Survivorship Bias and Small Samples Create Illusions
- **S-Tier Crypto PF 6.80 with n=27** is a hot streak, not edge [Dim01]
- **ETF OOS Sharpe 6.368 with 12 folds** is an artifact [Dim01]
- **Bond PF 1.72 with n=10** is statistically meaningless [Dim01]
- **Free data sources (yfinance) inflate returns 1-4% annually** through survivorship bias [Dim06, Dim12]
- **0.4% of Pump.fun traders profitable** — the rest are exit liquidity [Dim07]
- **Confidence:** HIGH — documented across Dim01, Dim05, Dim06, Dim07, Dim12

### Theme 4: Code Quality and Governance Crisis
- **119K commits, 11 contributors, AI agents committing without review** [Dim12]
- **5+ copies of outcome_resolver.py** creating version-control risk [Dim05, Dim10, Dim12]
- **Nested HTML comment bug** in production code [Dim09]
- **No CI/CD, no testing framework, no code review gates** [Dim12]
- **Only 5% of institutional infrastructure exists** despite massive commit velocity [Dim12]
- More code != better code. Velocity without quality control = technical debt. [Cross-Insight 6]
- **Confidence:** HIGH — directly observable from repository analysis

### Theme 5: Measurement Fixes Are Not Strategy Fixes
- **Resolver fix revealed FOREX PF 0.27** — it didn't improve it [Dim10, Cross-Insight 3]
- **6 days post-fix is 4-8x too short** for meaningful evaluation [Dim10]
- **72.7% of picks still open at 24h** — the tracking window creates systematic bias [Source doc]
- **Post-fix numbers represent TRUE performance of unchanged (broken) strategies** [Dim10]
- The dashboard annotation "numbers are now genuine" means "strategies are genuinely losing" [Dim10]
- **Confidence:** HIGH — statistical minimum requirements are mathematical facts

---

## Key Contradictions and Conflicts

### Conflict 1: Optimal ml_score Threshold (HIGH IMPACT)
- **Action Plan says:** ml_score >= 0.90 (66.7% accuracy)
- **Dim02 says:** Confidence 0.70-0.79 is the sweet spot (57% WR); 0.90+ is WORSE (47% WR)
- **Resolution:** These may measure DIFFERENT score types. Action Plan refers to "ml_score" (gating threshold); Dim02 refers to "confidence" (display score). The platform has multiple score types that behave differently. Users should filter by trust_score >= 5 (68-71% WR) rather than any single ml_score threshold. [Cross-Verification, Conflict Zone C-1]

### Conflict 2: Forex Verdict — HALT vs MONITOR
- **Dim01 says:** DANGEROUS — PF 0.27, OOS Sharpe -1.406 → HALT
- **Action Plan says:** TRUE WR ~49% post-bug-fix, PF 3.59 from "trusted filter" → T3 candidate
- **Resolution:** These use DIFFERENT data slices. PF 0.27 is overall; PF 3.59 is from a specific "trusted" subset that may have selection bias. The 6-day post-fix window is insufficient. HALT for now, reassess June 1 with 30+ days of data. [Cross-Verification, Conflict Zone C-2]

### Conflict 3: Crypto S-Tier — SCALE vs ABANDON
- **Dim01 says:** DANGEROUS — n=27, negative OOS Sharpe → ABANDON
- **Action Plan says:** Exceptional metrics, scale with on-chain data
- **Resolution:** The metrics ARE exceptional (PF 6.80, WR 70.4%) but n=27 is statistically meaningless and OOS Sharpe is negative for ALL crypto tiers collectively. Don't abandon but don't scale either. Require n>=50 before any allocation increase. Current allocation should be minimal. [Cross-Verification, Conflict Zone C-3]

### Conflict 4: C-Tier Handling — 0% vs 5%
- **Dim01/Dim08 say:** PF 0.56, Kelly strongly negative → 0% allocation
- **Action Plan says:** Reduce to 5%, don't hard suspend (diversification value)
- **Resolution:** Dim08 mathematically shows C-Tier Quarter-Kelly is -5.3% (direct = wealth destruction). The contrarian argument (effective PF = 1/0.56 = 1.79) requires 100+ trade backtest validation. Default: 0% allocation. Only consider contrarian approach after validated backtest. [Dim01, Dim08, Source doc]

### Conflict 5: Kill Switch Assessment — Adequate vs Gaps
- **Dim08 says:** Overall 6.5/10, ADEQUATE. Probability of ruin effectively 0%.
- **Dim08 ALSO says:** Critical gaps — no daily loss limit, no consecutive loss halt, no volatility circuit breaker.
- **Resolution:** Both are true. The EXISTING kill switch (5% DD → 50% size, 10% DD → halt) is mathematically sound. The MISSING elements (daily loss limit, consecutive loss halt, vol circuit) are the gaps. Fix the gaps to raise score from 6.5 to 9.0/10. [Dim08, Section 8]

---

## Most Important Data Points for the Final Report

### Priority 1: Report Foundation (Must Include)
1. Only Equity passes all 5 investability gates (PF 1.72, OOS Sharpe +3.527) — 7 asset classes should get 0% allocation [Dim01]
2. R:R 1.5-2.0 band is the ONLY profitable zone (PF 5.81, Kelly +47.2%); R:R >2.0 is catastrophic (PF 0.35) [Dim01, Dim08]
3. Composite scoring is broken — not monotonic, gives most weight to least predictive components [Dim02]
4. Platform has ~5% of institutional infrastructure; 0% of strategies have PSR > 0.95 [Dim12]
5. 99.7% risk of ruin for meme coins; 0.4% of Pump.fun traders profitable [Dim07]
6. Penny stocks average -24% to -27% annually; AQR/Dimensional exclude them [Dim06]
7. The resolver fix revealed FOREX PF 0.27 — it didn't fix the strategy [Dim10]
8. 119K commits with AI agents committing without review = governance crisis [Dim12]

### Priority 2: Actionable Recommendations
9. Optimal UI path: Verified Alpha + High Conviction + R:R 1.5+ (66-70% WR, 0-2 picks) [Dim03]
10. trust_score >= 5 and forward_wr 50-65% are the most predictive filters (68-71% WR) [Dim02]
11. 11 strategies are failing; 4 invertible, 2 should be banned, 2 hidden-edge strategies deserve scale-up [Dim04]
12. Kelly Quarter at 11.8% for R:R 1.5-2.0 band is mathematically correct and conservative [Dim08]
13. Six hard gates for 90-day MVP: PSR>0.95, DSR>0.95, n>=200, cost modeling, single source of truth, correlation guard [Dim12]
14. HTML bug fix: replace comment block at template.html lines 1813-1825 with `<!-- UEPS mount point -->` [Dim09]

### Priority 3: Context and Caveats
15. 6 days post-resolver-fix is 4-8x too short for evaluation; wait until June 1 [Dim10]
16. 5 new swarm engines deployed same window = attribution problem [Dim10]
17. Free data sources inflate returns 1-4% annually through survivorship bias [Dim12]
18. Expected returns: 15-25% for disciplined users; -20 to -40% for YOLO approach [Dim11]
19. The platform's true value is capital preservation through exclusion, not pick generation [Cross-Insight 8]

---

# PART 3: RECOMMENDED CHAPTER STRUCTURE

Based on the research findings, the following chapter structure is recommended for the comprehensive audit report:

---

## Proposed Report Structure

### Executive Summary (1-2 pages)
- Verdict: ONE proven asset class, NINE requiring zero allocation
- The 5 key numbers every stakeholder must know
- Immediate actions (this week) vs transformation (90-day/12-month)

### Chapter 1: The Asset Class Verdict (Foundation)
- **Source dimensions:** Dim01 (primary), Dim06, Dim07
- Five-gate framework and results
- Only Equity passes (PF 1.72, OOS Sharpe +3.527)
- FOREX: revealed as broken (PF 0.27 post-fix)
- COMMODITY: abandoned (PF 0.02, 58% flat exits)
- MEME coins: excluded (99.7% risk of ruin)
- PENNY stocks: excluded (-24% to -27% annually)
- The 1.5-2.0 R:R band discovery (PF 5.81)
- Recommended allocation: 25% Equity, 5% ETF (pending), 70% cash

### Chapter 2: The Broken Scoring System (Critical Finding)
- **Source dimensions:** Dim02 (primary), Dim03
- elite_score is not monotonic (4/9 inversions)
- ml_score is noise (r=-0.012) yet gets 9-25 points
- regime_bonus is anti-predictive (r=-0.115)
- What users should ACTUALLY filter for: trust_score >= 5, forward_wr 50-65%
- The overconfidence penalty: 0.70-0.79 beats 0.90+
- Proposed weight rebalance (not yet implemented)

### Chapter 3: Strategy Health and Failure Analysis
- **Source dimensions:** Dim04 (primary)
- 11 failing strategies categorized by failure mode
- 4 invertible strategies (with academic basis)
- 2 strategies to ban immediately (unknown, gainer_compression_relaxed_mut)
- Hidden edge: signal_validation (PF 2.58) and mega_mutation (PF 3.19)
- The consensus trap: why agreement signals fail
- Academic framework for strategy lifecycle management

### Chapter 4: Backtesting Infrastructure Gaps
- **Source dimensions:** Dim05 (primary), Dim10
- Negative OOS Sharpe for 3 of 4 asset classes
- No CPCV, PSR, DSR, or multiple testing correction
- 5+ copies of outcome_resolver.py
- The resolver fix: measurement fix, not strategy fix
- 6 days is 4-8x too short for evaluation
- 5 new engines = attribution problem
- Roadmap to institutional-grade backtesting

### Chapter 5: Risk Management Assessment
- **Source dimensions:** Dim08 (primary)
- Kelly sizing: mathematically correct (8.5/10)
- Probability of ruin: effectively 0% with current sizing
- Cross-asset diversification: weak (5.2/10)
- Kill switch gaps: no daily loss limit, no consecutive loss halt, no vol circuit
- ETF-Equity correlation (0.85) = hidden concentration
- Enhanced kill switch recommendations

### Chapter 6: Code Quality and Governance Crisis
- **Source dimensions:** Dim09, Dim10, Dim12
- 119K commits, AI agents without review
- 5+ copies of outcome_resolver.py
- Nested HTML comment bug (exact location identified)
- No CI/CD, no testing framework
- AI agent governance framework needed

### Chapter 7: UI/UX Analysis and Optimal User Path
- **Source dimensions:** Dim03 (primary)
- Optimal filter combination: Verified Alpha + High Conviction + R:R 1.5+
- 192/210 picks gated out = value through exclusion
- Smart Picks naming confusion (3 elements, same name)
- UX enhancement recommendations (filter chips, pick counts, tooltips)
- HTML bug fix instructions

### Chapter 8: User Safety Guide
- **Source dimensions:** Dim11 (primary)
- The 30-second decision rule
- Expected returns by discipline level
- Position sizing rules by asset class
- Red flags and hard stops
- Signal alpha decay curve (0-48h peak, 120h+ random)
- Honest answer: index funds are better for most people

### Chapter 9: Hedge Fund Transformation Roadmap
- **Source dimensions:** Dim12 (primary)
- Gap analysis: ~5% of institutional infrastructure
- 90-day MVP: 6 hard gates, ~$1,500 cost, 867-5,233% ROI
- 12-month transformation: $32K-78K cost, credible quant fund quality
- Week-by-week implementation plan
- What Renaissance/Two Sigma/Citadel would do differently

### Appendices
- A: Summary statistics table (all asset classes)
- B: Score component correlation matrix
- C: Strategy decision matrix (all 11 failing strategies)
- D: Kill switch ladder (current vs enhanced)
- E: 90-day implementation timeline
- F: Academic source index (50+ citations)

---

## Source Structure Map (Chapters <- Dimensions)

| Chapter | Primary Dimensions | Cross-Verification | Insights |
|---------|-------------------|-------------------|----------|
| Ch 1: Asset Class Verdict | Dim01, Dim06, Dim07 | HC-1, HC-4, HC-5 | Insight 1, 5, 9 |
| Ch 2: Broken Scoring | Dim02, Dim03 | HC-3 | Insight 2 |
| Ch 3: Strategy Health | Dim04 | HC-2 | Insight 4 |
| Ch 4: Backtesting Gaps | Dim05, Dim10 | HC-7 | Insight 3, 7 |
| Ch 5: Risk Management | Dim08 | HC-2, HC-8 | Insight 9 |
| Ch 6: Code Quality | Dim09, Dim10, Dim12 | HC-6 | Insight 6 |
| Ch 7: UI/UX | Dim03 | HC-8 | Insight 8 |
| Ch 8: User Safety | Dim11 | HC-1, HC-5 | Insight 9, 10 |
| Ch 9: Transformation | Dim12 | HC-3 | Insight 10 |

---

## Total Citation Count by Dimension

| Dimension | Citations/Sources | Type |
|-----------|------------------|------|
| Dim01 (Asset Edge) | 15+ academic/industry | Peer-reviewed, platform data |
| Dim02 (Scoring) | 15 academic, platform audit | Platform's own audit (n=3,500) |
| Dim03 (UI/UX) | 18 industry/UX research | Best practices, platform data |
| Dim04 (Strategy) | 12 academic | Jegadeesh & Titman, Hong & Stein, etc. |
| Dim05 (Backtesting) | 25+ academic/industry | Lopez de Prado, Harvey & Liu, etc. |
| Dim06 (Penny Stocks) | 20+ peer-reviewed academic | Bruggemann et al., Eraker & Ready, etc. |
| Dim07 (Meme Coins) | 12 academic/on-chain | Dune Analytics, arXiv papers, AFA Journal |
| Dim08 (Risk) | 20+ industry/academic | Kelly literature, correlation studies |
| Dim09 (HTML Bug) | 5 technical | HTML spec, W3C, platform code |
| Dim10 (Code Change) | 6 industry/academic | TradeProb, EdgeFlo, Lopez de Prado |
| Dim11 (User Safety) | Cross-references all dims | Platform data, academic synthesis |
| Dim12 (Hedge Fund) | 25+ industry/academic | Renaissance, Two Sigma, Citadel sources |
| Cross-Verification | 8 confirmed findings | 2+ agents, independent sources |
| 10 Insights | Synthesis across all dims | Multi-dimensional pattern recognition |
| **TOTAL** | **200+ unique sources** | Peer-reviewed, regulatory, platform data |

---

*Synthesis compiled from 14 research artifacts + 1 source document.*
*Cross-verification: 8 HIGH confidence findings confirmed by 2+ independent sources.*
*3 conflict zones identified and resolved.*
*200+ unique academic, industry, and platform data sources cited across all dimensions.*
