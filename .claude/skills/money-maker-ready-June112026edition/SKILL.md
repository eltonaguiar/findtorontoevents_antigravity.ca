---
name: money-maker-ready-June112026edition
description: The June-2026 EDITION of the money-ready program — executes the self-correcting MASTER LOOP (docs/MONEY_READY_MASTER_LOOP_2026-06.md) that converges toward 2-3 profitable asset classes even from 0/9. Use when the user says "/money-maker-ready-June112026edition", "run the master loop", "weekly money-ready cycle", or at the monthly edition review. Inherits data sources + hard rules from /money-maker-ready and /money-maker-readyv2. Aliases - mmr-june2026, master-loop, money-loop.
---

# /money-maker-ready-June112026edition — the Master Loop (June 2026 edition)

> ⚠️ **SUPERSEDED 2026-07-11 by `money-maker-ready-July112026edition`** (see `reports/edition_review_2026-07.md`). The June structural bet — mine the crypto ledger for directional alpha — was EXHAUSTED (no net-of-cost alpha; root cause = entry_price P0 + ~90% unresolved). The July edition pivots the primary track to ETF **tactical asset allocation** (the one validated find) + treats the crypto ledger as fix-before-mine. Use the July edition. This block below is retained for history.

**Canonical plan:** `docs/MONEY_READY_MASTER_LOOP_2026-06.md` — READ IT FIRST; this skill is the executor.
**Edition discipline:** this is a DATED edition. On the 11th of each month, run the edition review (Section E below) and either re-stamp or supersede with a new edition skill. Editions never silently mutate — improvements are visible diffs.

## ⛔ MANDATORY — ALL ASSET CLASSES + ALL DATA SOURCES (do NOT tunnel on crypto)

**The #1 recurring failure of agents on this repo is looking ONLY at the crypto `at_signal_outcomes` ledger and concluding "no edge."** That ledger is ~93% crypto AND is contaminated (see the `entry_price` P0 below). Concluding "no edge across all classes" from crypto alone is WRONG and has cost months. Before ANY "no edge" verdict you MUST have surveyed, at minimum:

- **All 9 databases** (creds `/home/eaguiar2015/dbpasses.txt`, convention `ejaguiar1_<name>` / `<name>1234560` @ the `tools/db_env.py` host — NEVER echo/commit): `ejaguiar1_stocks` (at_signal_outcomes, daily_prices, crypto_ohlcv, **futures_daily_ohlcv**, **equity_daily_ohlcv**), `ejaguiar1_backtests` (**bt_backtest_trades 32.7M rows w/ real entry+exit+TP+SL**, bt_backtest_runs 285 aggregated PF/Sharpe), `ejaguiar1_memecoin` (58 tables: bt100_results, mc_winners…), `ejaguiar1_news` (sentiment), plus events/deals/favcreators. (Sports `ejaguiar1_sportsbet` is a separate goal — operator may de-scope.)
- **Every asset class**: CRYPTO, MEMECOIN, EQUITY, ETF, FOREX, COMMODITY, FUTURES, BOND — AND the cross-cutting SOURCES the operator expects edge from: **copytraders / public trades** (Hyperliquid `copy_hl`, `multi_asset_copytrader`), **stock fundamentals / value**, **prediction markets (Kalshi / Polymarket** `copy_pm`, `prediction_market_consensus`). If a class/source has too few resolved rows to judge, say so and check whether the emitter is wired + resolving — do NOT silently omit it.

**P0 DATA-INTEGRITY GATE (read `reports/DATA_INTEGRITY_entry_price_2026-07-03.md`):** `at_signal_outcomes.entry_price` is only ~29% clean (37% >10% off bar, 7% >50%), systematically +1.3% (inflates SHORT / deflates LONG), and `intrabar_pnl_pct` RIDES it. Prefer `bt_backtest_trades` (real entry+exit) or re-resolve from bar-aligned NEXT-bar entries. Every candidate must pass the **3 mandatory controls** (memory `feedback-entry-price-contamination-regime-2026-07-03`): (1) entry_price vs OHLCV-bar integrity, (2) regime control vs matched-random entries + check market direction, (3) look-ahead control (shift entry to next bar — signal-bar entry is look-ahead-biased).

