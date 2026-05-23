# Quantitative Trading Platform Audit Report — Structure Skeleton

**Total Word Target:** 13,500 words (range: 12,000-15,000)
**Chapters:** 9 + Appendices
**Heading Format:** H1 = report title only; H2 = chapters (N.0); H3 = sections (N.N); H4 = content points (N.N.N). No H5. No 4-digit numbering.

---

## H2 1.0 EXECUTIVE SUMMARY (~1,000 words)

### H3 1.1 The Verdict in Five Numbers
#### H4 1.1.1 Present the five irreducible metrics: Equity OOS Sharpe +3.527, R:R 1.5-2.0 band PF 5.81, trust_score >=5 WR 68-71%, platform infrastructure at 5% institutional, 99.7% meme coin risk of ruin
#### H4 1.1.2 Table: Asset Class Verdict Summary (9 classes x SAFE/DANGEROUS/CONDITIONAL with one-line justification)
#### H4 1.1.3 The capital preservation thesis: 192 of 210 picks gated out by optimal filters; platform value is exclusion, not generation

### H3 1.2 Immediate Actions vs Transformation
#### H4 1.2.1 Table: This Week (5 emergency items — R:R gate fix, ml_score threshold, C-Tier suspension, 2 strategy bans, HTML bug fix)
#### H4 1.2.2 Table: 30-Day (5 infrastructure items — CPCV deployment, PSR/DSR gates, outcome_resolver consolidation, kill switch gaps, orphaned code integration)
#### H4 1.2.3 Table: 90-Day (6 institutional MVP hard gates with cost estimate $1,500 and ROI projection 867-5,233%)

### H3 1.3 How to Read This Report
#### H4 1.3.1 Audience pathway map: technical team → Chapters 2, 3, 4, 8; business stakeholders → Chapters 1, 5, 7, 9; retail users → Chapters 5, 7, 9
#### H4 1.3.2 Confidence level legend (HIGH/MEDIUM-HIGH/MEDIUM) and evidence type tags per finding
#### H4 1.3.3 Definition of SAFE vs DANGEROUS vs CONDITIONAL verdicts with investment implication

**Required Elements:** 1 summary table (5 numbers), 1 verdict matrix (9 asset classes), 3 action tables (This Week/30-Day/90-Day)
**Maps to:** E1, E12, E14, E22, E27, I1, I10, I13, C1, C2, C3, C5, C16

---

## H2 2.0 ASSET CLASS EDGE VERDICT (~2,500 words)

### H3 2.1 The Five-Gate Investability Framework
#### H4 2.1.1 Define Gate 1 (Profit Factor > 1.5), Gate 2 (Win Rate > 50%), Gate 3 (OOS Sharpe > 0), Gate 4 (n >= 100), Gate 5 (Positive Quarter-Kelly)
#### H4 2.1.2 Table: Five-gate pass/fail matrix for all 9 asset classes (Equity, ETF, Crypto S/A/B/C, Forex, Commodity, Bond, Futures)
#### H4 2.1.3 Explain why OOS Sharpe is the decisive gate and cite Jacquier et al. 2025, Bailey & Lopez de Prado DSR

### H3 2.2 Equity: The Only SAFE Asset Class
#### H4 2.2.1 Present Equity full metrics: PF 1.72, WR 53.1%, OOS Sharpe +3.527, n=256 closed, 136W/105L/15U, +233.48% realized PnL
#### H4 2.2.2 Open picks analysis: 4 active positions, short-term vs long-term performance split
#### H4 2.2.3 Walk-forward validation: 47 folds, OOS WR 57.9%, consistency 66.0%, worst-fold WR 20.0%
#### H4 2.2.4 Verdict: SAFE. Recommended allocation: 25% of portfolio. Table: Tier-2 proven strategies for Equity (signal_validation, mega_mutation, rl_agent, claude_gainer with PF/WR/n)

### H3 2.3 ETF: CONDITIONAL — Pending Validation
#### H4 2.3.1 Present ETF metrics: PF 1.24, WR 52.9%, OOS Sharpe 6.368, but only 12 folds, decay 10.8, n=85
#### H4 2.3.2 Survivorship bias analysis: why 6.368 Sharpe is likely artifact; estimated true Sharpe 2.0-3.0
#### H4 2.3.3 Verdict: CONDITIONAL. Recommended allocation: 5% maximum pending n>=100 and fold count >=20. Table: conditions for upgrade to SAFE

### H3 2.4 Crypto Tier Analysis
#### H4 2.4.1 S-Tier: PF 6.80, WR 70.4%, n=27 — survivorship filter, not reproducible edge. Verdict: CONDITIONAL (n>=50 required)
#### H4 2.4.2 A-Tier: PF 1.58, WR 42.4%, n=304 — sub-50% WR, fails Gate 2. Verdict: DANGEROUS for direct allocation
#### H4 2.4.3 B-Tier: PF 1.28, WR 45.0%, n=940 — marginal with R:R 1.5-2.0 overlay only. Verdict: CONDITIONAL
#### H4 2.4.4 C-Tier: PF 0.56, WR 28.1%, n=224 — negative expectancy, Kelly -5.3%. Verdict: DANGEROUS (0% allocation, contrarian only after validation)
#### H4 2.4.5 Aggregate Crypto OOS Sharpe -0.242 (302 folds) = definitive overfitting. Table: all 4 tiers with verdict and allocation

