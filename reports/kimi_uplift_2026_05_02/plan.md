# Plan: Hedge-Fund-Grade Audit Uplift for findtorontoevents.ca/audit

## Date: 2026-05-02
## Objective: Transform the failing audit dashboard into a world-class hedge fund signal platform

---

## Context Summary

The findtorontoevents.ca/audit platform predicts signals across Crypto, Equity, Forex, Commodity, Bond, ETF, and Futures asset classes. Current state:

| Asset Class | Current Tier | Blocker |
|-------------|-------------|---------|
| Crypto S-Tier | T1 (PF 30.17) | n=16 too small |
| Crypto C-Tier | FAIL (PF 0.36) | Unfiltered value destroyer |
| Equities L100 | T1 (PF 2.90) | None - SCALE IMMEDIATELY |
| ETFs L20/L50 | T1 (PF 2.67-2.88) | Was mislabeled DEAD |
| Forex | FAIL (0% WR) | Resolver bug + over-filters |
| Commodities | FAIL (PF 0.95) | No confidence gate applied |
| Bonds | T3 (PF 1.72) | n=20 insufficient |
| Futures | Inconclusive | n=2 |

## Key Issues Already Fixed (in uploaded files)
- outcome_resolver.py v2: asset-class thresholds, bar-replay, MAX_RESOLVE_RETRIES=3
- hc_filter.js: per-asset-class WR floors lowered (70%->55%/50%)
- hedge_fund_quality_gate.py: FOREX_BANNED_SYMBOLS cleared, confidence bands disabled

## Remaining Gaps
1. No statistical rigor module (bootstrap CIs, PSR, DSR, BH-FDR)
2. No HRP allocator for risk-parity position sizing
3. No decay tracker for rolling Sharpe monitoring
4. Missing new researcher personas (8 stubs)
5. No comprehensive METHODOLOGY documenting the path to world-class

---

## Execution Stages

### Stage 1 — Code Implementation + PR
**Skill:** vibecoding-general-swarm (Python module creation)
**Sub-agents:**
- Agent 1: Create new Python modules (statistical_rigor.py, hrp_allocator.py, decay_tracker.py) + 8 researcher persona stubs + updates doc
- Agent 2: Clone repo, create branch, commit changes, open PR via GitHub API using PAT

### Stage 2 — METHODOLOGY.md
**Skill:** general-writing (technical report)
**Sub-agents:**
- Agent 3: Write comprehensive METHODOLOGY.md covering all findings, approach, and roadmap

---

## Deliverables
1. GitHub PR with new modules and improvements
2. METHODOLOGY.md — comprehensive methodology document
