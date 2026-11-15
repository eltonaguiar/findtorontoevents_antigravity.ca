# Profitability Plan Deliverable — scratch-hippodraco
**Date:** 2026-11-15 (AM UTC)  
**Worktree:** scratch-hippodraco  
**Branch:** to be merged into `origin/main`  
**Status:** Plan + analysis only. No production code changes, no capital deployment.

---

## Folder contents

| Folder | Purpose |
|--------|---------|
| `01-asset-class-plans/` | Plan per asset class to reach profitability |
| `02-asset-class-analysis/` | Holding-period × trading-style analysis + proven/contest-winning algorithms |
| `03-subq-decision-support/` | How to use SubQ API keys (via dbpasses.txt) + fact-checking framework |
| `04-framework-answers/` | Answers to the framework questions (asset-class inventory, probability ranking, profitability framework, risk overlay) |
| `05-essential-questions/` | Further essential questions to find a profitable algorithm |
| `06-company-research/` | How financial prediction / risk-management firms went from struggling to trustworthy |
| `07-key-metrics/` | Key metrics that must be satisfied, from multiple professional perspectives |
| (root files) | `AI_AGENT_PROMPTS.md`, `PREDICTION_MARKET_COPY_TRADING.md`, `OUTPERFORM_SP500_BUY_AND_HOLD.md` |

---

## Root-level deliverables

| File | Purpose |
|------|---------|
| `README.md` | This index |
| `AI_AGENT_PROMPTS.md` | Prompts to give to AI coding agents in parallel worktrees (one asset class per agent) |
| `PREDICTION_MARKET_COPY_TRADING.md` | Why Kalshi/Polymarket copy trading still produces no winners |
| `OUTPERFORM_SP500_BUY_AND_HOLD.md` | The missing bar: any equity/ETF edge must beat SPY total return and buy & hold on clean OOS |

---

## Executive verdict (from the November 14 final plan)

> **No asset class is currently proven profitable.** The November 14, 2026 final plan is unambiguous: 0/23 hypotheses across 4 protocol versions survived clean out-of-sample, effective-N, capital, and execution gates. Information coefficient ≈ 0, win rates ≈ 40%, accuracy below target. All 9 classes return `sizing_allowed: false`. **Do not deploy capital yet.**

The highest-probability lower-risk path is **not** a prediction edge from this system — it is low-cost diversified index exposure (ETFs / mutual funds) plus disciplined risk rules, while the research continues under strict gates.

**Highest-priority research slot:** EQUITY (pre-registered SPY total-return benchmark test).

---

## How to use this folder

1. Read `07-key-metrics/KEY_METRICS.md` first — it defines the bar that must be cleared.
2. Read `OUTPERFORM_SP500_BUY_AND_HOLD.md` — any equity/ETF edge must beat SPY total return and buy & hold.
3. Read `PREDICTION_MARKET_COPY_TRADING.md` — why Kalshi/Polymarket copy trading still fails.
4. Read `AI_AGENT_PROMPTS.md` — if dispatching parallel worktree agents.
5. Read `01-asset-class-plans/PLAN_PER_ASSET_CLASS.md` for the per-class path.
6. Read `04-framework-answers/` for the full inventory, probability ranking, and 5-step framework.
7. Read `03-subq-decision-support/SUBQ_DECISION_SUPPORT.md` before calling any external LLM/decision API.
8. Only then consider any capital allocation — and only to low-cost index exposure, never to an unproven signal from this system.

---
