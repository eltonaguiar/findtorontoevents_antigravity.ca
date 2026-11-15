# Profitability Improvement Plan — Parallel Agent Worktree

**Date:** 2026-11-15 (AM)
**Branch:** main
**Purpose:** Find truly profitable, repeatable strategies per asset class OR identify the top 1-2 asset classes with winning strategies that can survive real-money paper trading and scale.

## Executive Summary

After reviewing 24 hours of local + remote commits, peer reviews (9 peers), backtest simulations, and the final_v3/final_v4 plans:

- **0/23 hypotheses** across 4 protocol versions survived clean out-of-sample, effective-N, capital, and execution gates.
- **Information coefficient ≈ 0.** Win rates near 40%. Accuracy below target.
- **All 9 asset classes return `sizing_allowed: false`.** Do NOT deploy capital yet.
- **Mutual funds:** Zero production infrastructure. Structurally incompatible as active picks (monthly NAV only, no intraday TP/SL), but valid as passive core allocation.
- **Bottom line:** The highest-probability lower-risk path is NOT alpha hunting — it's low-cost diversified ETF/MF allocation + disciplined risk rules, while research continues under strict gates.

## Folder Structure

| File | Purpose |
|------|---------|
| `01_asset_class_plans/plan_per_asset_class.md` | Per-asset-class profitability plan |
| `02_holding_period_analysis/holding_period_vs_style.md` | Holding periods vs trading styles + proven/contest-winning algorithms |
| `03_subq_decision_support/subq_fact_check.md` | SubQ API key usage + fact-checking framework |
| `04_essential_questions/essential_questions.md` | Essential questions to find a profitable algorithm |
| `05_prediction_market_copytrading/why_no_winners.md` | Why Kalshi/Polymarket + copy trading have not produced winners |
| `06_key_metrics/key_metrics_perspectives.md` | Key metrics from Sharpe / pro investor / MF manager / bank trader perspectives |
| `07_agent_prompts/agent_prompts.md` | Prompts for AI coding agents in parallel worktrees |
| `08_qa_validation/qa_protocol.md` | QA validation protocol (PnL=0%, blank fields, open/recently closed flags) |

## Immediate Go/No-Go Rule

**No real-money allocation until ≥1 asset class passes ALL gates:**
- Benchmark-relative net expectancy CI excluding zero
- DSR ≥ 0.95 (cumulative trial count)
- PBO ≤ 0.10
- SPA p ≤ 0.10
- Forward n ≥ 100 closed picks over ≥ 3 distinct months
- Cost-adjusted PF ≥ 1.15 (equity) or higher for other classes

Until then, the only money deployment vehicle is low-cost index ETF/MF allocation with risk overlays.
