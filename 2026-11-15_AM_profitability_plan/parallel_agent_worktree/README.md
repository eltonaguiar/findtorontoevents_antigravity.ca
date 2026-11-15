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
| `01_asset_class_plans/run_simulation_backtest.py` | Executable backtest simulation script (yfinance data, costs, walk-forward) |
| `01_asset_class_plans/simulation_results_2026-11-15.json` | Raw simulation results (37 combos, ~150 walk-forward folds) |
| `01_asset_class_plans/SIMULATION_RESULTS.md` | Human-readable simulation results summary |
| `08_qa_validation/FORWARD_TEST_TRACKING_PROTOCOL.md` | Forward-test tracking: fast elimination vs hold longer |

## Simulation Validation (executed 2026-11-15)

Ran `run_simulation_backtest.py` against live yfinance data (2020-01-01 → 2025-12-31), 7 equity ETFs + 5 crypto symbols, 5 strategies, 37 symbol×strategy combos, 4 bps round-trip cost, 5-fold walk-forward.

**Result: 0/37 combos passed all 7 money-ready gates.** Best performer (ADA-USD EMA Trend Crossover) passed 4/7 but failed Sharpe, DSR, PBO — confirming no statistically significant edge exists. DSR ≈ 0 and PBO ≈ 0.999 across nearly all combos.

This independently validates the plan's conclusion: **no asset class is currently proven profitable.**

## Cross-Reference: Parallel Simulation (Buffy/Codebuff)

A parallel agent ran a separate pre-registered backtest at `2026-11-15_1233AM_winning-strategies/buffy/10_simulations/` using different data (2004-2026 monthly + daily, real T-bill cash, 6bps equity / 15bps crypto costs, DSR, 2x cost stress, IS/OOS). **It reached the same conclusion:**

| Finding | My simulation (2020-2025) | Buffy backtest (2004-2026) |
|---------|---------------------------|---------------------------|
| Low-cost beta profitable after costs | N/A (not tested as beta core) | SUPPORTED (10.76% CAGR, DSR 0.99) |
| No active rule beats benchmark | 0/37 passed all gates | NO active rule beat matched-exposure |
| RSI(2) swing rule | Deeply negative (-118% to -186%) | REJECTED (0.21% CAGR, DSR 0.00) |
| Dual momentum | Not tested | REJECTED (-2.57%/yr) |
| BTC trend | Negative (-18% to -130%) | PROMISING but unproven (DSR 0.84) |
| Trend overlay reduces drawdown | N/A | SUPPORTED (-21.8% vs -50.8% MDD) |

Both simulations agree: **beta capture is the only proven path; no active rule has a statistically significant edge.** Buffy's forward protocol (`FORWARD_PROTOCOL.md`) adds a Stage 0 "kill in backtest" framework and FAST vs SLOW strategy handling that complements the forward-test tracking protocol in `08_qa_validation/FORWARD_TEST_TRACKING_PROTOCOL.md`.

## Immediate Go/No-Go Rule

**No real-money allocation until ≥1 asset class passes ALL gates:**
- Benchmark-relative net expectancy CI excluding zero
- DSR ≥ 0.95 (cumulative trial count)
- PBO ≤ 0.10
- SPA p ≤ 0.10
- Forward n ≥ 100 closed picks over ≥ 3 distinct months
- Cost-adjusted PF ≥ 1.15 (equity) or higher for other classes

Until then, the only money deployment vehicle is low-cost index ETF/MF allocation with risk overlays.
