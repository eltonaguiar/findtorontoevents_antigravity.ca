---
name: money-maker-ready-July112026edition
description: The July-2026 EDITION of the money-ready program. SUPERSEDES money-maker-ready-June112026edition. The June edition's structural bet (converge to 2-3 profitable asset classes by mining the crypto ledger) was EXHAUSTED and found no net-of-cost alpha; the ONE structural change this edition makes is to REORIENT the primary money-making track from crypto-ledger directional-edge-mining (measurement-broken, dead) to ETF TACTICAL ASSET ALLOCATION (the one validated find), while treating the crypto ledger as fix-before-mine. Use when the user says "/money-maker-ready-July112026edition", "run the master loop", "weekly money-ready cycle", or at the monthly edition review. Inherits data sources + hard rules from /money-maker-ready and /money-maker-readyv2. Aliases - mmr-july2026, master-loop, money-loop.
---

# /money-maker-ready-July112026edition — the Master Loop (July 2026 edition)

**Supersedes:** `money-maker-ready-June112026edition` (2026-07-11 edition review; see `reports/edition_review_2026-07.md`). Editions never silently mutate — this is the visible diff.
**Canonical plan:** `docs/MONEY_READY_MASTER_LOOP_2026-06.md` (still the base loop). This edition's ONE structural change: **the primary track is now ETF tactical asset allocation, not crypto-ledger edge-mining.**

## ⭐ THE STRUCTURAL CHANGE (why this edition exists)

For months the program mined the crypto `at_signal_outcomes` ledger for directional alpha and found NONE that survives scrutiny. The 2026-07 exhaustive sweep (all 9 DBs, all classes, all sources, peer-AI + subagents, the 3 controls) proved the root cause is **not missing strategies** — it is (1) a corrupt `entry_price` (P0) + ~90% of positions never resolving, and (2) net-of-cost systematic ALPHA being ~impossible for a small operator on free data (inefficiencies < retail cost). Reports: `reports/CROSS_ASSET_EDGE_SYNTHESIS_2026-07-04.md`, `FREE_DATA_EDGE_HUNT_CAPSTONE_2026-07-04.md`, `DATA_INTEGRITY_entry_price_2026-07-03.md`.

**The one thing that robustly works: ETF TACTICAL ASSET ALLOCATION (TAA / dual-momentum).** Not alpha — smart-beta: it matches the market's return with ~half the drawdown (crash avoidance), validated look-ahead-free across 2007-2026 including the 2008 GFC. THIS is the money-ready track now. Details in the snapshot below.

**Loop reorientation:** MEASURE/DIAGNOSE/ACT/FORWARD/RATCHET still apply, but ACT's default focus is the TAA/ETF track + data-integrity fixes, NOT crypto replay-variant batches. Only re-mine the crypto ledger after it is re-resolved from bar-aligned NEXT-bar entries (and note: the OPEN backlog is systematic losers — a dead end).

## ⛔ MANDATORY — ALL ASSET CLASSES + ALL DATA SOURCES (do NOT tunnel on crypto)