### H3 2.5 The Broken Asset Classes
#### H4 2.5.1 Forex: PF 0.27 post-resolver-fix, OOS Sharpe -1.406, n=1169 — measurement fix revealed broken strategy, not fixed it. Verdict: DANGEROUS (HALT until June 1 reassessment)
#### H4 2.5.2 Commodity: cta_commodity_momentum_term PF 0.02, 58% flat exits, OOS Sharpe -2.412 — strategy finds no setups. Verdict: DANGEROUS (ban strategy, deploy triple-screen replacement)
#### H4 2.5.3 Bond: PF 1.72, WR 50.0%, n=20 — statistically meaningless sample. Verdict: DANGEROUS (insufficient data)
#### H4 2.5.4 Futures: PF 0.00, n=2 — no viable data. Verdict: DANGEROUS

### H3 2.6 The Golden Finding: R:R 1.5-2.0 Band
#### H4 2.6.1 Present the discovery: PF 5.81, Kelly +47.2%, avg PnL +4.98% in 1.5-2.0 R:R band vs PF 0.35, avg loss -17.88% in >2.0 band
#### H4 2.6.2 Table: PF and Kelly by R:R band (<1.5, 1.5-2.0, 2.0+) with interpretation
#### H4 2.6.3 Why the previous recommendation (lower floor to 1.25) was catastrophically wrong: R:R 1.0-1.25 band PF 1.01, Kelly -1.6%

### H3 2.7 Recommended Capital Allocation
#### H4 2.7.1 Table: Final allocation matrix (Asset Class | Allocation | Condition | Rationale) — 25% Equity, 5% ETF pending, 70% cash/reserve, 0% all others
#### H4 2.7.2 Rebalancing triggers: what metrics must change for allocation revision

**Required Elements:** 5-gate framework table, 9-asset verdict matrix, Equity deep-dive with open/closed picks, Crypto 4-tier table, broken classes diagnosis, R:R band table (3 bands), final allocation table
**Maps to:** E1, E2, E10, E11, E14, E17, E20, I9, I11, I14, C1, C3, C5, C6, C16

---

## H2 3.0 THE BROKEN SCORING SYSTEM (~1,800 words)

### H3 3.1 F-Score vs Score vs Composite Score — What Each Measures
#### H4 3.1.1 F-Score (shown as 4/9): Piotroski F-Score methodology — 9 binary criteria breakdown (profitability 4, leverage/liquidity 3, efficiency 2). What it measures: fundamental financial health. Platform adaptation and calculation.
#### H4 3.1.2 Score (shown as 0.748, 0.703): The ml_score or composite score — machine learning confidence output. Range 0.0-1.0. What it measures: model prediction confidence. Calculation methodology.
#### H4 3.1.3 Composite Score / elite_score: Weighted combination of forward_wr (25 pts), regime_bonus (20 pts), ml_score (9-25 pts), and other components. The formula and weight structure.
#### H4 3.1.4 Visual hierarchy diagram: F-Score (fundamental health, 0-9) → ml_score/Score (model confidence, 0.0-1.0) → elite_score/composite (weighted prediction quality, 0-100). Which score to use for which decision.

### H3 3.2 Why the Composite Score Is Not Monotonic
#### H4 3.2.1 Define monotonicity: higher score must predict higher WR. Present evidence: 4 inversions out of 9 deciles
#### H4 3.2.2 Table: Decile-by-decile WR vs elite_score (D1-D9) with inversion points highlighted (D6-D7 dead zone: score 30-40, WR 35-43%)
#### H4 3.2.3 The overconfidence penalty: confidence 0.70-0.79 delivers 57% WR; 0.90+ delivers only 47% WR. Why medium confidence outperforms high confidence.

### H3 3.3 Inverted Weights: The Least Predictive Components Get the Most Points
#### H4 3.3.1 Table: Score component correlation ranking — forward_wr r=+0.242 (BEST, 25 pts), ml_score r=-0.012 (NOISE, gets 9-25 pts), regime_bonus r=-0.115 (ANTI-PREDICTIVE, gets 20 pts)
#### H4 3.3.2 Quantify the misallocation: regime_bonus gets 20 points for -0.115 correlation (anti-predictive), while forward_wr gets only 25 points for +0.242 correlation (best predictor)
#### H4 3.3.3 Proposed weight rebalance: forward_wr 25→55 pts (+37%), regime_bonus 20→5 pts (-75%), ml_score 9→4 pts (-55%). Expected impact on monotonicity.

