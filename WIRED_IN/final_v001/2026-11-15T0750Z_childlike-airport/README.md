# WIRED_IN — final_v001 — 2026-11-15T0750Z_childlike-airport

**Finalized Strategy to Prove Profitable Strategies per Asset Class for findtorontoevents.ca/audit**

This folder implements the plan synthesized from:
- Core statistical measures prompt (in PRE_PROMPT.MD)
- ALL_STRATEGIES.md (700+ strategies, baby, alpha_engine, world_class_v21, ml_enhanced, regime/momentum/HMM/stat-arb)
- WIRED_IN/2026-11-15T0150Z_childlike-airport/ (shadow monitoring pattern, wired_in_trend_momo_4d, short_duration_ballast, paper-only)
- 2026-11-15_AM_profitability-plan/* (per-asset plans, negative-result diagnosis, simulation results, forward_tracker)
- money_ready_verdict.json (0/9 classes pass; CRYPTO PF~0.92, EQUITY~0.94)
- Today's commits (quant kits, benchmark ledger, resolver integration, no stale jobs)
- Project constraints (benchmark beat after costs, PBO<0.3/DSR>0.95/n≥100/PF≥1.5, pre-registered forward, wired_in folder convention, no noisy scripts unless requested, cherry-pick only own files)

**Current State Summary**
- No MONEY_READY class.
- wired_in_childlike is paper shadow (PF too low on replay).
- Strong historical signals exist (94% WR FETUSDT ml_enhanced, 70-81% equity pilots) but fail full forward/statistical/benchmark gates.
- Full pipeline built: resolver, benchmark_closed_ledger, audit cron, freshness guards, dashboard tiles.

**Finalized Strategy (executable phases)**

**Phase 0 – Data Quality (immediate)**
- Confirm no stale GitHub jobs (none found; guardians healthy).
- Validate DB freshness & cross-DB consistency on ejaguiar1_stocks (trading_picks ~143k rows, outcomes, bt_backtest_trades).
- Re-generate benchmark_ledger_proof.json and money_ready_verdict.json.

**Phase 1 – Candidate Selection (from ALL_STRATEGIES.md inventory)**
Prioritize highest historical signals per class:
- **CRYPTO**: ml_enhanced_FETUSDT_1d_B_lightgbm (94% WR) + regime/HMM variants.
- **EQUITY**: stocks_rsi2_pullback, world_class_v21_regime_mom, world_class_v21_sector_rel (70-81% pilots).
- **ETF**: Extend wired_in_trend_momo_4d with adaptive vol targeting + fundamental/macro gates.
- **BOND**: Enhance wired_in_short_duration_ballast with yield-curve/macro alignment.
- **FOREX/COMMODITY/FUTURES**: Lift freeze after contamination audit; start with pilot_cross_momentum or funding_carry.
- Add 2-3 top baby_strategies per class from incubator reports.

**Phase 2 – Rigorous Proof per Candidate**
For each candidate:
1. Pre-register immutable JSON picks (timestamped, matching resolver schema).
2. Run walk-forward + purged k-fold on clean data (no leakage).
3. Compute full must-pass metrics (net costs, expectancy>0, PF≥1.5, deflated Sharpe≥0.7, Sortino≥1.0, Calmar≥0.4, MDD≤20%, bootstrap CI excludes 0, DSR p<0.05, walk-forward≥60%, MC≥70% positive paths, regime robustness ≥3/4, shuffle control).
4. Forward-test via universal_pick_resolver (accumulate ≥100 independent trades).
5. Run benchmark_closed_ledger.py (paired bootstrap vs SPY/BTC, MC timing, coin-flip CI).
6. Apply enhanced gates (high-conviction tags, macro alignment, edge decay<0.2, PBO<0.05, SPA p<0.05).
7. Only promote to `sizing_allowed=true` and remove `paper_only` if MONEY_READY on all metrics + benchmark beat.

**Phase 3 – Dashboard Integration & Deployment**
- Emit qualified picks to wired_in JSONs (active/closed).
- Update audit_dashboard tiles, benchmark_proof.html, performance health, money_ready_verdict.json.
- Create this exact folder structure with full evidence (ALGORITHM_SPEC.md per class, PICK_JUSTIFICATION with tables/ATR, RESEARCH_AND_BACKTEST with replay results, ELIMINATION of weaker variants, this plan, PRE_PROMPT.MD).
- Cherry-pick only these files to main via clean temp worktree from origin/main (no force, own files only, leave worktree dirty).

**Phase 4 – Continuous Validation Loop**
- Hourly cron + forward_tracker monitors outcomes.
- Monthly full re-proof on accumulated data.
- Kill under-performers per QA protocol (Sharpe<0 after 40 trades etc.).
- Parallel: implement remaining money_ready_enhancements (fundamental/macro gates, adaptive R:R, volatility targeting).

**Expected Outcome**
At least one (ideally all) asset class reaches MONEY_READY verdict with green dashboard tiles, benchmark-beating net returns, full statistical proof, and live resolver tracking. This closes the standing goal of statistically valid profitable approaches feeding the audit page.

**Verification Commands (run before commit)**
- `python3 -m py_compile *.py` (if any scripts added)
- `gh run list --workflow=audit-dashboard.yml --limit=5` (confirm no stale failures)
- `tools/db_freshness_check.py` (if available)
- Lint/typecheck per project (npm run lint if applicable)

This folder is self-contained evidence. Deploy via cherry-pick to main as specified. Next agent should execute Phases 0-3 and verify dashboard updates.

**Files in this folder:**
- PRE_PROMPT.MD (core metrics + context)
- THIS_FILE (finalized strategy)
- (To be added by execution: ALGORITHM_SPEC.md per class, justification tables, replay results, updated JSONs, evidence MDs)

Commit message example: `wired_in(final_v001): finalized profitability strategy per asset class with full proof gates - 2026-11-15T0750Z_childlike-airport`