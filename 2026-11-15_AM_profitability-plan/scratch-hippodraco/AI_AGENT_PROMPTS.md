# AI Coding Agent Prompts — Parallel Worktree Edge Hunt
**Date:** 2026-11-15  
**Purpose:** Prompts to give to AI coding agents running in parallel worktrees on different machines, each attempting to find a truly profitable strategy per asset class.  
**Ground rule:** Every agent must ground its work in the mandatory data-integrity filters and the master gate (07-key-metrics/KEY_METRICS.md). No agent may claim profitability without `(asset_class \| n \| timeframe)` and clean OOS.

---

## How to use these prompts

Assign **one asset class per worktree** (or one agent per class). Each agent:
1. Reads `01-asset-class-plans/PLAN_PER_ASSET_CLASS.md` and `07-key-metrics/KEY_METRICS.md`
2. Runs the prompt below for its assigned class
3. Produces a worktree-local report `reports/<CLASS>_edge_hunt_<UTC>.md`
4. Submits to swarm second-opinion before any promotion discussion

Do **not** let agents share uncommitted state. Each worktree is isolated; merge only through reviewed PRs to main.

---

## Prompt template (per asset class)

Copy the block below into each worktree agent, replacing `<ASSET_CLASS>` and `<BENCHMARK>`.

```
You are an AI coding agent hunting for a statistically valid, costed, out-of-sample profitable strategy in the <ASSET_CLASS> asset class. You work in an isolated git worktree. Do not deploy capital. Do not edit production dashboards. Produce a report only.

## Your mission
Find ONE pre-specified, statistically valid procedure for <ASSET_CLASS> that beats <BENCHMARK> on clean out-of-sample forward data, after realistic costs, with multiple-testing correction. If none exists, report "no edge found" with evidence — that is a valid and valuable result.

## Mandatory constraints (violating these invalidates your result)

1. Data-integrity filters (money-maker-readyv2, ALL must be applied):
   - Exclude backfill labels: resolver_version NOT LIKE 'backfill%' AND resolved_at IS NOT NULL
   - Exclude banned sources: Predictions, sandbox_opposite, rapid_fire, incubator_gainer, luxalgo_filters, multi_asset_copytrader, forex_copy_trader, signal_validation, multi_asset_cot, regime_terminal, multi_asset_scanner, myfxbook_retail_contrarian, ig_contrarian_sentiment
   - Per-class sane-pnl guard: ABS(pnl_pct) <= FOREX 20 / COMMODITY 30 / BOND 25 / CRYPTO 95 / else 50
   - Count EXPIRED as a NON-WIN: WR = WON / (WON+LOST+EXPIRED+FLAT)
   - Intrabar validation before trusting WR: tools/reresolve_intrabar.py
   - Require >=3 distinct months at n>=30/month

2. Master gate (07-key-metrics/KEY_METRICS.md):
   - n resolved (forward/OOS) >= 100 (Tier 2) / >= 500 (Tier 1)
   - Profit Factor after costs >= 1.5
   - Win Rate (EXPIRED-inclusive) >= 50%
   - Max Drawdown <= 20% (default)
   - Net expectancy after costs > 0
   - DSR >= 0.95 with CORRECT nb_trials (all strategies tested that season, NOT nb_trials=1)
   - SPA family-wise p <= 0.10
   - Beat transparent benchmark: <BENCHMARK>

3. No fabrication: never UPDATE TIME_EXIT->LOST with pnl_pct=0.0, never mass-DELETE ghost rows, never blind-unblock classes, never invert ML confidence without retrain+parity.

## Required outputs (write to reports/<ASSET_CLASS>_edge_hunt_<UTC>.md)

### A. Measurement audit
- Fraction of recent_closed with blank entry_time
- Fraction of TIME_EXIT rows with exit_price==entry_price (fabricated flats)
- Fraction of active_raw with blank current_price
- Is dashboard_data.json stale (>2h)? Use live URL, not local copy

### B. Candidate strategies
For each candidate strategy in <ASSET_CLASS>:
  - strategy name, source system
  - n resolved, WR (EXPIRED-inclusive), PF after costs, MDD, Sharpe (class-frequency annualised, NOT blindly √252)
  - DSR with correct nb_trials, SPA p-value, PBO
  - Cost model used (fees/spreads/funding/roll per class from tools/data/transaction_costs.json)
  - Benchmark comparison vs <BENCHMARK> on same window
  - Single-source concentration check (>60% from one source = reject)
  - Outlier cap check (PF > ~10 = suspect)

### C. Walk-forward result
- Pre-registered selection rule (never saw test month)
- Forward trades n, WR, PF, total P/L, max DD
- Randomization p-value vs random selection (800 null draws if possible)
- Bonferroni-corrected p for all variants tested

### D. Verdict (one of)
- "EDGE CANDIDATE — passes T2 gate" (n>=100, PF>=1.5, WR>=50%, MDD<20%, beats benchmark)
- "NO EDGE — does not clear gate" (state which metric failed)
- "DATA INSUFFICIENT" (n<100, or data quality prevents validation)

### E. Reproducibility
- Exact commands run (with file paths and line numbers)
- git SHA of code/data used
- Any SubQ/LLM second-opinion used (cite provider + prompt + fact-check result)

## Do NOT
- Deploy capital
- Edit audit_dashboard/index.html
- Run audit_trail/dashboard_generator.py locally
- Add to BLOCKED_ASSET_STRATEGY_PAIRS without explicit user approval
- Claim performance without (asset_class \| n \| timeframe)
- Trust AI tournament leaderboard WR (43-89 resolved, wide CIs, ~47% still OPEN)

---

## Per-class benchmark assignments

| Worktree / Agent | Asset Class | Benchmark | Priority |
|------------------|-------------|-----------|----------|
| Agent 1 | EQUITY (US) | SPY total return | P1 (highest) |
| Agent 2 | ETF | SPY / appropriate ETF benchmark | P1 |
| Agent 3 | CRYPTO | BTC-USD / sector basket | P2 (after OHLCV backfill) |
| Agent 4 | COMMODITY / FUTURES | Appropriate continuous futures / cash | P2 (after real feed fix) |
| Agent 5 | BOND | TLT / IEF / AGG total return | P3 (after FRED unblock) |
| Agent 6 | FOREX | Flat cash / carry-adjusted | P3 (currently blocked) |
| Agent 7 | MUTUAL FUNDS | Appropriate index fund | P3 (after class registration + NAV) |

---

## Swarm second-opinion (before any promotion)

After each agent writes its report, fan the result to multiple providers via `tools/consult_multi.py --fanout`:
- Prompt: "Review this edge claim for <ASSET_CLASS>: [paste report sections B and C]. Check for multiple-testing flaws, cost omissions, single-source concentration, and whether it truly beats <BENCHMARK> on clean OOS. Ground your answer in pf_registry.json canonical numbers."
- Require agreement across providers grounded in the same canonical numbers before considering promotion.

## Promotion rule (final)

No class is promoted to live capital unless ALL gates pass on BOTH rolling 90-day AND frozen out-of-sample walk-forward. Until then, all agents report "no edge found" or "paper-pilot only."

---
