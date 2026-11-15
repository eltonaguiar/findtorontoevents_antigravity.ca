# PRE_PROMPT.md

**Worktree:** flaxen-hair_2026-11-15T0741_flaxen-hair  
**Date:** 2026-11-15T07:41 UTC  
**Repo:** findtorontoevents_antigravity.ca

---

## Original Prompt (from Kilo Agent System Instructions)

"You are Kilo, a highly skilled software engineer with extensive knowledge in many programming languages, frameworks, design patterns, and best practices."

**Goal:** Accomplish the user's task, NOT engage in back and forth conversation.

**Core Task:** Review AI machine learning algorithms for various asset classes (stocks, bonds, ETFs, mutual funds, forex, crypto) and database of stats per asset class. Look for errors like stale data, propose fixes, and have a summary with datetime + worktree name (.MD).

**Also:** Check dbpasses.txt and check databases themselves for stale data, any findings.

Cross-reference recent active picks and recently closed picks per asset class for PnL accuracy, spot check every single column for accuracy, staleness, calculation errors, etc.

---

## Source Documents Reviewed (All from WIRED_IN/ on origin/main)

The following documents were reviewed as prior work by prior agents (Task children of the main session):

### WIRED_IN/2026-11-15T0234_flaxen-hair/ (flaxen-hair Agent Manager worktree)

| File | Content |
|------|---------|
| `01_asset_class_plans/AUDIT_REPORT.md` | Full audit report: 0/23 hypotheses proven profitable across 4 protocol versions |
| `01_asset_class_plans/ASSET_CLASS_PROFITABILITY_PLANS.md` | Per-asset-class profitability plans ranked by probability |
| `01_asset_class_plans/EQUITY_PLAN.md` | Equity-specific plan: connors_rsi2 scanner, vix_spike_reversal, only class with positive cost margin (3.23×, mean +0.323%, n=738) |
| `01_asset_class_plans/PHASE1_FILE_LIST.md` | Priority-ordered file list for sub-agents (TIER 1-5) |
| `01_asset_class_plans/SINGLE_AGENT_PROMPT.md` | Single-agent prompt for quant research contractor |
| `01_asset_class_plans/STRATEGY_SHORTLIST.md` | Ranked candidate strategies with PnL, WR, PF, Sharpe, n counts and per-asset-class verdicts |
| `02_holding_period_analysis/BACKTEST_AND_TRACKING_PROTOCOL.md` | Forward-test protocol: kill fast (Tier 1), hold longer (Tier 2), promote to paper trading (Tier 3), live capital (Tier 4) |
| `02_holding_period_analysis/FORWARD_TEST_EXECUTION_PLAN.md` | Forward-test execution plan |
| `02_holding_period_analysis/HOLDING_PERIODS_AND_STYLES.md` | Per-class analysis by holding period vs trading style (scalping/day/swing/position/long-term) |
| `02_holding_period_analysis/backtest_results.json` | 42 strategy-symbol combinations tested, 0 passed P0 gates |
| `02_holding_period_analysis/forward_test_pick_generator.py` | Forward-test pick generator with QA gates |
| `03_proven_algorithms/PROVEN_ALGORITHMS.md` | Top algorithms from TradingView contests — verified: NONE profitable |
| `04_subq_decision_support/AGENT_PROMPTS.md` | Compressed single-agent prompt for parallel worktrees |
| `04_subq_decision_support/PREDICTION_MARKETS_WHY_NO_WINNERS.md` | Why Kalshi/Polymarket copy trading fails: zero-sum, bot/adverse-selection dominance, fees, size mismatch |
| `04_subq_decision_support/SUBQ_DECISION_SUPPORT.md` | SubQ API key usage and fact-checking protocol |
| `04_subq_decision_support/SUBQ_USAGE_GUIDE.md` | How to use SubQ for fact-checking |
| `05_framework_answers/EXTENSION_TO_PRIOR_ANALYSIS.md` | Extends prior analysis with explicit per-asset-class recommendations |
| `05_framework_answers/FRAMEWORK_ANSWERS.md` | Answers to all 6 detailed framework questions |
| `06_essential_questions/ESSENTIAL_QUESTIONS.md` | Essential questions for finding profitable algorithms |
| `07_company_turnarounds/HOW_FIRMS_BECAME_TRUSTWORTHY.md` | Case studies: Renaissance Technologies, Two Sigma, AQR, Bridgewater, Citadel |
| `07_company_turnarounds/TURNAROUNDS.md` | Common patterns across successful firms: data engineering > model complexity, out-of-sample testing, risk budgeting, separate research from production, diversification, transparency about failures |
| `08_key_metrics/KEY_METRICS.md` | Key metrics from multiple perspectives (scurry trader, mutual fund manager, bank trader, risk manager) |
| `08_key_metrics/KEY_METRICS_MULTI_PERSPECTIVE.md` | Sharpe/PF/WR from trader, mutual fund manager, bank trader, risk manager perspectives |
| `README.md` | Package overview — bottom line: NO asset class proven profitable, ETF TAA only risk-adjusted validated approach |

