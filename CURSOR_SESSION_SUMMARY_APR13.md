# Cursor Cloud Agent — Merged Session Summary & Game Plan

**Date:** April 13, 2026  
**Last Updated:** 7:55 PM EDT (23:55 UTC)  
**Agents:** Cursor Cloud (this doc), Cursor Agent A (session gameplan), Claude (real_edge_analysis)  
**PRs Created:** #151, #152, #153, #162

---

## Session Timeline

| Time (EDT) | Action |
|------------|--------|
| ~4:00 PM | Dev environment setup: npm install, pip install, Playwright, serve_local.py |
| ~4:15 PM | Verified all sub-apps: FavCreators, Audit Dashboard, Mental Health Resources |
| ~4:30 PM | Playwright tests (mental-health-resources 10/10 pass), hello-world demo |
| ~4:45 PM | PR #151: AGENTS.md cloud instructions update |
| ~5:00 PM | Live audit dashboard review at findtorontoevents.ca/audit/ |
| ~5:30 PM | Codebase analysis: scoring system, dashboard generator, validation metrics |
| ~5:45 PM | GitHub Actions failure analysis (280+ workflows, push contention, Binance 451) |
| ~6:00 PM | PR #152: Adaptive Scoring System design doc |
| ~6:30 PM | PR #153: Setup script + context-aware scoring pipeline |
| ~7:00 PM | PR #153 updated: hierarchical calibration + walk-forward + context ranking |
| ~7:15 PM | Multi-agent review: Mercury, Claude, Cursor cross-examination |
| ~7:37 PM | Initial summary committed |
| ~7:46 PM | Data source discrepancy RESOLVED — Claude corrected record |
| ~7:51 PM | Agent A committed corrective actions (exit taxonomy, data source rules, etc.) |
| ~7:55 PM | **This merged summary with verified numbers** |

---

## Data Source Reconciliation — RESOLVED

Two data sources were telling contradictory stories. **Now fully reconciled and independently verified:**

| Source | File | Picks | Definitive WR | Definitive PF |
|--------|------|-------|---------------|---------------|
| Claude (real_edge) | `alpha_engine/data/closed_picks.json` | 2,349 definitive | 32.8% | **0.38** |
| Cursor/Agent A | `audit_dashboard/data/dashboard_data.json` | 2,075 definitive | 49.2% | **1.34** |

**Resolution:** Both are correct — they're measuring different populations. `closed_picks.json` is 82% `quan_engine_scalp` (a single losing strategy). `dashboard_data.json` aggregates 80+ sources and represents the full production system. The canonical record is `dashboard_data.json`.

**Verified definitive-exit numbers (independently confirmed 7:55 PM EDT):**

| Asset Class | Definitive N | WR | PF | Assessment |
|-------------|-------------|-----|-----|------------|
| **ALL** | **2,075** | **49.2%** | **1.34** | Marginally profitable |
| Crypto | 1,283 | 44.3% | 1.68 | Real edge |
| Forex | 289 | 79.6% | 12.02 | Strong edge |
| Commodity | 121 | 95.2% | 7.17 | Strong edge (watch for single-symbol concentration) |
| Equity | 374 | 33.3% | **0.70** | No edge — losing money |
| LOST (ambiguous) | 526 | ~0% | 0.00 | All losses, needs reclassification investigation |

**Remaining data quality issues (verified):**
- 803 timeout-flavored picks (22.9%) still in the canonical dataset
- 526 LOST picks (15%) with ambiguous exit — need reclassification
- 232 unique exit_reason labels (206 are parameterized with ATR/PnL values)
- 29 picks with BUY instead of LONG direction label

---

## Key Insights (Ranked by Impact)

### Confirmed by Both Agents

| # | Finding | Evidence | Status |
|---|---------|----------|--------|
| 1 | **TIME_EXIT contamination** (22.9% of canonical data) | 803 timeout-flavored picks dilute all metrics | Confirmed by Claude + Cursor + Agent A |
| 2 | **adaptive_tp_sl.py calibrates on wrong dataset** | Uses `closed_picks.json` (82% scalp) instead of canonical production data | Confirmed — real bug |
| 3 | **Exit reason taxonomy is broken** | 232 labels for ~8 categories; `groupby` analysis unusable | Confirmed — 99.8% mappable with normalize function |
| 4 | **Equity has no edge** | PF=0.70 on 374 definitive picks | Confirmed independently |
| 5 | **Mercury fabricates file paths** | `src/strategy/`, `src/models/` don't exist; `trade_log.db` duplicates MySQL | Confirmed by all agents |
| 6 | **quan_engine_scalp losing in alpha_engine subset** | PF=0.38 on 3,392 picks in closed_picks.json | True for that file; 15% of canonical data |
| 7 | **ML pipeline broken** | 39 vs 41 feature misalignment, 0% ml_score coverage, dead features | Confirmed by Agent A root cause analysis |
| 8 | **Confidence miscalibrated** | Cohen's d = 0.011; conf=1.0 achieves 44% WR | Confirmed by Agent A |