### H3 3.4 What Users Should Actually Filter By
#### H4 3.4.1 Primary filter: trust_score >= 5 delivers 68-71% WR — the single most effective filter on the platform
#### H4 3.4.2 Secondary filter: forward_wr 50-65% range (optimal confidence zone)
#### H4 3.4.3 Tertiary filter: R:R 1.5-2.0 band (the golden zone from Chapter 2)
#### H4 3.4.4 Table: Filter hierarchy for users — Rank | Filter | Expected WR | Pick Count | Use Case

### H3 3.5 Score System Fix Recommendations
#### H4 3.5.1 Immediate: Add score explainability tooltips to dashboard showing what each score measures
#### H4 3.5.2 30-day: Implement proposed weight rebalance and test on holdout set
#### H4 3.5.3 90-day: Deploy unified score with documented formula, monotonicity validation, and user-facing explanation

**Required Elements:** Score type comparison table (F-Score/Score/Composite), decile monotonicity table (9 deciles), component correlation table (3 components), filter hierarchy table (4 filters), weight rebalance proposal
**Maps to:** E8, E9, E13, E26, I8, I9, C12

---

## H2 4.0 UI/UX AUDIT AND OPTIMAL FILTER PATH (~1,500 words)

### H3 4.1 The Pick Discovery Problem
#### H4 4.1.1 Enumerate all UI paths: high-conviction picks button, smart picks tab, smart picks button, verified alpha button, all filter combinations (score/source/strategy/high-grade/trusted/R:R/safe symbols/recent)
#### H4 4.1.2 The paradox: 192 of 210 total picks are gated out by the best filter — the platform's value is capital preservation through exclusion
#### H4 4.1.3 Three "Smart Picks" elements share the same name but have different behaviors — document each and the UX violation

### H3 4.2 Exhaustive Filter Combination Testing
#### H4 4.2.1 Table: Filter combination results — Filter Set | Pick Count | Estimated WR | PF | Notes (test all 12+ combinations)
#### H4 4.2.2 Best conservative path: Verified Alpha + High Conviction + R:R 1.5+ = 66-70% WR, 0-2 picks (highest quality, lowest quantity)
#### H4 4.2.3 Best daily driver: Verified Alpha + High Conviction = 65-68% WR, 3-8 picks (quality with usability)
#### H4 4.2.4 Best moderate path: Verified Alpha + WR >=50% gate = ~64.1% WR (broader set)

### H3 4.3 Filter Performance by User Profile
#### H4 4.3.1 Table: Conservative profile filters (capital preservation, 8-12% target return) — specific button clicks and settings
#### H4 4.3.2 Table: Moderate profile filters (balanced growth, 12-18% target return) — specific button clicks and settings
#### H4 4.3.3 Table: Aggressive profile filters (maximizing edge exposure, 18-25% target return) — specific button clicks and settings
#### H4 4.3.4 Recent filter analysis: Last 10 vs Last 20 vs Last 50 vs Last 100 — which recency window adds vs destroys value

### H3 4.4 Guide Page Accuracy Audit
#### H4 4.4.1 Table: Guide Claim vs Actual Data vs Discrepancy Severity (5+ claims cross-referenced)
#### H4 4.4.2 Does the Guide properly reflect per-asset-class edge? Verdict: partial misalignment on Crypto tiers and R:R recommendations
#### H4 4.4.3 Recommended fixes to Guide documentation

### H3 4.5 Supplementary Tab Analysis
#### H4 4.5.1 US Equity Picks tab: what it shows, how it differs from main dashboard, whether it adds value
#### H4 4.5.2 Closed Picks tab: historical pattern analysis, what can be learned from resolved positions
#### H4 4.5.3 Tab reduction recommendation: from 13 tabs to 5 (which to keep/merge/hide)

### H3 4.6 HTML Bug Fix Instructions
#### H4 4.6.1 Bug location: template.html lines 1813-1825, US Equity Picks tab — visible leaked text
#### H4 4.6.2 Root cause: HTML does not support nested comments; inner --> closes outer comment prematurely
#### H4 4.6.3 Exact fix: replace multi-line comment block with `<!-- UEPS mount point -->`
#### H4 4.6.4 Verification steps: reload US Equity Picks tab, confirm no visible leaked text, confirm 11 script tags still balanced
#### H4 4.6.5 Secondary cleanup: wrap 15+ console.log statements in debug flags for production

**Required Elements:** 1 filter combination results table (12+ rows), 3 user profile filter tables, Guide accuracy audit table (5+ claims), HTML bug location and fix code block, tab consolidation recommendation
**Maps to:** E3, E4, E5, E6, E7, E25, E26, I3, I6, I17, I18, C17, C18

---

## H2 5.0 STRATEGY HEALTH AND FAILURE ANALYSIS (~2,000 words)