Before ANY "no edge" verdict you MUST have surveyed all 9 databases (creds `/home/eaguiar2015/dbpasses.txt`, convention `ejaguiar1_<name>` / `<name>1234560` @ the `tools/db_env.py` host — NEVER echo/commit) and every asset class + cross-cutting source (copytraders, fundamentals, prediction markets). Free ETF/equity data via yfinance into `etf_daily_ohlcv` (2005-2026, 36+ ETFs) and `equity_daily_ohlcv`; `daily_prices` is now refreshed by `tools/refresh_daily_prices_yf.py` (the old fetch_prices.php 404'd). Concluding "no edge across all classes" from crypto alone is the #1 recurring failure and has cost months.

## ⛔ P0 DATA-INTEGRITY GATE + 3 MANDATORY CONTROLS (unchanged, still binding)

`at_signal_outcomes.entry_price` is ~29% clean / +1.3% biased; `intrabar_pnl_pct` rides it (`reports/DATA_INTEGRITY_entry_price_2026-07-03.md`). Prefer `bt_backtest_trades` (real entry+exit) or re-resolve from bar-aligned NEXT-bar entries. Every candidate must pass the **3 controls** (memory `feedback-entry-price-contamination-regime-2026-07-03`): (1) entry_price vs OHLCV-bar integrity; (2) regime control vs matched-random entries + check market direction; (3) **look-ahead control — shift entry to the NEXT bar** (signal-bar entry is look-ahead-biased; it collapsed macd_rsi 2.47→0.37 and every apparent LONG "edge").

## ⛔ NEW: NO FABRICATED WIN-RATES (2026-07 lesson)

Hardcoded win-rates in production scoring were FABRICATED and force-scored losers to elite: `copy_hl_NMTD_25M 81.3%` (0 resolved trades), the `ML_PROVEN_STRATEGIES` dict (4/6 at 0-2 trades; ml_enhanced_* is really 28% WR / −0.96% net), `ml_strategy_reviver` (FET 0.941/17 vs DB 5@40%). All three are now removed/gated (`reports/ML_AUDIT_2026-07-04.md`). **Rule: any hardcoded WR/PF/closed-count in code must be re-verified against a LIVE at_signal_outcomes query before it is trusted; if unbacked, remove it.**

## What this skill does (one weekly cycle)

1. **MEASURE** — (a) TAA track: `python3 tools/tactical_blend_tracker.py --stdout` (current holdings) + confirm etf_daily_ohlcv/daily_prices are fresh; (b) legacy honest-ledger coverage: `tools/build_intrabar_truth_by_class.py --stdout`, `tools/check_one_sided_resolution.py` (still red — measurement broken).
2. **DIAGNOSE** — score H1-H5 (master MD §3). For the TAA track the gate is risk-adjusted-vs-SPY (Sharpe/Calmar/MaxDD + both-halves + all-thirds), NOT the intrabar-PF gate.
3. **ACT** — default: advance the TAA track (forward-track POC, refine blend, validate a new documented TAA variant look-ahead-free on etf_daily_ohlcv 2005-2026) OR ship a data-integrity/plumbing fix. Crypto replay-variant batches ONLY after ledger re-resolution.
4. **FORWARD** — TAA POC gate is 6-12 MONTHS forward vs SPY (2-week checkpoint = liveness only). Crypto forward-lane gate unchanged (net-PF CI-LB>1.15 @ n≥80, time-split, conc<35%) but nothing is close.
5. **RATCHET** — commit the weekly scorecard; update this snapshot; keep `poc_picks` resolving (`poc-picks-checkpoint.yml`).

## Data + credentials / Hard rules / Section E (monthly edition review)
Inherited verbatim from the June edition + `/money-maker-ready` + `/money-maker-readyv2` (do not duplicate): DBs via `tools/db_env.py` only; backup before ANY table mutation; every claim `(asset_class | n | timeframe)`; direct-SQL re-verify any subagent/LLM number; pre-register before backtest (M-107); mutate-before-kill; promotion FORWARD-lane only. **Section E monthly edition review runs on the 11th** — this July edition IS that review (one structural change: the TAA pivot).

## Current state snapshot (2026-07-11 — RE-VERIFY, never trust this block after ~1 week)

**THE MONEY-READY TRACK = ETF TACTICAL ASSET ALLOCATION (validated, deployed, forward-tracking).**
- **Tactical rotation** (`tools/tactical_rotation_tracker.py`): top-5 asset-class ETFs by **6-month** momentum (regime-robust default; was 9m), monthly, abs-momentum-filter→bonds. 2007-2026 (incl 2008 GFC): Sharpe 0.88 vs SPY 0.74, **MaxDD −19% vs SPY −51%**, Calmar 0.48 vs 0.21, positive all 3 time-thirds.
- **VAA-G4** (Keller): 2nd independent TAA strategy, also beats SPY (Sharpe 0.77, MaxDD −20%), regime-COMPLEMENTARY to the rotation.
- **v2 POC = 50/50 BLEND** (`tools/tactical_blend_tracker.py`): **Sharpe 0.89, MaxDD −16%, Calmar 0.50** — beats BOTH components with the smoothest regime profile. The strongest, most-robust result of the whole investigation. (Known refinement: cap single-ETF weight ~35% — current blend can lean one ETF heavy when VAA+rotation overlap.)
- Honest label: smart-beta, NOT alpha — matches market return with ~half the drawdown. In-sample-robust (2005-26), NOT proven-forward → forward-track at modest size.

**LIVE POC (measurable, in DB):** `ejaguiar1_stocks.poc_picks`, poc_id `tactical_asset_rotation_v1` — 5 picks EEM/IWM/DBC/QQQ/EFA @20%, entry 2026-07-04, **auto-resolves 2026-07-18** (`poc-picks-checkpoint.yml` + `tools/resolve_poc_picks.py` → updates pnl_pct + basket-vs-SPY verdict). 2wk = liveness read; real gate 6-12mo.

**Also deployed:** diversified BETA portfolio (`tools/beta_portfolio_tracker.py`) — the honest floor.

**CRYPTO LEDGER = MEASUREMENT-BROKEN, DO NOT MINE FOR ALPHA.** No candidate survives the 3 controls; entry_price P0 + 90% unresolved. Re-resolve from bar-aligned NEXT-bar entries before trusting anything; the OPEN backlog is systematic losers (dead end).

**ML LAYER = HALTED + fabricated WRs + was LEAKING losers (now largely contained).** 2026-07-11 re-check (2 agents, `reports/ML_AUDIT_2026-07-04.md`): the `enhanced-ml-crypto.yml` emitter was writing 28%-WR `ml_enhanced_*` losers into trading_picks every 2h with NO halt gate (only the downstream selector checked the flag). FIXED: `elite_scorer.ML_PROVEN_STRATEGIES={}`, `ml_strategy_reviver` gated off, and `ml_predictor_merger.run_merger()` now fail-closed on `ml_trading_enabled` (commit 4a005dc3; re-enable via `ML_EMIT_ENABLED=1`). VERDICT = **RETIRE/PAUSE, do NOT retrain**: models retrain daily in CI but on entry_price-contaminated (29%-clean) / no-alpha labels → retraining propagates contamination. OPEN: retire ml_gatekeeper A/B (dead, 100% synthetic log, no caller — stop its CI); pause enhanced-ml-crypto + meta/battleground retrains until labels are entry-clean; regenerate the frozen feature_health_report (2026-05-27, 5 picks) that drives the halt.

**Infra fixed this cycle:** `daily_prices` freeze (dead fetch_prices.php 404) → replaced by `tools/refresh_daily_prices_yf.py` (+11,791 rows, current). GH Actions healthy (only-known failures: CI Tests drift = PR#665, Sports de-scoped).

**NEXT STEPS (keep this block updated):** (1) 2026-07-18 measure poc_picks (auto); (2) forward-track the blend POC 6-12mo; (3) cap the blend concentration (~35%/ETF); (4) validate more documented TAA variants (DAA/PAA/Faber-GTAA) look-ahead-free on etf_daily_ohlcv; (5) finish ML remediation (gate ml_crypto_predictor, retire ml_gatekeeper, restart ml_health); (6) only re-mine crypto after ledger re-resolution.