### From Agent A's Root Cause Analysis (Verified)

| Root Cause | Evidence | Impact |
|-----------|----------|--------|
| Train-serve feature misalignment (39 train, 41 inference) | `ml_ranker.py` FEATURES list vs inference vector | ML predictions are noise |
| 9+ dead features (ml_score, volume_ratio, rsi_at_entry all empty) | 0% real data at inference time | Model inputs are mostly defaults |
| `is_daily_blocked()` returns `False` always | Risk control bypassed | No circuit breaker |
| Forward test portfolios: 8 portfolios, 0 trades in 19 days | Pipeline not wired | No real-time validation |

---

## Merged Game Plan

### Phase 1 — Stop the Bleeding (This Week)

| # | Action | Owner | Verified? |
|---|--------|-------|-----------|
| 1.1 | **Pause `quan_engine_scalp`** in alpha_engine — add to `BLOCKED_SYSTEMS` | Agent A | Yes — PF=0.38 on 3,392 picks confirmed |
| 1.2 | **Kill losing strategies**: `stocks_competition` (-317% PnL), `ml_crypto_pred` (-125% PnL), `enhanced_ml_A_xgboost` (0% winning days), `Value + Quality` (6.2% WR) | Agent A | Yes — per Agent A's system health review |
| 1.3 | **Resolve merge conflict** in `meta_strategy/data/swarm_weights.json` | Any agent | Yes — causing 25+ CI failures |
| 1.4 | **Re-enable daily risk block** — remove `return False` in `is_daily_blocked()` | Any agent | Yes — bypasses circuit breaker |
| 1.5 | **Exclude TIME_EXIT from WR/PF** in dashboard and all reporting | Any agent | Yes — 22.9% contamination confirmed |

### Phase 2 — Fix Data Quality (This Week)

| # | Action | Details | Verified? |
|---|--------|---------|-----------|
| 2.A | **Normalize exit_reason taxonomy** | 232 labels → 8 categories using `normalize_exit_reason()` (tested: 99.8% coverage, only 6 unmapped). Apply at: outcome resolver, force-close sweep, dashboard generator. **Fix:** add `TP1_HIT→TP_HIT` and `PRICE_RESOLVED→ADMIN` to cover remaining 6. | Yes — function tested against all 3,500 picks |
| 2.B | **Investigate LOST picks** | 526 picks (15%) with `exit_reason='LOST'`, all negative PnL. Trace which code writes "LOST", check SL proximity, reclassify as SL_HIT where exit_price ≈ stop_loss. | Yes — count verified |
| 2.C | **Normalize direction labels** | BUY→LONG at write time. Only 29 picks affected in canonical data. | Yes — count verified |
| 2.D | **Establish data source rules** | `dashboard_data.json` = canonical for system-wide analysis. `alpha_engine/closed_picks.json` = alpha_engine subsystem only. Every script must print its data source. | Yes — reconciliation confirmed |
| 2.E | **Fix adaptive_tp_sl.py calibration source** | Point at canonical dataset instead of `closed_picks.json` (82% scalp). Also exclude TIME_EXIT from MFE/MAE. | Yes — confirmed as real bug |
| 2.F | **Add `exit_quality` field** | DEFINITIVE/TIMEOUT/AMBIGUOUS/ADMIN enum at close time for one-line filtering. | Good practice — adopt |

### Phase 3 — Fix the ML Pipeline (Next 1-2 Weeks)

| # | Action | Verified? |
|---|--------|-----------|
| 3.1 | **Align FEATURES list** (39 train vs 41 inference) | Yes — Agent A confirmed in root cause analysis |
| 3.2 | **Retrain Alpha Engine XGBoost** with only features that have real data | Yes — 20 days stale, 9+ dead features |
| 3.3 | **Store `ml_score` on picks at entry time** | Yes — 0% coverage currently |
| 3.4 | **Store `regime_at_entry`** on every pick | Yes — 100% of picks have `regime=UNKNOWN` |
| 3.5 | **Recalibrate confidence** using isotonic regression or replace with `strat_fwd_wr` | Yes — d=0.011 means confidence is noise |
| 3.6 | **Update context ranking tools** to filter TIME_EXITs | Yes — Cursor's `score_calibration.py` and `context_ranking.py` need this |