### H3 5.1 Strategy Failure Overview
#### H4 5.1.1 Table: 11 failing strategies — Strategy Name | Asset Class | 7d WR | Baseline WR | Drop | Failure Category | Priority
#### H4 5.1.2 Four failure categories defined: regime change (4 strategies), adverse selection/crowding (3), overfitting (2), structural/breakage (2)

### H3 5.2 Strategy-by-Strategy Diagnosis
#### H4 5.2.1 Regime change strategies: diagnosis for each of 4 strategies — what regime shift occurred, what regime filter would restore edge
#### H4 5.2.2 Adverse selection/crowding strategies: diagnosis for each of 3 strategies — why consensus signals become self-defeating
#### H4 5.2.3 Overfitting strategies: diagnosis for each of 2 strategies — which parameters were over-optimized, which IS/OOS gap proves it
#### H4 5.2.4 Structural/breakage strategies: diagnosis for each of 2 strategies — code bugs, data pipeline failures, gate misconfiguration

### H3 5.3 Inverse Strategy Candidates
#### H4 5.3.1 Academic basis for inversion: Jegadeesh & Titman momentum reversal, Chan contrarian literature
#### H4 5.3.2 Table: 4 invertible strategies — Strategy | Current WR | Inverted Expected WR | Academic Basis | Validation Required
#### H4 5.3.3 cta_commodity_momentum_term: PF 0.02 → invert to term structure carry per Fuertes et al.
#### H4 5.3.4 myfxbook_retail_contrarian, futures_momentum, goldmine_1x_consensus, MomentumEMA: inversion methodology and paper trade validation plan

### H3 5.4 Strategies to Ban Immediately
#### H4 5.4.1 "unknown" strategy: undocumented logic, 18% WR — ban with code removal
#### H4 5.4.2 gainer_compression_relaxed_mut: 32% baseline WR, overfitted — ban with code removal
#### H4 5.4.3 cta_commodity_momentum_term: PF 0.02, 58% flat exits — ban permanently, deploy triple-screen replacement

### H3 5.5 Hidden Edge: Underallocated Tier-2 Strategies
#### H4 5.5.1 signal_validation: PF 2.58, WR 63.0%, MDD 12.0%, n=184 — deserves scale-up from THIN to full allocation
#### H4 5.5.2 mega_mutation: PF 3.19, WR 67.9%, MDD 36.0%, n=78 — deserves scale-up with MDD monitoring
#### H4 5.5.3 rl_agent: PF 2.54, WR 60.0%, MDD 2.1%, n=5 — promising but needs n>=50 before allocation
#### H4 5.5.4 claude_gainer: PF 2.23, WR 56.2%, MDD 33.5%, n=32 — deserves scale-up with MDD guard
#### H4 5.5.5 Table: Tier-2 strategy allocation recommendations (current vs proposed allocation, conditions)

### H3 5.6 Parameter Optimization Playbook
#### H4 5.6.1 Framework: which parameters to tweak, in which direction, by how much, with backtest validation gates
#### H4 5.6.2 Table: Parameter tweak recommendations for 3 highest-impact strategies — Parameter | Current | Proposed | Expected Impact | Validation Gate
#### H4 5.6.3 Orphaned winning strategies lacking recent picks: identification and reactivation plan
#### H4 5.6.4 New strategy research recommendations with academic backing

**Required Elements:** 11-strategy failure table, 4 inverse strategy table, 3 ban-now strategies with rationale, 4 Tier-2 strategy deep-dive, parameter tweak table (3 strategies), academic citation list
**Maps to:** E2, E15, E16, I4, I5, C6, C10, C14, C15

---

## H2 6.0 RISK MANAGEMENT ASSESSMENT (~1,200 words)

### H3 6.1 Overall Risk Framework Score
#### H4 6.1.1 Table: Risk component scores (Kelly sizing 8.5/10, cross-asset diversification 5.2/10, kill switch ladder 6.0/10, overall 6.5/10 ADEQUATE with material gaps)
#### H4 6.1.2 Kelly sizing verification: Quarter-Kelly 11.8% for R:R 1.5-2.0 band is mathematically correct and conservative

### H3 6.2 Probability of Ruin Analysis
#### H4 6.2.1 Monte Carlo results: 10,000 paths, 0% halted with 10% DD hard halt, median final equity 2.564x after 252 trades
#### H4 6.2.2 Table: Ruin probability by asset class allocation (Equity-only vs Equity+Crypto B vs YOLO portfolio)
#### H4 6.2.3 Position sizing formula: Kelly fraction calculation with Quarter-Kelly application for retail investors

### H3 6.3 Kill Switch Analysis
#### H4 6.3.1 Current kill switch ladder: 5% DD → 50% size reduction, 10% DD → halt. Table: current vs enhanced
#### H4 6.3.2 Three critical gaps: no daily loss limit (2-3% industry standard), no consecutive loss halt (5-7 losses), no volatility circuit breaker (VIX >40)
#### H4 6.3.3 Enhanced kill switch recommendations with implementation priority