### WIRED_IN/2026-11-15T0125/flaxen-hair/ (Prior worktree session)

| File | Content |
|------|---------|
| `01_specification/ASSET_CLASS_SPECIFICATIONS.md` | Per-asset-class specifications |
| `01_specification/mutual_funds_asset_class.md` | Mutual funds: zero coverage, not a prediction class |
| `01_specification/other_asset_classes.md` | Forex, commodity, bond, futures analysis |
| `02_justification/AUDIT_REPORT.md` | Full audit report with per-asset-class results table |
| `02_justification/SINGLE_AGENT_PROMPT.md` | Compressed single-agent prompt |

### WIRED_IN/2026-11-15T0130Z_scratch-hippodraco/ (Scratch-hippodraco worktree)

| File | Content |
|------|---------|
| `elimination/eliminated_asset_classes.md` | Eliminated asset classes with reasoning |
| `picks/pick_justification.md` | Pick justifications |
| `research/backtesting_methodology.md` | Backtesting methodology |
| `spec/asset_class_spec_BOND.md` | Bond asset class spec |
| `spec/asset_class_spec_COMMODITY_FUTURES.md` | Commodity futures spec |
| `spec/asset_class_spec_CRYPTO.md` | Crypto spec |
| `spec/asset_class_spec_EQUITY.md` | Equity spec |
| `spec/asset_class_spec_ETF.md` | ETF spec |
| `spec/asset_class_spec_FOREX.md` | Forex spec |
| `spec/asset_class_spec_MUTUAL_FUNDS.md` | Mutual funds spec |

### WIRED_IN/2026-11-15T0150Z_childlike-airport/ (childlike-airport worktree)

| File | Content |
|------|---------|
| `ALGORITHM_SPEC.md` | Algorithm specification |
| `ELIMINATION.md` | Elimination rationale |
| `PARTICLE_1_FREE_429.md` | Particle_1_free_429 analysis |
| `PICK_JUSTIFICATION.md` | Pick justification |
| `README.md` | Folder overview |
| `RESEARCH_AND_BACKTEST.md` | Research and backtesting methodology |
| `picks/active_picks.json` | Active picks data |
| `picks/closed_picks.json` | Closed picks data |

### WIRED_IN/2026-11-15T065338Z_hilarious-seer/ (hilarious-seer worktree)

| File | Content |
|------|---------|
| `AUDIT_REPORT_TEMPLATE.md` | Audit report template |
| `CRYPTO_AUDIT.md` | Crypto audit report |
| `ETF_MF_AUDIT.md` | ETF/MF audit |
| `NEGATIVE_RESULT_DIAGNOSIS_TEMPLATE.md` | Negative result diagnosis template |
| `PENNY_STOCK_AUDIT.md` | Penny stock audit |
| `PRE_PROMPT.MD` | Pre-prompt template |
| `PROOF_STANDARD_METRICS.md` | Proof standard metrics |
| `QUANT_AUDIT_PROMPT.md` | Quant audit prompt |
| `README.md` | Folder overview |
| `REPO_INVENTORY_HEADSTART.md` | Repo inventory head start |
| `STRATEGY_SHORTLIST_TEMPLATE.md` | Strategy shortlist template |

### WIRED_IN/2026-11-15T0700Z_finpredict-summary/ (finpredict-summary worktree)

| File | Content |
|------|---------|
| `PROFIT_MARKET_SUMMARY.md` | Profit market summary |
| `SINGLE_AGENT_PROMPT.md` | Single-agent prompt |
| `STRATEGY_SHORTLIST.md` | Strategy shortlist |
| `harvested_ideas/00_inventory.csv` | Raw inventory CSV |
| `harvested_ideas/01_failures_taxonomy.md` | Failures taxonomy |
| `harvested_ideas/02_methods_catalogue.md` | Methods catalogue |

