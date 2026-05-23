# Plan: World-Class Hedge Fund Quality Audit & Enhancement PR

## Date: 2026-05-02
## Objective: Transform findtorontoevents.ca/audit from failing to world-class with evidence-backed enhancements per asset class

---

## Context Summary

The findtorontoevents.ca/audit platform generates trading picks across 7 asset classes (Crypto, Equity, Forex, Commodity, Bond, ETF, Futures). Current state:

| Asset Class | Tier | Status |
|-------------|------|--------|
| Crypto S-Tier | T1 (PF 30.17, 85.7% WR) | EXCEPTIONAL but n=16 |
| Crypto A-Tier L50 | T2 (PF 1.58, 54% WR) | Degrading at L100 |
| Crypto B-Tier L20 | T1 (PF 2.71, 65% WR) | Best B-Tier window |
| Crypto C-Tier | FAIL (PF 0.36, 28% WR) | VALUE DESTROYER |
| Equities L100 | T1 (PF 2.90, 59% WR, +176.74%) | CROWN JEWEL |
| ETFs L20/L50 | T1 (PF 2.67-2.88, 70-72% WR) | RESURRECTED |
| Forex | FAIL (0-5% WR) | CATASTROPHIC but salvageable |
| Commodities | FAIL (PF 0.95, 14-35% WR) | WEAK |
| Bonds | T3 (PF 1.72, 50% WR) | PROMISING |
| Futures | Inconclusive (n=2) | NEED DATA |

Key issues: resolver bugs, over-restrictive filters, shadow-blocked alpha, missing data points, no statistical rigor, no decay tracking.

---

## Execution Stages

### Stage 1: Deep Research Swarm — Per-Asset-Class Analysis
**Skill:** deep-research-swarm (Route B: Focused Search)
**Agents (all parallel):**
- **Crypto_Analyst**: Deep dive on CRYPTO (S/A/B/C tiers), near-miss strategies, banned symbols review, confidence bands
- **Equity_ETF_Analyst**: Deep dive on EQUITY + ETF performance, scalability analysis, factor sleeves
- **Forex_Commodity_Analyst**: Deep dive on FOREX recovery path, COMMODITY investigation, root cause chain
- **Bond_Futures_Analyst**: Deep dive on BOND scaling, FUTURES data accumulation, new asset class expansion
- **Quant_Manager**: Review all strategies for hedge-fund quality, edge checklist, benchmark comparison
- **QA_Analyst**: Identify missing/invalid data points, audit TRK% vs FWD WR% discrepancy, pipeline integrity

**Output:** 6 research briefs with evidence-backed findings

### Stage 2: Strategy Near-Miss Analysis & Gate Review
**Agents (all parallel):**
- **Shadow_Picks_Analyzer**: Analyze shadow_blocked.json for killed alpha, quantify PnL left on table per gate
- **Gate_Optimizer**: Review all gates (QUALITY, RR, WINNER_FILTER) for optimal thresholds per asset class
- **New_Strategies_Researcher**: Research additional strategies for failing asset classes, meme coins, penny stocks, mutual funds

**Output:** Near-miss report, optimized gate thresholds, new strategy recommendations

### Stage 3: Report Writing — PR Enhancement Document
**Skill:** report-writing
**Agent:**
- **PR_Writer**: Synthesize all research into comprehensive PR enhancement markdown with evidence

**Output:** HEDGE_FUND_ENHANCEMENT_PR_2026_05_02.md

### Stage 4: Code Review & Implementation Suggestions
**Skill:** vibecoding-general-swarm
**Agent:**
- **Code_Reviewer**: Review current codebase, produce diff suggestions for key fixes

**Output:** Code review document with concrete implementation suggestions

---

## Deliverables
1. HEDGE_FUND_ENHANCEMENT_PR_2026_05_02.md — comprehensive PR document
2. per_asset_class_analysis.md — detailed per-asset-class findings
3. near_miss_analysis.md — shadow blocked + gate optimization
4. code_review_suggestions.md — concrete code changes
5. new_strategies_research.md — expansion strategies for failing classes