### H3 6.4 Cross-Asset Correlation and Hidden Concentration
#### H4 6.4.1 ETF-Equity correlation 0.85: counts as ONE position for concentration limits
#### H4 6.4.2 All Crypto tiers internal correlation 0.65: should aggregate to single position
#### H4 6.4.3 True independent bets: ~4 (not 9). Table: correlation matrix and effective position count
#### H4 6.4.4 Diversification score improvement path: 5.2/10 → 8.0/10

**Required Elements:** 4-component risk score table, Monte Carlo ruin results table, kill switch ladder table (current vs enhanced), correlation matrix, position sizing formula with worked example
**Maps to:** E12, I1, I10, I11, C2, C5, C8

---

## H2 7.0 SPECIAL ASSET CLASSES: PENNY STOCKS AND MEME COINS (~1,500 words)

### H3 7.1 Penny Stock Viability Analysis
#### H4 7.1.1 Academic evidence: Bruggemann et al. 2016 — 10,000+ OTC stocks 2001-2010, average annual returns -24% to -27%, median -37%. Eraker & Ready 2015 — aggregate investor losses $180 billion.
#### H4 7.1.2 Cost structure destruction: bid-ask spreads 1-3% vs 0.01-0.05% for S&P 500. SEC example: $0.04 bid / $0.10 ask = 60% spread. Stock must rise 15-30% just to break even.
#### H4 7.1.3 The $100 investor scenario: $100 position with 2% round-trip spread loses 2% immediately. Doubling requires 100%+ gain net of spreads. Table: realistic payoff scenarios.
#### H4 7.1.4 Only exception: most liquid subset during high-yield spread compression (crisis-timing strategy, not stock-picking alpha). Verdad Advisors 1996-May 2024.
#### H4 7.1.5 Professional consensus: AQR, Dimensional, Alpha Architect systematically exclude penny stocks. Larry Swedroe quote.

### H3 7.2 Penny Stock Verdict and Conditions
#### H4 7.2.1 Verdict: DANGEROUS for all retail investors. Default exclusion.
#### H4 7.2.2 If included despite verdict: create PENNY as separate restricted asset class with mandatory filters ($1M+ daily volume, <2% spread, exchange-listed, price >$1), 2% max per pick, 5% total allocation cap
#### H4 7.2.3 Table: Penny stock filter requirements and position limits

### H3 7.3 Meme Coin Viability Analysis
#### H4 7.3.1 On-chain evidence: Dune Analytics 13.55 million wallets, 5.7 million meme coins created. Only 0.4% of Pump.fun traders realized >$10,000 profits. Platform earned $398M in revenue.
#### H4 7.3.2 Risk of ruin: 99.7% for $100 investor with platform parameters (65.6% WR, 5% avg win, -47.2% avg loss). Kelly fraction: -244% (negative expected value).
#### H4 7.3.3 Loss statistics: 80-95% of meme coin traders lose money (Binance Square: 86.44% unprofitable). Social media investors lose 1% per trade in crypto.
#### H4 7.3.4 Pump-and-dump: $7.78M extracted by creators/early gainers, $3.27M in realized losses across 17,000+ victim addresses. Retail provides exit liquidity.
#### H4 7.3.5 Academic finding: Belcastro's 902% return requires institutional ML infrastructure and uses in-sample data only. No retail-accessible strategy with positive expectancy.

### H3 7.4 Meme Coin Verdict and Asset Class Reclassification
#### H4 7.4.1 Verdict: COMPLETELY EXCLUDE from quantitative system. The 65.6% WR with -12.96% avg PnL pattern (small wins, catastrophic losses) is structurally negative-EV.
#### H4 7.4.2 Create MEME as distinct asset class with separate gating, separate position limits, hard 5% portfolio cap, spread-adjusted R:R
#### H4 7.4.3 Why current classification under CRYPTO is dangerous: fundamentally different risk profile requires separate treatment

### H3 7.5 Comparative Table: Penny vs Meme vs Platform Edge
#### H4 7.5.1 Table: Penny Stock vs Meme Coin vs Equity (expected return, ruin probability, min capital, professional consensus, retail suitability)

**Required Elements:** Academic evidence table (penny stocks), $100 scenario payoff table, penny filter requirements table, meme coin on-chain statistics table, ruin probability calculation, comparative table (3 asset types), 20+ academic citations
**Maps to:** E18, E19, I2, C7, C9

---

## H2 8.0 CODE QUALITY AND TECHNICAL DEBT (~1,200 words)

### H3 8.1 Repository Health Assessment
#### H4 8.1.1 119,598 commits with 11 contributors including AI agents (KIMI, Claude, Cursor, Copilot) — velocity without quality control
#### H4 8.1.2 Table: Code quality metrics (commits, contributors, AI agents, CI/CD status, testing framework, code review gates, documentation coverage)
#### H4 8.1.3 The outcome_resolver.py crisis: 5+ copies across directories, bugs fixed in one don't propagate, fix may not be applied everywhere

