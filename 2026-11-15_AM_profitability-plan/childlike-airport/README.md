# 2026-11-15 AM Profitability Plan — `childlike-airport`

**Date (UTC):** 2026-11-15 (AM window)  
**Worktree/author:** `childlike-airport` (Kilo)  
**Scope:** Per-asset-class profitability plan, holding-period/style and “proven/famous” algorithm analysis (fact-checked), current-state answers, essential questions, industry turnaround research, multi-perspective metrics, parallel-agent prompts, peer-plan review, **model-based backtest simulations**, and a **forward-test tracking protocol**. Evidence synthesis/reporting only — **no production changes, no capital deployment claim**.

## Bottom line
- **No asset class is currently proven reliably profitable/money-ready.** Repo verdicts show failing/insufficient gates (e.g. `money_ready_verdict.json` 2026-11-14: CRYPTO intrabar n=3705 WR 35.87% PF 0.9196 expectancy −0.0586 `NOT_READY`; EQUITY intrabar n=250 WR 59.2% PF 0.9392 with failing gates). Peer `final_v4/flaxen-hair_2026-11-14T2304/` synthesis (reported): 0/23 survived clean OOS/effective-N/capital/execution gates, IC≈0, sizing blocked. **Default `sizing_allowed=false`.**
- **Profitability must be benchmark-relative, net of all costs:** equity/ETF alpha vs **SPY/total-market buy-and-hold (total return)** risk-matched; cash hurdle **T-bills/SGOV-like**; allocations vs matched blend. Beating 0% is not enough.
- **Highest-probability lower-risk real-money path:** low-cost diversified passive ETF/MF allocation (beta/ballast) and/or disciplined TAA, measured net-of-fee vs proper benchmarks — not prediction alpha. Active/prediction sleeves remain unproven research under strict gates.
- **Kalshi/Polymarket copy-trading:** structurally disadvantaged (zero-sum minus fees, adverse selection/latency, bot/pro dominance, size/survivorship/settlement/copy-fidelity issues); treat as hypothesis only with timestamped, net, capacity-aware forward scorecards.

## Contents
| Folder | Purpose |
|---|---|
| `00_plan/` | Per-asset-class profitability plan (phased, gated) |
| `01_holding_periods_and_famous_algorithms/` | Holding periods/styles × asset class; “proven/famous”/contest algorithms (fact-checked) |
| `02_current_state_and_risk_reality/` | Current-state answers, thorough asset-class/surface inventory, outperformance & PM reality |
| `03_essential_questions/` | Essential questions to find/validate a profitable algorithm |
| `04_industry_turnarounds/` | How firms became trustworthy with real money (transferable controls) |
| `05_key_metrics_perspectives/` | Metrics/gates by perspective (quant, PM, MF manager, bank trader, risk/allocator) |
| `06_subq_and_factcheck/` | SubQ decision-support note and fact-check of claims/principles |
| `07_agent_prompts/` | Ready-to-use prompts for parallel worktree/machine agents |
| `08_review_grok_agent_pm_plan/` | Review of `2026-11-14_PM_plan/grok_agent` on main |
| `09_backtest_simulations/` | **Executed** model-based sims: plan, code, results (JSON/CSV/MD) — assumption-driven, not live proof |
| `10_forward_test_protocol/` | Easy forward-test tracking, fast-kill vs hold rules, and CSV tracker template |

## Backtest simulations (executed, model-based)
Ran `python3 09_backtest_simulations/run_simulations.py` (stdlib, seed `20261115`, 2000 paths, 10y, RF 3%). See `09_backtest_simulations/SIMULATION_PLAN_AND_RESULTS.md`.
- **Equity B&H proxy:** median CAGR 6.95%, Sharpe 0.34, MDD −29.45%, P(>0) 92.2%, P(beat cash) 78.7%.
- **60/40 balanced (monthly rebalance, 5bps):** median CAGR 5.99%, Sharpe 0.37, MDD −17.68%, P(>0) 97.45%, P(beat cash) 83.15% — lower drawdown/risk-managed profile.
- **Bonds defensive proxy:** median CAGR 3.76%, MDD −9.16%, P(>0) 98.8%.
- **Dual-momentum toy (regime-switching):** median MDD −18.15% vs B&H −42.30%, MDD improved in 99.7% of paths (model regimes).
- **Cost sensitivity:** 80 scenarios, 59 net-negative; marginal gross edges (PF≤1.1 / WR≤50%) often turn net-negative at 10–30bps RT — reinforces net-of-cost/benchmark gates.
- **Caveat:** simulations show plausible behavior under assumptions only; **not** proof of live profitability or validated alpha. Must confirm on trusted historical data and forward paper vs buy-and-hold benchmarks.

## Forward-test tracking (easy protocol)
See `10_forward_test_protocol/FORWARD_TEST_TRACKING_PROTOCOL.md` + `tracker_template.csv`.
- Time-boxed horizons (H0 sanity → H4 long-term), pre-registered strategy cards.
- **FAST KILL:** data/fill invalid, net expectancy≤0 or PF_net<1, benchmark lag, or risk breach at eligible checkpoint.
- **HOLD:** clean but insufficient sample/time for design horizon (with next review date).
- **PROMOTE (paper-scale candidate):** net positive, benchmark-competitive risk-adjusted, within cost/risk model for horizon — still not live-capital-ready until full gates pass.

## Key evidence anchors (repo)
- `audit_dashboard/data/money_ready_verdict.json`, `dashboard_data.json` (`performance.asset_class_health`), `summary_picks.json`
- `final_v4/flaxen-hair_2026-11-14T2304/`, `final_v4/*`, `final_v5/childlike-airport-20261114T230642Z/`
- `docs/ALL_STRATEGIES.md`, `docs/STRATEGY_PER_ASSET_CLASS_MASTERPLAN.md`, `docs/MONEY_READY_MASTER_LOOP_2026-06.md`, `.claude/skills/money-maker-ready*`
- Peer plan reviewed: `2026-11-14_PM_plan/grok_agent/*` (+ `STRUCTURED_AGENT_PROMPT.md`)
- Local probe: `/tmp/kilo/regime_filtered_vwap_v12_results.json` (n=129 PF 1.210 Sharpe 3.758 MDD 9.994% **PBO 0.489 fails strict <0.3** — research-only)

## Caveats
- Metrics cohort/window/definition-dependent; raw aggregates can be contaminated. All “edge” claims remain **unproven** until independently reproduced on canonical, net, benchmark-relative, forward data.
- SubQ: no verifiable completed live invocation/artifact in this session (credentials never exposed); SubQ-style support fact-checked against repo evidence and grounded principles (`06_subq_and_factcheck/`).
