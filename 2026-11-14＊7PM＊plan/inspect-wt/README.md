# 2026-11-14 · 7PM · plan / inspect-wt — profitability plans, style analysis, agent prompts

**Folder-name note:** the requested pattern `<todaysdate>*<AMPM>*<plan>` is realized with
**fullwidth asterisks `＊` (U+FF0A)** — ASCII `*` is illegal in Windows filenames and a
literal `*` path in git would break every Windows checkout (git for Windows refuses to
materialize reserved names). The fullwidth form renders identically, is valid on
Windows/macOS/Linux, and is what you see on GitHub.

**Contents (7 asks of the request, answered):**

| # | Ask | Where |
|---|---|---|
| 1 | Plan per asset class to get profitability | `01_plan_per_asset_class/` — `_overview.md` (ranking, benchmark framing) + 7 class files (mutual_funds, etf, equity, crypto, commodity_futures, bond, forex) |
| 2 | Holding periods × trading styles + top proven/famous/contest algorithms ("Hoffman" etc.) | `02_style_and_holding_analysis/holding_periods_by_class.md`, `top_proven_algorithms.md` (evidence-ranked Tier 1/2/3; **Rob Hoffman identified**, TradingView contests = *programming* not trading, WCTC winners + their own non-repeatability admissions) |
| 2b | Leverage SubQ API key(s) + fact-check | `subq/` — `ask_subq.py` (Decisions API `POST /v1/systemone`, model `subq-snap-1.2` — the only API this key permits; chat needs unpermitted `subq-savant-1.4`), `subq_responses.json` (47 typed answers with probabilities), **`factcheck.md`** (GROUNDED/PARTIAL per answer) |
| 3 | Verify + answer the pasted Nov-14 "0/23, no class proven" analysis | `03_verified_answers/flaxen_hair_analysis_verified.md` — claim table, post-#773 corrections, **benchmark framing added (outperform SPY / B&H / 60/40 / class beta)**, MF conviction priced honestly |
| 4 | Prompts for the parallel AI coding agents | `04_agent_prompts/prompts_for_parallel_agents.md` — universal frame (PROMPT 0) + 7 class-specific paste-ready prompts with numeric gates baked in |
| 4b | Why Kalshi/Polymarket copy-trading still loses | `05_prediction_market_copytrading/why_copy_trading_fails.md` — 7 structural reasons, each labeled arithmetic vs probabilistic |
| 5 | Further essential questions | `06_essential_questions/essential_questions.md` — 26 falsifiable questions (edge/measurement/statistics/process/MF-track) |
| 5b | Companies: struggling → trusted with real money | `07_industry_case_studies/research_raw.md` — 10 sourced case studies (Kalshi, Kensho, SAC→Point72, Citadel, AQR, Kraken, IEX, Alpaca, Wealthfront, Two Sigma counter-case) + **5-pattern synthesis** (regulator on-ramp, third-party verification, transparent drawdown survival, model governance, time+audited reporting) |
| 6 | Key metrics by perspective (Sharpe etc.) | `08_key_metrics_by_perspective/key_metrics.md` — risk committee / fund manager / bank prop trader / pro investor / our gates / retail paper-trader |

**Standing ground rules applied throughout:** every profitability claim is
**benchmark-relative** (SPY B&H, 60/40, AGG+cash, or class beta — the correction the user
made to the Nov-14 analysis); probabilities are conditioned on stated events and shown
with SubQ's independent estimates where they diverge; failures are reported (our own
monthly DD-stop backtest failed and is labeled FAILED on the risk page); no fabricated
numbers — everything traceable to `subq_responses.json`, `research_raw.md` links, or
scripts in `final_v4/inspect-wt/03_risk_management/`.

**Companion packages:** `final_v4/inspect-wt/` (finalized plan, QA plan for PnL=0% +
blank-field validation, risk-management page with reproducible backtests — both subagent
review FAILs fixed and pushed), `final_v2/inspect-wt/`, `final_2026_11_14/inspect-wt/`.