### H3 8.2 The Resolver Fix: Measurement Fix, Not Strategy Fix
#### H4 8.2.1 What the resolver fix did: eliminated infinite retry loop that was blocking winners from being recorded
#### H4 8.2.2 What it did NOT do: improve any strategy's actual performance. "Like fixing a broken speedometer."
#### H4 8.2.3 FOREX PF 0.27 was already losing money — the bug just hid it. Table: before fix vs after fix metrics (apparent vs true)

### H3 8.3 Evaluation Timeline Requirements
#### H4 8.3.1 Why 6 days is categorically insufficient: need 200-500 trades = 3-8 weeks at current velocity
#### H4 8.3.2 Table: Minimum evaluation timeline — Date | Days | Evaluation Level | Confidence
#### H4 8.3.3 Five new swarm engines deployed in same window = fundamental attribution problem
#### H4 8.3.4 Recommended observation dates: 2026-05-18 (14 days, gross directional), 2026-06-01 (30+ days, meaningful), 2026-08-01 (90+ days, institutional)

### H3 8.4 Orphaned Code Goldmines
#### H4 8.4.1 Table: Top 5 orphaned code candidates — File | Description | Estimated Impact | Integration Effort | Priority
#### H4 8.4.2 signal_quality_ml.py: could improve WR by 5-15 percentage points
#### H4 8.4.3 alpha_vs_beta_benchmark.py: enables proper benchmark comparison
#### H4 8.4.4 index_backup_v99.html features, meta_model_chatgpt.py, feature_flags.json: integration rationale

### H3 8.5 AI Agent Governance Framework
#### H4 8.5.1 Current state: AI agents commit without human review
#### H4 8.5.2 Required governance: pre-commit hooks, human review gates, testing requirements, rollback procedures
#### H4 8.5.3 Table: AI agent governance policy (Agent Type | Allowed Actions | Review Required | Testing Required)

**Required Elements:** Code quality metrics table, outcome_resolver duplication table, before/after fix metrics table, evaluation timeline table (3 dates), top 5 orphaned code table, AI governance policy table
**Maps to:** E21, E23, I15, I16, I17, C10, C11, C13

---

## H2 9.0 INSTITUTIONAL TRANSFORMATION ROADMAP (~1,800 words)

### H3 9.1 Gap Analysis: Where the Platform Stands
#### H4 9.1.1 Quantify: approximately 5% of institutional infrastructure required for quantitative trading
#### H4 9.1.2 Table: Infrastructure comparison — Component | Current State | Institutional Standard | Gap
#### H4 9.1.3 Key statistics: only 5% of strategies have n >= 200; 0% have PSR > 0.95; 0% have DSR > 0.95

### H3 9.2 What a Quant/Hedge Fund Manager Would Add
#### H4 9.2.1 Missing data sources: alternative data, on-chain analytics, sentiment feeds, institutional flow data
#### H4 9.2.2 Missing analytical frameworks: CPCV (Lopez de Prado 2018), PSR/DSR validation, multiple testing correction (Harvey & Liu 2014), bootstrap validation
#### H4 9.2.3 Missing risk management: daily loss limits, consecutive loss halts, volatility circuit breakers, correlation guards
#### H4 9.2.4 Missing validation: walk-forward with 20+ folds minimum, transaction cost modeling, benchmark comparison, overfitting prevention
#### H4 9.2.5 Table: Quant/Hedge Fund methodology additions — Category | Addition | Cost | Expected Impact | Priority

### H3 9.3 The 90-Day MVP Transformation
#### H4 9.3.1 Six non-negotiable hard gates: PSR > 0.95, DSR > 0.95, n >= 200, transaction costs modeled, single source of truth (outcome_resolver), correlation guard active
#### H4 9.3.2 Cost estimate: ~$1,500. ROI projection: 867%-5,233%
#### H4 9.3.3 Week-by-week plan: Weeks 1-2 Emergency fixes, Weeks 3-4 Infrastructure, Weeks 5-8 Golden Portfolio, Weeks 9-12 Institutional Readiness
#### H4 9.3.4 Go/No-Go decision framework at Week 12

### H3 9.4 The 12-Month Full Transformation
#### H4 9.4.1 Cost estimate: $32,400-$78,000
#### H4 9.4.2 Target: credible quantitative fund quality with $500K AUM, ROI 64%-1,400%
#### H4 9.4.3 Table: 12-month milestone roadmap — Quarter | Milestone | Deliverable | Success Criteria
#### H4 9.4.4 What Renaissance/Two Sigma/Citadel do differently: 99%+ signal rejection rate as sign of scientific discipline

### H3 9.5 The Binary Choice
#### H4 9.5.1 Option A: Stay retail-focused — maintain current Equity edge, narrow scope, 15-25% returns for disciplined users
#### H4 9.5.2 Option B: Commit to institutional MVP — 90-day/$1,500 transformation, broader asset class viability, institutional capital eligibility
#### H4 9.5.3 Table: Option comparison — Dimension | Retail Path | Institutional Path | Cost | Timeline | Outcome
#### H4 9.5.4 Recommendation: pursue 90-day MVP regardless; the status quo is already expensive (capital wasted on non-working strategies)