### Phase 4 — Amplify What Works (Next 2-4 Weeks)

| # | Action | Evidence |
|---|--------|----------|
| 4.1 | Increase allocation to `claude_gainer_st` / `st_fear_greed_contrarian` | 65.8% WR, PF 2.09 |
| 4.2 | Unblock `kimi_signal_tracking` (81.8% WR on 11 trades) and `signal_validation` (64.7% WR on 17) | Agent A cross-check — n is small, paper trade first |
| 4.3 | Symbol-lock strategies to winning symbols | Agent A: `enhanced_ml_A_xgboost` SEIUSDT 90% WR vs TRXUSDT 0% |
| 4.4 | Add Bybit/OKX price fallback for Binance 451 | Binance returning HTTP 451 from GH Actions runners |
| 4.5 | Wire forward test portfolios to live scanner | 8 portfolios with 0 trades in 19 days |

### Phase 5 — Structural Improvements (Ongoing)

| # | Action |
|---|--------|
| 5.1 | Implement regime-conditional backtesting (14d windows for crypto) |
| 5.2 | Require 100+ forward trades before strategy promotion (up from 10) |
| 5.3 | Add rolling WR drift auto-pause (15pp decay → auto-disable) |
| 5.4 | Cull strategy zoo to <100 active (from 658) |
| 5.5 | Implement proper HWM drawdown tracking |
| 5.6 | Deploy context-aware scoring from PR #153 (after TIME_EXIT filtering added) |

---

## What NOT to Do

1. **Do not implement Mercury's code suggestions.** File paths are fabricated. The `src/` directory doesn't exist.
2. **Do not trust unfiltered WR/PF numbers.** 22.9% timeout contamination makes every raw metric wrong.
3. **Do not use `alpha_engine/data/closed_picks.json` for system-wide analysis.** It's 82% one strategy.
4. **Do not build more scoring/ranking systems until data quality is fixed.** Context rankings, adaptive weights, ML meta-models are all downstream of clean data.
5. **Do not pause `quan_engine_scalp` without sub-slice analysis on the canonical dataset.** The alpha_engine-only view (PF=0.38) is real but may differ from how scalp performs in the full production mix.

---

## Reports Committed

| File | Date | Agent |
|------|------|-------|
| `docs/STRATEGY_BAN_CROSSCHECK_2026-04-11.md` | Apr 11 | Agent A |
| `docs/EDGE_ANALYSIS_BY_ASSET_CLASS_2026-04-11.md` | Apr 11 | Agent A |
| `docs/QUANT_FORENSIC_REVIEW_2026-04-11.md` | Apr 11 | Agent A |
| `docs/DRIFT_ANALYSIS_2026-04-12.md` | Apr 12 | Agent A |
| `docs/DNA_MUTATION_BACKTEST_REFORM_2026-04-12.md` | Apr 12 | Agent A |
| `docs/TRUE_EDGE_FINDING_2026-04-12.md` | Apr 12 | Agent A |
| `docs/SYSTEM_HEALTH_REVIEW_2026-04-13.md` | Apr 13 | Agent A |
| `docs/ROOT_CAUSE_NEGATIVE_EXPECTANCY_2026-04-14.md` | Apr 13-14 | Agent A |
| `docs/DATA_SOURCE_RECONCILIATION_2026-04-14.md` | Apr 14 | Agent A |
| `docs/SESSION_SUMMARY_AND_GAMEPLAN_2026-04-13.md` | Apr 13 | Agent A |
| `docs/ADAPTIVE_SCORING_SYSTEM.md` | Apr 13 | Cursor Cloud |
| `docs/dev_onboarding.md` | Apr 13 | Cursor Cloud |
| `CURSOR_SESSION_SUMMARY_APR13.md` | Apr 13 | **This document** |

---

## Critical Warnings

1. **Never analyze data without stating the source.** `alpha_engine/data/closed_picks.json` and `dashboard_data.json` tell fundamentally different stories.
2. **Mercury's outputs are untrustworthy.** Do not implement code without verifying file paths exist.
3. **"Proven edge" strategies decay fast.** `st_fear_greed_contrarian` went from 83% day-WR to PF 0.68 in 48 hours (per Agent A). Static rankings are unreliable.
4. **No single metric tells the story.** Always report: WR + PF + bootstrap CI + data source + exit_reason filter applied.

---

*Last updated: April 13, 2026 7:55 PM EDT*