---

## PROMPT (The actual task)

Given all the above context, your task is to:

1. **Review all financial prediction updates from the past 24-48 hours** — both local worktree files and remote GitHub changes.

2. **Review the WIRED_IN folder structure on remote main** — All prior agent worktrees under `WIRED_IN/` to understand what has already been done.

3. **Create your own folder** under `WIRED_IN/final_v001/<datetime>_<worktreename>` — i.e., `WIRED_IN/final_v001/2026-11-15T0741_flaxen-hair/`

4. **Review everything saved in prior worktrees** — including but not limited to:
   - `ALL_STRATEGIES.MD` (comprehensive strategy inventory)
   - `BABY_STRATEGIES.MD` (baby strategy implementations)
   - Any other `.MD` files you find relevant

5. **Devise your finalized strategy** — To find and prove a statistically valid, profitable trading approach per asset class, that will feed into the `findtorontoevents.ca/audit` dashboard (active picks, recently closed picks).

**Key findings from prior audits that you MUST incorporate:**

- **dbpasses.txt** is located at `/home/eaguiar2015/dbpasses.txt` (outside the repo, contains live keys — do not read/expose contents)
- **PnL calculation bug:** `pnl_pct` stored inconsistently — some rows as ratio (e.g., -0.04), some as percent (e.g., -3.64 meaning -3.64%). Same symbol/strategy rows differ up to 100×.
- **Stale data:** `recent_picks.txt` dated 2026-03-11 claims "Past 2 Hours" (8 months stale). `multi_asset_closed.json` (2026-03-11→13). `institutional_picks.json` (2026-04-03, still OPEN, 7-8 months stale).
- **No verifiable live PnL:** All 41 picks in `multi_asset_picks.json` are `forward_test_only=true`, `pnl_pct=null`.
- **Non-unique pick IDs:** `vix_reversal::SI=F::2026-03-11` duplicated 4+ times across corpus.
- **Mutual funds:** Zero coverage — no algorithm, no data source.
- **`dbpasses.txt` missing:** Not found in repo root; located at `/home/eaguiar2015/dbpasses.txt` (outside repo, contains live keys — do NOT read/expose).
- **5 empty tables in `meta_strategy.db`:** `live_performance`, `walkforward_results`, `permutation_signals`, `meta_label_predictions`, `adversarial_compat`.

---

## DELIVERABLES (write all to WIRED_IN/final_v001/2026-11-15T0741_flaxen-hair/):

### 1. `Summary.MD` — LIVING DOCUMENT (created FIRST)
- What was done in this session
- Inventory highlights from all prior worktrees
- Ranked candidates with explicit verdicts (proven / promising / reject)
- Recommended asset class(es) + timeframe(s) + TP/SL + parameters
- Statistical evidence
- Exact reproduction commands

### 2. `01_asset_class_plans/` — Per-asset-class profitability plans

### 02_holding_period_analysis/ — Per-class analysis by holding period vs trading style

### 03_proven_algorithms/ — Top algorithms from TradingView contests

### 04_subq_decision_support/ — SubQ decision support protocol

### 05_framework_answers/ — Answers to framework questions

### 06_essential_questions/ — Essential questions for finding profitable algorithms

### 07_company_turnarounds/ — Company turnaround case studies

### 08_key_metrics/ — Key metrics from multiple perspectives

---

## 8. CONSTRAINTS (NON-NEGOTIABLE)

- **NEVER** use broad globs like `audit_trail/**` or `audit_dashboard/**` — they match generated data files (`.json`, `index.html`) that the workflow commits, risking infinite loops (if the push trigger is ever re-enabled).
- **NEVER remove the `[skip ci]`** from the workflow's own commit message — it's the primary infinite-loop protection.
- **NEVER re-add the `push:` trigger** without re-reading the 2026-05-19 removal rationale — the cancel-cascade problem was real and costly.
- **Never commit secrets, credentials, tokens, private keys.**
- **dbpasses.txt** is located at `/home/eaguiar2015/dbpasses.txt` (outside the repo, contains live keys) — DO NOT READ OR EXPOSE CONTENTS.

**DECISION: NO-GO for live capital deployment.** No asset class has proven statistically valid profitability. All pick values are forward-test-only with null PnL.

---