**Required Elements:** Infrastructure gap table (10+ components), quant methodology additions table (4 categories), 90-day week-by-week plan table, 12-month quarterly roadmap table, option comparison table
**Maps to:** E16, E22, I13, I16, C10, C11, C16

---

## H2 10.0 USER SAFETY AND INVESTMENT GUIDE (~1,500 words)

### H3 10.1 The 30-Second Decision Rule
#### H4 10.1.1 Table: Quick decision matrix — If you see this → Do this. Equity + ml_score >= 0.90 = GREAT IDEA; Crypto B-Tier L20 + R:R 1.5-2.0 = CAUTION; Commodity/Forex/C-Tier/Meme = CLOSE THE TAB
#### H4 10.1.2 Green flags: high-conviction equity pick with trust_score >=5, forward_wr 50-65%, R:R 1.5-2.0
#### H4 10.1.3 Red flags: any single red flag should prevent investment regardless of other metrics

### H3 10.2 What Is SAFE vs GREAT IDEA for Real Money
#### H4 10.2.1 SAFE: Equity picks with Verified Alpha + High Conviction + R:R 1.5-2.0, Quarter-Kelly position sizing, stop-loss at -5%
#### H4 10.2.2 GREAT IDEA: Equity Tier-2 strategies (signal_validation, mega_mutation) at full allocation, all gates green, within 48 hours of signal
#### H4 10.2.3 DO NOT INVEST list: 8 specific items (C-Tier Crypto, Commodity cta strategy, Forex overall, Meme coins, Penny stocks, Futures, Bond n<20, any untrusted filter pick)

### H3 10.3 Expected Returns by Discipline Level
#### H4 10.3.1 Table: Disciplined user (Equity only, strict filters, Quarter-Kelly) = 15-25% annually, 8-12% max DD
#### H4 10.3.2 Table: Moderate approach (Equity + Crypto B + ETF) = 12-20% annually, 12-18% max DD
#### H4 10.3.3 Table: YOLO approach (all asset classes, no filters, max sizing) = -20 to -40% annually, >30% max DD
#### H4 10.3.4 Signal alpha decay curve: Hours 0-48 = peak strength; Hours 48-120 = viable but degraded; Hours 120+ = edge approaching random. Best entry within 48 hours.

### H3 10.4 Practical Capital and Sizing Guide
#### H4 10.4.1 Minimum starting capital: $5,000 (below this, transaction costs eat the edge). Ideal: $25,000+
#### H4 10.4.2 Table: Position sizing by capital level — Capital | Max Position | Asset Classes | Expected Monthly Trades
#### H4 10.4.3 Kelly calculation worked example for $10,000 account with R:R 1.5-2.0 pick
#### H4 10.4.4 The honest answer: for most people, index funds (S&P 500 ~10%) are better than active trading

### H3 10.5 The "Worthy of Investing" Final List
#### H4 10.5.1 Table: Specific picks/strategies/asset classes meeting all criteria — Item | Allocation | Position Size | Stop Loss | Time Horizon | Confidence
#### H4 10.5.2 Table: "Worth the Risk" conditional items — Item | Conditions | Max Allocation | Validation Required
#### H4 10.5.3 Table: Explicit "DO NOT INVEST" list — Item | Why | What Would Change Verdict

### H3 10.6 Dashboard Enhancement Recommendations
#### H4 10.6.1 What explanatory content to add: score tooltips, tier definition cards, risk warnings, filter explanation panels
#### H4 10.6.2 Where to add it: above the filter bar, per-asset-class header, pick detail modal, footer safety disclaimer
#### H4 10.6.3 How to present complex metrics simply: use color coding (green/yellow/red), progressive disclosure, plain-language labels alongside technical terms

**Required Elements:** 30-second decision matrix table, SAFE/IDEA/DO-NOT table, 3 discipline-level return tables, position sizing table (4 capital tiers), Kelly worked example, Worthy of Investing table, Worth the Risk table, DO NOT INVEST table (8+ items), dashboard enhancement plan
**Maps to:** E7, E12, E13, E27, I1, I2, I3, I10, I12, I17

---

## H2 11.0 APPENDICES (~800 words reference material)

### H3 11.1 Appendix A: Complete Asset Class Statistics Table
#### H4 11.1.1 Full metrics table: all 9 asset classes with PF, WR, OOS Sharpe, n, PnL, trend direction, key strategies

### H3 11.2 Appendix B: Score Component Correlation Matrix
#### H4 11.2.1 Table: all score components with correlation to actual WR, current weight, proposed weight, monotonicity contribution

