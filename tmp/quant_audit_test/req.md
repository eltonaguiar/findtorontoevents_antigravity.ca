# Comprehensive Quantitative Trading Platform Audit — Extracted Requirements

---

## 1. EXPLICIT QUESTIONS / REQUESTS (27 items)

### E1. Edge Determination Per Asset Class
**Request:** Review predictions and logic from GitHub repository (https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/) and frontend (https://findtorontoevents.ca/audit) to determine if the platform has statistical edge per asset class, and if so, precisely where that edge exists.

### E2. Low PF/WR Root Cause Investigation
**Request:** For any item/asset class with low Profit Factor (PF) or low Win Rate (WR), or any item not producing top-notch picks, conduct deep investigation into why performance is poor. Identify root causes (data quality issues, gate misconfiguration, strategy flaws, tracking window problems, etc.).

### E3. Ideal UI Path for Best Picks
**Request:** Determine the optimal UI element for users to find the platform's best picks. Specifically compare and evaluate:
- The "high-conviction picks" button
- The "smart picks" tab items
- The "smart picks" button
- The "verified alpha" button
- All combinations of filters (score, source, strategy, high-grade, trusted, R:R 1.5+, safe symbols, all picks)
- All "recent" filters (Last 10, Last 20, Last 50, Last 100, etc.)

### E4. Guide Accuracy Verification
**Request:** Check the ?Guide page and verify whether it accurately reflects the edge profile per asset class. Determine if the guide documentation matches actual performance data.

### E5. Alternative Tab Analysis
**Request:** Check supplementary tabs including "US Equity Picks" and "Closed Picks" for additional insights beyond the main dashboard.

### E6. HTML Comment Bug Fix
**Request:** Investigate and fix a specific HTML rendering bug where broken comment text appears: `' inside this block — HTML does not support nested comments and the inner --> would close the outer. -->'`. Identify which tab contains this bug and provide a fix.

### E7. Page Enhancement for User Clarity
**Request:** Determine the best way to enhance the audit page to properly explain to end users what all the metrics, scores, and filters mean. The page needs better explanatory content.

### E8. F-Score vs Score Clarification
**Request:** Clarify the distinction between:
- F-Score (shown as 4/9)
- Score (shown as 0.748)
- Score (shown as 0.703)
Explain what each metric measures, how they are calculated, and why values differ.

### E9. Composite Scoring Confirmation
**Request:** Confirm whether "Score 0.748" referenced alongside wording about "Composite scoring" is indeed a composite score. Explain the composite methodology if so.

### E10. Swing Plays Analysis
**Request:** Go through swing plays (medium-term holds) and analyze their performance, edge, and suitability for real capital allocation.

### E11. Closed Holds Analysis
**Request:** Go through closed holds and analyze historical performance, lessons learned, and patterns in resolved positions.

### E12. User Safety Guide
**Request:** Provide users with a practical guide on what is actually "safe" to invest real money in — or better yet, what constitutes a GREAT IDEA for real capital deployment.

### E13. Dashboard Filtering Recommendation
**Request:** Recommend the specific filter configuration users should apply to the dashboard to find investable opportunities. Which combination of filters produces the highest-conviction, safest picks.

### E14. Trusted Asset Class Identification
**Request:** Identify which asset classes can be trusted with real capital (if any). Provide evidence-based trustworthiness rankings.

### E15. Deep Per-Asset-Class Strategy Research
**Request:** For asset classes that cannot be trusted, conduct deep research feeding in all available strategies to find:
- Parameter tweaks that could improve performance
- Top-performing strategies that lack recent picks (orphaned winners)
- Inverse strategies for failing approaches
- New data sources or methodologies to add

### E16. Backtesting Methodology Review
**Request:** Review current backtesting methodologies and determine if there is a superior approach that would produce consistent winners across all asset classes. Evaluate walk-forward analysis, purged cross-validation, transaction cost modeling, and benchmark comparison adequacy.

### E17. Broken Asset Class Identification
**Request:** Identify extremely broken or "messed up" asset classes — ones that other AI systems have recommended abandoning entirely. Document which asset classes are in this category and why.

### E18. Penny Stock Viability Analysis
**Request:** Investigate whether penny stocks offer genuine profit potential despite warnings from other systems. Specifically analyze the scenario where a small investor puts $100 into a penny stock and it doubles or triples. Assess how predictable this scenario is and whether small-capital investors can exploit this asymmetric opportunity.

### E19. Meme Coin Viability Analysis
**Request:** Similarly investigate meme coins for profit potential. Analyze whether predictable profit scenarios exist for small-capital investors in meme coin markets, despite extreme volatility risks.

### E20. Comprehensive Asset Class Performance Review
**Request:** For every asset class, analyze:
- Open picks (currently active positions)
- Closed picks (historically resolved positions)
- Short-term performance metrics
- Long-term performance metrics

### E21. Code Change Recency Assessment
**Request:** Determine whether recent code changes are too recent to properly evaluate. If so, acknowledge the evaluation limitation and recommend appropriate observation periods before drawing conclusions.

### E22. Quant/Hedge Fund Manager Methodology Gap Analysis
**Request:** Theoretically determine what additional data points, analytical frameworks, risk management protocols, and methodologies a professional Quant or Hedge Fund Manager would add to the project to identify truly "WORTHY OF INVESTING IN" and "WORTH THE RISK" opportunities.

### E23. GitHub Repository Code Review
**Request:** Review the codebase at the GitHub repository for logic quality, strategy implementation, data pipeline integrity, and potential bugs or issues.

### E24. Frontend Audit Dashboard Review
**Request:** Review the live frontend at findtorontoevents.ca/audit for UI/UX issues, data accuracy, filter functionality, and presentation quality.

### E25. Filter Combination Exhaustive Testing
**Request:** Test every combination of filters available on the dashboard including score thresholds, source filters, strategy filters, high-grade toggle, trusted toggle, R:R 1.5+ filter, safe symbols filter, all-picks view, and all recent filters (Last 10, Last 20, Last 50, Last 100, etc.).

### E26. Guide Page Edge Reflection Audit
**Request:** Cross-reference the ?Guide content against actual per-asset-class edge data to verify the guide does not mislead users about where edge exists.

### E27. "Worthy of Investing" Item Identification
**Request:** After all analysis, produce a definitive list of items (specific picks, strategies, asset classes, filter combinations) that are genuinely "WORTHY OF INVESTING IN" with real capital, and items that are "WORTH THE RISK" versus those that should be avoided.

---

## 2. IMPLICIT NEEDS (18 items)

### I1. Risk-Adjusted Return Framework
The user repeatedly references real money investment. The report must provide a risk-adjusted framework that goes beyond raw PF/WR to address drawdown, volatility, maximum loss scenarios, and capital preservation for retail investors.

### I2. Retail Investor Accessibility
The user asks about "$100 in a penny stock" — this reveals the target audience includes small-capital retail investors. The report must address position sizing, minimum capital requirements, and realistic expectations for non-institutional accounts.

### I3. Actionable Filter Presets
The user wants to know "how would you filter the dashboard" — this implies the report must produce specific, actionable filter presets (saved filter combinations) that users can directly apply, not just theoretical recommendations.

### I4. Strategy Parameter Optimization Playbook
The request to "find tweaks to their parameters" implies a need for a structured parameter optimization methodology — which parameters to tweak, in which direction, by how much, with backtest validation gates.

### I5. Inverse Strategy Construction Guide
The request to "look for inverse" for failing strategies implies a need for a methodology to construct inverse/reversal strategies from underperforming ones, including when inversion is appropriate vs. when the strategy should simply be abandoned.

### I6. HTML/Markup Quality Audit
The explicit mention of the HTML comment bug implies a broader need for frontend code quality review — the report should check for similar rendering issues across all tabs and components.

### I7. Documentation-Performance Alignment
The request to check if the Guide "properly reflects" edge implies a systematic need to audit all user-facing documentation against actual data, ensuring no documentation misleads users into poor decisions.

### I8. Score Explainability Framework
The confusion around F-Score vs Score vs Composite Score reveals that the platform uses multiple scoring systems without clear user-facing explanations. The report must propose a score explainability framework.

### I9. Tier Classification System Understanding
The dashboard shows S-Tier, A-Tier, B-Tier, C-Tier classifications. The report must explain what these tiers mean, how picks are assigned to tiers, and whether the tier system itself is producing edge or is just a descriptive label.

### I10. Kill-Switch and Risk Management Integration
The FOOLPROOF_ACTION_PLAN references kill-switches, position sizing, and risk management. The report must integrate these risk controls into all recommendations — no pick recommendation without corresponding risk management.

### I11. Diversification Guidance
The user asks which asset classes can be trusted and references "if any" — implying a need for cross-asset-class portfolio construction guidance, not just per-asset-class recommendations.

### I12. Time Horizon Suitability Mapping
References to "swing plays" and "closed holds" and "short-term, long-term" imply a need to map picks/strategies to appropriate investor time horizons and capital commitment periods.

### I13. Academic/Institutional Benchmarking
The request for what a "Quant or Hedge Fund Manager" would do implies the report should benchmark current methodologies against institutional standards (PSR, DSR, walk-forward OOS, transaction cost modeling, bootstrap validation).

### I14. Survivorship Bias Awareness
The FOOLPROOF_ACTION_PLAN notes that S-Tier crypto has n=14 and may be a "survivorship filter" — the report must explicitly address survivorship bias in all performance metrics.

### I15. Data Quality Assessment
Multiple references to "post-resolver-v2" and measurement artifacts in the action plan imply a critical need to assess data pipeline quality, resolution accuracy, and measurement methodology before trusting any metrics.

### I16. Soft vs Hard Gate Recommendation
The action plan describes "soft gate rollout" — the report must recommend whether gates should be enforced (hard) or advisory (soft) given current evidence quality.

### I17. Orphaned Code Value Assessment
The action plan identifies 16 orphaned code goldmines. The report should assess which of these (Signal Quality ML, Alpha/Beta benchmark, etc.) would most improve the user's ability to find worthy picks.

### I18. Mobile vs Desktop Experience
The UI/UX action plan mentions different presentations for mobile vs desktop — the report should consider how filter recommendations and pick discovery paths differ by device.

---

## 3. TARGET AUDIENCE

### Primary Audience
- **Platform operators / quantitative developers** (Elton and team) — responsible for strategy development, gate configuration, and code changes
- **Retail investors with small-to-medium capital** ($100-$50,000) — seeking actionable guidance on which dashboard filters to use and which picks are safe for real money

### Secondary Audience
- **Potential institutional partners or investors** evaluating the platform's rigor
- **Future quantitative researchers** joining the project who need context on current state

### Audience Implications
- Report must balance technical depth (for developers/quants) with actionable simplicity (for retail users)
- Must include both "what to fix in code" and "what buttons to click" recommendations
- Must address the "$100 investor" use case explicitly — realistic position sizing and risk assessment for small accounts
- Must be honest about limitations — the audience includes people making real financial decisions

---

## 4. SCOPE BOUNDARIES

### IN SCOPE
- All asset classes visible on dashboard: Crypto (S/A/B/C tiers), Equity/Stocks, Forex, Commodities, Futures, ETFs, Bonds
- Implied/separate asset classes: Meme Coins, Penny Stocks, Mutual Funds/CEFs
- All filter combinations and UI paths for pick discovery
- Frontend audit dashboard at findtorontoevents.ca/audit (all tabs, all sections)
- GitHub repository code review (logic, strategies, data pipelines, gates)
- Backtesting methodology assessment and recommendations
- Score/metric system clarification (F-Score, composite score, ml_score, etc.)
- Risk management framework (position sizing, Kelly criteria, kill-switches)
- User-facing documentation accuracy (?Guide and related help content)
- HTML/frontend bug identification and fixes
- Per-strategy performance analysis including orphaned/inverse strategies
- Retail investor guidance (filter presets, safety ratings, capital allocation)

### OUT OF SCOPE
- Actual code implementation/fixes (analysis and recommendations only)
- Direct financial advice or personalized investment recommendations
- Real-money trading or capital deployment
- Legal/regulatory compliance analysis
- Competitor platform comparisons
- Infrastructure/DevOps recommendations (except where directly affecting data quality)
- Marketing or growth strategy

### AMBIGUOUS — REQUIRES CLARIFICATION
- Whether "closed holds" refers to resolved positions in the "Closed Picks" tab or a specific hold-duration category
- Whether the user expects the report to include live testing of the frontend or screenshot-based analysis
- The exact timeframe for "recent picks" and "recent code changes" evaluation

---

## 5. REQUIRED DELIVERABLES

### D1. Edge Assessment Matrix
Per-asset-class determination of whether statistical edge exists, with evidence:
- Asset Class | Has Edge? | Evidence Strength | Key Metrics | Confidence Level
- Include all 9+ asset classes (Crypto S/A/B/C, Equity, ETF, Forex, Commodity, Bond, Futures, Meme, Penny)

### D2. Low Performer Root Cause Analysis
For each underperforming item/asset class:
- Specific diagnosis (data quality, gate issue, strategy issue, tracking window, sample size)
- Corrective action recommendation
- Priority level (P0 critical, P1 high, P2 medium)

### D3. UI Pick Discovery Recommendation
Definitive recommendation on the optimal UI path:
- Ranked comparison of all filter buttons/tabs (high-conviction, smart picks, verified alpha)
- Best filter combination per asset class
- Specific filter settings for different user profiles (conservative, moderate, aggressive)

### D4. Filter Combination Test Results
Results of testing all filter combinations:
- Filter Set | Pick Count | PF | WR | Notes
- Recommendation on which combinations to promote/hide/disable

### D5. Guide Accuracy Report
Cross-reference of ?Guide claims vs. actual data:
- Guide Claim | Actual Data | Discrepancy | Severity | Recommended Fix

### D6. HTML Bug Fix
- Location of bug (which tab/component)
- Root cause explanation
- Corrected HTML/markup
- Verification steps

### D7. F-Score vs Score Explanation Document
Clear explanation of:
- What F-Score (4/9) measures — Piotroski F-Score methodology, 9 criteria breakdown
- What Score (0.748, 0.703) measures — likely ml_score or composite
- How composite scoring works if applicable
- Which score users should prioritize for pick selection
- Visual diagram or table showing score hierarchy

### D8. User Safety & Investment Guide
Practical guide for retail investors:
- What is "safe" vs. "GREAT IDEA" for real money
- Recommended capital allocation per asset class
- Specific filter presets for conservative/moderate/aggressive profiles
- Position sizing recommendations (Kelly-derived, retail-appropriate)
- Red flags that should prevent any investment
- Green flags indicating high-conviction opportunities

### D9. Trusted Asset Class Ranking
Evidence-based trustworthiness ranking:
- Asset Class | Trust Level (A-F) | Evidence | Min Capital | Max Allocation | Conditions

### D10. Strategy Optimization Playbook
For failing or borderline asset classes:
- Current strategy diagnosis
- Parameter tweak recommendations with expected impact
- Orphaned winning strategies to reactivate
- Inverse strategy candidates
- New strategies to research with academic backing

### D11. Backtesting Methodology Assessment
Evaluation of current backtesting vs. best practices:
- Current Method | Gap | Recommended Fix | Priority
- Must cover: walk-forward OOS, transaction costs, PSR/DSR, bootstrap, benchmark comparison, overfitting prevention

### D12. Penny Stock Viability Report
Specific analysis of penny stock profit potential:
- Historical $100 investment scenarios
- Predictability assessment
- Risk/reward profile for small-capital investors
- Realistic win rate and payoff expectations
- Recommendation: viable or not for retail investors

### D13. Meme Coin Viability Report
Parallel analysis for meme coins:
- Historical profit scenarios for small investments
- Predictability of pump/dump cycles
- Social sentiment overlay value
- Risk profile and survivorship considerations
- Recommendation: viable or not for retail investors

### D14. Comprehensive Per-Asset Performance Report
For each asset class:
- Open picks analysis (active positions)
- Closed picks analysis (resolved positions)
- Short-term performance (Last 10, 20, 50)
- Long-term performance (Last 100+)
- Trend direction (improving, stable, decaying)
- Key strategies driving performance

### D15. Code Change Recency Assessment
- Timeline of recent code changes
- Which changes are too new to evaluate
- Recommended observation periods before drawing conclusions
- Interim recommendations for affected asset classes

### D16. Quant/Hedge Fund Gap Analysis
Theoretical analysis of institutional-grade improvements:
- Missing data sources
- Missing analytical frameworks
- Missing risk management protocols
- Missing validation methodologies
- Prioritized integration roadmap

### D17. Page Enhancement Recommendations
Specific recommendations for improving the audit page:
- What explanatory content to add
- Where to add it
- How to present complex metrics simply
- Example: score explainability tooltips, tier definition cards, risk warnings

### D18. "Worthy of Investing" Final List
Definitive output:
- Specific picks/strategies/asset classes that meet all criteria for real capital
- Filter configuration to find them
- Position sizing per opportunity
- Risk management rules per opportunity
- Explicit "DO NOT INVEST" list for dangerous items

---

## 6. CRITICAL ISSUES THAT MUST BE ADDRESSED

### C1. R:R Gate Misconfiguration — HIGHEST PRIORITY
**Evidence:** Independent verification found the 1.5-2.0 R:R band has PF 5.81 (excellent), but >2.0 band has PF 0.35 (catastrophic). A previous recommendation to lower floor to 1.25 was WRONG — that band has PF 1.01, Kelly -1.6% (unprofitable).
**Action Required:** Confirm R:R gate is set to floor 1.5, ceiling 2.0. If not, this is the single highest-impact fix.

### C2. ml_score Threshold Set Too Low
**Evidence:** ml_score 0.8-0.9 band has 39.3% accuracy (worse than coin flip). Only ml_score >= 0.90 has 66.7% accuracy.
**Action Required:** Verify current ml_score threshold. If below 0.90, raises are immediately needed.

### C3. 24-Hour Tracking Window Bias
**Evidence:** 72.7% of picks are still open at 24 hours. The "killed alpha" analysis was systematically biased by the 24h window. Only 27.3% hit TP or SL within 24h.
**Action Required:** Tracking must be extended to 120h minimum before any performance conclusions are valid.

### C4. Measurement Artifacts Distorting True Performance
**Evidence:** Forex had "0% WR" that was actually a measurement artifact (p=9.1x10^-37) caused by an infinite retry loop blocking winners. True WR from trusted filter is 48.7% with PF 3.59.
**Action Required:** Audit all asset classes for similar measurement artifacts. Any WR near 0% or 100% should be flagged for investigation.

### C5. CRYPTO C-Tier Value Destruction
**Evidence:** C-Tier has PF 0.36, WR 28%, 68.5% of trades are losers. Only tier with negative expectancy.
**Action Required:** Either suspend (with 5% allocation cap and paper trade only) or use as contrarian indicator. Must not be presented to users as viable picks.

### C6. Commodity Strategy Complete Failure
**Evidence:** cta_commodity_momentum_term has PF 0.02. 58% flat exits at L100 = strategy finding no real setups.
**Action Required:** Ban this strategy permanently. Deploy triple-screen replacement before any commodity picks go live.

### C7. Meme Coin Asset Class Misclassification
**Evidence:** Meme coins (DOGE/SHIB/PEPE) are classified under CRYPTO but have fundamentally different risk profiles — WR 65.6% but avg PnL -12.96% (small wins, catastrophic losses).
**Action Required:** Create MEME as distinct asset class with separate gating, separate position limits, hard 5% portfolio cap, spread-adjusted R:R.

### C8. Mutual Fund Incompatibility
**Evidence:** Mutual funds are fundamentally incompatible with intraday TP/SL strategies — NAV prices once daily at 4pm, shorting impossible, early redemption fees 30-90 days.
**Action Required:** Exclude mutual funds from intraday strategies entirely. CEFs can remain as separate asset class with monthly rebalancing.

### C9. Penny Stock Spread Destruction
**Evidence:** Penny stocks have avg spread ~0.50% round-trip. A $100 position with 2% spread loses 2% immediately. Doubling requires 100%+ gain net of spreads.
**Action Required:** Any penny stock recommendation must include spread-adjusted R:R. Position cap of 2% per pick, 5% max total allocation.

### C10. Orphaned Code Not Deployed
**Evidence:** 16 orphaned code goldmines found representing 200+ hours of dormant development. Signal Quality ML Predictor alone could improve WR by 5-15pp.
**Action Required:** Immediate integration of top 5 candidates: signal_quality_ml.py, alpha_vs_beta_benchmark.py, index_backup_v99.html features, meta_model_chatgpt.py, feature_flags.json.

### C11. Outcome Resolver Duplication Bug
**Evidence:** 5+ copies of outcome_resolver.py across directories. Bugs fixed in one don't propagate.
**Action Required:** Consolidate to single source of truth at alpha_engine/outcome_resolver.py. Delete duplicates.

### C12. Score System Confusion
**Evidence:** User explicitly confused about F-Score (4/9) vs Score (0.748) vs Score (0.703) vs "Composite scoring." Multiple overlapping score systems without clear documentation.
**Action Required:** Create single, documented scoring hierarchy. Add explainability tooltips to dashboard. Clarify which score to use for which decision.

### C13. S-Tier Survivorship Bias
**Evidence:** Crypto S-Tier has PF 30.17, WR 85.7% but n=14. This is a survivorship filter (picks that already passed all gates), not a reproducible strategy.
**Action Required:** Do not present S-Tier as a standalone strategy. Clarify to users that these are post-filtered picks requiring upstream edge generation.

### C14. Equity SHORT Ban Non-Compliance
**Evidence:** Academic studies (MDPI 2026) show short momentum Sharpe -0.35 to -1.54 universally. Short strategies are value-destructive.
**Action Required:** Verify short ban is enforced across all strategies. Conditional reintroduction only in systematic bear regime.

### C15. AAPL Symbol Ban Exception
**Evidence:** AAPL remains banned for all strategies except markov_zone_transition with score >= 55.
**Action Required:** Verify this exception is properly implemented and documented. Any AAPL pick must show the specific strategy that generated it.

### C16. Walk-Forward OOS Decay
**Evidence:** Walk-forward OOS metrics show CRYPTO Sharpe -0.242, COMMODITY Sharpe -2.412, FOREX Sharpe -1.406. Only EQUITY (3.527) and ETF (6.368) show positive OOS Sharpe.
**Action Required:** Asset classes with negative OOS Sharpe must not be recommended for live capital until walk-forward performance improves.

### C17. UI Tab Overload
**Evidence:** Dashboard has Overview, Dashboards, Score Tracker, ML Health, Links, US Equity Picks, Closed Picks, and more. Action plan recommends reduction from 13 tabs to 5.
**Action Required:** Identify which tabs are misleading, redundant, or presenting outdated data. Recommend tab consolidation.

### C18. HTML Nested Comment Bug
**Evidence:** Specific broken comment text visible to users: `' inside this block — HTML does not support nested comments and the inner --> would close the outer. -->'`
**Action Required:** Fix immediately. Audit all templates for similar nested comment issues.

---

## 7. CONTEXT FROM UPLOADED DOCUMENTS

### 7.1 FOOLPROOF_ACTION_PLAN.docx Key Data Points
- **Date:** 2026-05-02, Version 2.1
- **Deployed Agents:** 6+ specialized (crypto strategist, equity PM, forex strategist, bond/futures analyst, CIO quant manager, QA auditor, independent quant reviewer, UI auditor, code archaeologist, API researcher)
- **Original PR Material Errors Corrected:** R:R floor (keep 1.5, add ceiling 2.0), ml_score (use >= 0.90 not 0.82), tracking (120h not 24h), C-Tier (5% allocation not suspend), WINNER_FILTER (A/B test not abolish)
- **Golden Finding:** 1.5-2.0 R:R band has ALL alpha: PF 5.81, Kelly +47.2%, avg PnL +4.98%
- **Catastrophic Finding:** >2.0 R:R band: PF 0.35, avg loss -17.88%
- **Orphaned Code:** 16 goldmines, 200+ hours dormant
- **12-Week Timeline:** Emergency fixes (W1-2), Infrastructure (W3-4), Golden Portfolio (W5-8), Institutional Readiness (W9-12)
- **Go/No-Go Decision:** Week 12

### 7.2 Dashboard Screenshot (image.png) — Crypto/Non-Crypto Performance
**Crypto Panel:**
- S-Tier: 70.4% WR, 6 active, 27 closed, 19 W / 8 L / 0 unresolved, PF 6.80, +92.91% realized, +0.00% unrealized, Overall PnL +92.91%
- A-Tier: 42.4% WR, 4 active, 304 closed, 129 W / 175 L / 0 unresolved, PF 1.58, +95.23% realized, +0.00% unrealized, Overall PnL +95.23%
- B-Tier: 45.0% WR, 2 active, 940 closed, 425 W / 514 L / 3 unresolved, PF 1.28, +147.56% realized, +0.00% unrealized, Overall PnL +147.56%
- C-Tier: 28.1% WR, 0 active, 224 closed, 63 W / 161 L / 0 unresolved, PF 0.56, -123.53% realized, -0.55% unrealized, Overall PnL -123.53%
- Aggregate: 42.5% WR, +212.16% PnL, 12 active, 1492 closed

**Non-Crypto Panel:**
- Equities & Stocks: 53.1% WR, 4 active, 256 closed, 136 W / 105 L / 15 unresolved, PF 1.72, +233.48% realized, +0.01% unrealized, Overall PnL +233.48%
- Forex: 21.4% WR, 2 active, 912 closed, 195 W / 232 L / 485 unresolved, PF 1.41, -23.15% realized, +0.03% unrealized, Overall PnL -23.15%
- Commodities: 21.2% WR, 0 active, 675 closed, 143 W / 187 L / 345 unresolved, PF 1.04, +5.72% realized, +0.00% unrealized, Overall PnL +5.72%
- Futures: 0.0% WR, 0 active, 2 closed, 0 W / 0 L / 2 unresolved, PF 0.00, +0.00% realized, +0.00% unrealized, Overall PnL +0.00%
- ETFs: 52.9% WR, 0 active, 85 closed, 45 W / 37 L / 3 unresolved, PF 1.32, -20.58% realized, +0.00% unrealized, Overall PnL -20.58%
- Bonds: 50.0% WR, 0 active, 20 closed, 10 W / 8 L / 2 unresolved, PF 1.72, -3.41% realized, +0.00% unrealized, Overall PnL -3.41%
- Aggregate: 27.2% WR, -264.43% PnL, 6 active, 1950 closed

### 7.3 Dashboard Screenshot (image(1).png) — Major Goal / Walk-Forward OOS / Tier-2
**Major Goal Status:**
- EQUITY: T2 candidate (PF 1.41, WR 52.7%, n=421) — Scale
- CRYPTO: PF 1.25, WR 44.6%, n=8067 (clean) — Sub-T2, cut quan_engine drag
- ETF: PF 1.24, WR 55.2%, n=87 — Borderline T3, n→100
- COMMODITY: PF 1.78, WR 46.9%, n=750 (post-resolver-v2) — Meets T2 PF, lift WR
- FOREX: PF 0.27, WR 46.4%, n=1169 (post-resolver-v2) — Sub-floor, investigate-before-kill
- BOND: PF 1.72, WR 55.6%, n=18 — Meets T2 thresholds, n<100 charter floor

**Tier Definitions:** T1 PF>2/WR>55/MDD<10 (Renaissance), T2 PF>1.5/WR>50/MDD<20 (Institutional), T3 PF>1.2/WR>48/MDD<30 (Retail-OK)

**Walk-Forward OOS Metrics:**
- COMMODITY: 130 folds, OOS WR 43.2%, OOS Sharpe -2.412, Decay 0.2, Consistency 36.2%, Worst-fold WR 0.0%
- CRYPTO: 302 folds, OOS WR 43.0%, OOS Sharpe -0.242, Decay 0.1, Consistency 57.3%, Worst-fold WR 0.0%
- EQUITY: 47 folds, OOS WR 57.9%, OOS Sharpe 3.527, Decay 0.2, Consistency 66.0%, Worst-fold WR 20.0%
- ETF: 12 folds, OOS WR 61.7%, OOS Sharpe 6.368, Decay 10.8, Consistency 66.7%, Worst-fold WR 20.0%
- FOREX: 177 folds, OOS WR 47.5%, OOS Sharpe -1.406, Decay 0.1, Consistency 57.6%, Worst-fold WR 0.0%

**Tier-2 Proven Strategies:**
- signal_validation: WR 63.0%, PF 2.58, MDD 12.0%, n=184 (THIN), 90d cum +183.2%, Tier 2 badge
- mega_mutation: WR 67.9%, PF 3.19, MDD 36.0%, n=78 (THIN), 90d cum +181.6%, Building badge
- rl_agent: WR 60.0%, PF 2.54, MDD 2.1%, n=5 (THIN), 90d cum +6.4%, Building badge
- claude_gainer: WR 56.2%, PF 2.23, MDD 33.5%, n=32 (THIN), 90d cum +80.2%, Building badge

---

## 8. EVIDENCE SOURCES FOR REPORT

1. **GitHub Repository:** https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/ — strategy code, logic, data pipelines
2. **Frontend Audit Dashboard:** https://findtorontoevents.ca/audit — live UI, filters, performance data
3. **FOOLPROOF_ACTION_PLAN.docx** — 8,500-word internal analysis with per-asset-class breakdowns, corrected gate recommendations, UI plan, 12-week timeline
4. **Dashboard Screenshots (2)** — visual evidence of crypto/non-crypto panels, major goal status, walk-forward OOS metrics, tier-2 strategies
5. **Referenced Internal Data:** shadow tracking data (n=253), post-resolver-v2 metrics, walk-forward by class output, asset_class_health data, strategy tier badges

---

*Requirements extracted from user query + 3 uploaded files.*
*27 explicit requests, 18 implicit needs, 18 critical issues identified.*
*18 required deliverables defined.*