## What this skill does (one weekly cycle)

1. **MEASURE** — refresh the honest ledger + coverage metrics; run the H1 structural audit:
   ```bash
   python3 tools/build_intrabar_truth_by_class.py --stdout       # per-class honest n/WR/PF
   python3 tools/stamp_entry_conditions.py --stdout              # forward lane state
   python3 tools/check_one_sided_resolution.py                   # coverage pathology
   # coverage: resolved/emitted ratio, terminal NULL-pnl count, dup-rate (SQL patterns in the master MD §3)
   # H1 stratified spot-replay: 10 random recent resolutions per focus class vs independent bars
   ```
2. **DIAGNOSE** — score H1-H5 per focus class (table in master MD §3). H1 red = halt everything else.
3. **ACT (parallel)** — for each focus class (currently CRYPTO + COMMODITY), run the top remedy:
   - Replay-variant batches via the proven harness (mirror `reports/strategy_bt_crypto_2026-06-11.json` methodology: entry-anchored first-touch, SL-wins-ties, pre-entry features only, per-symbol-day dedup, net of costs). **Pre-register the batch (hypothesis + falsification) BEFORE running; the batch is ONE FDR family; family closes after its registered comparisons.**
   - Plumbing/data fixes ship same-day with tests (the #129 discipline).
4. **FORWARD** — check the pre-registered checkpoint calendar (master MD §7); promote/kill ONLY at the bars (95% CI lower bound of net PF > 1.15 at n≥80 forward + time-split + concentration<35%).
5. **RATCHET** — commit the weekly scorecard to `reports/weekly_loop_scorecard_<date>.md`; file/resolve incidents via `tools/audit_pick_funnel/cli_track.py`; update the live pages.

## Data + credentials (for ANY agent, including brand-new ones)
- Read the orientation in master MD §0. DBs via `tools/db_env.py` ONLY; local agents get passwords from `/home/eaguiar2015/dbpasses.txt` (gitignored — NEVER commit/echo); remote agents ask the operator.
- **Backup to `ejaguiar1_backups` before ANY table mutation** (`tools/db_backup_to_backups.py`; ≤64-char table names; FK tables need CREATE-AS-SELECT copy).
- All source-of-truth pointers, tier definitions, mandatory data-integrity filters, and the reject-without-reverify list: inherit from `/money-maker-ready` + `/money-maker-readyv2` (do not duplicate here).

## Hard rules (non-negotiable, inherited + edition-specific)
- Every claim: `(asset_class | n | timeframe)`. Direct-SQL re-verify any number a subagent/peer/LLM produces.
- Pre-register before backtest (M-107). Tuning families close after their registered comparisons — no variant-fishing.
- Mutate-before-kill for strategies; do-not-relitigate list is binding (master MD §8).
- Promotion is FORWARD-lane only. Replay results select candidates; they never size anything.
- One focus-class slot rotates out after 3 consecutive null weekly cycles.

## E. Monthly edition review (run on the 11th)
1. Score the month: per focus class — did the CI lower bound improve? checkpoints hit/missed? incidents P0 aging?
2. What circled (3-null rotations, refuted batches) — add to do-not-relitigate.
3. What the next edition changes (one structural change max — editions evolve, not churn).
4. Write `reports/edition_review_<YYYY-MM>.md`, supersede or re-stamp the skill, update the master MD header.
5. Hand the operator the external-review task spec (master MD §9) if the edition made structural changes.

## Failure-hypothesis quick reference (full table: master MD §3)
H1 measurement → halt + fix · H2 backtest-only → shadow + close family · H3 data scarcity → free APIs (FRED/CFTC/EDGAR) + shadow-lane universe widening · H4 external signals → per-source scorecards keep/kill · H5 coverage → extend resolution before judging.

## Current state snapshot (2026-07-04 — RE-VERIFY, never trust this block after ~1 week)

**VERDICT: no net-of-cost systematic ALPHA exists on the internal ledger / free data (exhaustive, swarm-confirmed).** Every crypto-ledger candidate (luxalgo SHORT, rsi5070, mega_mutation, funding, etc.) dissolved under the 3 controls above. Root cause = the entry_price P0 + ~90% of positions never resolving, NOT missing strategies. STOP re-mining the crypto ledger for directional alpha until it is re-resolved from bar-aligned entries.

**THE ONE REAL FIND (2026-07-04): asset-class MOMENTUM ROTATION (dual-momentum / TAA).** Hold top-5 asset-class ETFs by 9-month momentum, monthly, abs-momentum-filter→bonds. Universe = 14 liquid free ETFs (etf_daily_ohlcv, yfinance). Robust: ALL 16 (top-N×lookback) grid cells cut MaxDD to −12/−17% vs SPY −24%; 9-month region Sharpe 1.09-1.21 / Calmar 0.81-1.10 vs SPY 1.00/0.68; both-halves+. It is smart-beta (better RISK-ADJUSTED return, NOT excess return); in-sample-robust → forward-track, don't over-size. Tool: `tools/tactical_rotation_tracker.py`. Report: `reports/TACTICAL_ROTATION_EDGE_2026-07-04.md`.

**LIVE PROOF-OF-CONCEPT (measurable, in DB):** table `ejaguiar1_stocks.poc_picks`, poc_id `tactical_asset_rotation_v1` — 5 picks EEM/IWM/DBC/QQQ/EFA @20% each, entry 2026-07-04, **measurement_date 2026-07-18**, benchmark SPY. Entry prices locked. **CHECKPOINT 2026-07-18 (cron/reminder set):** fetch current prices, UPDATE poc_picks.exit_price/pnl_pct/status, compare basket vs SPY. (2wk is too short for a monthly TAA verdict — it's a liveness/plumbing read; the real gate is 6-12mo forward.)

**Also deployed:** diversified BETA portfolio (`tools/beta_portfolio_tracker.py`, real ETF sleeves SPY/DBC/AGG/GLD/BTC, inverse-vol + light crash guard) — the honest floor (beta, not alpha).

**ML LAYER AUDIT (2026-07-04, reports/ML_AUDIT_2026-07-04.md):** the ML layer is globally HALTED (`ml_trading_enabled=False`), stale (models last trained 2026-06-03, health check 06-21), and its "elite" WRs were FABRICATED — 4/6 hardcoded strategies have 0-2 resolved trades; `ml_enhanced_*` aggregate is honest 28% WR / −0.96% net (claimed 87-94%). FIXED: emptied the fabricated `ML_PROVEN_STRATEGIES` override in elite_scorer.py (was force-scoring losers to elite). OPEN tweaks: purge ml_strategy_reviver hardcoded dict; halt-emission-or-retrain ml_crypto_predictor (still emitting −0.96% picks); wire-or-retire ml_gatekeeper (shadow + 100% synthetic A/B log); restart ml_health monitor. Do NOT trust any ML WR until retrained on clean data + validated look-ahead-free (3 controls).

**NEXT STEPS (keep this block updated):** (1) 2026-07-18 measure poc_picks; (2) forward-track tactical rotation 6-12mo; (3) re-resolve the crypto ledger from bar-aligned NEXT-bar entries (the only path to trust any ledger candidate) — but note the OPEN backlog is systematic losers (dead end for backlog resolution); (4) mine codebase strategy docs (reports/etf_strategy_catalog.md, high_sharpe_strategies_report.md, academic_trading_strategies.md); (5) ML-algorithm audit in flight (utilization/staleness/fabricated-WR).