### H3 11.3 Appendix C: Strategy Decision Matrix
#### H4 11.3.1 Full table: all 11 failing strategies with diagnosis, action (invert/ban/fix/scale), priority, academic basis

### H3 11.4 Appendix D: Kill Switch Ladder
#### H4 11.4.1 Table: current kill switch ladder vs enhanced version with trigger levels, actions, and rationale

### H3 11.5 Appendix E: 90-Day Implementation Timeline
#### H4 11.5.1 Gantt-style week-by-week breakdown: Week 1 through Week 12 with deliverables and go/no-go criteria

### H3 11.6 Appendix F: Academic Source Index
#### H4 11.6.1 Categorized bibliography: 50+ sources organized by dimension (edge/scoring/backtesting/risk/penny/meme/infrastructure)

**Required Elements:** 6 appendix tables, 50+ academic citations
**Maps to:** D1-D18 from requirements document

---

## WORD COUNT SUMMARY

| Chapter | Words | % of Total | Primary Audience |
|---------|-------|-----------|------------------|
| 1.0 Executive Summary | 1,000 | 7.4% | All |
| 2.0 Asset Class Edge Verdict | 2,500 | 18.5% | Technical + Business |
| 3.0 Broken Scoring System | 1,800 | 13.3% | Technical |
| 4.0 UI/UX Audit | 1,500 | 11.1% | Technical + Retail |
| 5.0 Strategy Health | 2,000 | 14.8% | Technical |
| 6.0 Risk Management | 1,200 | 8.9% | Technical + Business |
| 7.0 Penny/Meme Analysis | 1,500 | 11.1% | Business + Retail |
| 8.0 Code Quality | 1,200 | 8.9% | Technical |
| 9.0 Transformation Roadmap | 1,800 | 13.3% | Business + Technical |
| 10.0 User Safety Guide | 1,500 | 11.1% | Retail + Business |
| 11.0 Appendices | 800 | 5.9% | Reference |
| **Contingency buffer** | **-700** | **-5.2%** | |
| **TOTAL** | **13,500** | **100%** | |

**Table count:** 45+ required tables
**Figure count:** 5+ recommended (score hierarchy diagram, signal decay curve, allocation pie chart, kill switch ladder diagram, transformation roadmap timeline)
**Academic citations:** 200+ unique sources

---

## REQUIREMENTS TRACEABILITY MATRIX

| Requirement ID | Chapter | H4 Location |
|---------------|---------|-------------|
| E1 Edge per asset class | Ch 2.0 | 2.2.1-2.5.4 |
| E2 Low PF/WR root cause | Ch 2.0, Ch 5.0 | 2.5.1-2.5.4, 5.2.1-5.2.4 |
| E3 Ideal UI path | Ch 4.0 | 4.2.1-4.2.4 |
| E4 Guide accuracy | Ch 4.0 | 4.4.1-4.4.3 |
| E5 Alternative tabs | Ch 4.0 | 4.5.1-4.5.3 |
| E6 HTML bug fix | Ch 4.0 | 4.6.1-4.6.5 |
| E7 Page enhancement | Ch 4.0, Ch 10.0 | 4.4.1-4.4.3, 10.6.1-10.6.3 |
| E8 F-Score vs Score | Ch 3.0 | 3.1.1-3.1.4 |
| E9 Composite scoring | Ch 3.0 | 3.1.3, 3.2.1-3.2.3 |
| E10 Swing plays | Ch 2.0 | 2.2.2, 2.4.2 |
| E11 Closed holds | Ch 2.0, Ch 4.0 | 2.2.2, 4.5.2 |
| E12 User safety guide | Ch 10.0 | All sections |
| E13 Dashboard filtering | Ch 3.0, Ch 4.0 | 3.4.1-3.4.4, 4.3.1-4.3.4 |
| E14 Trusted asset classes | Ch 2.0, Ch 10.0 | 2.7.1, 10.5.1-10.5.3 |
| E15 Deep per-class research | Ch 5.0 | 5.6.1-5.6.4 |
| E16 Backtesting review | Ch 9.0 | 9.2.2, 9.3.1 |
| E17 Broken asset classes | Ch 2.0 | 2.5.1-2.5.4 |
| E18 Penny stocks | Ch 7.0 | 7.1.1-7.2.3 |
| E19 Meme coins | Ch 7.0 | 7.3.1-7.4.3 |
| E20 Comprehensive per-class | Ch 2.0 | All sections |
| E21 Code change recency | Ch 8.0 | 8.3.1-8.3.4 |
| E22 Quant/Hedge Fund gap | Ch 9.0 | All sections |
| E23 GitHub code review | Ch 8.0 | 8.1.1-8.1.3 |
| E24 Frontend review | Ch 4.0 | All sections |
| E25 Filter combination testing | Ch 4.0 | 4.2.1-4.2.4 |
| E26 Guide edge reflection | Ch 4.0 | 4.4.1-4.4.3 |
| E27 Worthy of investing | Ch 10.0 | 10.5.1-10.5.3 |
